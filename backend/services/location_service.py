"""
定位服务模块：处理GPS坐标与节点匹配
"""
import math
from typing import Dict, Any, List, Optional, Tuple
from backend.models.system_state import system_state
from backend.utils.logger import logger


def calculate_gps_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    使用Haversine公式计算两点之间的GPS距离（米）
    
    Args:
        lat1, lon1: 第一个点的纬度和经度
        lat2, lon2: 第二个点的纬度和经度
    
    Returns:
        两点之间的距离（米）
    """
    # 地球半径（米）
    R = 6371000.0
    
    # 转换为弧度
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Haversine公式
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def calculate_map_distance(node1: Dict[str, Any], node2: Dict[str, Any]) -> float:
    """
    计算两个节点之间的地图坐标距离（像素单位）
    
    Args:
        node1, node2: 节点字典，包含x和y坐标
    
    Returns:
        两点之间的距离（像素）
    """
    x1 = float(node1.get('x', 0))
    y1 = float(node1.get('y', 0))
    x2 = float(node2.get('x', 0))
    y2 = float(node2.get('y', 0))
    
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def find_nearest_nodes_by_gps(
    latitude: float,
    longitude: float,
    max_results: int = 5,
    max_distance_m: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    根据GPS坐标查找最近的节点
    
    优先使用节点自带的GPS坐标进行匹配（最精确）。
    如果没有节点带有GPS坐标，则尝试使用GPS参考点进行坐标转换。
    
    Args:
        latitude: 纬度
        longitude: 经度
        max_results: 返回的最多节点数
        max_distance_m: 最大搜索距离（米），None表示不限制
    
    Returns:
        按距离排序的节点列表，每个节点包含距离信息
    """
    nodes = system_state.get('nodes', [])
    if not nodes:
        return []
    
    # 首先检查哪些节点有GPS坐标
    nodes_with_gps = [
        n for n in nodes 
        if n.get('latitude') is not None and n.get('longitude') is not None
    ]
    
    if nodes_with_gps:
        # 如果有节点带GPS坐标，直接计算GPS距离（最精确的方法）
        node_distances = []
        for node in nodes_with_gps:
            node_lat = float(node['latitude'])
            node_lon = float(node['longitude'])
            
            # 使用Haversine公式计算GPS距离
            distance_m = calculate_gps_distance(latitude, longitude, node_lat, node_lon)
            
            if max_distance_m is None or distance_m <= max_distance_m:
                node_distances.append({
                    'node': node,
                    'distance_m': distance_m
                })
        
        # 按距离排序
        node_distances.sort(key=lambda x: x['distance_m'])
        
        # 返回最近的节点
        results = []
        for item in node_distances[:max_results]:
            node_info = dict(item['node'])
            node_info['estimated_distance_m'] = round(item['distance_m'], 2)
            results.append(node_info)
        
        logger.info(f"使用节点GPS坐标匹配: 找到 {len(results)} 个节点（从 {len(nodes_with_gps)} 个带GPS坐标的节点）")
        return results
    
    # 如果没有节点带GPS坐标，尝试使用GPS参考点（备选方法）
    gps_ref = system_state.get('gps_reference', None)
    
    if gps_ref:
        # 如果有GPS参考点，可以进行坐标转换
        ref_lat = gps_ref.get('latitude')
        ref_lon = gps_ref.get('longitude')
        ref_x = gps_ref.get('map_x')
        ref_y = gps_ref.get('map_y')
        scale = gps_ref.get('scale', 1.0)  # 米/像素的比例
        
        if all(x is not None for x in [ref_lat, ref_lon, ref_x, ref_y]):
            # 计算GPS坐标到参考点的距离
            lat_diff = latitude - ref_lat
            lon_diff = longitude - ref_lon
            
            # 将GPS差异转换为地图坐标差异（近似）
            # 1度纬度 ≈ 111,000米，1度经度 ≈ 111,000 * cos(纬度)米
            lat_m = lat_diff * 111000.0
            lon_m = lon_diff * 111000.0 * math.cos(math.radians(ref_lat))
            
            # 转换为地图坐标（像素）
            map_x = ref_x + (lon_m / scale)
            map_y = ref_y - (lat_m / scale)  # Y轴可能需要翻转
            
            # 计算所有节点到转换后坐标的距离
            node_distances = []
            for node in nodes:
                node_x = float(node.get('x', 0))
                node_y = float(node.get('y', 0))
                distance_px = math.sqrt((node_x - map_x) ** 2 + (node_y - map_y) ** 2)
                distance_m = distance_px * scale
                
                if max_distance_m is None or distance_m <= max_distance_m:
                    node_distances.append({
                        'node': node,
                        'distance_px': distance_px,
                        'distance_m': distance_m
                    })
        else:
            # GPS参考点配置不完整，使用备选方法
            logger.warning("GPS参考点配置不完整，使用备选匹配方法")
            return find_nearest_nodes_fallback(latitude, longitude, max_results)
    else:
        # 没有GPS参考点，使用备选方法
        return find_nearest_nodes_fallback(latitude, longitude, max_results)
    
    # 按距离排序
    node_distances.sort(key=lambda x: x['distance_m'])
    
    # 返回最近的节点
    results = []
    for item in node_distances[:max_results]:
        node_info = dict(item['node'])
        node_info['estimated_distance_m'] = round(item['distance_m'], 2)
        results.append(node_info)
    
    return results


