# app.py 重构方案

## 当前问题
- 单文件 4334 行，维护困难
- 功能耦合严重，难以测试
- 代码组织不清晰，查找困难

## 重构目标
1. 按功能模块拆分
2. 使用 Flask Blueprint 组织路由
3. 分离业务逻辑和路由处理
4. 保持向后兼容
5. 提高代码可测试性

## 建议的目录结构

```
backend/
├── __init__.py              # Flask 应用工厂
├── config.py                # 配置管理
├── app.py                   # 应用入口（精简版，<200行）
├── models/                  # 数据模型
│   ├── __init__.py
│   ├── system_state.py     # 系统状态管理
│   └── types.py            # 类型定义
├── utils/                   # 工具函数
│   ├── __init__.py
│   ├── rate_limiter.py     # 限流器
│   ├── logger.py           # 日志配置
│   ├── health_check.py     # 健康检查
│   ├── memory_management.py # 内存管理
│   └── persistence.py      # 数据持久化
├── services/                # 业务逻辑层
│   ├── __init__.py
│   ├── path_planning.py    # 路径规划服务
│   ├── vehicle_service.py  # 车辆管理服务
│   ├── driver_service.py   # 司机管理服务
│   ├── monitor_service.py  # 监控服务
│   ├── dqn_service.py      # DQN服务
│   └── dxf_parser.py        # DXF解析服务
├── blueprints/              # Flask Blueprint 路由
│   ├── __init__.py
│   ├── health.py           # 健康检查路由
│   ├── vehicles.py         # 车辆相关路由
│   ├── drivers.py          # 司机相关路由
│   ├── nodes.py            # 节点相关路由
│   ├── edges.py            # 道路相关路由
│   ├── monitor.py          # 监控相关路由
│   ├── dqn.py              # DQN相关路由
│   ├── travel_time.py      # 行驶时间数据库路由
│   ├── dispatch.py         # 调度控制路由
│   └── map_import.py       # 地图导入路由
└── workers/                 # 后台工作线程
    ├── __init__.py
    └── dispatch_worker.py  # 调度工作线程
```

## 重构步骤

### 阶段 1：创建基础结构（不影响现有功能）

1. **创建 `backend/` 目录结构**
2. **提取配置到 `config.py`**
   - 环境变量
   - 文件路径
   - 常量定义

3. **提取工具函数到 `utils/`**
   - 限流器
   - 日志配置
   - 健康检查
   - 内存管理
   - 数据持久化

### 阶段 2：提取业务逻辑（保持接口不变）

4. **创建 `models/system_state.py`**
   - 系统状态管理
   - 线程锁管理

5. **创建 `services/` 模块**
   - 路径规划服务
   - 车辆管理服务
   - 司机管理服务
   - 监控服务
   - DQN服务

### 阶段 3：拆分路由（使用 Blueprint）

6. **创建 `blueprints/` 模块**
   - 按功能域拆分路由
   - 每个 Blueprint 负责一组相关路由

7. **更新 `app.py`**
   - 使用应用工厂模式
   - 注册所有 Blueprint
   - 保持启动逻辑

### 阶段 4：提取后台任务

8. **创建 `workers/` 模块**
   - 调度工作线程
   - 维护任务线程

## 详细拆分方案

### 1. config.py - 配置管理

```python
import os
from pathlib import Path

class Config:
    # 环境检测
    ON_PYTHONANYWHERE = 'PYTHONANYWHERE_DOMAIN' in os.environ
    
    # 文件路径
    BASE_DIR = Path(__file__).parent.parent
    CHECKPOINT_FILE = BASE_DIR / 'system_checkpoint.json' if not ON_PYTHONANYWHERE else None
    TRAVEL_DB_FILE = BASE_DIR / 'travel_time_database.json' if not ON_PYTHONANYWHERE else None
    TRAVEL_DB_BACKUP_DIR = BASE_DIR / 'travel_db_backups' if not ON_PYTHONANYWHERE else None
    LOG_FILE = BASE_DIR / 'traffic_system.log' if not ON_PYTHONANYWHERE else None
    
    # 限流配置
    RATE_LIMIT_MAX_REQUESTS = 200
    RATE_LIMIT_WINDOW_SECONDS = 60
    
    # 内存管理配置
    MAX_ARRIVAL_RECORDS = 5000
    MAX_DRIVER_ROUTES = 20
    MAX_TRAVEL_TIME_RECORDS = 1000000
    TRAVEL_DB_SAVE_INTERVAL = 50
    
    # 维护任务配置
    MAINTENANCE_INTERVAL = 300  # 5分钟
```

### 2. models/system_state.py - 系统状态管理

```python
import threading
from typing import Dict, Any

class SystemState:
    """系统状态单例"""
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
        if self._initialized:
            return
        
        self.lock = threading.RLock()
        self.dqn_lock = threading.Lock()
        
        self.state = {
            'nodes': [],
            'edges': [],
            'vehicles': [],
            # ... 其他状态
        }
        
        self._initialized = True
    
    def get(self, key, default=None):
        with self.lock:
            return self.state.get(key, default)
    
    def set(self, key, value):
        with self.lock:
            self.state[key] = value
    
    def update(self, updates: Dict[str, Any]):
        with self.lock:
            self.state.update(updates)

# 全局实例
system_state = SystemState()
```

