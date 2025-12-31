"""
节点相关 Blueprint
"""
from flask import Blueprint, request, jsonify
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state

bp = Blueprint('nodes', __name__, url_prefix='/api')

def get_node_by_id(node_id):
    """获取节点（需要从 app.py 迁移）"""
    from backend.services.path_planning_service import get_node_by_id as _get_node_by_id
    return _get_node_by_id(node_id)

@bp.route('/nodes', methods=['GET'])
@api_handler
def get_nodes():
    """获取节点列表"""
    with system_state.lock:
        nodes = system_state.get('nodes', [])
        return jsonify({
            'success': True,
            'nodes': nodes
        })

@bp.route('/nodes', methods=['POST'])
@api_handler
def add_node():
    """添加节点"""
    data = request.json or {}
    
    with system_state.lock:
        nodes = system_state.get('nodes', [])
        
        # 如果没有提供节点ID，自动生成一个
        node_id = data.get('id')
        if not node_id:
            # 生成新的节点ID：查找现有的最大序号，然后+1
            max_index = 0
            for node in nodes:
                node_id_str = node.get('id', '')
                # 尝试从节点ID中提取数字（例如 N1_2 -> 2）
                import re
                match = re.search(r'N(\d+)(?:_(\d+))?', node_id_str)
                if match:
                    row = int(match.group(1))
                    col = int(match.group(2)) if match.group(2) else 0
                    # 计算序号（假设是N行_M列的格式）
                    index = row * 1000 + col
                    max_index = max(max_index, index)
            
            # 生成新ID（格式：N行_列）
            new_row = (max_index // 1000) + 1
            new_col = (max_index % 1000) + 1
            node_id = f'N{new_row}_{new_col}'
        
        # 检查节点是否已存在
        if any(n.get('id') == node_id for n in nodes):
            return jsonify({'success': False, 'message': f'节点 {node_id} 已存在'}), 400
        
        new_node = {
            'id': node_id,
            'name': data.get('name', node_id),
            'x': float(data.get('x', 0)),
            'y': float(data.get('y', 0)),
            'type': data.get('type', 'crossroad'),
            # GPS坐标（可选，高精度保留6位小数）
            'latitude': round(float(data['latitude']), 6) if data.get('latitude') is not None else None,
            'longitude': round(float(data['longitude']), 6) if data.get('longitude') is not None else None
        }
        
        nodes.append(new_node)
        system_state.set('nodes', nodes)
        
        return jsonify({
            'success': True,
            'node': new_node,
            'message': f'节点 {node_id} 添加成功'
        })

@bp.route('/nodes/<node_id>', methods=['DELETE'])
@api_handler
def delete_node(node_id):
    """删除节点"""
    with system_state.lock:
        nodes = system_state.get('nodes', [])
        node = get_node_by_id(node_id)
        
        if not node:
            return jsonify({'success': False, 'message': f'节点 {node_id} 不存在'}), 404
        
        # 检查是否有边连接到此节点
        edges = system_state.get('edges', [])
        connected_edges = [
            e for e in edges 
            if e.get('start_node') == node_id or e.get('end_node') == node_id
        ]
        
        if connected_edges:
            return jsonify({
                'success': False,
                'message': f'节点 {node_id} 仍有 {len(connected_edges)} 条边连接，无法删除'
            }), 400
        
        # 删除节点
        nodes = [n for n in nodes if n.get('id') != node_id]
        system_state.set('nodes', nodes)
        
        return jsonify({
            'success': True,
            'message': f'节点 {node_id} 删除成功'
        })

@bp.route('/nodes/<node_id>/position', methods=['POST'])
@api_handler
def update_node_position(node_id):
    """更新节点位置"""
    data = request.json or {}
    
    x = data.get('x')
    y = data.get('y')
    
    if x is None or y is None:
        return jsonify({'success': False, 'message': '请提供 x 和 y 坐标'}), 400
    
    with system_state.lock:
        nodes = system_state.get('nodes', [])
        node = get_node_by_id(node_id)
        
        if not node:
            return jsonify({'success': False, 'message': f'节点 {node_id} 不存在'}), 404
        
        # 更新节点位置
        for n in nodes:
            if n.get('id') == node_id:
                n['x'] = float(x)
                n['y'] = float(y)
                break
        
        system_state.set('nodes', nodes)
        
        # 刷新边几何（需要从 app.py 迁移）
        try:
            from backend.services.path_planning_service import refresh_edge_geometry
            refresh_edge_geometry()
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': f'节点 {node_id} 位置已更新',
            'node': get_node_by_id(node_id)
        })

@bp.route('/nodes/<node_id>/congestion', methods=['POST'])
@api_handler
def update_node_congestion(node_id):
    """更新节点拥堵状态"""
    data = request.json or {}
    congestion_level = data.get('congestion_level', 0)
    
    with system_state.lock:
        node = get_node_by_id(node_id)
        
        if not node:
            return jsonify({'success': False, 'message': f'节点 {node_id} 不存在'}), 404
        
        node_congestion = system_state.get('node_congestion', {})
        if congestion_level == 0:
            # 正常状态，删除拥堵记录
            if node_id in node_congestion:
                del node_congestion[node_id]
        else:
            # 存储为数字，与其他服务保持一致
            node_congestion[node_id] = int(congestion_level)
        system_state.set('node_congestion', node_congestion)
        
        # 立即应用节点拥堵状态到相关道路（更新道路的congestion_coeff）
        from backend.services.system_service import update_monitor_data
        update_monitor_data()
        
        return jsonify({
            'success': True,
            'message': f'节点 {node_id} 拥堵状态已更新',
            'congestion_level': congestion_level
        })

