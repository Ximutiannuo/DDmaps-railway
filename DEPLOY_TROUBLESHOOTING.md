# PythonAnywhere 部署问题排查指南

## ❌ 错误：ModuleNotFoundError: No module named 'backend.config'

### 问题原因
PythonAnywhere 无法找到 `backend` 模块，通常是因为：
1. `backend` 目录没有上传
2. 文件路径配置不正确
3. `backend/__init__.py` 文件缺失

### 解决步骤

#### 步骤 1：检查文件是否上传
在 PythonAnywhere 的 Bash Console 中运行：
```bash
cd /home/wdd123456  # 替换为你的用户名
ls -la              # 查看文件列表
ls -la backend/     # 检查 backend 目录是否存在
```

**应该看到：**
- `app.py` 文件
- `backend/` 目录
- `backend/__init__.py` 文件
- `backend/config.py` 文件

#### 步骤 2：检查 WSGI 配置
在 PythonAnywhere 的 Web 标签页中，编辑 WSGI 配置文件，确保内容如下：

```python
import sys

# 添加项目路径到 Python 路径
# 替换 'wdd123456' 为你的 PythonAnywhere 用户名
path = '/home/wdd123456'
if path not in sys.path:
    sys.path.insert(0, path)

# 导入 Flask 应用
from app import app as application
```

**重要提示：**
- 路径必须是 `/home/你的用户名`（不是 `/home/你的用户名/mysite`）
- 确保 `sys.path.insert(0, path)` 使用 `insert(0, ...)` 而不是 `append(...)`

#### 步骤 3：验证 backend 目录结构
在 Bash Console 中运行：
```bash
cd /home/wdd123456
find backend -name "*.py" | head -20  # 查看 backend 目录下的 Python 文件
```

**应该看到：**
- `backend/__init__.py`
- `backend/config.py`
- `backend/blueprints/__init__.py`
- `backend/services/__init__.py`
- 等等...

#### 步骤 4：测试导入
在 Bash Console 中运行：
```bash
cd /home/wdd123456
python3.10 -c "import sys; sys.path.insert(0, '.'); from backend.config import Config; print('导入成功！')"
```

如果这个命令失败，说明文件确实没有上传或路径不对。

#### 步骤 5：检查文件权限
在 Bash Console 中运行：
```bash
cd /home/wdd123456
ls -la backend/__init__.py
ls -la backend/config.py
```

**应该看到文件权限类似：**
```
-rw-r--r-- 1 wdd123456 wdd123456 1234 Nov 22 08:00 backend/__init__.py
-rw-r--r-- 1 wdd123456 wdd123456 5678 Nov 22 08:00 backend/config.py
```

#### 步骤 6：重新上传 backend 目录（如果需要）
如果 `backend` 目录不存在或不完整：
1. 在本地压缩 `backend` 目录
2. 在 PythonAnywhere 的文件管理器中上传
3. 解压到 `/home/你的用户名/` 目录
4. 确保解压后结构是 `/home/你的用户名/backend/...`

### 常见问题

#### Q1: 上传后 backend 目录在子目录中
**错误结构：**
```
/home/wdd123456/mysite/backend/
```

**正确结构：**
```
/home/wdd123456/backend/
```

**解决方法：** 将 `backend` 目录移动到正确位置，或修改 WSGI 配置中的路径。

#### Q2: backend 目录存在但缺少 __init__.py
**解决方法：** 确保 `backend/__init__.py` 文件存在（可以是空文件）。

#### Q3: Python 版本不匹配
**解决方法：** 确保在 Bash Console 中使用 Python 3.10：
```bash
python3.10 --version
```

### 调试技巧

在 WSGI 配置文件中临时添加调试代码：
```python
import sys
import os

path = '/home/wdd123456'
if path not in sys.path:
    sys.path.insert(0, path)

# 调试信息（部署成功后可以删除）
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)
print("Files in path:", os.listdir(path))
print("Backend exists:", os.path.exists(os.path.join(path, 'backend')))
print("Backend __init__.py exists:", os.path.exists(os.path.join(path, 'backend', '__init__.py')))

from app import app as application
```

查看调试信息：在 PythonAnywhere 的 Web 标签页中，点击 "Error log" 查看输出。

