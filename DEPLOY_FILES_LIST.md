# PythonAnywhere 部署文件清单（完整版）

## ✅ 必须上传的文件和目录

### 1. 核心应用文件
```
app.py                          # Flask 主应用文件（必需）
requirements.txt                # Python 依赖包列表（必需）
```

### 2. 后端代码（整个 backend 目录，保持完整结构）
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
│   ├── dqn_service.py
│   └── location_service.py
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

### 3. 前端文件（必需）
```
traffic_system.html             # 管理端页面（必需）
driver.html                     # 司机端页面（必需）
css/
└── styles.css                  # 样式文件（必需）
js/
├── api.js                      # API 工具（必需）
├── app-main.js                 # 主应用逻辑（必需）
├── charts.js                   # 图表功能（必需）
├── config.js                   # 配置文件（必需）
├── ui-manager.js               # UI 管理（必需）
├── utils.js                    # 工具函数（必需）
└── websocket.js                # WebSocket 客户端（必需）
```

### 4. 数据文件（可选，如果需要保留现有数据）
```
system_checkpoint.json          # 系统状态备份（可选）
travel_time_database.json       # 行程时间数据库（可选）
travel_db_backups/              # 备份目录（可选）
```

## ❌ 不需要上传的文件（排除）

### Python 缓存文件
- 所有 `__pycache__/` 目录
- 所有 `*.pyc` 文件
- 所有 `*.pyo` 文件

### 日志文件
- `*.log` 文件
- `traffic_system.log`

### 虚拟环境
- `.venv/` 目录
- `venv/` 目录
- `env/` 目录

### 开发工具和测试文件
- `tests/` 目录
- `ts/` 目录（TypeScript 源文件）
- `tsconfig.json`
- `package.json`
- `extract_ui_js.py`
- `generate_ssl_cert.py`
- `verify_service_stability.py`

### 文档文件（可选，不影响运行）
- `*.md` 文件（README、部署文档等）
- `CLEANUP_PLAN.md`
- `CLEANUP_SUMMARY.md`
- `DEPLOY_FILES_LIST.md`
- `DEPLOY_TROUBLESHOOTING.md`
- `MIGRATION_GUIDE.md`
- `OPTIMIZATION_COMPLETED.md`
- `OPTIMIZATION_SUGGESTIONS.md`
- `PYTHONANYWHERE_DEPLOY.md`
- `PYTHONANYWHERE_UNZIP_GUIDE.md`
- `REFACTORING_PLAN.md`
- `UPLOAD_CHECKLIST.md`
- `VERIFY_STABILITY.md`
- `WSGI_CONFIG_EXAMPLE.py`

### 压缩包和备份（已包含在源文件中）
- `*.zip` 文件
- `backend.zip`
- `js.zip`
- `travel_db_backups.zip`

### SSL 证书（如果使用 HTTPS）
- `ssl/` 目录（PythonAnywhere 会自动处理 HTTPS）

### 系统文件
- `.DS_Store` (macOS)
- `Thumbs.db` (Windows)
- `.git/` 目录（如果使用 Git，可选）

## 📦 快速打包命令

### Windows PowerShell
```powershell
# 方法1：使用 PowerShell 压缩（推荐）
# 创建临时目录，复制需要的文件
$tempDir = "deploy_temp"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

# 复制核心文件
Copy-Item app.py $tempDir\
Copy-Item requirements.txt $tempDir\
Copy-Item traffic_system.html $tempDir\
Copy-Item driver.html $tempDir\

# 复制目录
Copy-Item -Recurse backend $tempDir\
Copy-Item -Recurse css $tempDir\
Copy-Item -Recurse js $tempDir\

# 可选：复制数据文件
# Copy-Item system_checkpoint.json $tempDir\
# Copy-Item travel_time_database.json $tempDir\
# Copy-Item -Recurse travel_db_backups $tempDir\

# 压缩
Compress-Archive -Path $tempDir\* -DestinationPath deploy.zip -Force

# 清理临时目录
Remove-Item -Recurse -Force $tempDir

Write-Host "✅ 部署包已创建: deploy.zip"
```

### Linux/Mac (Bash)
```bash
# 创建临时目录
mkdir -p deploy_temp

# 复制核心文件
cp app.py requirements.txt traffic_system.html driver.html deploy_temp/

# 复制目录（排除 __pycache__）
rsync -av --exclude='__pycache__' --exclude='*.pyc' backend deploy_temp/
rsync -av css js deploy_temp/

# 可选：复制数据文件
# cp system_checkpoint.json deploy_temp/
# cp travel_time_database.json deploy_temp/
# cp -r travel_db_backups deploy_temp/

# 压缩
cd deploy_temp
zip -r ../deploy.zip .
cd ..

# 清理
rm -rf deploy_temp

echo "✅ 部署包已创建: deploy.zip"
```

## 📋 文件结构检查清单

上传前请确认：

- [ ] `app.py` 存在
- [ ] `requirements.txt` 存在
- [ ] `backend/` 目录完整（包含所有子目录和文件）
- [ ] `traffic_system.html` 存在
- [ ] `driver.html` 存在
- [ ] `css/styles.css` 存在
- [ ] `js/` 目录包含所有 7 个 JS 文件
- [ ] 没有 `__pycache__/` 目录
- [ ] 没有 `*.pyc` 文件
- [ ] 没有虚拟环境目录

## 🚀 PythonAnywhere 部署步骤

### 1. 上传文件
- 登录 PythonAnywhere
- 进入 Files 标签页
- 上传 `deploy.zip` 到 `/home/yourusername/`
- 解压：`unzip deploy.zip`

### 2. 安装依赖
在 Bash Console 中运行：
```bash
cd /home/yourusername
pip3.10 install --user -r requirements.txt
```

### 3. 配置 WSGI
在 Web 标签页中，编辑 WSGI 配置文件：
```python
import sys

# 替换 'yourusername' 为你的 PythonAnywhere 用户名
path = '/home/yourusername'
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application
```

### 4. 配置静态文件（可选）
在 Web 标签页的 Static files 部分：
- URL: `/static/js/`
- Directory: `/home/yourusername/js/`

### 5. 重启应用
点击 "Reload" 按钮重启 Web 应用

## ⚠️ 重要提示

1. **WebSocket 支持**：PythonAnywhere 免费账户不支持 WebSocket，需要付费账户
2. **文件路径**：确保所有路径使用相对路径
3. **数据持久化**：系统状态保存在内存中，重启后会丢失
4. **HTTPS**：PythonAnywhere 自动提供 HTTPS，无需配置 SSL 证书

## 🔍 验证部署

部署后访问：
- 管理端：`https://yourusername.pythonanywhere.com/`
- 司机端：`https://yourusername.pythonanywhere.com/driver`

如果遇到问题，检查：
1. PythonAnywhere 的 Error log
2. 控制台中的 JavaScript 错误
3. 网络请求是否成功
