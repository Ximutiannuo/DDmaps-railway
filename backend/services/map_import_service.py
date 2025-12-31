"""
地图导入服务模块（DXF 解析）
"""
import math
import os
from typing import Dict, Any, List, Tuple, Optional

try:
    os.environ["EZDXF_DISABLE_FONT_MANAGER"] = "1"
    os.environ["EZDXF_USE_INTERNAL_FONT_MONO"] = "1"
    import ezdxf  # type: ignore
except ImportError:
    ezdxf = None

from backend.utils.logger import logger


def _round_point(point: Tuple[float, float], ndigits: int = 3) -> Tuple[float, float]:
    """四舍五入点坐标"""
    return round(point[0], ndigits), round(point[1], ndigits)


def _point_on_segment(point: Tuple[float, float], start: Tuple[float, float], end: Tuple[float, float],
                      tol: float = 1e-3) -> bool:
    """判断点是否位于线段上（包含端点）"""
    px, py = point
    x1, y1 = start
    x2, y2 = end
    
    # 如果线段长度为0，直接判断点是否等于端点
    line_length_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if line_length_sq < 1e-6:
        return math.dist(point, start) <= tol
    
    # 计算点到直线的距离（使用更宽松的容差）
    distance = _point_to_line_distance(point, start, end)
    if distance > tol:
        return False
    
    # 检查投影点是否在线段范围内（允许扩展到端点外一个容差距离）
    t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_length_sq
    
    # 如果投影点在线段范围内，或者非常接近端点（在容差范围内），认为在线段上
    return -tol <= t <= (1.0 + tol)


def _segment_intersection(seg1: Tuple[Tuple[float, float], Tuple[float, float]],
                          seg2: Tuple[Tuple[float, float], Tuple[float, float]],
                          tol: float = 1e-3) -> Tuple[float, float] | None:
    """计算两条线段的交点"""
    (x1, y1), (x2, y2) = seg1
    (x3, y3), (x4, y4) = seg2
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) <= tol:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
    if _point_on_segment((px, py), (x1, y1), (x2, y2), tol) and _point_on_segment((px, py), (x3, y3), (x4, y4), tol):
        return px, py
    return None


def _line_direction(start: Tuple[float, float], end: Tuple[float, float], tol: float = 1e-3) -> str:
    """判断线段方向"""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if abs(dx) <= tol:
        return 'vertical'
    if abs(dy) <= tol:
        return 'horizontal'
    return 'oblique'


def _point_to_line_distance(point: Tuple[float, float], line_start: Tuple[float, float], line_end: Tuple[float, float]) -> float:
    """计算点到直线的距离"""
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end
    
    # 如果线段长度为0，返回点到点的距离
    line_length_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if line_length_sq < 1e-6:
        return math.dist(point, line_start)
    
    # 计算投影点
    t = max(0.0, min(1.0, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_length_sq))
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)
    
    return math.dist(point, (proj_x, proj_y))


def _are_parallel(seg1: Tuple[Tuple[float, float], Tuple[float, float]], 
                  seg2: Tuple[Tuple[float, float], Tuple[float, float]], 
                  angle_tol: float = 0.1) -> bool:
    """判断两条线段是否平行"""
    (x1, y1), (x2, y2) = seg1
    (x3, y3), (x4, y4) = seg2
    
    dx1 = x2 - x1
    dy1 = y2 - y1
    dx2 = x4 - x3
    dy2 = y4 - y3
    
    # 计算方向向量长度
    len1 = math.hypot(dx1, dy1)
    len2 = math.hypot(dx2, dy2)
    
    if len1 < 1e-6 or len2 < 1e-6:
        return False
    
    # 归一化方向向量
    u1 = (dx1 / len1, dy1 / len1)
    u2 = (dx2 / len2, dy2 / len2)
    
    # 计算点积（平行时接近1或-1）
    dot = u1[0] * u2[0] + u1[1] * u2[1]
    return abs(abs(dot) - 1.0) < angle_tol


