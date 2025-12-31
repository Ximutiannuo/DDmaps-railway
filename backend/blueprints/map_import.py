"""
地图导入相关 Blueprint
"""
from flask import Blueprint, request, jsonify
import tempfile
import os
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state
from backend.utils.logger import logger
import traceback

bp = Blueprint('map_import', __name__, url_prefix='/api')

# 从服务层导入
from backend.services.map_import_service import parse_dxf_file
from backend.services.system_service import _apply_map_data


@bp.route('/import-dxf', methods=['POST'])
@api_handler
def import_dxf_map():
    """上传并解析 DXF 文件，自动生成路网"""
    uploaded = request.files.get('file')
    if not uploaded:
        return jsonify({'success': False, 'message': '请上传 DXF 文件（字段名 file）'}), 400

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as temp_file:
            uploaded.save(temp_file.name)
            temp_path = temp_file.name
        nodes, edges = parse_dxf_file(temp_path)
    except ValueError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({'success': False, 'message': f'解析 DXF 时发生错误：{exc}'}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    try:
        _apply_map_data(nodes, edges)
        logger.info(f'DXF导入成功：{len(nodes)} 个节点，{len(edges)} 条道路')
        return jsonify({
            'success': True,
            'message': f'成功导入 DXF：{len(nodes)} 个节点，{len(edges)} 条道路',
            'node_count': len(nodes),
            'edge_count': len(edges)
        })
    except ValueError as exc:
        logger.error(f'DXF导入失败（数据验证）：{exc}')
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception as exc:
        logger.error(f'DXF导入失败（未知错误）：{exc}')
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'导入地图数据时发生错误：{exc}'}), 500


@bp.route('/dxf-to-json', methods=['POST'])
@api_handler
def dxf_to_json():
    """上传 DXF 文件并返回解析后的节点与道路 JSON"""
    uploaded = request.files.get('file')
    if not uploaded:
        return jsonify({'success': False, 'message': '请上传 DXF 文件（字段名 file）'}), 400

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as temp_file:
            uploaded.save(temp_file.name)
            temp_path = temp_file.name
        nodes, edges = parse_dxf_file(temp_path)
    except ValueError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({'success': False, 'message': f'解析 DXF 时发生错误：{exc}'}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return jsonify({
        'success': True,
        'node_count': len(nodes),
        'edge_count': len(edges),
        'nodes': nodes,
        'edges': edges
    })


@bp.route('/import-roadnet', methods=['POST'])
@api_handler
def import_roadnet():
    """通过 JSON 导入路网数据"""
    payload = request.json
    if not payload:
        return jsonify({'success': False, 'message': '请求体不能为空，需提供 JSON 数据'}), 400

    nodes = payload.get('nodes')
    edges = payload.get('edges')
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return jsonify({'success': False, 'message': 'JSON 中必须包含 nodes 和 edges 数组'}), 400

    # 基本校验
    node_ids = {node.get('id') for node in nodes if node.get('id')}
    if not node_ids:
        return jsonify({'success': False, 'message': '至少需要一个有效的节点（包含 id）'}), 400

    for edge in edges:
        if not edge.get('start_node') or not edge.get('end_node'):
            return jsonify({'success': False, 'message': f'道路 {edge.get("id", "")} 缺少 start_node 或 end_node'}), 400
        if edge['start_node'] not in node_ids or edge['end_node'] not in node_ids:
            return jsonify({'success': False, 'message': f'道路 {edge.get("id", "")} 引用了不存在的节点'}), 400

    try:
        _apply_map_data(nodes, edges)
        logger.info(f'成功导入 JSON 路网：{len(nodes)} 个节点，{len(edges)} 条道路')
        return jsonify({
            'success': True,
            'message': f'成功导入 JSON 路网：{len(nodes)} 个节点，{len(edges)} 条道路',
            'node_count': len(nodes),
            'edge_count': len(edges)
        })
    except ValueError as exc:
        logger.error(f'JSON路网导入失败（数据验证）：{exc}')
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception as exc:
        logger.error(f'JSON路网导入失败（未知错误）：{exc}')
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'导入地图数据时发生错误：{exc}'}), 500


@bp.route('/export-roadnet', methods=['GET'])
@api_handler
def export_roadnet():
    """导出当前路网为 JSON"""
    with system_state.lock:
        nodes = system_state.get('nodes', [])
        edges = system_state.get('edges', [])
        return jsonify({
            'success': True,
            'node_count': len(nodes),
            'edge_count': len(edges),
            'nodes': nodes,
            'edges': edges
        })

