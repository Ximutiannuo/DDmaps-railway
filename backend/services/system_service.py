"""
系统服务模块
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from backend.models.system_state import system_state
from backend.services.path_planning_service import (
    get_node_by_id,
    get_edges_connected_to_node,
    refresh_edge_geometry
)
from backend.services.vehicle_service import update_vehicle_positions
from backend.services.path_planning_service import (
    calculate_efficient_path,
    estimate_efficiency_score
)
from backend.utils.logger import logger


def init_monitor_data():
    """初始化监控数据"""
    system_state['monitor_data'] = {
        'edge_congestion': {},
        'edge_available': {},
        'entrance_queue': {},
        'vehicle_positions': {},
        'last_update': datetime.now().isoformat()
    }

    for edge in system_state['edges']:
        system_state['monitor_data']['edge_congestion'][edge['id']] = edge.get('congestion_coeff', 1.0)
        system_state['monitor_data']['edge_available'][edge['id']] = edge.get('is_available', True)

    for node in system_state['nodes']:
        if node['type'] in ['entrance', 'start']:
            system_state['monitor_data']['entrance_queue'][node['id']] = 0


def initialize_system():
    """初始化系统数据"""
    logger.info('🔧 开始初始化系统...')
    
    # 默认节点数据 - 6x5网格（节点间距：横向150px，纵向100px）
    system_state['nodes'] = [
        # 第一行
        {'id': 'N1_1', 'name': '起点1', 'x': 100, 'y': 100, 'type': 'start'},
        {'id': 'N1_2', 'name': '进场口1', 'x': 250, 'y': 100, 'type': 'entrance'},
        {'id': 'N1_3', 'name': '交叉口1', 'x': 400, 'y': 100, 'type': 'crossroad'},
        {'id': 'N1_4', 'name': '交叉口2', 'x': 550, 'y': 100, 'type': 'crossroad'},
        {'id': 'N1_5', 'name': '作业区1', 'x': 700, 'y': 100, 'type': 'work-area'},
        
        # 第二行
        {'id': 'N2_1', 'name': '起点2', 'x': 100, 'y': 200, 'type': 'start'},
        {'id': 'N2_2', 'name': '进场口2', 'x': 250, 'y': 200, 'type': 'entrance'},
        {'id': 'N2_3', 'name': '交叉口3', 'x': 400, 'y': 200, 'type': 'crossroad'},
        {'id': 'N2_4', 'name': '交叉口4', 'x': 550, 'y': 200, 'type': 'crossroad'},
        {'id': 'N2_5', 'name': '作业区2', 'x': 700, 'y': 200, 'type': 'work-area'},
        
        # 第三行
        {'id': 'N3_1', 'name': '起点3', 'x': 100, 'y': 300, 'type': 'start'},
        {'id': 'N3_2', 'name': '进场口3', 'x': 250, 'y': 300, 'type': 'entrance'},
        {'id': 'N3_3', 'name': '交叉口5', 'x': 400, 'y': 300, 'type': 'crossroad'},
        {'id': 'N3_4', 'name': '交叉口6', 'x': 550, 'y': 300, 'type': 'crossroad'},
        {'id': 'N3_5', 'name': '作业区3', 'x': 700, 'y': 300, 'type': 'work-area'},
        
        # 第四行
        {'id': 'N4_1', 'name': '起点4', 'x': 100, 'y': 400, 'type': 'start'},
        {'id': 'N4_2', 'name': '进场口4', 'x': 250, 'y': 400, 'type': 'entrance'},
        {'id': 'N4_3', 'name': '交叉口7', 'x': 400, 'y': 400, 'type': 'crossroad'},
        {'id': 'N4_4', 'name': '交叉口8', 'x': 550, 'y': 400, 'type': 'crossroad'},
        {'id': 'N4_5', 'name': '作业区4', 'x': 700, 'y': 400, 'type': 'work-area'},
        
        # 第五行
        {'id': 'N5_1', 'name': '起点5', 'x': 100, 'y': 500, 'type': 'start'},
        {'id': 'N5_2', 'name': '进场口5', 'x': 250, 'y': 500, 'type': 'entrance'},
        {'id': 'N5_3', 'name': '交叉口9', 'x': 400, 'y': 500, 'type': 'crossroad'},
        {'id': 'N5_4', 'name': '交叉口10', 'x': 550, 'y': 500, 'type': 'crossroad'},
        {'id': 'N5_5', 'name': '作业区5', 'x': 700, 'y': 500, 'type': 'work-area'},
        
        # 第六行
        {'id': 'N6_1', 'name': '起点6', 'x': 100, 'y': 600, 'type': 'start'},
        {'id': 'N6_2', 'name': '进场口6', 'x': 250, 'y': 600, 'type': 'entrance'},
        {'id': 'N6_3', 'name': '交叉口11', 'x': 400, 'y': 600, 'type': 'crossroad'},
        {'id': 'N6_4', 'name': '交叉口12', 'x': 550, 'y': 600, 'type': 'crossroad'},
        {'id': 'N6_5', 'name': '作业区6', 'x': 700, 'y': 600, 'type': 'work-area'}
    ]

    # 默认边数据 - 连接6x5网格
    system_state['edges'] = [
        # 横向连接 - 每行内部的连接（东西方向，长度150px）
        # 第一行横向
       {'id': 'E1_H1', 'start_node': 'N1_1', 'end_node': 'N1_2', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E1_H2', 'start_node': 'N1_2', 'end_node': 'N1_3', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E1_H3', 'start_node': 'N1_3', 'end_node': 'N1_4', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E1_H4', 'start_node': 'N1_4', 'end_node': 'N1_5', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        
        # 第二行横向
        {'id': 'E2_H1', 'start_node': 'N2_1', 'end_node': 'N2_2', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E2_H2', 'start_node': 'N2_2', 'end_node': 'N2_3', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E2_H3', 'start_node': 'N2_3', 'end_node': 'N2_4', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E2_H4', 'start_node': 'N2_4', 'end_node': 'N2_5', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        
        # 第三行横向
        {'id': 'E3_H1', 'start_node': 'N3_1', 'end_node': 'N3_2', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E3_H2', 'start_node': 'N3_2', 'end_node': 'N3_3', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E3_H3', 'start_node': 'N3_3', 'end_node': 'N3_4', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E3_H4', 'start_node': 'N3_4', 'end_node': 'N3_5', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        
        # 第四行横向
        {'id': 'E4_H1', 'start_node': 'N4_1', 'end_node': 'N4_2', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E4_H2', 'start_node': 'N4_2', 'end_node': 'N4_3', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E4_H3', 'start_node': 'N4_3', 'end_node': 'N4_4', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E4_H4', 'start_node': 'N4_4', 'end_node': 'N4_5', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        
        # 第五行横向
        {'id': 'E5_H1', 'start_node': 'N5_1', 'end_node': 'N5_2', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E5_H2', 'start_node': 'N5_2', 'end_node': 'N5_3', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E5_H3', 'start_node': 'N5_3', 'end_node': 'N5_4', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E5_H4', 'start_node': 'N5_4', 'end_node': 'N5_5', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        
        # 第六行横向
        {'id': 'E6_H1', 'start_node': 'N6_1', 'end_node': 'N6_2', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E6_H2', 'start_node': 'N6_2', 'end_node': 'N6_3', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E6_H3', 'start_node': 'N6_3', 'end_node': 'N6_4', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E6_H4', 'start_node': 'N6_4', 'end_node': 'N6_5', 'length': 150, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        
        # 纵向连接 - 列之间的连接（南北方向，长度100px）
        # 第一列纵向
        {'id': 'E1_V1', 'start_node': 'N1_1', 'end_node': 'N2_1', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E1_V2', 'start_node': 'N2_1', 'end_node': 'N3_1', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E1_V3', 'start_node': 'N3_1', 'end_node': 'N4_1', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E1_V4', 'start_node': 'N4_1', 'end_node': 'N5_1', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E1_V5', 'start_node': 'N5_1', 'end_node': 'N6_1', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        
        # 第二列纵向
        {'id': 'E2_V1', 'start_node': 'N1_2', 'end_node': 'N2_2', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E2_V2', 'start_node': 'N2_2', 'end_node': 'N3_2', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E2_V3', 'start_node': 'N3_2', 'end_node': 'N4_2', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E2_V4', 'start_node': 'N4_2', 'end_node': 'N5_2', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E2_V5', 'start_node': 'N5_2', 'end_node': 'N6_2', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        
        # 第三列纵向
        {'id': 'E3_V1', 'start_node': 'N1_3', 'end_node': 'N2_3', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E3_V2', 'start_node': 'N2_3', 'end_node': 'N3_3', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E3_V3', 'start_node': 'N3_3', 'end_node': 'N4_3', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E3_V4', 'start_node': 'N4_3', 'end_node': 'N5_3', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E3_V5', 'start_node': 'N5_3', 'end_node': 'N6_3', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        
        # 第四列纵向
        {'id': 'E4_V1', 'start_node': 'N1_4', 'end_node': 'N2_4', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E4_V2', 'start_node': 'N2_4', 'end_node': 'N3_4', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E4_V3', 'start_node': 'N3_4', 'end_node': 'N4_4', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E4_V4', 'start_node': 'N4_4', 'end_node': 'N5_4', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E4_V5', 'start_node': 'N5_4', 'end_node': 'N6_4', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        
        # 第五列纵向
        {'id': 'E5_V1', 'start_node': 'N1_5', 'end_node': 'N2_5', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E5_V2', 'start_node': 'N2_5', 'end_node': 'N3_5', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E5_V3', 'start_node': 'N3_5', 'end_node': 'N4_5', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E5_V4', 'start_node': 'N4_5', 'end_node': 'N5_5', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'},
        {'id': 'E5_V5', 'start_node': 'N5_5', 'end_node': 'N6_5', 'length': 100, 'max_weight': 50, 'max_width': 5, 'is_available': True, 'congestion_coeff': 1.0, 'direction': 'two-way'}
    ]

    # 为每条边设置默认方向
    for edge in system_state['edges']:
        system_state['edge_directions'][edge['id']] = edge['direction']

    # 初始化车辆数据
    system_state['vehicles'] = []
    system_state['vehicle_counter'] = 1
    system_state['work_zones'] = set()
    system_state['custom_congestion_edges'] = set()  # 初始化自定义拥堵道路
    system_state['node_congestion'] = {}  # 初始化节点拥堵状态
    system_state['edge_status'] = {}  # 初始化道路状态
    system_state['driver_routes'] = {}
    system_state['arrival_records'] = []
    system_state['route_time_stats'] = {}
    system_state['travel_time_database'] = []

    refresh_edge_geometry()
    # 初始化监控数据
    init_monitor_data()
    
    logger.info('✅ 系统初始化成功')
    return True


def apply_node_congestion_to_edges():
    """应用节点拥堵状态到相关道路"""
    for node_id, congestion_level in system_state['node_congestion'].items():
        if congestion_level == 0:
            continue  # 正常状态，不影响道路
        
        # 获取与该节点相连的所有道路
        connected_edges = get_edges_connected_to_node(node_id)
        
        # 根据节点拥堵级别影响道路拥堵系数
        # 拥堵级别：1=轻微(1.3), 2=中度(1.8), 3=严重(2.5)
        congestion_multiplier = {1: 1.3, 2: 1.8, 3: 2.5}.get(congestion_level, 1.0)
        
        for edge in connected_edges:
            # 如果道路已经有自定义状态，优先使用自定义状态
            edge_status = system_state['edge_status'].get(edge['id'], 'normal')
            if edge_status == 'closed':
                continue  # 封闭道路不受节点拥堵影响
            
            # 应用节点拥堵影响（取较大值，确保拥堵不会降低）
            base_congestion = edge.get('congestion_coeff', 1.0)
            # 如果道路本身有拥堵，叠加节点拥堵影响
            if edge_status == 'congested':
                edge['congestion_coeff'] = max(base_congestion, congestion_multiplier * 1.5)
            elif edge_status == 'construction':
                # 占道施工已经影响通行，叠加节点拥堵
                edge['congestion_coeff'] = max(base_congestion, congestion_multiplier * 1.2)
            else:
                # 正常道路，应用节点拥堵影响
                edge['congestion_coeff'] = max(base_congestion, congestion_multiplier)


def current_vehicle_location_node(vehicle: Dict[str, Any]) -> Optional[str]:
    """
    推断车辆当前位于哪个节点（用于从当前点重路由）
    简单策略：
    - 如果 vehicle.current_path 存在，取当前 edge 的 start 或 end 基于 progress
    - 否则使用最近的节点（按坐标）
    """
    if vehicle.get('current_path'):
        if len(vehicle['current_path']) > 0:
            edge = vehicle['current_path'][0]
            progress = vehicle.get('progress', 0)
            if progress < 0.5:
                return edge.get('start_node')
            else:
                return edge.get('end_node')
    # 回退：找最近节点
    pos = vehicle.get('current_position')
    if pos:
        min_dist = float('inf')
        nearest = None
        for n in system_state['nodes']:
            dx = n['x'] - pos.get('x', 0)
            dy = n['y'] - pos.get('y', 0)
            d = dx*dx + dy*dy
            if d < min_dist:
                min_dist = d
                nearest = n['id']
        return nearest
    # 找不到返回起点类型节点
    start = next((n for n in system_state['nodes'] if n['type'] == 'start'), None)
    return start['id'] if start else None


def reroute_vehicles(affected_edges_ids: Optional[List[str]] = None, force_reroute: bool = False, compare_efficiency: bool = True) -> List[str]:
    """
    对所有正在移动或等待的车辆进行重路由（或者仅针对受影响的车辆）
    affected_edges_ids: 如果提供，仅重算那些路径中包含这些 edge 的车辆（提高效率）
    force_reroute: 如果为 True，强制重路由（即使路径看起来相同）
    compare_efficiency: 如果为 True，比较新路径和当前路径的效率，只有新路径更优时才切换
    """
    affected = set(affected_edges_ids or [])
    updated = []

    for vehicle in system_state['vehicles']:
        if vehicle.get('status') not in ['moving', 'waiting']:
            continue

        # 若只处理受影响车辆，判断车辆当前路径是否包含受影响的边
        if affected:
            path_edges = vehicle.get('current_path', [])
            path_edge_ids = {e.get('id') for e in path_edges}
            if not (path_edge_ids & affected):
                continue

        # 计算新的起点
        start_node_id = current_vehicle_location_node(vehicle)
        if not start_node_id:
            continue

        # 保存当前路径和效率，用于比较
        old_path = vehicle.get('current_path', [])
        old_progress = vehicle.get('progress', 0.0)
        current_pos = vehicle.get('current_position', {})
        old_efficiency = vehicle.get('efficiency_score')
        if old_efficiency is None and old_path:
            old_efficiency = estimate_efficiency_score(old_path)

        new_path = calculate_efficient_path(start_node_id, vehicle.get('target_node'), vehicle)
        if new_path:
            # 如果启用了效率比较，且新路径不比当前路径更优，则不切换
            if compare_efficiency and old_path and old_efficiency is not None:
                new_efficiency = estimate_efficiency_score(new_path)
                # 效率分数越低越好（表示距离更短或时间更短）
                # 只有当新路径效率至少提高5%时才切换，避免频繁切换
                if new_efficiency >= old_efficiency * 0.95:
                    # 新路径效率没有明显提升（提升小于5%），不切换
                    continue
            
            # 尝试在新路径中找到与当前位置匹配的边
            new_progress = 0.0
            found_matching_edge = False
            
            # 如果旧路径的第一条边和新路径的第一条边相同，保持当前进度
            if old_path and len(old_path) > 0 and new_path and len(new_path) > 0:
                old_first_edge_id = old_path[0].get('id')
                new_first_edge_id = new_path[0].get('id')
                if old_first_edge_id == new_first_edge_id:
                    new_progress = old_progress
                    found_matching_edge = True
            
            # 如果没找到匹配的第一条边，尝试在新路径中找到包含当前位置的边
            if not found_matching_edge and current_pos:
                from backend.services.path_planning_service import get_edge_length_m
                import math
                
                pos_x = current_pos.get('x')
                pos_y = current_pos.get('y')
                
                if pos_x is not None and pos_y is not None:
                    for i, edge in enumerate(new_path):
                        edge_start_node = get_node_by_id(edge.get('start_node'))
                        edge_end_node = get_node_by_id(edge.get('end_node'))
                        
                        if not (edge_start_node and edge_end_node):
                            continue
                        
                        # 检查当前位置是否在这条边的路径上
                        start_x, start_y = edge_start_node['x'], edge_start_node['y']
                        end_x, end_y = edge_end_node['x'], edge_end_node['y']
                        
                        # 计算点到线段的最短距离
                        dx = end_x - start_x
                        dy = end_y - start_y
                        edge_length = math.sqrt(dx*dx + dy*dy)
                        
                        if edge_length <= 0:
                            continue
                        
                        # 计算当前位置在边上的投影比例
                        to_point_x = pos_x - start_x
                        to_point_y = pos_y - start_y
                        projection = (to_point_x * dx + to_point_y * dy) / (edge_length * edge_length)
                        projection = max(0.0, min(1.0, projection))  # 限制在0-1之间
                        
                        # 计算投影点
                        proj_x = start_x + projection * dx
                        proj_y = start_y + projection * dy
                        
                        # 计算距离（如果距离很近，认为车辆在这条边上）
                        dist_to_edge = math.sqrt((pos_x - proj_x)**2 + (pos_y - proj_y)**2)
                        
                        # 如果距离小于50像素，认为车辆在这条边上
                        if dist_to_edge < 50:
                            new_progress = projection
                            # 如果找到了匹配的边但不是第一条，需要移除之前的边
                            if i > 0:
                                new_path = new_path[i:]  # 更新新路径，移除之前的边
                            found_matching_edge = True
                            break
            
            # 设置路径和进度
            vehicle['current_path'] = new_path
            
            if not found_matching_edge:
                # 如果还是没找到，从起点开始（使用节点作为起点）
                vehicle['progress'] = 0.0
                # 将车辆位置设置为新路径第一条边的起点
                if new_path and len(new_path) > 0:
                    first_edge_start = get_node_by_id(new_path[0].get('start_node'))
                    if first_edge_start:
                        vehicle['current_position'] = {
                            'x': first_edge_start['x'],
                            'y': first_edge_start['y']
                        }
            else:
                # 找到了匹配的边，使用计算的进度
                vehicle['progress'] = new_progress
                # 更新当前位置以确保准确
                if new_path and len(new_path) > 0:
                    first_edge = new_path[0]
                    edge_start_node = get_node_by_id(first_edge.get('start_node'))
                    edge_end_node = get_node_by_id(first_edge.get('end_node'))
                    if edge_start_node and edge_end_node:
                        ratio = new_progress
                        vehicle['current_position'] = {
                            'x': edge_start_node['x'] + (edge_end_node['x'] - edge_start_node['x']) * ratio,
                            'y': edge_start_node['y'] + (edge_end_node['y'] - edge_start_node['y']) * ratio
                        }
            
            vehicle['status'] = 'moving'
            vehicle['efficiency_score'] = estimate_efficiency_score(new_path)
            vehicle['last_reroute_time'] = datetime.now().isoformat()
            updated.append(vehicle['id'])
        else:
            # 如果无法找到路径，标记为等待
            vehicle['status'] = 'waiting'
            vehicle['efficiency_score'] = None

    if updated:
        logger.info(f'🔁 重路由完成（车辆）: {updated}')
    return updated


def update_monitor_data():
    """更新监控数据（处理节点拥堵、道路状态、自定义拥堵和施工）"""
    # 确保 monitor_data 存在且包含必要的键
    if 'monitor_data' not in system_state:
        init_monitor_data()
    
    monitor_data = system_state['monitor_data']
    
    # 确保所有必要的键都存在
    if 'edge_congestion' not in monitor_data:
        monitor_data['edge_congestion'] = {}
    if 'edge_available' not in monitor_data:
        monitor_data['edge_available'] = {}
    if 'entrance_queue' not in monitor_data:
        monitor_data['entrance_queue'] = {}
    if 'vehicle_positions' not in monitor_data:
        monitor_data['vehicle_positions'] = {}
    
    monitor_data['last_update'] = datetime.now().isoformat()
    
    # 首先应用道路状态设置
    for edge in system_state['edges']:
        edge_status = system_state['edge_status'].get(edge['id'], 'normal')
        
        if edge_status == 'closed':
            # 封闭道路：不可用
            edge['is_available'] = False
            edge['congestion_coeff'] = 999.0  # 极大值，路径算法会避开
        elif edge_status == 'construction':
            edge['is_available'] = True
            edge['congestion_coeff'] = 999.0  # 占道施工路径算法会避开
        elif edge_status == 'congested':
            # 拥堵：可用但拥堵系数高
            edge['is_available'] = True
            edge['congestion_coeff'] = 2.0
        elif edge['id'] in system_state['custom_congestion_edges']:
            # 自定义拥堵道路
            edge['is_available'] = True
            edge['congestion_coeff'] = 3.0
        else:
            # 正常道路：恢复默认值（所有道路默认都是1.0，不再设置特殊拥堵值）
            edge['is_available'] = True
            edge['congestion_coeff'] = 1.0
        
    # 然后应用节点拥堵到相关道路（会叠加到道路状态上）
    apply_node_congestion_to_edges()
        
    # 更新监控数据
    for edge in system_state['edges']:
        monitor_data['edge_congestion'][edge['id']] = edge['congestion_coeff']
        monitor_data['edge_available'][edge['id']] = edge.get('is_available', True)
    
    # 确保 entrance_queue 包含所有入口节点的 ID
    for node in system_state['nodes']:
        if node['type'] in ['entrance', 'start']:
            if node['id'] not in monitor_data['entrance_queue']:
                monitor_data['entrance_queue'][node['id']] = 0
    
    # 更新进场口排队情况
    for entrance_id in list(monitor_data['entrance_queue'].keys()):
        queue_count = len([v for v in system_state['vehicles'] 
                          if v.get('assigned_entrance') == entrance_id and v.get('status') == 'waiting'])
        monitor_data['entrance_queue'][entrance_id] = queue_count
    
    # 更新车辆位置
    update_vehicle_positions()

    # 检测道路状态变化，触发重路由
    # 1. 检测变坏的道路（封闭/施工/拥堵）- 强制重路由
    affected_bad = []
    # 2. 检测恢复正常的道路（从封闭/施工/拥堵恢复）- 效率比较重路由
    affected_recovered = []
    
    # 获取上一次的道路状态（用于比较）
    prev_edge_status = monitor_data.get('prev_edge_status', {})
    current_edge_status = {}
    
    for e in system_state['edges']:
        edge_id = e['id']
        is_unavailable = not e.get('is_available', True)
        is_congested = e.get('congestion_coeff', 1.0) > 2.0
        
        # 记录当前状态
        current_edge_status[edge_id] = {
            'is_available': e.get('is_available', True),
            'congestion_coeff': e.get('congestion_coeff', 1.0)
        }
        
        # 检测当前状态：变坏的道路
        if is_unavailable or is_congested:
            affected_bad.append(edge_id)
        
        # 检测状态变化：恢复正常的道路
        if edge_id in prev_edge_status:
            prev_status = prev_edge_status[edge_id]
            prev_was_unavailable = not prev_status.get('is_available', True)
            prev_was_congested = prev_status.get('congestion_coeff', 1.0) > 2.0
            
            # 之前是封闭/施工/拥堵，现在恢复正常
            if (prev_was_unavailable or prev_was_congested) and not is_unavailable and not is_congested:
                affected_recovered.append(edge_id)
    
    # 更新上一次的道路状态
    monitor_data['prev_edge_status'] = current_edge_status
    
    # 处理变坏的道路：强制重路由（因为必须避开）
    if affected_bad:
        reroute_vehicles(affected_edges_ids=affected_bad, force_reroute=True, compare_efficiency=False)
    
    # 处理恢复正常的道路：效率比较重路由（只有更优时才切换）
    if affected_recovered:
        # 对于恢复正常的道路，需要检查所有可能受益的车辆
        # 因为车辆可能因为道路封闭而绕行了，现在道路恢复，应该重新评估是否走原路
        # 调用 reroute_vehicles 检查所有车辆，但启用效率比较，只有更优时才切换
        # 注意：不传入 affected_edges_ids，让它检查所有正在行驶的车辆
        reroute_vehicles(affected_edges_ids=None, force_reroute=False, compare_efficiency=True)


def _apply_map_data(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
    """使用给定的节点和道路数据更新系统状态"""
    # 验证数据有效性
    if not nodes or not edges:
        raise ValueError(f"无效的地图数据：节点数={len(nodes) if nodes else 0}，道路数={len(edges) if edges else 0}")
    
    # 深拷贝，避免外部引用影响内部状态
    nodes_copy = json.loads(json.dumps(nodes))
    edges_copy = json.loads(json.dumps(edges))

    # 确保节点、道路的必需字段存在
    for node in nodes_copy:
        node.setdefault('type', 'crossroad')
        node.setdefault('name', node.get('id', '未命名节点'))
        node['x'] = float(node.get('x', 0))
        node['y'] = float(node.get('y', 0))
    for edge in edges_copy:
        edge.setdefault('id', f"E{len(edges_copy)}")
        edge.setdefault('max_weight', 50.0)
        edge.setdefault('max_width', 6.0)
        edge.setdefault('is_available', True)
        edge.setdefault('congestion_coeff', 1.0)
        edge.setdefault('direction', 'two-way')
        # 确保长度为浮点数（米）
        # 优先使用 length_m（原始CAD坐标的米数），如果没有则从 length 获取
        length_m = edge.get('length_m')
        if length_m is None and edge.get('length') is not None:
            length_m = edge.get('length')
        # 如果还是没有，使用 length_display（转换后的显示长度，但这不是真实米数）
        if length_m is None and edge.get('length_display') is not None:
            length_m = edge.get('length_display')
        if length_m is not None:
            edge['length_m'] = float(length_m)
            edge['length'] = float(length_m)  # length 用于兼容，使用 length_m 的值
        else:
            # 如果都没有，设置为默认值 1.0 米
            edge['length_m'] = 1.0
            edge['length'] = 1.0
        if 'actual_length' in edge:
            try:
                edge['actual_length'] = float(edge['actual_length'])
            except (TypeError, ValueError):
                edge['actual_length'] = None

    # 使用锁保护，确保线程安全
    with system_state.lock:
        system_state['nodes'] = nodes_copy
        system_state['edges'] = edges_copy
        system_state['edge_directions'] = {edge['id']: edge.get('direction', 'two-way') for edge in edges_copy}
        system_state['vehicles'] = []
        system_state['vehicle_counter'] = 1
        system_state['drivers'] = {}
        system_state['driver_routes'] = {}
        # 清空集合类型的数据
        if isinstance(system_state.get('work_zones'), set):
            system_state['work_zones'].clear()
        else:
            system_state['work_zones'] = set()
        if isinstance(system_state.get('custom_congestion_edges'), set):
            system_state['custom_congestion_edges'].clear()
        else:
            system_state['custom_congestion_edges'] = set()
        system_state['node_congestion'] = {}
        system_state['edge_status'] = {}
        system_state['arrival_records'] = []
        system_state['route_time_stats'] = {}
    
    # 在锁外调用这些函数，避免死锁
    refresh_edge_geometry()
    init_monitor_data()
    
    # 导入地图后立即保存检查点，确保数据持久化（特别是在 PythonAnywhere 上）
    from backend.utils.persistence import save_checkpoint
    save_checkpoint()
    
    logger.info(f'地图数据已应用：{len(nodes_copy)} 个节点，{len(edges_copy)} 条道路')