def _calculate_road_width(center_seg: Tuple[Tuple[float, float], Tuple[float, float]], 
                          boundary_segments: List[Tuple[Tuple[float, float], Tuple[float, float]]],
                          tol: float = 1e-3, max_search_distance: float = 50.0) -> Optional[float]:
    """计算道路宽度：找到与中心线平行且距离合理的边界线，计算宽度"""
    parallel_segments = []
    (cx1, cy1), (cx2, cy2) = center_seg
    center_mid = ((cx1 + cx2) / 2, (cy1 + cy2) / 2)
    
    for boundary_seg in boundary_segments:
        if not _are_parallel(center_seg, boundary_seg):
            continue
        
        # 计算边界线中点到中心线的距离
        (bx1, by1), (bx2, by2) = boundary_seg
        boundary_mid = ((bx1 + bx2) / 2, (by1 + by2) / 2)
        distance = _point_to_line_distance(boundary_mid, center_seg[0], center_seg[1])
        
        # 只考虑距离合理的边界线（避免匹配到其他道路的边界）
        if 0.5 <= distance <= max_search_distance:
            # 检查边界线是否与中心线在同一个道路段上（投影重叠）
            # 计算边界线两端点到中心线的距离，如果都在合理范围内，认为是同一道路
            dist1 = _point_to_line_distance((bx1, by1), center_seg[0], center_seg[1])
            dist2 = _point_to_line_distance((bx2, by2), center_seg[0], center_seg[1])
            
            # 如果边界线两端点到中心线的距离相近，认为是同一道路的边界
            if abs(dist1 - distance) < max_search_distance and abs(dist2 - distance) < max_search_distance:
                parallel_segments.append((boundary_seg, distance))
    
    if not parallel_segments:
        return None
    
    # 按距离排序
    parallel_segments.sort(key=lambda x: x[1])
    
    # 如果有两条或更多平行边界线，取距离中心线最近的两条
    if len(parallel_segments) >= 2:
        # 取距离最近的两条，计算它们之间的距离作为道路宽度
        dist1 = parallel_segments[0][1]
        dist2 = parallel_segments[1][1]
        width = dist1 + dist2  # 中心线两侧的距离之和
    else:
        # 只有一条边界线，假设对称，宽度是距离的两倍
        width = parallel_segments[0][1] * 2
    
    return float(round(width, 3))


