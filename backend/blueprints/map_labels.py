"""
地图文字框相关 Blueprint
"""
from flask import Blueprint, request, jsonify
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state
from datetime import datetime
from uuid import uuid4

bp = Blueprint('map_labels', __name__, url_prefix='/api')

@bp.route('/map-labels', methods=['GET'])
@api_handler
def get_map_labels():
    """获取所有地图文字框"""
    with system_state.lock:
        labels = system_state.get('map_text_labels', [])
        return jsonify({
            'success': True,
            'labels': labels
        })

@bp.route('/map-labels', methods=['POST'])
@api_handler
def add_map_label():
    """添加地图文字框"""
    data = request.json or {}
    
    # 验证必需字段
    x = data.get('x')
    y = data.get('y')
    text = data.get('text', '').strip()
    
    if x is None or y is None:
        return jsonify({'success': False, 'message': '请提供 x 和 y 坐标'}), 400
    
    if not text:
        return jsonify({'success': False, 'message': '请提供文字内容'}), 400
    
    with system_state.lock:
        labels = system_state.get('map_text_labels', [])
        
        new_label = {
            'id': data.get('id') or f'label-{uuid4().hex[:8]}',
            'x': float(x),
            'y': float(y),
            'text': text,
            'font_size': float(data.get('font_size', 14)),
            'font_family': data.get('font_family', 'Arial'),
            'font_weight': data.get('font_weight', 'normal'),
            'color': data.get('color', '#000000'),
            'background_color': data.get('background_color', 'transparent'),
            'border_color': data.get('border_color', 'transparent'),
            'border_width': float(data.get('border_width', 0)),
            'border_radius': float(data.get('border_radius', 0)),
            'padding': float(data.get('padding', 4)),
            'opacity': float(data.get('opacity', 1.0)),
            'rotation': float(data.get('rotation', 0)),
            'z_index': int(data.get('z_index', 1)),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        labels.append(new_label)
        system_state.set('map_text_labels', labels)
        
        return jsonify({
            'success': True,
            'label': new_label,
            'message': '文字框添加成功'
        })

@bp.route('/map-labels/<label_id>', methods=['PUT'])
@api_handler
def update_map_label(label_id):
    """更新地图文字框"""
    data = request.json or {}
    
    with system_state.lock:
        labels = system_state.get('map_text_labels', [])
        label = next((l for l in labels if l.get('id') == label_id), None)
        
        if not label:
            return jsonify({'success': False, 'message': f'文字框 {label_id} 不存在'}), 404
        
        # 更新字段
        if 'x' in data:
            label['x'] = float(data['x'])
        if 'y' in data:
            label['y'] = float(data['y'])
        if 'text' in data:
            label['text'] = str(data['text']).strip()
        if 'font_size' in data:
            label['font_size'] = float(data['font_size'])
        if 'font_family' in data:
            label['font_family'] = data['font_family']
        if 'font_weight' in data:
            label['font_weight'] = data['font_weight']
        if 'color' in data:
            label['color'] = data['color']
        if 'background_color' in data:
            label['background_color'] = data['background_color']
        if 'border_color' in data:
            label['border_color'] = data['border_color']
        if 'border_width' in data:
            label['border_width'] = float(data['border_width'])
        if 'border_radius' in data:
            label['border_radius'] = float(data['border_radius'])
        if 'padding' in data:
            label['padding'] = float(data['padding'])
        if 'opacity' in data:
            label['opacity'] = float(data['opacity'])
        if 'rotation' in data:
            label['rotation'] = float(data['rotation'])
        if 'z_index' in data:
            label['z_index'] = int(data['z_index'])
        
        label['updated_at'] = datetime.now().isoformat()
        system_state.set('map_text_labels', labels)
        
        return jsonify({
            'success': True,
            'label': label,
            'message': f'文字框 {label_id} 已更新'
        })

@bp.route('/map-labels/<label_id>', methods=['DELETE'])
@api_handler
def delete_map_label(label_id):
    """删除地图文字框"""
    with system_state.lock:
        labels = system_state.get('map_text_labels', [])
        label = next((l for l in labels if l.get('id') == label_id), None)
        
        if not label:
            return jsonify({'success': False, 'message': f'文字框 {label_id} 不存在'}), 404
        
        labels = [l for l in labels if l.get('id') != label_id]
        system_state.set('map_text_labels', labels)
        
        return jsonify({
            'success': True,
            'message': f'文字框 {label_id} 已删除'
        })

