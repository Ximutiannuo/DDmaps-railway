"""
路径规划服务模块
"""
import heapq
import math
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.models.system_state import system_state
from backend.utils.logger import logger


def calculate_direction(start_node: Dict[str, Any], end_node: Dict[str, Any]) -> str:
    """计算两个节点之间的地理方向"""
    dx = end_node['x'] - start_node['x']
    dy = end_node['y'] - start_node['y']
    
    # 计算角度（弧度）
    angle_rad = math.atan2(dy, dx)
    # 转换为角度（0-360度，0度为正东方向）
    angle_deg = math.degrees(angle_rad) % 360
    
    # 根据角度确定方向
    if -22.5 <= angle_deg < 22.5:
        return 'east'
    elif 22.5 <= angle_deg < 67.5:
        return 'northeast'
    elif 67.5 <= angle_deg < 112.5:
        return 'north'
    elif 112.5 <= angle_deg < 157.5:
        return 'northwest'
    elif 157.5 <= angle_deg < 202.5:
        return 'west'
    elif 202.5 <= angle_deg < 247.5:
        return 'southwest'
    elif 247.5 <= angle_deg < 292.5:
        return 'south'
    elif 292.5 <= angle_deg < 337.5:
        return 'southeast'
    else:  # 337.5-360 和 -22.5 - 0
        return 'east'


def is_direction_allowed(edge_direction: str, start_node: Dict[str, Any], end_node: Dict[str, Any]) -> bool:
    """检查给定的行驶方向是否被允许"""
    if edge_direction == 'two-way':
        return True
    
    # 计算实际行驶方向
    actual_direction = calculate_direction(start_node, end_node)
    
    # 检查实际方向是否与道路允许的方向一致
    return actual_direction == edge_direction


def get_node_by_id(node_id: str) -> Optional[Dict[str, Any]]:
    """根据节点ID获取节点"""
    return next((n for n in system_state['nodes'] if n['id'] == node_id), None)


def get_edge_length_m(edge: Dict[str, Any]) -> float:
    """获取边的长度（米）"""
    # 优先使用 length_m（真实米数）
    length_m = edge.get('length_m')
    if length_m is not None:
        return float(length_m)
    # 回退到 length（兼容旧数据）
    length = edge.get('length')
    if length is not None:
        return float(length)
    # 默认值
    return 1.0


def get_vehicle_speed_kmph(vehicle_type: str) -> float:
    """获取车辆类型的默认速度（km/h）"""
    vehicle_cfg = system_state['vehicle_types'].get(vehicle_type, {})
    speed_kmph = vehicle_cfg.get('speed_kmph')
    if speed_kmph is None:
        # 默认速度
        if vehicle_type == '渣土车':
            speed_kmph = 30.0
        elif vehicle_type == '混凝土车':
            speed_kmph = 25.0
        else:
            speed_kmph = 25.0
        vehicle_cfg['speed_kmph'] = float(speed_kmph)
        system_state['vehicle_types'][vehicle_type] = vehicle_cfg
    return float(speed_kmph)


def get_edges_connected_to_node(node_id: str) -> List[Dict[str, Any]]:
    """获取与指定节点相连的所有道路"""
    connected_edges = []
    for edge in system_state['edges']:
        if edge['start_node'] == node_id or edge['end_node'] == node_id:
            connected_edges.append(edge)
    return connected_edges


def refresh_edge_geometry():
    """根据当前节点坐标刷新道路的显示长度，但保持 length_m（真实米数）不变"""
    node_lookup = {node['id']: (node['x'], node['y']) for node in system_state['nodes']}
    for edge in system_state['edges']:
        start_pos = node_lookup.get(edge.get('start_node'))
        end_pos = node_lookup.get(edge.get('end_node'))
        if start_pos and end_pos:
            length_display = math.dist(start_pos, end_pos)
            edge['length_display'] = float(round(length_display, 3))
            # 只有在 length_m 不存在时才设置（用于默认地图，DXF导入的应该已经有 length_m）
            if edge.get('length_m') is None:
                edge['length_m'] = float(length_display)
        # 确保 length 字段存在（用于兼容）
        length_m = edge.get('length_m')
        if length_m is not None:
            edge['length'] = float(length_m)
        elif edge.get('length') is not None:
            # 如果 length_m 不存在但 length 存在，使用 length 作为 length_m
            edge['length_m'] = float(edge['length'])


