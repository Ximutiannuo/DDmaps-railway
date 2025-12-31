"""
日志配置模块
"""
import logging
from backend.config import Config

logger = None

def setup_logger():
    """配置日志系统"""
    global logger
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE, encoding='utf-8') if Config.LOG_FILE else logging.StreamHandler(),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    return logger

# 初始化日志
setup_logger()


