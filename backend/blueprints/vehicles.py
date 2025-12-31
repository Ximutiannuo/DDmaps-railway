"""
车辆相关 Blueprint
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state
from backend.config import Config

bp = Blueprint('vehicles', __name__, url_prefix='/api')

# 从服务层导入
from backend.services.path_planning_service import (
    get_vehicle_speed_kmph as _get_vehicle_speed_kmph,
    get_node_by_id,
    calculate_efficient_path
)

# 尝试导入 update_vehicle_positions，如果失败则使用占位符
try:
    from backend.services.vehicle_service import update_vehicle_positions as _update_vehicle_positions
except ImportError:
    # 如果导入失败，定义一个空函数
    def _update_vehicle_positions():
        pass

def get_vehicle_speed_kmph(vehicle_type):
    """获取车辆速度（从服务层导入）"""
    return _get_vehicle_speed_kmph(vehicle_type)

@bp.route('/vehicles/<vehicle_id>/position', methods=['POST'])
@api_handler
def update_vehicle_position(vehicle_id):
    """更新车辆位置（GPS模式）"""
    data = request.json or {}
    x = data.get('x')
    y = data.get('y')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    mode = data.get('mode', 'gps')
    
    if x is None or y is None:
        return jsonify({
            'success': False,
            'message': '请提供车辆位置坐标 (x, y)'
        }), 400
    
    try:
        x = float(x)
        y = float(y)
    except (TypeError, ValueError):
        return jsonify({
            'success': False,
            'message': '坐标格式不正确'
        }), 400
    
    with system_state.lock:
        vehicles = system_state.get('vehicles', [])
        vehicle = next((v for v in vehicles if v.get('id') == vehicle_id), None)
        
        if not vehicle:
            return jsonify({
                'success': False,
                'message': f'车辆 {vehicle_id} 不存在'
            }), 404
        
        # 更新车辆位置
        vehicle['current_position'] = {'x': x, 'y': y}
        vehicle['position_mode'] = mode  # 标记为GPS模式，跳过自动位置更新
        
        # 如果提供了GPS坐标，也保存
        if latitude is not None and longitude is not None:
            vehicle['gps_latitude'] = float(latitude)
            vehicle['gps_longitude'] = float(longitude)
        
        # 更新最后更新时间
        vehicle['last_update_time'] = datetime.now().isoformat()
        
        system_state.set('vehicles', vehicles)
    
    return jsonify({
        'success': True,
        'message': '车辆位置已更新',
        'vehicle': vehicle
    })

@bp.route('/vehicles', methods=['GET'])
@api_handler
def get_vehicles():
    """获取车辆列表"""
    # 使用装饰器中的 with_lock，但这里需要直接访问 system_state
    with system_state.lock:
        if Config.ON_PYTHONANYWHERE:
            try:
                _update_vehicle_positions()  # 使用导入的函数
            except (NameError, TypeError):
                # 如果函数未定义或为 None，跳过更新
                pass
        return jsonify({
            'success': True,
            'vehicles': system_state.get('vehicles', []).copy()  # 返回副本避免并发修改
        })

@bp.route('/vehicles', methods=['POST'])
@api_handler
def add_vehicle():
    """添加车辆（使用高效路径规划）"""
    data = request.json or {}
    
    with system_state.lock:
        # 生成车辆ID
        vehicle_counter = system_state.get('vehicle_counter', 1)
        vehicle_id = data.get('id') or f"V{vehicle_counter}"
        system_state.set('vehicle_counter', vehicle_counter + 1)
        
        # 车辆类型
        vehicle_type = data.get('type', '渣土车')
        vehicle_types = system_state.get('vehicle_types', {})
        if vehicle_type not in vehicle_types:
            return jsonify({'success': False, 'message': f'不支持的车辆类型: {vehicle_type}'}), 400
        
        # 查找起始节点
        start_node_id = data.get('start_node')
        if not start_node_id:
            # 如果没有指定起点，默认使用第一个起点节点
            nodes = system_state.get('nodes', [])
            start_node = next((n for n in nodes if n.get('type') == 'start'), None)
            if not start_node:
                return jsonify({'success': False, 'message': '未找到起始节点'}), 400
            start_node_id = start_node['id']
        
        # 验证起点节点是否存在
        start_node = get_node_by_id(start_node_id)
        if not start_node:
            return jsonify({'success': False, 'message': f'起始节点 {start_node_id} 不存在'}), 400
        
        # 计算路径（使用车辆参数）
        target_node_id = data.get('target_node')
        if not target_node_id:
            return jsonify({'success': False, 'message': '请提供目标节点 target_node'}), 400
        
        # 验证目标节点是否存在
        target_node = get_node_by_id(target_node_id)
        if not target_node:
            return jsonify({'success': False, 'message': f'目标节点 {target_node_id} 不存在'}), 400
        
        vehicle_template = {
            'id': vehicle_id,
            'type': vehicle_type,
            'weight': float(data.get('weight', 20)),
            'width': float(data.get('width', 3)),
            'target_node': target_node_id,
            'start_node': start_node_id
        }
        
        path = calculate_efficient_path(start_node_id, target_node_id, vehicle_template)
        
        if not path:
            return jsonify({'success': False, 'message': '无法找到有效路径（可能被封路或限制）'}), 400
        
        # 创建新车辆
        new_vehicle = {
            'id': vehicle_id,
            'type': vehicle_type,
            'speed_kmph': get_vehicle_speed_kmph(vehicle_type),
            'weight': vehicle_template['weight'],
            'width': vehicle_template['width'],
            'target_node': target_node_id,
            'start_node': start_node_id,
            'current_position': {'x': start_node['x'], 'y': start_node['y']},
            'assigned_entrance': start_node_id if start_node.get('type') == 'entrance' else None,
            'current_path': path,
            'status': 'driving',
            'created_at': __import__('datetime').datetime.now().isoformat()
        }
        
        # 添加到车辆列表
        vehicles = system_state.get('vehicles', [])
        vehicles.append(new_vehicle)
        system_state.set('vehicles', vehicles)
        
        return jsonify({
            'success': True,
            'vehicle': new_vehicle,
            'message': f'车辆 {vehicle_id} 添加成功'
        })


@bp.route('/vehicles/<vehicle_id>', methods=['DELETE'])
@api_handler
def delete_vehicle(vehicle_id):
    """删除车辆（中断导航时调用）"""
    with system_state.lock:
        vehicles = system_state.get('vehicles', [])
        
        # 查找车辆
        vehicle_index = next((i for i, v in enumerate(vehicles) if v.get('id') == vehicle_id), None)
        
        if vehicle_index is None:
            return jsonify({
                'success': False,
                'message': f'车辆 {vehicle_id} 不存在'
            }), 404
        
        # 删除车辆
        removed_vehicle = vehicles.pop(vehicle_index)
        system_state.set('vehicles', vehicles)
        
        return jsonify({
            'success': True,
            'message': f'车辆 {vehicle_id} 已删除',
            'vehicle': removed_vehicle
        })


