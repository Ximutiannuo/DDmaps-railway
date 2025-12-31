"""
系统相关 Blueprint（初始化、重置、服务器信息等）
"""
from flask import Blueprint, request, jsonify
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state
from backend.services.system_service import initialize_system
# 使用 system_state.lock 进行线程安全访问
import socket

bp = Blueprint('system', __name__, url_prefix='/api')

@bp.route('/initialize', methods=['POST'])
@api_handler
def initialize():
    """初始化系统"""
    with system_state.lock:
        success = initialize_system()
    return jsonify({
        'success': success,
        'message': '系统初始化成功' if success else '系统初始化失败'
    })

@bp.route('/system/reset', methods=['POST'])
@api_handler
def reset_system():
    """重置系统"""
    with system_state.lock:
        success = initialize_system()
    return jsonify({
        'success': success,
        'message': '系统重置成功' if success else '系统重置失败'
    })

@bp.route('/server-info', methods=['GET'])
@api_handler
def get_server_info():
    """获取服务器信息（包括IP地址）"""
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                return ip
            except Exception:
                return None
    
    local_ip = get_local_ip()
    port = 5000
    
    return jsonify({
        'success': True,
        'local_ip': local_ip,
        'port': port,
        'urls': {
            'localhost': f'http://localhost:{port}',
            'local_ip': f'http://{local_ip}:{port}' if local_ip else None,
            'driver_url': f'http://{local_ip}:{port}/driver' if local_ip else None
        }
    })

@bp.route('/reroute', methods=['POST'])
@api_handler
def api_reroute():
    """手动触发重路由（可选传入 affected_edges 列表）"""
    from backend.services.system_service import reroute_vehicles
    
    data = request.json or {}
    affected = data.get('affected_edges')
    with system_state.lock:
        updated = reroute_vehicles(affected_edges_ids=affected)
    return jsonify({
        'success': True,
        'updated_vehicles': updated,
        'message': f'已重新计算 {len(updated)} 辆车的路径'
    })

@bp.route('/vehicle-types', methods=['GET'])
@api_handler
def get_vehicle_types():
    """获取车辆类型配置"""
    with system_state.lock:
        return jsonify({
            'success': True,
            'vehicle_types': system_state.get('vehicle_types', {})
        })

@bp.route('/vehicle-types/<vehicle_type>', methods=['POST'])
@api_handler
def update_vehicle_type(vehicle_type):
    """更新车辆类型配置"""
    from backend.services.system_service import reroute_vehicles
    
    data = request.json or {}
    with system_state.lock:
        vehicle_types = system_state.get('vehicle_types', {})
        if vehicle_type not in vehicle_types:
            return jsonify({'success': False, 'message': '车辆类型不存在'}), 404
        
        # 更新配置
        if 'speed_kmph' in data:
            vehicle_types[vehicle_type]['speed_kmph'] = float(data['speed_kmph'])
        elif 'speed_factor' in data:
            speed_factor = float(data['speed_factor'])
            vehicle_types[vehicle_type]['speed_factor'] = speed_factor
            vehicle_types[vehicle_type]['speed_kmph'] = speed_factor * 100.0
        if 'speed_kmph' in vehicle_types[vehicle_type]:
            vehicle_types[vehicle_type]['speed_factor'] = (
                vehicle_types[vehicle_type]['speed_kmph'] / 100.0
            )
        if 'can_use_one_way' in data:
            vehicle_types[vehicle_type]['can_use_one_way'] = bool(data['can_use_one_way'])
        if 'can_use_two_way' in data:
            vehicle_types[vehicle_type]['can_use_two_way'] = bool(data['can_use_two_way'])
        
        # 保存更新后的配置
        system_state.set('vehicle_types', vehicle_types)
        
        # 触发重路由（因为道路可用性可能改变）
        reroute_vehicles()
        
        return jsonify({
            'success': True,
            'message': f'车辆类型 {vehicle_type} 配置更新成功'
        })

@bp.route('/vehicle-types', methods=['POST'])
@api_handler
def add_vehicle_type():
    """添加新的车辆类型"""
    data = request.json or {}
    
    vehicle_type = data.get('type')
    if not vehicle_type:
        return jsonify({'success': False, 'message': '请提供车辆类型'}), 400
    
    with system_state.lock:
        vehicle_types = system_state.get('vehicle_types', {})
        if vehicle_type in vehicle_types:
            return jsonify({'success': False, 'message': '车辆类型已存在'}), 400
        
        speed_kmph = data.get('speed_kmph')
        if speed_kmph is None and data.get('speed_factor') is not None:
            try:
                speed_kmph = float(data.get('speed_factor')) * 100.0
            except (TypeError, ValueError):
                speed_kmph = None
        if speed_kmph is None:
            speed_kmph = 30.0
        
        # 添加新类型
        vehicle_types[vehicle_type] = {
            'speed_kmph': float(speed_kmph),
            'speed_factor': float(speed_kmph) / 100.0,
            'can_use_one_way': bool(data.get('can_use_one_way', True)),
            'can_use_two_way': bool(data.get('can_use_two_way', True))
        }
        
        # 保存更新后的配置
        system_state.set('vehicle_types', vehicle_types)
        
        return jsonify({
            'success': True,
            'message': f'车辆类型 {vehicle_type} 添加成功'
        })

@bp.route('/map-background', methods=['GET'])
@api_handler
def get_map_background():
    """获取地图背景"""
    with system_state.lock:
        return jsonify({
            'success': True,
            'map_background': system_state.get('map_background')
        })

@bp.route('/map-background', methods=['POST'])
@api_handler
def set_map_background():
    """设置地图背景"""
    data = request.json or {}
    map_background = data.get('map_background')
    
    if map_background:
        with system_state.lock:
            system_state.set('map_background', map_background)
        
        # 保存检查点，确保地图背景持久化
        from backend.utils.persistence import save_checkpoint
        save_checkpoint()
        
        return jsonify({
            'success': True,
            'message': '地图背景已保存'
        })
    else:
        return jsonify({
            'success': False,
            'message': '请提供地图背景数据'
        }), 400

@bp.route('/map-background', methods=['DELETE'])
@api_handler
def delete_map_background():
    """删除地图背景"""
    with system_state.lock:
        system_state.set('map_background', None)
    return jsonify({
        'success': True,
        'message': '地图背景已清除'
    })

@bp.route('/map-rotation', methods=['GET'])
@api_handler
def get_map_rotation():
    """获取地图旋转角度"""
    with system_state.lock:
        rotation = system_state.get('map_rotation', 0)
    return jsonify({
        'success': True,
        'rotation': float(rotation)
    })

@bp.route('/map-rotation', methods=['POST'])
@api_handler
def set_map_rotation():
    """设置地图旋转角度（度数）"""
    data = request.json or {}
    rotation = data.get('rotation', 0)
    
    try:
        rotation = float(rotation)
        # 标准化到 -360 到 360 度之间
        rotation = rotation % 360
        if rotation > 180:
            rotation -= 360
        elif rotation < -180:
            rotation += 360
    except (TypeError, ValueError):
        return jsonify({
            'success': False,
            'message': '旋转角度必须是数字'
        }), 400
    
    with system_state.lock:
        system_state.set('map_rotation', rotation)
    
    # 保存检查点，确保旋转角度持久化
    from backend.utils.persistence import save_checkpoint
    save_checkpoint()
    
    return jsonify({
        'success': True,
        'rotation': rotation,
        'message': f'地图旋转角度已设置为 {rotation}°'
    })

