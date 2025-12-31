"""
边/道路相关 Blueprint
"""
from flask import Blueprint, request, jsonify
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state

bp = Blueprint('edges', __name__, url_prefix='/api')

def get_node_by_id(node_id):
    """获取节点（需要从 app.py 迁移）"""
    from backend.services.path_planning_service import get_node_by_id as _get_node_by_id
    return _get_node_by_id(node_id)

@bp.route('/edges', methods=['POST'])
@api_handler
def add_edge():
    """添加边/道路"""
    data = request.json or {}
    
    edge_id = data.get('id')
    start_node_id = data.get('start_node')
    end_node_id = data.get('end_node')
    
    if not edge_id or not start_node_id or not end_node_id:
        return jsonify({'success': False, 'message': '请提供边ID、起点节点和终点节点'}), 400
    
    with system_state.lock:
        # 验证节点存在
        start_node = get_node_by_id(start_node_id)
        end_node = get_node_by_id(end_node_id)
        
        if not start_node:
            return jsonify({'success': False, 'message': f'起点节点 {start_node_id} 不存在'}), 400
        if not end_node:
            return jsonify({'success': False, 'message': f'终点节点 {end_node_id} 不存在'}), 400
        
        edges = system_state.get('edges', [])
        
        # 检查边是否已存在
        if any(e.get('id') == edge_id for e in edges):
            return jsonify({'success': False, 'message': f'边 {edge_id} 已存在'}), 400
        
        # 计算长度（如果未提供）
        length = data.get('length')
        if not length:
            import math
            dx = end_node['x'] - start_node['x']
            dy = end_node['y'] - start_node['y']
            length = math.sqrt(dx * dx + dy * dy)
        
        new_edge = {
            'id': edge_id,
            'start_node': start_node_id,
            'end_node': end_node_id,
            'length': float(length),
            'max_weight': float(data.get('max_weight', 50)),
            'max_width': float(data.get('max_width', 5)),
            'is_available': data.get('is_available', True),
            'congestion_coeff': float(data.get('congestion_coeff', 1.0)),
            'direction': data.get('direction', 'two-way')
        }
        
        edges.append(new_edge)
        system_state.set('edges', edges)
        
        # 更新边方向映射
        edge_directions = system_state.get('edge_directions', {})
        edge_directions[edge_id] = new_edge['direction']
        system_state.set('edge_directions', edge_directions)
        
        # 刷新边几何（需要从 app.py 迁移）
        try:
            from backend.services.path_planning_service import refresh_edge_geometry
            refresh_edge_geometry()
        except:
            pass
        
        return jsonify({
            'success': True,
            'edge': new_edge,
            'message': f'边 {edge_id} 添加成功'
        })