def build_graph(vehicle_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """构建邻接表（考虑道路方向和车辆限制）"""
    graph = {}
    vehicle_config = system_state['vehicle_types'].get(vehicle_type, {})
    
    for edge in system_state['edges']:
        if not edge.get('is_available', True):
            continue
        
        direction = edge.get('direction', 'two-way')
        
        # 检查车辆是否能使用这种道路类型
        if direction != 'two-way':  # 如果是单向道路
            if not vehicle_config.get('can_use_one_way', True):
                continue
        
        # 获取起点和终点节点
        start_node = get_node_by_id(edge['start_node'])
        end_node = get_node_by_id(edge['end_node'])
        
        if not start_node or not end_node:
            continue
            
        # 检查行驶方向是否允许
        if not is_direction_allowed(direction, start_node, end_node):
            continue
        
        # 正向连接
        graph.setdefault(edge['start_node'], []).append(edge)
        
        # 如果是双向道路，添加反向连接（但需要检查反向方向是否允许）
        if direction == 'two-way':
            # 计算反向方向
            reverse_direction = calculate_direction(end_node, start_node)
            # 创建反向边
            reverse_edge = {
                'id': edge['id'] + '_reverse',
                'start_node': edge['end_node'],
                'end_node': edge['start_node'],
                'length': edge['length'],
                'max_weight': edge['max_weight'],
                'max_width': edge['max_width'],
                'is_available': edge['is_available'],
                'congestion_coeff': edge['congestion_coeff'],
                'direction': reverse_direction
            }
            graph.setdefault(reverse_edge['start_node'], []).append(reverse_edge)
    
    return graph


def calculate_efficient_path(start_node_id: str, target_node_id: str, vehicle: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    使用 Dijkstra（基于优先队列）计算最小代价路径
    """
    vehicle_type = vehicle.get('type', '渣土车') if vehicle else '渣土车'
    graph = build_graph(vehicle_type)
    pq = []
    counter = 0  # 用于生成唯一标识符
    
    # (cost, counter, node_id, path_edges)
    heapq.heappush(pq, (0.0, counter, start_node_id, []))
    counter += 1
    
    visited_cost = {}  # node -> best cost found

    # Helper: check if a node is a work zone under construction
    def node_work_penalty(node_id):
        if node_id in system_state.get('work_zones', set()):
            return 3.0  # 大惩罚，尽量绕行施工区
        return 1.0

    while pq:
        cost, _, node_id, path = heapq.heappop(pq)
        if node_id in visited_cost and cost >= visited_cost[node_id]:
            continue
        visited_cost[node_id] = cost

        if node_id == target_node_id:
            return path  # 找到路径

        for edge in graph.get(node_id, []):
            # 如果车辆规格与道路不匹配（例如宽度、重量），则跳过（可扩展）
            if vehicle:
                if vehicle.get('width') and edge.get('max_width') and vehicle.get('width') > edge.get('max_width'):
                    continue
                if vehicle.get('weight') and edge.get('max_weight') and vehicle.get('weight') > edge.get('max_weight'):
                    continue

            # 基本权重：长度 * 拥堵系数
            edge_cost = get_edge_length_m(edge) * edge.get('congestion_coeff', 1.0)

            # 如果目标节点或经过节点是施工点，则放大权重（强制绕行）
            end_node_id = edge.get('end_node')
            edge_cost *= node_work_penalty(end_node_id)
            
            # 考虑节点拥堵：如果起点或终点节点有拥堵，增加权重
            start_node_id = edge.get('start_node')
            start_congestion = system_state['node_congestion'].get(start_node_id, 0)
            end_congestion = system_state['node_congestion'].get(end_node_id, 0)
            if start_congestion > 0:
                # 节点拥堵级别：1=轻微(1.2), 2=中度(1.5), 3=严重(2.0)
                congestion_penalty = {1: 1.2, 2: 1.5, 3: 2.0}.get(start_congestion, 1.0)
                edge_cost *= congestion_penalty
            if end_congestion > 0:
                congestion_penalty = {1: 1.2, 2: 1.5, 3: 2.0}.get(end_congestion, 1.0)
                edge_cost *= congestion_penalty

            # 额外微调：若边拥堵非常高（>2.0），给予显著惩罚
            if edge.get('congestion_coeff', 1.0) > 2.0:
                edge_cost *= 2.0

            new_cost = cost + edge_cost
            heapq.heappush(pq, (new_cost, counter, end_node_id, path + [edge]))
            counter += 1

    return []  # 无路径


def estimate_efficiency_score(path: List[Dict[str, Any]]) -> Optional[float]:
    """
    计算一条路径的"效率分"：数值越小越高效（这里返回一个综合代价，前端可用于排序/显示）
    为了可读性，我们把 score 定义为 总(length * congestion) / 10
    """
    if not path:
        return None
    total = 0.0
    for e in path:
        total += get_edge_length_m(e) * e.get('congestion_coeff', 1.0)
    return total / 10.0


def serialize_path_edges(path: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将路径中的边转换为可序列化的数据结构"""
    serialized = []
    for edge in path:
        serialized.append({
            'id': edge.get('id'),
            'edge_id': edge.get('id'),  # 添加edge_id作为别名，提高兼容性
            'start_node': edge.get('start_node'),
            'end_node': edge.get('end_node'),
            'length': edge.get('length'),
            'length_m': edge.get('length_m'),  # 添加length_m字段，确保完整信息
            'congestion_coeff': edge.get('congestion_coeff', 1.0),
            'direction': edge.get('direction', 'two-way'),
            'max_weight': edge.get('max_weight'),
            'max_width': edge.get('max_width')
        })
    return serialized


def build_node_sequence_from_path(start_node_id: str, path: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """根据路径生成节点序列"""
    sequence = []
    visited = set()

    start_node = get_node_by_id(start_node_id)
    if start_node:
        sequence.append({
            'id': start_node['id'],
            'name': start_node['name'],
            'type': start_node['type'],
            'x': start_node['x'],
            'y': start_node['y']
        })
        visited.add(start_node['id'])

    for edge in path:
        end_node_id = edge.get('end_node')
        if not end_node_id:
            continue
        if end_node_id in visited:
            continue
        end_node = get_node_by_id(end_node_id)
        if end_node:
            sequence.append({
                'id': end_node['id'],
                'name': end_node['name'],
                'type': end_node['type'],
                'x': end_node['x'],
                'y': end_node['y']
            })
            visited.add(end_node['id'])

    return sequence


def estimate_travel_minutes(
    path: List[Dict[str, Any]], 
    vehicle_type: str, 
    custom_speed_kmph: Optional[float] = None, 
    start_node: Optional[str] = None, 
    target_node: Optional[str] = None
) -> Optional[float]:
    """估算行驶时间（分钟）"""
    if not path:
        return None

    if start_node and target_node:
        stats_key = f'{start_node}->{target_node}'
        stats = system_state['route_time_stats'].get(stats_key)
        if stats and stats.get('average_minutes'):
            return stats['average_minutes']

    speed_kmph = None
    if custom_speed_kmph is not None:
        try:
            speed_kmph = float(custom_speed_kmph)
        except (TypeError, ValueError):
            speed_kmph = None
    if not speed_kmph:
        speed_kmph = get_vehicle_speed_kmph(vehicle_type)
    if speed_kmph <= 0:
        speed_kmph = 25.0

    distance_m = sum(get_edge_length_m(edge) for edge in path)
    if distance_m <= 0:
        return 1.0

    avg_congestion = sum(edge.get('congestion_coeff', 1.0) for edge in path) / max(1, len(path))
    effective_speed_kmh = speed_kmph / max(0.5, avg_congestion)
    if effective_speed_kmh <= 0:
        effective_speed_kmh = max(5.0, speed_kmph * 0.2)

    travel_minutes = (distance_m / 1000.0) / effective_speed_kmh * 60.0
    return max(0.1, travel_minutes)
