"""
节点服务模块
"""
from typing import Dict, Any, Optional, List
from backend.models.system_state import system_state
from backend.services.path_planning_service import get_node_by_id, get_edges_connected_to_node
from backend.services.system_service import update_monitor_data, reroute_vehicles, refresh_edge_geometry
from backend.utils.logger import logger


def create_node(node_data: Dict[str, Any]) -> Dict[str, Any]:
    """创建新节点"""
    nodes = system_state.get('nodes', [])
    node_id = node_data.get('id') or f"N{len(nodes) + 1}"
    
    new_node = {
        'id': node_id,
        'name': node_data.get('name', '未命名节点'),
        'x': float(node_data.get('x', 100)),
        'y': float(node_data.get('y', 100)),
        'type': node_data.get('type', 'crossroad'),
        # GPS坐标（可选）
        'latitude': node_data.get('latitude'),
        'longitude': node_data.get('longitude')
    }
    
    nodes.append(new_node)
    system_state.set('nodes', nodes)
    
    logger.info(f'创建节点: {node_id}, 位置: ({new_node["x"]}, {new_node["y"]})')
    return new_node


def update_node_position(node_id: str, x: float, y: float) -> bool:
    """更新节点位置"""
    node = get_node_by_id(node_id)
    if not node:
        logger.warning(f'节点 {node_id} 不存在')
        return False
    
    node['x'] = float(x)
    node['y'] = float(y)
    
    # 更新相关道路的实际长度
    edges = system_state.get('edges', [])
    for edge in edges:
        if edge['start_node'] == node_id or edge['end_node'] == node_id:
            start_node = get_node_by_id(edge['start_node'])
            end_node = get_node_by_id(edge['end_node'])
            if start_node and end_node:
                import math
                dx = end_node['x'] - start_node['x']
                dy = end_node['y'] - start_node['y']
                new_display_length = (dx**2 + dy**2)**0.5
                old_display_length = edge.get('length_display') or edge.get('actual_length') or new_display_length
                edge['actual_length'] = new_display_length
                edge['length_display'] = float(round(new_display_length, 3))
                if edge.get('length_m') is not None and old_display_length:
                    try:
                        ratio = new_display_length / float(old_display_length)
                    except (TypeError, ValueError, ZeroDivisionError):
                        ratio = 1.0
                    edge['length_m'] = float(max(edge.get('length_m', new_display_length) * ratio, 0.0))
                elif edge.get('length_m') is None:
                    edge['length_m'] = float(new_display_length)
                edge['length'] = float(edge.get('length_m', new_display_length))
    
    system_state.set('edges', edges)
    refresh_edge_geometry()
    
    logger.info(f'更新节点位置: {node_id} -> ({x}, {y})')
    return True


def delete_node(node_id: str) -> bool:
    """删除节点"""
    nodes = system_state.get('nodes', [])
    original_count = len(nodes)
    nodes = [n for n in nodes if n['id'] != node_id]
    
    if len(nodes) == original_count:
        logger.warning(f'节点 {node_id} 不存在')
        return False
    
    system_state.set('nodes', nodes)
    
    # 删除连接到该节点的道路
    edges = system_state.get('edges', [])
    edges = [e for e in edges if e['start_node'] != node_id and e['end_node'] != node_id]
    system_state.set('edges', edges)
    
    logger.info(f'删除节点: {node_id}')
    return True


def set_node_congestion(node_id: str, congestion_level: int) -> bool:
    """设置节点拥堵状态"""
    node = get_node_by_id(node_id)
    if not node:
        logger.warning(f'节点 {node_id} 不存在')
        return False
    
    if congestion_level not in [0, 1, 2, 3]:
        logger.warning(f'拥堵级别必须是 0(正常)、1(轻微)、2(中度) 或 3(严重)')
        return False
    
    node_congestion = system_state.get('node_congestion', {})
    if congestion_level == 0:
        if node_id in node_congestion:
            del node_congestion[node_id]
    else:
        node_congestion[node_id] = congestion_level
    system_state.set('node_congestion', node_congestion)
    
    update_monitor_data()
    
    connected_edges = get_edges_connected_to_node(node_id)
    affected_edge_ids = [e['id'] for e in connected_edges]
    if affected_edge_ids:
        reroute_vehicles(affected_edges_ids=affected_edge_ids)
    
    logger.info(f'设置节点拥堵: {node_id} -> {congestion_level}')
    return True


def set_node_gps_coordinates(node_id: str, latitude: float, longitude: float) -> bool:
    """设置节点的GPS坐标"""
    node = get_node_by_id(node_id)
    if not node:
        logger.warning(f'节点 {node_id} 不存在')
        return False
    
    # 验证GPS坐标范围
    if not (-90 <= latitude <= 90):
        logger.warning(f'纬度超出范围: {latitude}')
        return False
    if not (-180 <= longitude <= 180):
        logger.warning(f'经度超出范围: {longitude}')
        return False
    
    nodes = system_state.get('nodes', [])
    for n in nodes:
        if n['id'] == node_id:
            # 保留两位小数
            n['latitude'] = round(float(latitude), 6)
            n['longitude'] = round(float(longitude), 6)
            break
    
    system_state.set('nodes', nodes)
    logger.info(f'设置节点GPS坐标: {node_id} -> ({latitude:.2f}, {longitude:.2f})')
    
    # 保存检查点，确保 GPS 坐标持久化
    from backend.utils.persistence import save_checkpoint
    save_checkpoint()
    
    return True


def get_all_nodes() -> List[Dict[str, Any]]:
    """获取所有节点"""
    return system_state.get('nodes', [])