@bp.route('/edges/<edge_id>/status', methods=['POST'])
@api_handler
def update_edge_status(edge_id):
    """更新边/道路状态"""
    data = request.json or {}
    from datetime import datetime
    
    # 支持两种方式：
    # 1. 使用 status 字符串：'normal', 'congested', 'construction', 'closed'
    # 2. 使用 is_available 布尔值（向后兼容）
    status = data.get('status')
    is_available = data.get('is_available')
    
    with system_state.lock:
        edges = system_state.get('edges', [])
        edge = next((e for e in edges if e.get('id') == edge_id), None)
        
        if not edge:
            return jsonify({'success': False, 'message': f'边 {edge_id} 不存在'}), 404
        
        # 更新边状态映射
        edge_status_dict = system_state.get('edge_status', {})
        
        # 如果提供了 status 字符串
        if status is not None:
            valid_statuses = ['normal', 'congested', 'construction', 'closed']
            if status not in valid_statuses:
                return jsonify({'success': False, 'message': f'状态必须是以下之一: {", ".join(valid_statuses)}'}), 400
            
            # 根据状态设置 is_available
            if status == 'closed':
                edge['is_available'] = False
            else:
                edge['is_available'] = True
            
            # 更新 edge_status 字典（存储状态字符串）
            edge_status_dict[edge_id] = status
            system_state.set('edge_status', edge_status_dict)
            
            # 根据状态设置拥堵系数
            if status == 'congested':
                edge['congestion_coeff'] = 2.0
            elif status == 'construction':
                edge['congestion_coeff'] = 999.0  # 占道施工，路径算法会避开
            elif status == 'closed':
                edge['congestion_coeff'] = 999.0  # 封闭，路径算法会避开
            elif status == 'normal':
                # 正常状态，恢复默认拥堵系数（除非有自定义拥堵）
                if edge.get('congestion_coeff', 1.0) >= 999.0:
                    edge['congestion_coeff'] = 1.0
            
        # 如果只提供了 is_available（向后兼容）
        elif is_available is not None:
            edge['is_available'] = bool(is_available)
            # 如果设置为不可用，状态设为 closed
            if not is_available:
                edge_status_dict[edge_id] = 'closed'
            # 如果设置为可用，且当前状态是 closed，改为 normal
            elif edge_status_dict.get(edge_id) == 'closed':
                edge_status_dict[edge_id] = 'normal'
            system_state.set('edge_status', edge_status_dict)
        else:
            return jsonify({'success': False, 'message': '请提供 status 或 is_available 参数'}), 400
        
        system_state.set('edges', edges)
        
        # 触发监控数据更新（如果需要）
        try:
            from backend.services.system_service import update_monitor_data
            update_monitor_data()
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': f'边 {edge_id} 状态已更新',
            'status': edge_status_dict.get(edge_id, 'normal'),
            'is_available': edge['is_available']
        })

@bp.route('/edges/<edge_id>/congestion', methods=['POST'])
@api_handler
def update_edge_congestion(edge_id):
    """更新边/道路拥堵系数"""
    data = request.json or {}
    congestion_coeff = data.get('congestion_coeff')
    
    if congestion_coeff is None:
        return jsonify({'success': False, 'message': '请提供 congestion_coeff'}), 400
    
    with system_state.lock:
        edges = system_state.get('edges', [])
        edge = next((e for e in edges if e.get('id') == edge_id), None)
        
        if not edge:
            return jsonify({'success': False, 'message': f'边 {edge_id} 不存在'}), 404
        
        edge['congestion_coeff'] = float(congestion_coeff)
        system_state.set('edges', edges)
        
        return jsonify({
            'success': True,
            'message': f'边 {edge_id} 拥堵系数已更新',
            'congestion_coeff': float(congestion_coeff)
        })

@bp.route('/edges/<edge_id>/direction', methods=['POST'])
@api_handler
def update_edge_direction(edge_id):
    """更新边/道路方向"""
    data = request.json or {}
    direction = data.get('direction')
    
    if not direction:
        return jsonify({'success': False, 'message': '请提供 direction'}), 400
    
    # 允许的方向值：双向、反向，以及8个方向字符串（单向）
    valid_directions = ['two-way', 'reverse'] + [
        'north', 'south', 'east', 'west',
        'northeast', 'northwest', 'southeast', 'southwest'
    ]
    
    if direction not in valid_directions:
        return jsonify({'success': False, 'message': f'方向必须是以下之一: {", ".join(valid_directions)}'}), 400
    
    with system_state.lock:
        edges = system_state.get('edges', [])
        edge = next((e for e in edges if e.get('id') == edge_id), None)
        
        if not edge:
            return jsonify({'success': False, 'message': f'边 {edge_id} 不存在'}), 404
        
        # 如果是 reverse，需要反转起点和终点，并计算新的方向
        if direction == 'reverse':
            start_node = get_node_by_id(edge['start_node'])
            end_node = get_node_by_id(edge['end_node'])
            
            if not start_node or not end_node:
                return jsonify({'success': False, 'message': '无法反转：节点不存在'}), 400
            
            # 交换起点和终点
            edge['start_node'], edge['end_node'] = edge['end_node'], edge['start_node']
            
            # 计算新的方向（交换后的方向）
            from backend.services.path_planning_service import calculate_direction
            # 使用交换后的节点（注意这里 start_node 和 end_node 还是原来的，需要交换）
            new_start_node = get_node_by_id(edge['start_node'])  # 现在是原来的 end_node
            new_end_node = get_node_by_id(edge['end_node'])      # 现在是原来的 start_node
            if new_start_node and new_end_node:
                new_direction = calculate_direction(new_start_node, new_end_node)
                direction = new_direction
        
        edge['direction'] = direction
        system_state.set('edges', edges)
        
        # 更新边方向映射
        edge_directions = system_state.get('edge_directions', {})
        edge_directions[edge_id] = direction
        system_state.set('edge_directions', edge_directions)
        
        return jsonify({
            'success': True,
            'message': f'边 {edge_id} 方向已更新',
            'direction': direction
        })

