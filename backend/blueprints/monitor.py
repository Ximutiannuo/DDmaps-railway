"""
监控相关 Blueprint
"""
from flask import Blueprint, jsonify
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state
from backend.config import Config

bp = Blueprint('monitor', __name__, url_prefix='/api')

def update_monitor_data():
    """更新监控数据（需要从 app.py 迁移）"""
    from backend.services.system_service import update_monitor_data as _update_monitor_data
    return _update_monitor_data()

@bp.route('/monitor', methods=['GET'])
@api_handler
def get_monitor_data():
    """获取监控数据"""
    with system_state.lock:
        if Config.ON_PYTHONANYWHERE:
            update_monitor_data()
        
        return jsonify({
            'success': True,
            'monitor_data': system_state.get('monitor_data', {}),
            'work_zones': list(system_state.get('work_zones', set())),
            'node_congestion': system_state.get('node_congestion', {}),
            'edge_status': system_state.get('edge_status', {}),
            'arrival_records': system_state.get('arrival_records', [])[-50:],
            'route_time_stats': system_state.get('route_time_stats', {}),
            'travel_time_database': system_state.get('travel_time_database', [])[-200:]
        })

@bp.route('/websocket-status', methods=['GET'])
@api_handler
def get_websocket_status():
    """检测 WebSocket 是否可用"""
    try:
        # 使用字符串导入避免循环导入
        import sys
        if 'app' in sys.modules:
            app_module = sys.modules['app']
            socketio = getattr(app_module, 'socketio', None)
            WEBSOCKET_ENABLED = getattr(app_module, 'WEBSOCKET_ENABLED', False)
            ON_PYTHONANYWHERE = getattr(app_module, 'ON_PYTHONANYWHERE', False)
            socketio_available = getattr(app_module, 'socketio_available', False)
        else:
            socketio = None
            WEBSOCKET_ENABLED = False
            ON_PYTHONANYWHERE = Config.ON_PYTHONANYWHERE
            socketio_available = False
        
        # 在 PythonAnywhere 环境下，WebSocket 不可用（免费账户不支持）
        if ON_PYTHONANYWHERE:
            websocket_available = False
        else:
            # WebSocket 可用需要同时满足：SocketIO 库可用、WebSocket 已启用、socketio 对象已创建
            websocket_available = socketio_available and WEBSOCKET_ENABLED and socketio is not None
            
            # 如果不在 PythonAnywhere 且 SocketIO 库可用，即使 socketio 对象为 None，也允许尝试连接
            # （可能是初始化问题或检测时机问题，让 Socket.IO 客户端尝试连接，它会自动处理）
            if socketio_available and WEBSOCKET_ENABLED:
                # 在局域网环境下，如果 SocketIO 库可用且已启用，即使 socketio 对象可能未初始化，也允许尝试连接
                # 这样可以避免初始化时序问题导致的误判
                websocket_available = True
        
        return jsonify({
            'success': True,
            'websocket_enabled': websocket_available,
            'on_pythonanywhere': ON_PYTHONANYWHERE,
            'socketio_available': socketio_available,
            'transport_mode': 'polling' if ON_PYTHONANYWHERE else ('websocket_or_polling' if websocket_available else 'polling'),
            'message': 'WebSocket 可用' if websocket_available else ('WebSocket 不可用，将使用 HTTP 轮询' if ON_PYTHONANYWHERE else 'WebSocket 可用，将尝试连接')
        })
    except Exception as e:
        # 如果检测失败，在局域网环境下默认允许尝试连接
        on_pythonanywhere = Config.ON_PYTHONANYWHERE
        return jsonify({
            'success': True,
            'websocket_enabled': not on_pythonanywhere,  # 不在 PythonAnywhere 时允许尝试
            'on_pythonanywhere': on_pythonanywhere,
            'transport_mode': 'polling' if on_pythonanywhere else 'websocket_or_polling',
            'message': f'无法检测 WebSocket 状态: {str(e)}，将尝试连接' if not on_pythonanywhere else f'无法检测 WebSocket 状态: {str(e)}'
        })