@bp.route('/nodes/<node_id>/gps', methods=['POST'])
@api_handler
def set_node_gps(node_id):
    """设置节点的GPS坐标"""
    from backend.services.node_service import set_node_gps_coordinates
    
    data = request.json or {}
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if latitude is None or longitude is None:
        return jsonify({'success': False, 'message': '请提供纬度和经度'}), 400
    
    try:
        latitude = float(latitude)
        longitude = float(longitude)
        
        # 验证GPS坐标范围
        if not (-90 <= latitude <= 90):
            return jsonify({'success': False, 'message': '纬度必须在-90到90之间'}), 400
        if not (-180 <= longitude <= 180):
            return jsonify({'success': False, 'message': '经度必须在-180到180之间'}), 400
        
        # 保留两位小数
        latitude = round(latitude, 6)
        longitude = round(longitude, 6)
        
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'GPS坐标格式不正确'}), 400
    
    with system_state.lock:
        node = get_node_by_id(node_id)
        
        if not node:
            return jsonify({'success': False, 'message': f'节点 {node_id} 不存在'}), 404
        
        success = set_node_gps_coordinates(node_id, latitude, longitude)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'节点 {node_id} GPS坐标已设置: ({latitude:.6f}, {longitude:.6f})',
                'node': get_node_by_id(node_id)
            })
        else:
            return jsonify({'success': False, 'message': '设置GPS坐标失败'}), 400

@bp.route('/nodes/<node_id>/gps', methods=['GET'])
@api_handler
def get_node_gps(node_id):
    """获取节点的GPS坐标"""
    node = get_node_by_id(node_id)
    
    if not node:
        return jsonify({'success': False, 'message': f'节点 {node_id} 不存在'}), 404
    
    has_gps = node.get('latitude') is not None and node.get('longitude') is not None
    
    return jsonify({
        'success': True,
        'node_id': node_id,
        'has_gps': has_gps,
        'latitude': round(node.get('latitude'), 6) if node.get('latitude') is not None else None,
        'longitude': round(node.get('longitude'), 6) if node.get('longitude') is not None else None,
        'message': '已获取GPS坐标' if has_gps else '该节点尚未设置GPS坐标'
    })

@bp.route('/nodes/<node_id>/name', methods=['POST'])
@api_handler
def update_node_name(node_id):
    """更新节点名称和格式"""
    data = request.json or {}
    name = data.get('name')
    
    if name is None:
        return jsonify({'success': False, 'message': '请提供节点名称'}), 400
    
    with system_state.lock:
        nodes = system_state.get('nodes', [])
        node = get_node_by_id(node_id)
        
        if not node:
            return jsonify({'success': False, 'message': f'节点 {node_id} 不存在'}), 404
        
        # 更新节点名称和格式属性
        for n in nodes:
            if n.get('id') == node_id:
                n['name'] = str(name).strip()
                # 更新格式属性（如果提供）
                if 'label_font_size' in data:
                    n['label_font_size'] = float(data['label_font_size'])
                if 'label_font_family' in data:
                    n['label_font_family'] = data['label_font_family']
                if 'label_font_weight' in data:
                    n['label_font_weight'] = data['label_font_weight']
                if 'label_color' in data:
                    n['label_color'] = data['label_color']
                if 'label_background_color' in data:
                    n['label_background_color'] = data['label_background_color']
                if 'label_border_color' in data:
                    n['label_border_color'] = data['label_border_color']
                if 'label_border_width' in data:
                    n['label_border_width'] = float(data['label_border_width'])
                if 'label_border_radius' in data:
                    n['label_border_radius'] = float(data['label_border_radius'])
                if 'label_padding' in data:
                    n['label_padding'] = float(data['label_padding'])
                break
        
        system_state.set('nodes', nodes)
        
        return jsonify({
            'success': True,
            'message': f'节点 {node_id} 名称已更新',
            'node': get_node_by_id(node_id)
        })

@bp.route('/nodes/<node_id>/visibility', methods=['POST'])
@api_handler
def update_node_visibility(node_id):
    """更新节点显示状态"""
    data = request.json or {}
    is_visible = data.get('is_visible')
    
    if is_visible is None:
        return jsonify({'success': False, 'message': '请提供 is_visible 参数'}), 400
    
    with system_state.lock:
        nodes = system_state.get('nodes', [])
        node = get_node_by_id(node_id)
        
        if not node:
            return jsonify({'success': False, 'message': f'节点 {node_id} 不存在'}), 404
        
        # 更新节点显示状态
        for n in nodes:
            if n.get('id') == node_id:
                # 将 is_visible 转换为布尔值
                if is_visible:
                    n['is_visible'] = True
                else:
                    # 如果设置为 False，可以删除字段或设置为 False
                    # 为了兼容性，设置为 False
                    n['is_visible'] = False
                break
        
        system_state.set('nodes', nodes)
        
        return jsonify({
            'success': True,
            'message': f'节点 {node_id} 显示状态已更新',
            'node': get_node_by_id(node_id)
        })