### 3. blueprints/vehicles.py - 车辆路由示例

```python
from flask import Blueprint, request, jsonify
from backend.services.vehicle_service import VehicleService
from backend.utils.rate_limiter import api_handler

vehicles_bp = Blueprint('vehicles', __name__, url_prefix='/api/vehicles')

@vehicles_bp.route('', methods=['GET'])
@api_handler
def get_vehicles():
    """获取车辆列表"""
    service = VehicleService()
    vehicles = service.get_all_vehicles()
    return jsonify({
        'success': True,
        'vehicles': vehicles
    })

@vehicles_bp.route('', methods=['POST'])
@api_handler
def add_vehicle():
    """添加车辆"""
    data = request.json or {}
    service = VehicleService()
    vehicle = service.create_vehicle(data)
    return jsonify({
        'success': True,
        'vehicle': vehicle,
        'message': f'车辆 {vehicle["id"]} 添加成功'
    })
```

### 4. backend/__init__.py - 应用工厂

```python
from flask import Flask
from flask_cors import CORS
from backend.config import Config
from backend.utils.logger import setup_logger
from backend.models.system_state import system_state

def create_app():
    """应用工厂函数"""
    app = Flask(__name__)
    CORS(app)
    
    # 配置日志
    setup_logger()
    
    # 注册 Blueprint
    from backend.blueprints import health, vehicles, drivers, nodes, edges
    from backend.blueprints import monitor, dqn, travel_time, dispatch, map_import
    
    app.register_blueprint(health.bp)
    app.register_blueprint(vehicles.bp)
    app.register_blueprint(drivers.bp)
    app.register_blueprint(nodes.bp)
    app.register_blueprint(edges.bp)
    app.register_blueprint(monitor.bp)
    app.register_blueprint(dqn.bp)
    app.register_blueprint(travel_time.bp)
    app.register_blueprint(dispatch.bp)
    app.register_blueprint(map_import.bp)
    
    # 静态文件路由
    @app.route('/')
    def serve_index():
        return send_from_directory('.', 'traffic_system.html')
    
    @app.route('/driver')
    def serve_driver():
        return send_from_directory('.', 'driver.html')
    
    return app
```

### 5. app.py - 精简后的入口文件

```python
from backend import create_app
from backend.config import Config
from backend.models.system_state import system_state
from backend.utils.persistence import load_checkpoint, load_travel_time_database
from backend.services.system_service import initialize_system
from backend.workers.dispatch_worker import start_dispatch_worker

# 创建应用
app = create_app()

# 初始化 SocketIO（如果需要）
socketio = None
try:
    from flask_socketio import SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
except ImportError:
    pass

if __name__ == '__main__':
    # 加载检查点和训练数据
    checkpoint_loaded = load_checkpoint()
    travel_db_loaded = load_travel_time_database()
    
    # 初始化系统
    if not checkpoint_loaded:
        initialize_system()
    
    # 启动后台工作线程
    if not Config.ON_PYTHONANYWHERE:
        start_dispatch_worker()
    
    # 启动应用
    if socketio:
        socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
    else:
        app.run(debug=True, host='0.0.0.0', port=5000)
```

## 迁移策略

### 渐进式迁移（推荐）

1. **第一步：创建新结构，不修改现有代码**
   - 创建 `backend/` 目录
   - 创建基础模块框架
   - 保持 `app.py` 不变

2. **第二步：逐步提取功能**
   - 先提取工具函数（utils）
   - 再提取业务逻辑（services）
   - 最后拆分路由（blueprints）

3. **第三步：切换入口**
   - 更新 `app.py` 使用新结构
   - 测试所有功能
   - 确认无问题后删除旧代码

### 兼容性保证

- 保持所有 API 端点不变
- 保持系统状态结构不变
- 保持数据持久化格式不变

## 优势

1. **可维护性**：每个模块职责单一，易于理解和修改
2. **可测试性**：业务逻辑与路由分离，便于单元测试
3. **可扩展性**：新功能可以独立模块添加
4. **团队协作**：不同开发者可以并行工作不同模块
5. **代码复用**：服务层可以在不同路由中复用

## 注意事项

1. **循环导入**：注意模块间的依赖关系
2. **全局状态**：使用单例模式管理系统状态
3. **线程安全**：确保多线程环境下的数据安全
4. **向后兼容**：保持 API 接口不变

## 实施时间估算

- **阶段 1**（基础结构）：2-3 小时
- **阶段 2**（业务逻辑）：4-6 小时
- **阶段 3**（路由拆分）：3-4 小时
- **阶段 4**（后台任务）：1-2 小时
- **测试和调试**：2-3 小时

**总计**：约 12-18 小时

## 下一步

1. 确认重构方案
2. 创建 `backend/` 目录结构
3. 开始阶段 1 的实施


