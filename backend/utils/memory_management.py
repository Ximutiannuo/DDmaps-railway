"""
内存管理模块
"""
import gc
from datetime import datetime
from backend.models.system_state import system_state
from backend.config import Config
from backend.utils.logger import logger

def cleanup_memory():
    """清理内存：限制列表大小，清理已到达车辆，触发垃圾回收
    
    注意：不会清理 travel_time_database（训练数据），该数据由 append_travel_time_record 管理
    """
    with system_state.lock:
        # 限制 arrival_records 大小（仅用于界面显示，不影响训练）
        max_arrival_records = Config.MAX_ARRIVAL_RECORDS
        arrival_records = system_state.get('arrival_records', [])
        if len(arrival_records) > max_arrival_records:
            system_state.set('arrival_records', arrival_records[-max_arrival_records:])
            logger.info(f"清理 arrival_records，保留最近 {max_arrival_records} 条")
        
        # travel_time_database 不在这里清理，由 append_travel_time_record 管理
        # 该数据库用于DQN训练，限制为100万条（足够大，不会影响训练）
        
        # 限制 driver_routes 历史记录（仅用于界面显示，不影响训练）
        # 注意：driver_routes 只是用于司机界面显示历史路线，训练使用的是 travel_time_database
        driver_routes = system_state.get('driver_routes', {})
        for driver_id in list(driver_routes.keys()):
            routes = driver_routes[driver_id]
            if len(routes) > Config.MAX_DRIVER_ROUTES:
                system_state.state['driver_routes'][driver_id] = routes[-Config.MAX_DRIVER_ROUTES:]
        
        # 清理已到达的车辆（保留时间超过1小时）
        now = datetime.now()
        vehicles = system_state.get('vehicles', [])
        vehicles_before = len(vehicles)
        vehicles_to_keep = []
        removed_count = 0
        
        for vehicle in vehicles:
            status = vehicle.get('status', '')
            arrival_time_str = vehicle.get('arrival_time')
            
            # 保留所有非"已到达"状态的车辆
            if status != 'arrived':
                vehicles_to_keep.append(vehicle)
                continue
            
            # 对于已到达的车辆，检查到达时间
            if arrival_time_str:
                try:
                    arrival_time = datetime.fromisoformat(arrival_time_str)
                    hours_since_arrival = (now - arrival_time).total_seconds() / 3600.0
                    # 保留到达时间在1小时内的车辆（用于统计和显示）
                    if hours_since_arrival <= 1.0:
                        vehicles_to_keep.append(vehicle)
                    else:
                        removed_count += 1
                except (ValueError, TypeError):
                    # 时间格式错误，保留车辆（避免误删）
                    vehicles_to_keep.append(vehicle)
            else:
                # 没有到达时间，但状态是已到达，可能是旧数据，保留但记录
                vehicles_to_keep.append(vehicle)
        
        if removed_count > 0:
            system_state.set('vehicles', vehicles_to_keep)
            logger.info(f"清理已到达车辆: 删除 {removed_count} 辆（保留 {len(vehicles_to_keep)} 辆）")
        
        # 触发垃圾回收
        collected = gc.collect()
        if collected > 0:
            logger.debug(f"垃圾回收清理了 {collected} 个对象")


