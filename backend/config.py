"""
配置管理模块
"""
import os
from pathlib import Path

class Config:
    """应用配置"""
    
    # 环境检测
    ON_PYTHONANYWHERE = 'PYTHONANYWHERE_DOMAIN' in os.environ
    
    # 基础目录
    BASE_DIR = Path(__file__).parent.parent
    
    # 文件路径（PythonAnywhere 上也需要持久化，否则重启后数据丢失）
    CHECKPOINT_FILE = BASE_DIR / 'system_checkpoint.json'
    TRAVEL_DB_FILE = BASE_DIR / 'travel_time_database.json'
    TRAVEL_DB_BACKUP_DIR = BASE_DIR / 'travel_db_backups'
    LOG_FILE = BASE_DIR / 'traffic_system.log' if not ON_PYTHONANYWHERE else None  # 日志文件保持不变，PA 上用 StreamHandler
    
    # 限流配置（提高限制，避免管理端和司机端频繁请求被限流）
    RATE_LIMIT_MAX_REQUESTS = 2000  # 提高到 2000 请求/分钟
    RATE_LIMIT_WINDOW_SECONDS = 60
    
    # 内存管理配置
    MAX_ARRIVAL_RECORDS = 5000
    MAX_DRIVER_ROUTES = 20
    MAX_TRAVEL_TIME_RECORDS = 1000000
    TRAVEL_DB_SAVE_INTERVAL = 50
    
    # 维护任务配置
    MAINTENANCE_INTERVAL = 300  # 5分钟
    
    # 调度工作线程配置
    DISPATCH_WORKER_INTERVAL = 0.1  # 100ms
    DISPATCH_WORKER_SLEEP = 1.0  # 1秒
    
    # 健康检查配置
    HEALTH_CHECK_MEMORY_WARNING_MB = 500
    
    # CORS 配置
    # 允许的来源列表，用逗号分隔
    # 例如: "http://localhost:5000,http://localhost:3000,https://example.com"
    # 如果为空或未设置，则允许所有来源（仅用于开发）
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if os.environ.get('CORS_ALLOWED_ORIGINS') else None
    
    # 是否允许凭证（cookies, authorization headers）
    CORS_ALLOW_CREDENTIALS = os.environ.get('CORS_ALLOW_CREDENTIALS', 'false').lower() == 'true'
    
    # 允许的 HTTP 方法
    CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
    
    # 允许的 HTTP 头
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With']


