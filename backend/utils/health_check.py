"""
健康检查模块
"""
from typing import Dict, Any
from datetime import datetime
import os
from backend.models.system_state import system_state
from backend.config import Config
from backend.utils.logger import logger

def health_check() -> Dict[str, Any]:
    """系统健康检查"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    try:
        with system_state.lock:
            # 检查系统状态完整性
            required_keys = ['nodes', 'edges', 'vehicles', 'monitor_data']
            for key in required_keys:
                # 检查键是否存在于 system_state.state 中
                health_status['checks'][f'{key}_exists'] = key in system_state.state
            
            # 检查数据量
            health_status['checks']['node_count'] = len(system_state.get('nodes', []))
            health_status['checks']['edge_count'] = len(system_state.get('edges', []))
            health_status['checks']['vehicle_count'] = len(system_state.get('vehicles', []))
            health_status['checks']['database_size'] = len(system_state.get('travel_time_database', []))
            health_status['checks']['arrival_records_count'] = len(system_state.get('arrival_records', []))
            health_status['checks']['driver_count'] = len(system_state.get('drivers', {}))
            
            # 检查内存使用（如果可用）
            try:
                import psutil  # type: ignore
                process = psutil.Process(os.getpid())
                mem_info = process.memory_info()
                health_status['checks']['memory_mb'] = round(mem_info.rss / 1024 / 1024, 2)
                
                # 内存使用率警告（超过500MB）
                if health_status['checks']['memory_mb'] > Config.HEALTH_CHECK_MEMORY_WARNING_MB:
                    health_status['status'] = 'degraded'
                    health_status['checks']['memory_warning'] = f"内存使用较高: {health_status['checks']['memory_mb']} MB"
            except ImportError:
                health_status['checks']['memory_mb'] = None
            
            # 检查调度状态
            health_status['checks']['dispatch_running'] = system_state.get('dispatch_running', False)
            
            # 检查检查点文件状态
            if Config.CHECKPOINT_FILE:
                health_status['checks']['checkpoint_file_path'] = str(Config.CHECKPOINT_FILE)
                health_status['checks']['checkpoint_file_exists'] = os.path.exists(Config.CHECKPOINT_FILE)
                if os.path.exists(Config.CHECKPOINT_FILE):
                    try:
                        file_size = os.path.getsize(Config.CHECKPOINT_FILE)
                        health_status['checks']['checkpoint_file_size_mb'] = round(file_size / 1024 / 1024, 2)
                    except:
                        pass
            else:
                health_status['checks']['checkpoint_file_path'] = None
                health_status['checks']['checkpoint_file_exists'] = False
            
            # 检查训练数据持久化状态
            if Config.TRAVEL_DB_FILE:
                health_status['checks']['travel_db_file_exists'] = os.path.exists(Config.TRAVEL_DB_FILE)
                if os.path.exists(Config.TRAVEL_DB_FILE):
                    try:
                        file_size = os.path.getsize(Config.TRAVEL_DB_FILE)
                        health_status['checks']['travel_db_file_size_mb'] = round(file_size / 1024 / 1024, 2)
                    except:
                        pass
            
            # 检查是否有异常数据
            health_status['checks']['data_validity'] = True
            nodes = system_state.get('nodes', [])
            edges = system_state.get('edges', [])
            # 如果节点或道路为空，只是警告，不设置为 degraded（系统可能还未初始化）
            if not nodes or not edges:
                health_status['checks']['data_validity'] = False
                health_status['checks']['data_warning'] = f'节点数={len(nodes)}，道路数={len(edges)}'
                # 只有在数据完全无效时才设置为 degraded（例如：有节点但没有道路，或相反）
                if (nodes and not edges) or (edges and not nodes):
                    health_status['status'] = 'degraded'
            
            # 检查车辆状态分布
            vehicles = system_state.get('vehicles', [])
            status_counts = {}
            for v in vehicles:
                status = v.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            health_status['checks']['vehicle_status_distribution'] = status_counts
            
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        health_status['status'] = 'unhealthy'
        health_status['error'] = str(e)
    
    return health_status


