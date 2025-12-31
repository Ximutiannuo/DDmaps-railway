# PythonAnywhere WSGI 配置文件示例
# 将此文件内容复制到 PythonAnywhere 的 WSGI 配置文件中

import sys

# 添加项目路径到 Python 路径
# 替换 'wdd123456' 为你的 PythonAnywhere 用户名
path = '/home/wdd123456'
if path not in sys.path:
    sys.path.insert(0, path)

# 导入 Flask 应用
from app import app as application

# 如果遇到导入错误，可以尝试以下调试代码：
# import os
# print("Current working directory:", os.getcwd())
# print("Python path:", sys.path)
# print("Files in path:", os.listdir(path))
# print("Backend directory exists:", os.path.exists(os.path.join(path, 'backend')))
# print("Backend __init__.py exists:", os.path.exists(os.path.join(path, 'backend', '__init__.py')))

