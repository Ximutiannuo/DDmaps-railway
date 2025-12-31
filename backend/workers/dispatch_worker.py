"""
调度工作线程模块
"""
import time
import traceback
from datetime import datetime
from typing import Optional
import threading
from backend.models.system_state import system_state
from backend.services.vehicle_service import update_vehicle_positions
from backend.services.system_service import update_monitor_data
from backend.config import Config
from backend.utils.logger import logger

# 全局变量，用于存储 socketio 实例（在 app.py 中设置）
_socketio = None


def set_socketio(socketio_instance):
    """设置 socketio 实例（由 app.py 调用）"""
    global _socketio
    _socketio = socketio_instance


def dispatch_worker():
    """调度工作线程（增强稳定性）"""
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while True:
        try:
            with system_state.lock:
                dispatch_running = system_state.get('dispatch_running', False)
            
            if dispatch_running:
                try:
                    update_vehicle_positions()  # 更新车辆位置
                    update_monitor_data()  # 更新监控数据
                    
                    # WebSocket 广播实时数据
                    if _socketio:
                        try:
                            with system_state.lock:
                                # 发送完整数据，不限制车辆数量
                                _socketio.emit('vehicle_update', {
                                    'vehicles': system_state.get('vehicles', []),
                                    'monitor_data': system_state.get('monitor_data', {}),
                                    'timestamp': datetime.now().isoformat()
                                }, namespace='/')
                        except Exception as ws_error:
                            logger.warning(f"WebSocket 广播失败: {str(ws_error)}")
                            # 如果是资源不足错误，暂停一段时间
                            if 'resource' in str(ws_error).lower() or 'insufficient' in str(ws_error).lower():
                                logger.error("WebSocket 资源不足，暂停广播 5 秒")
                                time.sleep(5)
                    
                    consecutive_errors = 0  # 重置错误计数
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"调度工作线程执行失败 (连续错误 {consecutive_errors}/{max_consecutive_errors}): {str(e)}\n{traceback.format_exc()}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.critical("调度工作线程连续错误过多，暂停调度")
                        with system_state.lock:
                            system_state.set('dispatch_running', False)
                        consecutive_errors = 0
                        time.sleep(5)  # 等待更长时间后重试
                        continue
                
                time.sleep(0.1)
            else:
                consecutive_errors = 0
                time.sleep(1)
        except Exception as e:
            logger.critical(f"调度工作线程发生严重错误: {str(e)}\n{traceback.format_exc()}")
            time.sleep(5)  # 发生严重错误时等待更长时间


def start_dispatch_worker() -> Optional[threading.Thread]:
    """启动调度工作线程"""
    if Config.ON_PYTHONANYWHERE:
        logger.info("PythonAnywhere 环境，不启动后台调度线程")
        return None
    
    thread = threading.Thread(target=dispatch_worker, daemon=True)
    thread.start()
    logger.info("调度工作线程已启动")
    return thread

