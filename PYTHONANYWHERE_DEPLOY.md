# PythonAnywhere 部署文件清单

## ✅ 必须上传的文件和目录

### 核心文件
```
app.py                          # 主应用文件
requirements.txt                # Python 依赖包列表
```

### 后端代码（整个 backend 目录）
```
backend/
├── __init__.py
├── app_factory.py
├── config.py
├── blueprints/
│   ├── __init__.py
│   ├── health.py
│   ├── vehicles.py
│   ├── drivers.py
│   ├── nodes.py
│   ├── edges.py
│   ├── monitor.py
│   ├── dispatch.py
│   ├── dqn.py
│   ├── travel_time.py
│   ├── map_import.py
│   ├── system.py
│   └── map_labels.py          # 地图文字框
├── models/
│   ├── __init__.py
│   └── system_state.py
├── services/
│   ├── __init__.py
│   ├── vehicle_service.py
│   ├── driver_service.py
│   ├── node_service.py
│   ├── edge_service.py
│   ├── monitor_service.py
│   ├── path_planning_service.py
│   ├── system_service.py
│   ├── travel_time_service.py
│   ├── map_import_service.py
│   ├── dqn_service.py
│   └── location_service.py    # GPS定位服务（新增）
├── utils/
│   ├── __init__.py
│   ├── api_handler.py
│   ├── logger.py
│   ├── validators.py
│   ├── health_check.py
│   ├── persistence.py
│   ├── memory_management.py
│   └── rate_limiter.py
└── workers/
    ├── __init__.py
    ├── dispatch_worker.py
    └── maintenance_worker.py
```

### 前端文件
```
traffic_system.html             # 管理端页面
driver.html                     # 司机端页面
css/
└── styles.css                  # 样式文件
js/
├── api.js
├── app-main.js
├── charts.js
├── config.js
├── ui-manager.js
├── utils.js
└── websocket.js
```

### 数据文件（可选，如果需要保留现有数据）
```
system_checkpoint.json          # 系统状态备份（可选）
travel_time_database.json       # 行程时间数据库（可选）
travel_db_backups/              # 备份目录（可选）
```

## ❌ 不需要上传的文件

### Python 缓存
- `__pycache__/` 所有目录下的
- `*.pyc` 文件

### 日志文件
- `*.log` 文件
- `traffic_system.log`

### 虚拟环境
- `.venv/` 或 `venv/` 目录

### 文档文件（可选）
- `*.md` 文件（README 等，可选）

### 测试和开发文件
- `tests/` 目录
- `ts/` 目录（TypeScript 源文件）
- `tsconfig.json`
- `package.json`

### 系统文件
- `.DS_Store` (macOS)
- `Thumbs.db` (Windows)

## 📦 快速打包命令（Windows PowerShell）

```powershell
# 创建部署包（排除不需要的文件）
Compress-Archive -Path app.py,requirements.txt,backend,traffic_system.html,driver.html,js -DestinationPath deploy.zip -Force
```

## 📋 PythonAnywhere 部署步骤

### 1. 上传文件
- 使用 PythonAnywhere 的文件管理器上传所有必需文件
- 或使用 Git（如果已配置）
- 确保所有文件保持相同的目录结构

### 2. 安装依赖
在 Bash Console 中运行：
```bash
cd /home/yourusername/mysite  # 替换为你的项目路径
pip3.10 install --user -r requirements.txt
```

### 3. 配置 WSGI 文件
在 PythonAnywhere 的 Web 标签页中，编辑 WSGI 配置文件：
```python
import sys

# 添加项目路径到 Python 路径
# 替换 'yourusername' 为你的 PythonAnywhere 用户名
# 注意：如果你的文件直接在 /home/yourusername/ 下，路径就是 '/home/yourusername'
# 如果文件在 /home/yourusername/mysite/ 下，路径就是 '/home/yourusername/mysite'
path = '/home/yourusername'  # 或 '/home/yourusername/mysite'
if path not in sys.path:
    sys.path.insert(0, path)  # 使用 insert(0, ...) 而不是 append(...)

# 导入 Flask 应用
from app import app as application
```

**重要提示：**
- 路径必须是你的项目根目录（包含 `app.py` 和 `backend/` 的目录）
- 使用 `sys.path.insert(0, path)` 而不是 `append`，确保优先搜索你的项目路径
- 如果文件直接在 `/home/yourusername/` 下，路径就是 `/home/yourusername`
- 如果文件在子目录中，路径就是 `/home/yourusername/mysite`（或你的子目录名）

**重要**：PythonAnywhere 使用 WSGI，不需要 `socketio.run()`，只需要 Flask app 对象。

### 4. 配置静态文件（可选）
在 Web 标签页的 Static files 部分：
- URL: `/static/`
- Directory: `/home/yourusername/mysite/js/`

**注意**：HTML 文件通过 Flask 路由提供，不需要配置为静态文件。

### 5. HTML 文件路由
`app.py` 中已配置：
- `/` → `traffic_system.html`（管理端）
- `/driver` → `driver.html`（司机端）

### 6. WebSocket 配置（重要）
PythonAnywhere 免费账户**不支持 WebSocket**，需要：
- 升级到付费账户，或
- 修改代码使用长轮询（long polling）替代 WebSocket

### 7. 重启应用
点击 "Reload" 按钮重启 Web 应用

## ⚠️ 注意事项

1. **WebSocket 支持**：PythonAnywhere 的免费账户可能不支持 WebSocket，需要升级到付费账户
2. **文件路径**：确保所有路径使用相对路径或正确的绝对路径
3. **环境变量**：如果有环境变量配置，需要在 PythonAnywhere 的 Web 配置中设置
4. **数据持久化**：系统状态保存在内存中，重启后会丢失。如果需要持久化，确保上传数据文件

## 🔧 可能需要的配置调整

### 如果 WebSocket 不可用
在 `app.py` 中，SocketIO 初始化时可能需要调整：
```python
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
```

### CORS 配置
确保 `backend/config.py` 中的 CORS 设置允许你的域名访问

