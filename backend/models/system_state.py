"""
系统状态管理模块
"""
import threading
from typing import Dict, Any, Optional
from backend.config import Config

class SystemState:
    """系统状态单例管理类"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 线程锁
        self.lock = threading.RLock()  # 可重入锁，支持嵌套调用
        self.dqn_lock = threading.Lock()  # DQN操作专用锁
        
        # 系统状态字典
        self.state = {
            'nodes': [],
            'edges': [],
            'vehicles': [],
            'monitor_data': {},
            'dispatch_running': False,
            'vehicle_counter': 1,
            'work_zones': set(),
            'custom_congestion_edges': set(),
            'drivers': {},
            'driver_routes': {},
            'node_congestion': {},
            'edge_status': {},
            'arrival_records': [],
            'route_time_stats': {},
            'travel_time_database': [],
            'vehicle_types': {
                '渣土车': {'speed_factor': 0.3, 'can_use_one_way': True, 'can_use_two_way': True},
                '材料车': {'speed_factor': 0.4, 'can_use_one_way': True, 'can_use_two_way': True},
                '工程车': {'speed_factor': 0.25, 'can_use_one_way': True, 'can_use_two_way': True},
                '特种车': {'speed_factor': 0.5, 'can_use_one_way': False, 'can_use_two_way': True}
            },
            'edge_directions': {},
            'map_background': None,
            'map_text_labels': []  # 地图文字框列表
        }
        
        self._initialized = True
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取状态值"""
        with self.lock:
            return self.state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置状态值"""
        with self.lock:
            self.state[key] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """批量更新状态"""
        with self.lock:
            self.state.update(updates)
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        with self.lock:
            return self.state[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """支持字典式设置"""
        with self.lock:
            self.state[key] = value
    
    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        with self.lock:
            return key in self.state

# 全局单例实例
system_state = SystemState()