def find_nearest_nodes_fallback(
    latitude: float,
    longitude: float,
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    备选方法：没有GPS参考点时，返回所有节点供用户选择
    或者根据节点类型和名称进行智能匹配
    
    Args:
        latitude: 纬度
        longitude: 经度
        max_results: 返回的最多节点数
    
    Returns:
        节点列表（可能包含所有节点或按优先级排序的节点）
    """
    nodes = system_state.get('nodes', [])
    if not nodes:
        return []
    
    # 优先返回入口和起点节点（通常司机在这些位置开始）
    priority_nodes = []
    other_nodes = []
    
    for node in nodes:
        node_type = node.get('type', '')
        if node_type in ['entrance', 'start']:
            priority_nodes.append(dict(node))
        else:
            other_nodes.append(dict(node))
    
    # 先返回优先级节点，然后返回其他节点
    results = priority_nodes[:max_results]
    if len(results) < max_results:
        remaining = max_results - len(results)
        results.extend(other_nodes[:remaining])
    
    # 如果还是不够，返回所有节点
    if len(results) < max_results and len(results) < len(nodes):
        all_nodes = [dict(n) for n in nodes if n not in results]
        results.extend(all_nodes[:max_results - len(results)])
    
    # 为每个节点添加提示信息
    for node in results:
        node['location_hint'] = '请根据您的位置选择最近的节点'
    
    return results


def update_driver_location(
    driver_id: str,
    latitude: float,
    longitude: float,
    accuracy: Optional[float] = None
) -> Dict[str, Any]:
    """
    更新司机的位置信息
    
    Args:
        driver_id: 司机ID
        latitude: 纬度
        longitude: 经度
        accuracy: GPS精度（米）
    
    Returns:
        包含位置信息和附近节点的字典
    """
    from datetime import datetime
    
    # 查找最近的节点
    nearest_nodes = find_nearest_nodes_by_gps(latitude, longitude, max_results=5)
    
    # 更新司机信息
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        driver = drivers.get(driver_id, {})
        
        # 如果司机不存在，自动注册（使用基本信息）
        if not driver:
            logger.info(f"司机 {driver_id} 未注册，自动注册")
            driver = {
                'id': driver_id,
                'name': f'司机 {driver_id}',
                'phone': '',
                'license_plate': '',
                'contact': '',
                'vehicle_type': '渣土车',
                'weight': 20,
                'width': 3,
                'registered_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
            drivers[driver_id] = driver
            system_state.set('drivers', drivers)
        
        # 更新司机位置信息
        driver['location'] = {
            'latitude': float(latitude),
            'longitude': float(longitude),
            'accuracy': float(accuracy) if accuracy is not None else None,
            'updated_at': datetime.now().isoformat()
        }
        
        # 更新最后活跃时间
        driver['last_active'] = datetime.now().isoformat()
        
        drivers[driver_id] = driver
        system_state.set('drivers', drivers)
    
    logger.info(f"更新司机 {driver_id} 位置: ({latitude}, {longitude})")
    
    return {
        'success': True,
        'location': driver['location'],
        'nearest_nodes': nearest_nodes,
        'message': f'已找到 {len(nearest_nodes)} 个附近节点'
    }


def get_driver_location(driver_id: str) -> Optional[Dict[str, Any]]:
    """
    获取司机的当前位置
    
    Args:
        driver_id: 司机ID
    
    Returns:
        位置信息字典，如果不存在则返回None
    """
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        driver = drivers.get(driver_id)
        if driver:
            return driver.get('location')
    return None

