"""
道路服务模块
"""
from typing import Dict, Any, Optional, List
from backend.models.system_state import system_state
from backend.services.path_planning_service import get_node_by_id, calculate_direction
from backend.services.system_service import update_monitor_data, reroute_vehicles, refresh_edge_geometry
from backend.utils.logger import logger


def create_edge(edge_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """创建新道路"""
    edges = system_state.get('edges', [])
    edge_id = edge_data.get('id') or f"E{len(edges) + 1}"
    
    start_node = get_node_by_id(edge_data.get('start_node'))
    end_node = get_node_by_id(edge_data.get('end_node'))
    
    if not start_node or not end_node:
        logger.warning('起点或终点节点不存在')
        return None
    
    import math
    dx = end_node['x'] - start_node['x']
    dy = end_node['y'] - start_node['y']
    actual_length = (dx**2 + dy**2)**0.5
    length_input = edge_data.get('length')
    if length_input is not None:
        try:
            length_m = float(length_input)
        except (TypeError, ValueError):
            length_m = actual_length
    else:
        length_m = actual_length
    
    default_direction = calculate_direction(start_node, end_node)
    
    new_edge = {
        'id': edge_id,
        'start_node': edge_data['start_node'],
        'end_node': edge_data['end_node'],
        'length': float(length_m),
        'length_m': float(length_m),
        'actual_length': actual_length,
        'max_weight': float(edge_data.get('max_weight', 50)),
        'max_width': float(edge_data.get('max_width', 5)),
        'is_available': True,
        'congestion_coeff': 1.0,
        'direction': edge_data.get('direction', default_direction)
    }
    
    edges.append(new_edge)
    system_state.set('edges', edges)
    
    edge_directions = system_state.get('edge_directions', {})
    edge_directions[edge_id] = new_edge['direction']
    system_state.set('edge_directions', edge_directions)
    
    refresh_edge_geometry()
    
    monitor_data = system_state.get('monitor_data', {})
    monitor_data.setdefault('edge_congestion', {})[new_edge['id']] = new_edge['congestion_coeff']
    monitor_data.setdefault('edge_available', {})[new_edge['id']] = new_edge['is_available']
    system_state.set('monitor_data', monitor_data)
    
    logger.info(f'创建道路: {edge_id}, 起点: {edge_data["start_node"]}, 终点: {edge_data["end_node"]}')
    return new_edge


def set_edge_status(edge_id: str, status: str) -> bool:
    """设置道路状态：normal(正常)、congested(拥堵)、construction(占道施工)、closed(封闭)"""
    edges = system_state.get('edges', [])
    edge = next((e for e in edges if e['id'] == edge_id), None)
    if not edge:
        logger.warning(f'道路 {edge_id} 不存在')
        return False
    
    valid_statuses = ['normal', 'congested', 'construction', 'closed']
    if status not in valid_statuses:
        logger.warning(f'状态必须是: {", ".join(valid_statuses)}')
        return False
    
    edge_status = system_state.get('edge_status', {})
    custom_congestion_edges = system_state.get('custom_congestion_edges', set())
    
    if status == 'normal':
        if edge_id in edge_status:
            del edge_status[edge_id]
        if edge_id in custom_congestion_edges:
            custom_congestion_edges.remove(edge_id)
    else:
        edge_status[edge_id] = status
        if status == 'congested':
            custom_congestion_edges.add(edge_id)
        elif status in ['construction', 'closed']:
            if edge_id in custom_congestion_edges:
                custom_congestion_edges.remove(edge_id)
    
    system_state.set('edge_status', edge_status)
    system_state.set('custom_congestion_edges', custom_congestion_edges)
    
    update_monitor_data()
    reroute_vehicles(affected_edges_ids=[edge_id])
    
    logger.info(f'设置道路状态: {edge_id} -> {status}')
    return True


def set_edge_direction(edge_id: str, direction: str) -> bool:
    """设置道路方向"""
    edges = system_state.get('edges', [])
    edge = next((e for e in edges if e['id'] == edge_id), None)
    if not edge:
        logger.warning(f'道路 {edge_id} 不存在')
        return False
    
    # DIRECTION_TYPES 应该从配置或常量模块导入
    DIRECTION_TYPES = {
        'two-way': {'name': '双向', 'value': 'two-way'},
        'north': {'name': '北向', 'value': 'north'},
        'south': {'name': '南向', 'value': 'south'},
        'east': {'name': '东向', 'value': 'east'},
        'west': {'name': '西向', 'value': 'west'},
        'north-east': {'name': '东北向', 'value': 'north-east'},
        'north-west': {'name': '西北向', 'value': 'north-west'},
        'south-east': {'name': '东南向', 'value': 'south-east'},
        'south-west': {'name': '西南向', 'value': 'south-west'},
    }
    
    if direction not in DIRECTION_TYPES:
        logger.warning(f'方向参数必须是: {", ".join(DIRECTION_TYPES.keys())}')
        return False
    
    edge['direction'] = direction
    edge_directions = system_state.get('edge_directions', {})
    edge_directions[edge_id] = direction
    system_state.set('edge_directions', edge_directions)
    
    reroute_vehicles(affected_edges_ids=[edge_id])
    
    logger.info(f'设置道路方向: {edge_id} -> {direction}')
    return True


def get_all_edges() -> List[Dict[str, Any]]:
    """获取所有道路"""
    return system_state.get('edges', [])

