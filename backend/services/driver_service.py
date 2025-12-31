"""
司机服务模块
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from backend.models.system_state import system_state
from backend.services.path_planning_service import (
    calculate_efficient_path,
    get_node_by_id,
    get_vehicle_speed_kmph,
    estimate_efficiency_score,
    estimate_travel_minutes,
    build_node_sequence_from_path,
    serialize_path_edges
)
from backend.utils.logger import logger


def register_driver(driver_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """注册或更新司机"""
    driver_id = driver_data.get('driver_id') or driver_data.get('id')
    if not driver_id:
        drivers = system_state.get('drivers', {})
        driver_id = f"D{len(drivers) + 1}"
    
    name = driver_data.get('name', f'司机{driver_id}')
    vehicle_type = driver_data.get('vehicle_type', '渣土车')
    vehicle_types = system_state.get('vehicle_types', {})
    if vehicle_type not in vehicle_types:
        logger.warning(f'不支持的车辆类型: {vehicle_type}')
        return None
    
    drivers = system_state.get('drivers', {})
    driver_info = drivers.get(driver_id, {})
    driver_info.update({
        'driver_id': driver_id,
        'name': name,
        'vehicle_type': vehicle_type,
        'weight': float(driver_data.get('weight', driver_info.get('weight', 20))),
        'width': float(driver_data.get('width', driver_info.get('width', 3))),
        'contact': driver_data.get('contact') or driver_info.get('contact'),
        'last_active': datetime.now().isoformat()
    })
    
    custom_speed_value = driver_data.get('custom_speed_kmph')
    if custom_speed_value is not None:
        try:
            custom_speed_value = float(custom_speed_value)
            if custom_speed_value <= 0:
                custom_speed_value = None
        except (TypeError, ValueError):
            custom_speed_value = None
    
    if custom_speed_value is not None:
        driver_info['custom_speed_kmph'] = custom_speed_value
    elif 'custom_speed_kmph' not in driver_info:
        driver_info['custom_speed_kmph'] = get_vehicle_speed_kmph(vehicle_type)
    
    if driver_data.get('default_start_node'):
        driver_info['default_start_node'] = driver_data.get('default_start_node')
    if driver_data.get('default_target_node'):
        driver_info['default_target_node'] = driver_data.get('default_target_node')
    
    drivers[driver_id] = driver_info
    system_state.set('drivers', drivers)
    
    logger.info(f'注册司机: {driver_id}, 姓名: {name}')
    return driver_info


def get_driver_by_id(driver_id: str) -> Optional[Dict[str, Any]]:
    """根据ID获取司机"""
    drivers = system_state.get('drivers', {})
    return drivers.get(driver_id)


def get_all_drivers() -> List[Dict[str, Any]]:
    """获取所有司机"""
    drivers = system_state.get('drivers', {})
    return list(drivers.values())


def remember_driver_route(driver_id: str, route_record: Dict[str, Any]):
    """记录司机路线请求"""
    driver_routes = system_state.get('driver_routes', {})
    if driver_id not in driver_routes:
        driver_routes[driver_id] = []
    driver_routes[driver_id].append(route_record)
    
    max_routes = system_state.get('MAX_DRIVER_ROUTES', 20)
    if len(driver_routes[driver_id]) > max_routes:
        driver_routes[driver_id] = driver_routes[driver_id][-max_routes:]
    
    system_state.set('driver_routes', driver_routes)


def calculate_driver_route_preview(
    driver_id: str,
    start_node_id: Optional[str] = None,
    target_node_id: Optional[str] = None,
    vehicle_data: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """计算司机路线预览（不创建实际车辆）"""
    drivers = system_state.get('drivers', {})
    driver = drivers.get(driver_id)
    if not driver:
        logger.warning(f'司机 {driver_id} 未注册')
        return None
    
    vehicle_data = vehicle_data or {}
    start_node_id = start_node_id or driver.get('default_start_node')
    target_node_id = target_node_id or driver.get('default_target_node')
    
    if not start_node_id:
        logger.warning('请提供起点 start_node')
        return None
    if not target_node_id:
        logger.warning('请提供目标节点 target_node')
        return None
    
    start_node = get_node_by_id(start_node_id)
    if not start_node:
        logger.warning(f'起点 {start_node_id} 不存在')
        return None
    target_node = get_node_by_id(target_node_id)
    if not target_node:
        logger.warning(f'目标节点 {target_node_id} 不存在')
        return None
    
    vehicle_type = vehicle_data.get('vehicle_type', driver.get('vehicle_type', '渣土车'))
    vehicle_types = system_state.get('vehicle_types', {})
    if vehicle_type not in vehicle_types:
        logger.warning(f'不支持的车辆类型: {vehicle_type}')
        return None
    
    weight = float(vehicle_data.get('weight', driver.get('weight', 20)))
    width = float(vehicle_data.get('width', driver.get('width', 3)))
    custom_speed = vehicle_data.get('custom_speed_kmph', driver.get('custom_speed_kmph'))
    
    try:
        custom_speed = float(custom_speed) if custom_speed is not None else None
    except (TypeError, ValueError):
        custom_speed = None
    if custom_speed is not None and custom_speed <= 0:
        custom_speed = None
    
    vehicle_template = {
        'id': f'driver-{driver_id}',
        'type': vehicle_type,
        'weight': weight,
        'width': width,
        'target_node': target_node_id,
        'start_node': start_node_id,
        'custom_speed_kmph': custom_speed
    }
    
    path = calculate_efficient_path(start_node_id, target_node_id, vehicle_template)
    
    if not path:
        logger.warning('无法找到有效路径，请尝试其他节点或检查道路状态')
        return None
    
    efficiency = estimate_efficiency_score(path)
    estimated_minutes = estimate_travel_minutes(
        path,
        vehicle_type,
        custom_speed_kmph=custom_speed,
        start_node=start_node_id,
        target_node=target_node_id
    )
    node_sequence = build_node_sequence_from_path(start_node_id, path)
    serialized_edges = serialize_path_edges(path)
    
    route_record = {
        'driver_id': driver_id,
        'start_node': start_node_id,
        'target_node': target_node_id,
        'vehicle_type': vehicle_type,
        'weight': weight,
        'width': width,
        'requested_at': datetime.now().isoformat(),
        'efficiency_score': efficiency,
        'estimated_minutes': estimated_minutes,
        'path_edges': serialized_edges,
        'path_nodes': node_sequence,
        'custom_speed_kmph': custom_speed
    }
    
    if custom_speed is not None:
        driver['custom_speed_kmph'] = custom_speed
    remember_driver_route(driver_id, route_record)
    driver['last_active'] = route_record['requested_at']
    driver['default_start_node'] = start_node_id
    driver['default_target_node'] = target_node_id
    drivers[driver_id] = driver
    system_state.set('drivers', drivers)
    
    return route_record

