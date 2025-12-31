# PythonAnywhere 上传文件清单

## ✅ 必须上传的文件和目录

### 1. 核心应用文件
```
app.py                          # 主应用文件（必需）
requirements.txt                # Python 依赖包列表（必需）
```

### 2. 后端代码（整个 backend 目录）
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
│   └── map_labels.py
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
│   └── dqn_service.py
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

### 3. 前端文件
```
traffic_system.html             # 管理端页面（必需）
driver.html                     # 司机端页面（必需）
js/
├── api.js                      # API 调用模块（必需）
├── utils.js                    # 工具函数（必需）
├── charts.js                   # 图表功能（必需）
├── websocket.js                # WebSocket 通信（必需）
├── config.js                   # 配置模块（必需）
└── ui-manager.js               # UI 管理模块（必需）
css/
└── styles.css                  # 样式文件（必需）
```

### 4. 数据文件（可选，如果需要保留现有数据）
```
system_checkpoint.json          # 系统状态备份（可选）
travel_time_database.json       # 行程时间数据库（可选）
travel_db_backups/              # 备份目录（可选）
```

## ❌ 不需要上传的文件

### Python 缓存文件
- `__pycache__/` 所有目录下的
- `*.pyc` 文件

### 日志文件
- `*.log` 文件
- `traffic_system.log`

### 开发工具和测试文件
- `tests/` 目录
- `ts/` 目录（TypeScript 源文件）
- `tsconfig.json`
- `package.json`
- `extract_ui_js.py`
- `verify_service_stability.py`

### 文档文件（可选）
- `*.md` 文件（README、部署文档等，可选）
- `CLEANUP_PLAN.md`
- `CLEANUP_SUMMARY.md`
- `MIGRATION_GUIDE.md`
- `OPTIMIZATION_COMPLETED.md`
- `OPTIMIZATION_SUGGESTIONS.md`
- `PYTHONANYWHERE_DEPLOY.md`
- `REFACTORING_PLAN.md`
- `VERIFY_STABILITY.md`

### 压缩包文件
- `backend.zip`
- `js.zip`

### 系统文件
- `.DS_Store` (macOS)
- `Thumbs.db` (Windows)
- `.git/` 目录（如果使用 Git，不需要上传）

## 📦 快速打包命令

### Windows PowerShell
```powershell
# 创建部署包（排除不需要的文件）
Compress-Archive -Path app.py,requirements.txt,backend,traffic_system.html,driver.html,js,css -DestinationPath deploy.zip -Force
```

### 如果包含数据文件
```powershell
Compress-Archive -Path app.py,requirements.txt,backend,traffic_system.html,driver.html,js,css,system_checkpoint.json,travel_time_database.json,travel_db_backups -DestinationPath deploy.zip -Force
```

## 📋 上传步骤

### 方法 1：使用 PythonAnywhere 文件管理器
1. 登录 PythonAnywhere
2. 进入 Files 标签页
3. 导航到你的项目目录（如 `/home/yourusername/mysite`）
4. 上传所有必需的文件和目录，保持相同的目录结构

### 方法 2：使用 Git（推荐）
如果项目已使用 Git：
1. 在本地提交所有更改
2. 推送到远程仓库（GitHub/GitLab）
3. 在 PythonAnywhere 的 Bash Console 中：
```bash
cd /home/yourusername/mysite
git clone <your-repo-url> .
# 或者如果已存在，使用 git pull
```

## 🔧 上传后的配置步骤

### 1. 安装依赖
在 PythonAnywhere 的 Bash Console 中：
```bash
cd /home/yourusername/mysite  # 替换为你的项目路径
pip3.10 install --user -r requirements.txt
```

### 2. 配置 WSGI 文件
在 PythonAnywhere 的 Web 标签页中，编辑 WSGI 配置文件：
```python
import sys
path = '/home/yourusername/mysite'  # 替换为你的项目路径
if path not in sys.path:
    sys.path.append(path)

from app import app as application
```

### 3. 配置静态文件（可选）
在 Web 标签页的 Static files 部分：
- URL: `/static/js/`
- Directory: `/home/yourusername/mysite/js/`

- URL: `/static/css/`
- Directory: `/home/yourusername/mysite/css/`

### 4. 重启应用
点击 Web 标签页的 "Reload" 按钮重启应用

## ⚠️ 重要提醒

1. **WebSocket 支持**：PythonAnywhere 免费账户不支持 WebSocket，会自动使用轮询模式
2. **文件路径**：确保所有路径使用相对路径
3. **数据持久化**：系统状态保存在内存中，重启后会丢失。如需持久化，上传数据文件
4. **目录结构**：上传时保持与本地相同的目录结构

