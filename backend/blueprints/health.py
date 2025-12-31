"""
健康检查 Blueprint
"""
import sys
import os
import json
from flask import Blueprint, jsonify
from backend.utils.health_check import health_check
from backend.utils.api_handler import api_handler
from backend.config import Config

bp = Blueprint('health', __name__, url_prefix='/api')

@bp.route('/health', methods=['GET'])
@api_handler
def api_health():
    """系统健康检查API"""
    try:
        health = health_check()
        # 只有在 unhealthy 时才返回 503，degraded 时返回 200（但包含警告信息）
        status_code = 200 if health['status'] in ('healthy', 'degraded') else 503
        return jsonify(health), status_code
    except Exception as e:
        # 如果健康检查本身失败，返回 503
        from backend.utils.logger import logger
        logger.error(f"健康检查异常: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'error': str(e)
        }), 503


@bp.route('/debug-checkpoint', methods=['GET'])
@api_handler
def debug_checkpoint():
    """调试端点：查看检查点文件详情"""
    result = {
        'config': {
            'checkpoint_file': str(Config.CHECKPOINT_FILE) if Config.CHECKPOINT_FILE else None,
            'checkpoint_file_exists': os.path.exists(Config.CHECKPOINT_FILE) if Config.CHECKPOINT_FILE else False,
            'base_dir': str(Config.BASE_DIR),
        },
        'checkpoint_content': None,
        'error': None
    }
    
    try:
        if Config.CHECKPOINT_FILE and os.path.exists(Config.CHECKPOINT_FILE):
            with open(Config.CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                content = json.load(f)
            result['checkpoint_content'] = {
                'version': content.get('version'),
                'timestamp': content.get('timestamp'),
                'node_count': len(content.get('nodes', [])),
                'edge_count': len(content.get('edges', [])),
                'has_map_background': content.get('map_background') is not None,
                'keys': list(content.keys())
            }
    except Exception as e:
        result['error'] = str(e)
    
    # 也检查 app.py 中的路径和初始化日志
    try:
        import app
        result['app_py'] = {
            'CHECKPOINT_FILE': getattr(app, 'CHECKPOINT_FILE', 'NOT_DEFINED'),
            'BASE_DIR': getattr(app, 'BASE_DIR', 'NOT_DEFINED'),
        }
        # 获取初始化日志
        result['init_log'] = getattr(app, '_init_log', ['未找到初始化日志'])
    except Exception as e:
        result['app_py_error'] = str(e)
    
    return jsonify(result)


@bp.route('/python-version', methods=['GET'])
@api_handler
def python_version():
    """检查应用使用的 Python 版本和 PyTorch 状态"""
    try:
        import torch
        torch_version = torch.__version__
        torch_available = True
    except ImportError:
        torch_version = None
        torch_available = False
    
    return jsonify({
        'success': True,
        'python_version': sys.version,
        'python_version_info': {
            'major': sys.version_info.major,
            'minor': sys.version_info.minor,
            'micro': sys.version_info.micro
        },
        'python_executable': sys.executable,
        'torch_available': torch_available,
        'torch_version': torch_version,
        'message': f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'
    })


@bp.route('/health-check-detail', methods=['GET'])
@api_handler
def health_check_detail():
    """
    详细的健康检查，包括服务层和 Blueprint 状态
    
    用于验证服务层和 Blueprint 在生产环境中的稳定性
    """
    result = {
        'success': True,
        'service_layer': {
            'available': False,
            'modules': {}
        },
        'blueprints': {
            'available': False,
            'modules': {}
        },
        'recommendations': []
    }
    
    # 检查服务层
    try:
        # 尝试导入主要服务模块
        service_modules = {
            'path_planning_service': [
                'calculate_direction',
                'get_node_by_id',
                'calculate_efficient_path',
            ],
            'system_service': [
                'initialize_system',
                'update_monitor_data',
                'reroute_vehicles',
            ],
            'vehicle_service': [
                'update_vehicle_positions',
            ],
        }
        
        all_services_ok = True
        for module_name, functions in service_modules.items():
            try:
                module = __import__(f'backend.services.{module_name}', fromlist=[''])
                module_status = {}
                for func_name in functions:
                    if hasattr(module, func_name):
                        module_status[func_name] = 'available'
                    else:
                        module_status[func_name] = 'missing'
                        all_services_ok = False
                result['service_layer']['modules'][module_name] = module_status
            except ImportError as e:
                result['service_layer']['modules'][module_name] = {'error': str(e)}
                all_services_ok = False
        
        result['service_layer']['available'] = all_services_ok
        
        if not all_services_ok:
            result['recommendations'].append('部分服务层模块不可用，请检查导入错误')
        
    except Exception as e:
        result['service_layer']['error'] = str(e)
        result['recommendations'].append(f'检查服务层时出错: {str(e)}')
    
    # 检查 Blueprint
    try:
        blueprint_modules = [
            'health', 'vehicles', 'drivers', 'nodes', 'edges',
            'monitor', 'dispatch', 'system'
        ]
        
        all_blueprints_ok = True
        for bp_name in blueprint_modules:
            try:
                module = __import__(f'backend.blueprints.{bp_name}', fromlist=[''])
                if hasattr(module, 'bp'):
                    result['blueprints']['modules'][bp_name] = {
                        'available': True,
                        'name': module.bp.name
                    }
                else:
                    result['blueprints']['modules'][bp_name] = {'available': False, 'error': '未找到 bp 属性'}
                    all_blueprints_ok = False
            except ImportError as e:
                result['blueprints']['modules'][bp_name] = {'available': False, 'error': str(e)}
                all_blueprints_ok = False
        
        result['blueprints']['available'] = all_blueprints_ok
        
        if not all_blueprints_ok:
            result['recommendations'].append('部分 Blueprint 模块不可用，请检查导入错误')
            
    except Exception as e:
        result['blueprints']['error'] = str(e)
        result['recommendations'].append(f'检查 Blueprint 时出错: {str(e)}')
    
    # 最终建议
    if result['service_layer']['available'] and result['blueprints']['available']:
        result['recommendations'].append('✓ 服务层和 Blueprint 均正常，可以考虑删除 app.py 中的后备实现代码')
    else:
        result['recommendations'].append('✗ 发现问题，建议修复后再删除后备代码')
    
    return jsonify(result)


