"""
车辆服务模块
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from backend.models.system_state import system_state
from backend.services.path_planning_service import (
    calculate_efficient_path,
    get_node_by_id,
    get_vehicle_speed_kmph,
    estimate_efficiency_score,
    get_edge_length_m
)
from backend.utils.logger import logger


def update_vehicle_positions():
    """更新车辆位置（根据实际距离与速度计算）"""
    now = datetime.now()
    vehicles = system_state.get('vehicles', [])
    
    for vehicle in vehicles:
        # 如果车辆处于GPS模式，跳过自动位置更新
        if vehicle.get('position_mode') == 'gps':
            continue
        vehicle_type = vehicle.get('type', '渣土车')
        speed_kmph = vehicle.get('speed_kmph') or get_vehicle_speed_kmph(vehicle_type)
        base_speed_mps = speed_kmph * 1000.0 / 3600.0  # km/h -> m/s

        last_update_str = vehicle.get('last_update_time')
        try:
            last_update = datetime.fromisoformat(last_update_str) if last_update_str else None
        except (TypeError, ValueError):
            last_update = None

        if last_update is None:
            # 第一次更新，初始化时间戳，但不移动车辆，确保车辆从起点开始显示
            vehicle['last_update_time'] = now.isoformat()
            # 确保 progress 为 0，车辆位置在起点
            vehicle['progress'] = 0.0  # 强制设置为0
            
            # 确保位置在正确的起点
            # 优先使用车辆的 start_node（应该是路线规划的起点）
            vehicle_start_node_id = vehicle.get('start_node')
            if vehicle_start_node_id:
                start_node_obj = get_node_by_id(vehicle_start_node_id)
                if start_node_obj:
                    vehicle['current_position'] = {'x': start_node_obj['x'], 'y': start_node_obj['y']}
            # 如果没有 start_node，使用路径第一条边的起点作为后备
            elif vehicle.get('current_path') and len(vehicle['current_path']) > 0:
                first_edge = vehicle['current_path'][0]
                first_edge_start_node = get_node_by_id(first_edge['start_node'])
                if first_edge_start_node:
                    vehicle['current_position'] = {'x': first_edge_start_node['x'], 'y': first_edge_start_node['y']}
            continue

        delta_seconds = max((now - last_update).total_seconds(), 0.0)
        vehicle['last_update_time'] = now.isoformat()

        if delta_seconds <= 0:
            continue

        if vehicle.get('status') != 'moving' or not vehicle.get('current_path'):
            continue

        remaining_time = delta_seconds
        # 确保进度存在
        vehicle['progress'] = float(vehicle.get('progress', 0.0))

        while remaining_time > 0 and vehicle.get('current_path'):
            current_edge = vehicle['current_path'][0]
            start_node = get_node_by_id(current_edge['start_node'])
            end_node = get_node_by_id(current_edge['end_node'])
            
            # 调试信息：记录边的信息
            edge_id = current_edge.get('id', 'unknown')
            dx = end_node['x'] - start_node['x'] if (start_node and end_node) else 0
            dy = end_node['y'] - start_node['y'] if (start_node and end_node) else 0
            is_vertical = abs(dx) < abs(dy) if (start_node and end_node) else False
            length_m = get_edge_length_m(current_edge)
            
            if not (start_node and end_node):
                # 无法定位节点，跳过该道路
                from backend.utils.logger import logger
                logger.warning(f'⚠️ [车辆移动] 车辆 {vehicle["id"]}: 无法找到节点，跳过边 {edge_id}, '
                             f'start_node={current_edge.get("start_node")}, end_node={current_edge.get("end_node")}')
                vehicle['current_path'].pop(0)
                vehicle['progress'] = 0.0
                continue
            
            # 调试信息已移除（之前用于排查车辆移动问题）

            length_m = get_edge_length_m(current_edge)
            if length_m <= 0:
                length_m = 1.0

            # 已经走过的距离（米）
            progress = max(0.0, min(1.0, float(vehicle.get('progress', 0.0))))
            distance_travelled_m = progress * length_m
            remaining_distance_m = max(length_m - distance_travelled_m, 0.0)

            # 结合道路与节点拥堵程度调整速度
            edge_penalty = max(0.3, current_edge.get('congestion_coeff', 1.0))
            node_penalty = 1.0
            congestion_penalty_map = {1: 1.2, 2: 1.5, 3: 2.0}
            node_congestion = system_state.get('node_congestion', {})
            start_congestion = node_congestion.get(current_edge['start_node'], 0)
            end_congestion = node_congestion.get(current_edge['end_node'], 0)
            node_penalty = max(
                congestion_penalty_map.get(start_congestion, 1.0),
                congestion_penalty_map.get(end_congestion, 1.0)
            )
            total_penalty = max(0.3, edge_penalty * node_penalty)

            effective_speed_mps = base_speed_mps / total_penalty
            if effective_speed_mps <= 0:
                effective_speed_mps = base_speed_mps * 0.1 or 0.01

            time_needed = remaining_distance_m / effective_speed_mps if remaining_distance_m > 0 else 0.0

            if time_needed > remaining_time:
                # 只能走部分路段
                distance_step = effective_speed_mps * remaining_time
                new_distance = distance_travelled_m + distance_step
                vehicle['progress'] = max(0.0, min(1.0, new_distance / length_m))
                remaining_time = 0.0
            else:
                # 可以走完整条道路
                vehicle['current_path'].pop(0)
                vehicle['progress'] = 0.0
                vehicle['current_position'] = {'x': end_node['x'], 'y': end_node['y']}
                remaining_time -= time_needed
                if vehicle['current_path']:
                    continue
                # 车辆已到达目的地，但等待司机确认到达
                # 不自动设置 arrival_time，只有司机点击"确认到达"时才设置
                # 这样可以确保行驶时间是从"提交为实际车辆"到"确认到达"的准确时间
                vehicle['status'] = 'arrived'  # 标记为已到达，但等待司机确认
                # 清除 current_path（用于移动的路径），但保留 planned_path_edges 和 planned_path_nodes（用于确认到达时计算）
                vehicle['current_path'] = []  # 清除当前路径，防止继续移动
                # 保留 planned_path_edges 和 planned_path_nodes，供确认到达时使用
                # vehicle['arrival_time'] = now.isoformat()  # 移除自动设置，由司机确认到达时设置
                break
                
            # 更新当前位置
            ratio = max(0.0, min(1.0, float(vehicle.get('progress', 0.0))))
            vehicle['current_position'] = {
                'x': start_node['x'] + (end_node['x'] - start_node['x']) * ratio,
                'y': start_node['y'] + (end_node['y'] - start_node['y']) * ratio
            }
    
    system_state.set('vehicles', vehicles)


def create_vehicle(vehicle_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """创建新车辆"""
    vehicle_id = vehicle_data.get('id')
    if not vehicle_id:
        vehicle_counter = system_state.get('vehicle_counter', 1)
        vehicle_id = f"V{vehicle_counter}"
        system_state.set('vehicle_counter', vehicle_counter + 1)
    
    vehicle_type = vehicle_data.get('type', '渣土车')
    vehicle_types = system_state.get('vehicle_types', {})
    if vehicle_type not in vehicle_types:
        logger.warning(f'不支持的车辆类型: {vehicle_type}')
        return None
    
    start_node_id = vehicle_data.get('start_node')
    if not start_node_id:
        nodes = system_state.get('nodes', [])
        start_node = next((n for n in nodes if n.get('type') == 'start'), None)
        if not start_node:
            logger.warning('未找到起始节点')
            return None
        start_node_id = start_node['id']
    
    start_node = get_node_by_id(start_node_id)
    if not start_node:
        logger.warning(f'起始节点 {start_node_id} 不存在')
        return None
    
    target_node_id = vehicle_data.get('target_node')
    if not target_node_id:
        logger.warning('请提供目标节点 target_node')
        return None
    
    target_node = get_node_by_id(target_node_id)
    if not target_node:
        logger.warning(f'目标节点 {target_node_id} 不存在')
        return None
    
    vehicle_template = {
        'id': vehicle_id,
        'type': vehicle_type,
        'weight': float(vehicle_data.get('weight', 20)),
        'width': float(vehicle_data.get('width', 3)),
        'target_node': target_node_id,
        'start_node': start_node_id
    }
    
    path = calculate_efficient_path(start_node_id, target_node_id, vehicle_template)
    
    if not path:
        logger.warning('无法找到有效路径（可能被封路或限制）')
        return None
    
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
        'status': 'moving',
        'estimated_time': len(path) * 2.0,  # 简单估算
        'progress': 0,
        'efficiency_score': estimate_efficiency_score(path),
        'created_time': datetime.now().isoformat(),
        'last_update_time': datetime.now().isoformat()
    }
    
    vehicles = system_state.get('vehicles', [])
    vehicles.append(new_vehicle)
    system_state.set('vehicles', vehicles)
    
    logger.info(f'创建车辆: {vehicle_id}, 类型: {vehicle_type}, 起点: {start_node_id}, 目标: {target_node_id}')
    return new_vehicle


def get_vehicle_by_id(vehicle_id: str) -> Optional[Dict[str, Any]]:
    """根据ID获取车辆"""
    vehicles = system_state.get('vehicles', [])
    return next((v for v in vehicles if v.get('id') == vehicle_id), None)


def get_all_vehicles() -> List[Dict[str, Any]]:
    """获取所有车辆"""
    return system_state.get('vehicles', []).copy()

