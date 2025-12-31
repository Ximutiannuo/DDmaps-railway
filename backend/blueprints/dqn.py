"""
DQN 相关 Blueprint
"""
from flask import Blueprint, request, jsonify
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state
# 从服务层导入
from backend.services.path_planning_service import (
    get_node_by_id,
    calculate_efficient_path,
    serialize_path_edges
)
from backend.utils.logger import logger
import traceback

bp = Blueprint('dqn', __name__, url_prefix='/api/dqn')

# 尝试导入 PyTorch 和 DQN 相关模块
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None

# 从服务层导入 DQN 规划器
from backend.services.dqn_service import ensure_dqn_planner


def check_torch_available():
    """运行时检测 PyTorch 是否可用（支持动态安装后检测）"""
    global TORCH_AVAILABLE, torch, nn
    try:
        # 如果之前检测失败，尝试重新导入
        if not TORCH_AVAILABLE or torch is None:
            import torch as _torch
            from torch import nn as _nn
            torch = _torch
            nn = _nn
            TORCH_AVAILABLE = True
            logger.info("PyTorch 运行时检测成功")
        return TORCH_AVAILABLE
    except ImportError:
        TORCH_AVAILABLE = False
        torch = None
        nn = None
        return False


@bp.route('/status', methods=['GET'])
@api_handler
def dqn_status():
    """查看 DQN 功能状态"""
    # 运行时检测 PyTorch 是否可用
    available = check_torch_available()
    try:
        planner = ensure_dqn_planner()
        trained = bool(planner and getattr(planner, 'is_trained', False))
        device = str(getattr(planner, 'device', 'cpu')) if trained else None
    except RuntimeError:
        trained = False
        device = None
    
    return jsonify({
        'success': True,
        'available': available,
        'trained': trained,
        'device': device
    })


@bp.route('/train', methods=['POST'])
@api_handler
def dqn_train():
    """使用行驶时间数据库训练 DQN"""
    try:
        # 运行时检测 PyTorch 是否可用
        if not check_torch_available():
            return jsonify({'success': False, 'message': '当前环境未安装 PyTorch，请先运行 pip install torch。如果已安装，请重启应用。'}), 500
        
        payload = request.json or {}
        records = payload.get('records')
        if not records:
            records = system_state.get('travel_time_database', [])
        
        if not records:
            return jsonify({
                'success': False,
                'message': '训练数据为空。请先收集一些行驶时间记录，或通过导入功能添加训练数据。'
            }), 400
        
        epochs = int(payload.get('epochs', 5))
        batch_size = int(payload.get('batch_size', 64))
        gamma = payload.get('gamma')
        
        logger.info(f"开始DQN训练: {len(records)} 条记录, {epochs} 轮, batch_size={batch_size}")
        
        planner = ensure_dqn_planner()
        metrics = planner.train_from_records(records, epochs=epochs, batch_size=batch_size, gamma=gamma)
        
        logger.info(f"DQN训练完成: {metrics}")
        
        return jsonify({
            'success': True,
            'message': 'DQN 训练完成',
            'metrics': metrics
        })
    except ValueError as exc:
        logger.error(f"DQN训练参数错误: {str(exc)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(exc)}), 400
    except RuntimeError as exc:
        logger.error(f"DQN训练运行时错误: {str(exc)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(exc)}), 500
    except Exception as exc:
        logger.error(f"DQN训练未知错误: {str(exc)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'训练过程中发生错误: {str(exc)}。请检查训练数据格式是否正确，确保数据包含 path_nodes 和 target_node 字段。'
        }), 500


@bp.route('/route', methods=['POST'])
@api_handler
def dqn_route():
    """使用 DQN 规划最优路径"""
    # 运行时检测 PyTorch 是否可用
    if not check_torch_available():
        return jsonify({'success': False, 'message': '当前环境未安装 PyTorch，请先运行 pip install torch。如果已安装，请重启应用。'}), 500
    
    data = request.json or {}
    start_node = data.get('start_node')
    target_node = data.get('target_node')
    epsilon = float(data.get('epsilon', 0.0))
    
    if not start_node or not target_node:
        return jsonify({'success': False, 'message': '请提供 start_node 和 target_node'}), 400
    
    if not get_node_by_id(start_node) or not get_node_by_id(target_node):
        return jsonify({'success': False, 'message': '起点或终点节点不存在'}), 404
    
    try:
        planner = ensure_dqn_planner()
    except RuntimeError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 500
    
    if not planner.is_trained:
        return jsonify({'success': False, 'message': 'DQN 尚未训练，请先调用 /api/dqn/train'}), 400
    
    route_edges = planner.predict_route(start_node, target_node, epsilon=epsilon)
    if not route_edges:
        fallback_path = calculate_efficient_path(start_node, target_node, None)
        serialized = serialize_path_edges(fallback_path)
        return jsonify({
            'success': True,
            'message': 'DQN 未能找到有效路径，已回退到传统 Dijkstra 结果',
            'route_edges': serialized,
            'edge_count': len(serialized),
            'planner': 'dijkstra'
        })
    
    return jsonify({
        'success': True,
        'message': 'DQN 路径规划成功',
        'route_edges': route_edges,
        'edge_count': len(route_edges),
        'planner': 'dqn'
    })