def parse_dxf_file(file_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """解析 DXF 文件，生成节点和道路数据"""
    if ezdxf is None:
        raise ValueError("当前环境未安装 ezdxf，请先运行 pip install ezdxf")
    try:
        doc = ezdxf.readfile(file_path)
    except Exception as exc:
        raise ValueError(f"无法读取 DXF 文件：{exc}") from exc

    ms = doc.modelspace()
    # (start_pt, end_pt, road_type)
    center_segments: List[Tuple[Tuple[float, float], Tuple[float, float], str]] = []
    boundary_segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

    for entity in ms:
        if entity.dxftype() != 'LINE':
            continue
        layer = (entity.dxf.layer or '').strip()
        linetype = (entity.dxf.linetype or '').strip()
        
        start_pt = (float(entity.dxf.start.x), float(entity.dxf.start.y))
        end_pt = (float(entity.dxf.end.x), float(entity.dxf.end.y))
        if start_pt == end_pt:
            continue
        
        # 识别道路中心线
        # 主路：JIS_08_37
        # 支路：JIS_08_50
        is_center_line = False
        road_type = 'branch'  # 默认为支路
        linetype_upper = linetype.upper()
        layer_upper = layer.upper()
        
        # 检查线型（支持大小写不敏感，以及可能的变体）
        if 'JIS_08_37' in linetype_upper or 'JIS08_37' in linetype_upper:
            is_center_line = True
            road_type = 'main'
            logger.debug(f"识别到主路(JIS_08_37): layer={layer}, linetype={linetype}")
        elif 'JIS_08_50' in linetype_upper or 'JIS08_50' in linetype_upper:
            is_center_line = True
            road_type = 'branch'
            logger.debug(f"识别到支路(JIS_08_50): layer={layer}, linetype={linetype}")
        # 检查图层名称（兼容旧逻辑）
        elif layer == '道路中心线' or layer_upper == '道路中心线' or '道路中心线' in layer:
            is_center_line = True
            # 如果通过图层识别，默认视为支路，除非有其他线索
            road_type = 'branch' 
            logger.debug(f"识别到道路中心线图层: layer={layer}, linetype={linetype}")
        
        if is_center_line:
            center_segments.append((start_pt, end_pt, road_type))
        # 识别道路边界线：ByLayer线型或特定图层
        elif linetype == 'ByLayer' or linetype_upper == 'BYLAYER' or layer in ['道路边界', '道路边线', '边界线', '边线']:
            boundary_segments.append((start_pt, end_pt))

    if not center_segments:
        # 提供更详细的错误信息，帮助用户调试
        all_layers = set()
        all_linetypes = set()
        for entity in ms:
            if entity.dxftype() == 'LINE':
                layer = (entity.dxf.layer or '').strip()
                linetype = (entity.dxf.linetype or '').strip()
                if layer:
                    all_layers.add(layer)
                if linetype:
                    all_linetypes.add(linetype)
        error_msg = "未在 DXF 文件中找到任何道路中心线（Layer=道路中心线 或 LineType=JIS_08_50）\n"
        if all_layers:
            error_msg += f"文件中存在的图层: {', '.join(sorted(all_layers))}\n"
        if all_linetypes:
            error_msg += f"文件中存在的线型: {', '.join(sorted(all_linetypes))}"
        raise ValueError(error_msg)
    
    logger.info(f"识别到 {len(center_segments)} 条道路中心线（JIS_08_50线型）")

    # 计算所有交点（JIS_08_50线段的交点就是节点）
    node_points: List[Tuple[float, float]] = []
    logger.info(f"开始计算 {len(center_segments)} 条JIS_08_50线段的交点...")
    
    intersection_count = 0
    for idx, (seg1_start, seg1_end, _) in enumerate(center_segments):
        seg1 = (seg1_start, seg1_end)
        for (seg2_start, seg2_end, _) in center_segments[idx + 1:]:
            seg2 = (seg2_start, seg2_end)
            point = _segment_intersection(seg1, seg2, tol=0.05)  # 增加容差到5cm，确保识别所有交点
            if point is None:
                continue
            intersection_count += 1
            rounded = _round_point(point)
            # 检查是否已存在（使用距离判断，避免精度问题）
            is_duplicate = False
            for existing in node_points:
                if math.dist(rounded, existing) < 0.05:  # 5cm容差，匹配交点计算容差
                    is_duplicate = True
                    break
            if not is_duplicate:
                node_points.append(rounded)
                logger.debug(f"找到新交点: {rounded} (原始坐标: {point})")
    
    logger.info(f"找到 {intersection_count} 个交点，去重后 {len(node_points)} 个节点")

    # 保留线段端点作为节点（避免孤立道路）
    # 端点也是节点，因为它们是道路的起点或终点
    endpoint_count = 0
    for start_pt, end_pt, _ in center_segments:
        for raw_point in (start_pt, end_pt):
            rounded = _round_point(raw_point)
            # 检查是否已存在（使用距离判断）
            is_duplicate = False
            for existing in node_points:
                if math.dist(rounded, existing) < 0.01:  # 1cm容差
                    is_duplicate = True
                    break
            if not is_duplicate:
                node_points.append(rounded)
                endpoint_count += 1
    
    logger.info(f"添加了 {endpoint_count} 个端点作为节点，总共 {len(node_points)} 个节点")

    if not node_points:
        raise ValueError("未解析到有效的道路节点，请检查 DXF 文件中的道路中心线")

    node_points.sort(key=lambda p: (p[0], p[1]))
    node_id_map: Dict[Tuple[float, float], str] = {}
    nodes: List[Dict[str, Any]] = []
    original_point_map: Dict[str, Tuple[float, float]] = {}
    
    # 创建节点时，使用四舍五入后的坐标作为key，避免精度问题
    for index, point in enumerate(node_points, start=1):
        node_id = f"N{index}"
        rounded_point = _round_point(point)  # 使用四舍五入后的坐标作为key
        node_id_map[rounded_point] = node_id
        original_point_map[node_id] = point
        nodes.append({
            'id': node_id,
            'name': f'节点{index}',
            'x': float(point[0]),  # 占位，稍后统一转换坐标
            'y': float(point[1]),
            'type': 'crossroad'
        })
    
    logger.info(f"创建了 {len(nodes)} 个节点")

    edges: List[Dict[str, Any]] = []
    created_pairs: set[Tuple[str, str]] = set()
    edge_index = 1

    for start_pt, end_pt, road_type in center_segments:
        relevant_nodes: List[Tuple[float, float]] = []
        rounded_start = _round_point(start_pt)
        rounded_end = _round_point(end_pt)
        
        # 查找这条线段上的所有节点（包括端点和中间的交点）
        # 使用更大的容差（5cm）来匹配节点，确保识别所有在线段上的交点
        for point in node_points:
            # 检查点是否在线段上（包括端点）
            # 使用点到直线距离判断，更准确
            distance = _point_to_line_distance(point, rounded_start, rounded_end)
            if distance <= 0.05:  # 5cm容差，匹配交点计算容差
                # 检查投影是否在线段范围内
                px, py = point
                x1, y1 = rounded_start
                x2, y2 = rounded_end
                dx = x2 - x1
                dy = y2 - y1
                line_length_sq = dx * dx + dy * dy
                if line_length_sq > 1e-6:
                    t = ((px - x1) * dx + (py - y1) * dy) / line_length_sq
                    # 如果投影在线段范围内或非常接近端点，认为在线段上
                    if -0.1 <= t <= 1.1:  # 允许扩展到端点外10%
                        # 避免重复添加（使用距离判断，而不是直接比较，避免精度问题）
                        is_duplicate = False
                        for existing in relevant_nodes:
                            if math.dist(point, existing) < 0.05:  # 5cm容差
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            relevant_nodes.append(point)
                            logger.debug(f"节点 {point} 在线段 ({rounded_start} -> {rounded_end}) 上，距离: {distance:.3f}m, 投影参数: {t:.3f}")
        
        # 如果找不到足够的节点，跳过这条线段
        # 至少需要2个节点（起点和终点）才能创建边
        if len(relevant_nodes) < 2:
            logger.warning(f"线段 ({start_pt} -> {end_pt}) 上只有 {len(relevant_nodes)} 个节点，跳过")
            continue

        direction = _line_direction(start_pt, end_pt)
        if direction == 'vertical':
            relevant_nodes.sort(key=lambda p: p[1])
        elif direction == 'horizontal':
            relevant_nodes.sort(key=lambda p: p[0])
        else:
            sx, sy = start_pt
            relevant_nodes.sort(key=lambda p: (p[0] - sx) ** 2 + (p[1] - sy) ** 2)

        # 确保按照节点顺序分段创建边（两个节点之间的道路就是一条边）
        logger.info(f"线段 ({start_pt[0]:.2f}, {start_pt[1]:.2f}) -> ({end_pt[0]:.2f}, {end_pt[1]:.2f}) 上有 {len(relevant_nodes)} 个节点: {[f'({p[0]:.2f}, {p[1]:.2f})' for p in relevant_nodes]}")
        if len(relevant_nodes) > 2:
            logger.info(f"将分段成 {len(relevant_nodes) - 1} 条边")
        
        for idx in range(len(relevant_nodes) - 1):
            start_point = relevant_nodes[idx]
            end_point = relevant_nodes[idx + 1]
            
            # 使用四舍五入后的坐标查找节点ID（避免精度问题）
            rounded_start = _round_point(start_point)
            rounded_end = _round_point(end_point)
            
            # 如果精确匹配失败，尝试使用距离匹配（容差1cm）
            start_id = None
            end_id = None
            
            if rounded_start in node_id_map:
                start_id = node_id_map[rounded_start]
            else:
                # 尝试距离匹配
                for point, nid in node_id_map.items():
                    if math.dist(rounded_start, point) < 0.01:
                        start_id = nid
                        break
            
            if rounded_end in node_id_map:
                end_id = node_id_map[rounded_end]
            else:
                # 尝试距离匹配
                for point, nid in node_id_map.items():
                    if math.dist(rounded_end, point) < 0.01:
                        end_id = nid
                        break
            
            if start_id is None or end_id is None:
                logger.warning(f"无法找到节点ID: start={start_point} (rounded={rounded_start}), end={end_point} (rounded={rounded_end})")
                continue
            if start_id == end_id:
                continue
            pair_key = tuple(sorted((start_id, end_id)))
            if pair_key in created_pairs:
                continue
            created_pairs.add(pair_key)
            length = math.dist(start_point, end_point)
            length_m = float(round(length, 3))
            
            # 计算道路宽度：找到与当前中心线段对应的边界线
            current_center_seg = (start_point, end_point)
            road_width = _calculate_road_width(current_center_seg, boundary_segments)
            
            # 如果计算出宽度，使用计算值；否则使用默认值
            if road_width is not None and road_width > 0:
                max_width = float(round(road_width, 3))
                # 根据道路宽度调整拥堵系数：宽路通行效率更高
                # 宽度越大，拥堵系数越小（但最小不低于0.8）
                width_factor = max(0.8, 1.0 - (max_width - 3.0) * 0.05)  # 宽度每增加1米，拥堵系数减少0.05
                congestion_coeff = max(0.8, min(1.5, width_factor))
            else:
                max_width = 6.0  # 默认宽度
                congestion_coeff = 1.0
            
            edges.append({
                'id': f"E{edge_index}",
                'start_node': start_id,
                'end_node': end_id,
                'length': length_m,
                'length_m': length_m,
                'max_weight': 50.0,
                'max_width': max_width,
                'is_available': True,
                'congestion_coeff': congestion_coeff,
                'direction': 'two-way',
                'road_type': road_type  # 存储道路类型：'main' 或 'branch'
            })
            edge_index += 1

    if not edges:
        raise ValueError("未生成任何道路，请确认道路中心线之间存在交点或端点")

    # 根据节点的度数调整类型
    degree: Dict[str, int] = {node['id']: 0 for node in nodes}
    for edge in edges:
        if edge['start_node'] in degree:
            degree[edge['start_node']] += 1
        else:
            logger.warning(f"边 {edge['id']} 的起点节点 {edge['start_node']} 不存在")
        if edge['end_node'] in degree:
            degree[edge['end_node']] += 1
        else:
            logger.warning(f"边 {edge['id']} 的终点节点 {edge['end_node']} 不存在")
    
    # 统计节点度数分布
    degree_distribution = {}
    for node in nodes:
        deg = degree.get(node['id'], 0)
        degree_distribution[deg] = degree_distribution.get(deg, 0) + 1
        if deg <= 1:
            node['type'] = 'entrance'
        elif deg >= 3:
            node['type'] = 'crossroad'
        else:
            node['type'] = 'crossroad'
    
    logger.info(f"节点度数分布: {degree_distribution}")
    logger.info(f"尽头点数量: {degree_distribution.get(0, 0) + degree_distribution.get(1, 0)}")
    logger.info(f"交叉口数量: {degree_distribution.get(2, 0) + sum(v for k, v in degree_distribution.items() if k >= 3)}")

    # 坐标转换：将 CAD 坐标转为屏幕坐标（左上角为原点，Y 轴向下）
    xs = [pt[0] for pt in node_points]
    ys = [pt[1] for pt in node_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    target_max = 1200.0
    scale = min(target_max / width, target_max / height)
    padding = 60.0

    for node in nodes:
        ox, oy = original_point_map[node['id']]
        node['x'] = float((ox - min_x) * scale + padding)
        node['y'] = float((max_y - oy) * scale + padding)  # 翻转 Y 轴

    # 根据转换后的坐标重新计算道路显示长度（但保持 length_m 不变，因为它是原始CAD坐标的米数）
    node_lookup = {node['id']: (node['x'], node['y']) for node in nodes}
    for edge in edges:
        start_pos = node_lookup[edge['start_node']]
        end_pos = node_lookup[edge['end_node']]
        edge['length_display'] = float(round(math.dist(start_pos, end_pos), 3))
        # 确保 length_m 存在且保持不变（原始CAD坐标的米数）
        if 'length_m' not in edge or edge.get('length_m') is None:
            edge['length_m'] = edge.get('length', edge['length_display'])
        # length 字段用于显示和兼容，使用 length_m
        edge['length'] = edge.get('length_m', edge['length_display'])

    return nodes, edges

