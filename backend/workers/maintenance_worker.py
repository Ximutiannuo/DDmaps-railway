"""
维护工作线程模块
"""
import time
import threading
from typing import Optional
from backend.utils.memory_management import cleanup_memory
from backend.utils.persistence import save_checkpoint, save_travel_time_database
from backend.utils.health_check import health_check
from backend.config import Config
from backend.utils.logger import logger

def maintenance_worker():
    """定期维护任务：清理内存、保存检查点、保存训练数据、健康检查"""
    while True:
        try:
            time.sleep(Config.MAINTENANCE_INTERVAL)  # 每5分钟执行一次
            cleanup_memory()
            save_checkpoint()
            # 强制保存训练数据（确保定期持久化）
            save_travel_time_database(force=True)
            health = health_check()
            if health['status'] != 'healthy':
                logger.warning(f"系统健康状态: {health['status']}")
        except Exception as e:
            logger.error(f"维护任务执行失败: {str(e)}")

def start_maintenance_worker() -> Optional[threading.Thread]:
    """启动维护线程"""
    if Config.ON_PYTHONANYWHERE:
        return None
    
    thread = threading.Thread(target=maintenance_worker, daemon=True)
    thread.start()
    logger.info("维护工作线程已启动")
    return thread

