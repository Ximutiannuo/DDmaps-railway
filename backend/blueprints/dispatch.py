"""
调度相关 Blueprint
"""
from flask import Blueprint, request, jsonify
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state

bp = Blueprint('dispatch', __name__, url_prefix='/api')

@bp.route('/dispatch/start', methods=['POST'])
@api_handler
def start_dispatch():
    """启动调度"""
    with system_state.lock:
        if system_state.get('dispatch_running', False):
            return jsonify({
                'success': False,
                'message': '调度已在运行中'
            }), 400
        
        system_state.set('dispatch_running', True)
        
        return jsonify({
            'success': True,
            'message': '调度已启动'
        })

@bp.route('/dispatch/stop', methods=['POST'])
@api_handler
def stop_dispatch():
    """停止调度"""
    with system_state.lock:
        if not system_state.get('dispatch_running', False):
            return jsonify({
                'success': False,
                'message': '调度未在运行'
            }), 400
        
        system_state.set('dispatch_running', False)
        
        return jsonify({
            'success': True,
            'message': '调度已停止'
        })

@bp.route('/dispatch/status', methods=['GET'])
@api_handler
def get_dispatch_status():
    """获取调度状态"""
    with system_state.lock:
        return jsonify({
            'success': True,
            'dispatch_running': system_state.get('dispatch_running', False),
            'vehicle_count': len(system_state.get('vehicles', []))
        })


