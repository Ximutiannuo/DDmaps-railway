"""
监控服务模块
"""
from typing import Dict, Any
from backend.models.system_state import system_state
from backend.services.system_service import update_monitor_data
from backend.config import Config


def get_monitor_data() -> Dict[str, Any]:
    """获取监控数据"""
    if Config.ON_PYTHONANYWHERE:
        update_monitor_data()
    
    return {
        'monitor_data': system_state.get('monitor_data', {}),
        'work_zones': list(system_state.get('work_zones', set())),
        'node_congestion': system_state.get('node_congestion', {}),
        'edge_status': system_state.get('edge_status', {}),
        'arrival_records': system_state.get('arrival_records', [])[-50:],
        'route_time_stats': system_state.get('route_time_stats', {}),
        'travel_time_database': system_state.get('travel_time_database', [])[-200:]
    }