@bp.route('/edges/<edge_id>/name', methods=['POST'])
@api_handler
def update_edge_name(edge_id):
    """更新边/道路名称和格式"""
    data = request.json or {}
    name = data.get('name')
    
    if name is None:
        return jsonify({'success': False, 'message': '请提供道路名称'}), 400
    
    with system_state.lock:
        edges = system_state.get('edges', [])
        edge = next((e for e in edges if e.get('id') == edge_id), None)
        
        if not edge:
            return jsonify({'success': False, 'message': f'边 {edge_id} 不存在'}), 404
        
        # 更新道路名称和格式属性
        edge['name'] = str(name).strip()
        # 更新格式属性（如果提供）
        if 'label_font_size' in data:
            edge['label_font_size'] = float(data['label_font_size'])
        if 'label_font_family' in data:
            edge['label_font_family'] = data['label_font_family']
        if 'label_font_weight' in data:
            edge['label_font_weight'] = data['label_font_weight']
        if 'label_color' in data:
            edge['label_color'] = data['label_color']
        if 'label_background_color' in data:
            edge['label_background_color'] = data['label_background_color']
        if 'label_border_color' in data:
            edge['label_border_color'] = data['label_border_color']
        if 'label_border_width' in data:
            edge['label_border_width'] = float(data['label_border_width'])
        if 'label_border_radius' in data:
            edge['label_border_radius'] = float(data['label_border_radius'])
        if 'label_padding' in data:
            edge['label_padding'] = float(data['label_padding'])
        
        system_state.set('edges', edges)
        
        return jsonify({
            'success': True,
            'message': f'道路 {edge_id} 名称已更新',
            'edge': edge
        })

@bp.route('/roads', methods=['GET'])
@api_handler
def get_roads():
    """获取路网信息（包含方向信息）"""
    with system_state.lock:
        # 确保返回最新的拥堵系数（包括节点拥堵对道路的影响）
        from backend.services.system_service import update_monitor_data
        update_monitor_data()
        
        nodes = system_state.get('nodes', [])
        edges = system_state.get('edges', [])
        edge_directions = system_state.get('edge_directions', {})
        
        # 为每条边添加方向信息
        roads = []
        for edge in edges:
            road = edge.copy()
            road['direction'] = edge_directions.get(edge['id'], edge.get('direction', 'two-way'))
            roads.append(road)
        
        # 获取方向类型配置
        from backend.config import Config
        direction_types = getattr(Config, 'DIRECTION_TYPES', {
            'two-way': '双向',
            'east': '东',
            'northeast': '东北',
            'north': '北',
            'northwest': '西北',
            'west': '西',
            'southwest': '西南',
            'south': '南',
            'southeast': '东南'
        })
        
        return jsonify({
            'success': True,
            'nodes': nodes,
            'edges': edges,
            'roads': roads,  # 保持兼容性
            'direction_types': direction_types
        })


