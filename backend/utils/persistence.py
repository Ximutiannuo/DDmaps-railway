"""
数据持久化模块
"""
import json
import os
import shutil
from datetime import datetime
from typing import Optional
from backend.models.system_state import system_state
from backend.config import Config
from backend.utils.logger import logger

# 训练数据自动保存计数器
_travel_db_save_counter = 0

def ensure_backup_dir():
    """确保备份目录存在"""
    if Config.TRAVEL_DB_BACKUP_DIR and not os.path.exists(Config.TRAVEL_DB_BACKUP_DIR):
        try:
            os.makedirs(Config.TRAVEL_DB_BACKUP_DIR, exist_ok=True)
        except Exception as e:
            logger.warning(f"无法创建备份目录: {str(e)}")

def save_travel_time_database(force: bool = False) -> bool:
    """保存训练数据到文件"""
    if Config.TRAVEL_DB_FILE is None:
        return False
    
    global _travel_db_save_counter
    if not force:
        _travel_db_save_counter += 1
        if _travel_db_save_counter < Config.TRAVEL_DB_SAVE_INTERVAL:
            return False
    
    try:
        with system_state.lock:
            db = system_state.get('travel_time_database', [])
            if not db:
                return False
            
            # 保存到主文件
            temp_file = str(Config.TRAVEL_DB_FILE) + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'version': 1,
                    'timestamp': datetime.now().isoformat(),
                    'record_count': len(db),
                    'records': db
                }, f, ensure_ascii=False, indent=2)
            
            # 原子性替换
            if os.path.exists(Config.TRAVEL_DB_FILE):
                os.replace(temp_file, Config.TRAVEL_DB_FILE)
            else:
                os.rename(temp_file, Config.TRAVEL_DB_FILE)
            
            _travel_db_save_counter = 0
            logger.info(f"训练数据已保存: {len(db)} 条记录 -> {Config.TRAVEL_DB_FILE}")
            
            # 定期创建备份（每天一次）
            ensure_backup_dir()
            if Config.TRAVEL_DB_BACKUP_DIR:
                backup_file = os.path.join(
                    Config.TRAVEL_DB_BACKUP_DIR,
                    f"travel_db_backup_{datetime.now().strftime('%Y%m%d')}.json"
                )
                if not os.path.exists(backup_file):
                    shutil.copy2(Config.TRAVEL_DB_FILE, backup_file)
                    logger.info(f"训练数据备份已创建: {backup_file}")
            
            return True
    except Exception as e:
        logger.error(f"保存训练数据失败: {str(e)}")
        temp_file = str(Config.TRAVEL_DB_FILE) + '.tmp'
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        return False

def load_travel_time_database() -> bool:
    """从文件加载训练数据"""
    if Config.TRAVEL_DB_FILE is None or not os.path.exists(Config.TRAVEL_DB_FILE):
        return False
    
    try:
        with open(Config.TRAVEL_DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        with system_state.lock:
            if isinstance(data, dict) and 'records' in data:
                records = data['records']
                system_state.set('travel_time_database', records)
                logger.info(f"训练数据已加载: {len(records)} 条记录从 {Config.TRAVEL_DB_FILE}")
            elif isinstance(data, list):
                # 兼容旧格式
                system_state.set('travel_time_database', data)
                logger.info(f"训练数据已加载（旧格式）: {len(data)} 条记录从 {Config.TRAVEL_DB_FILE}")
            else:
                logger.warning(f"训练数据文件格式不正确: {Config.TRAVEL_DB_FILE}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"加载训练数据失败: {str(e)}")
        return False

def save_checkpoint() -> None:
    """保存系统状态检查点（不包含训练数据，训练数据单独保存）"""
    if Config.CHECKPOINT_FILE is None:
        return
    
    try:
        with system_state.lock:
            checkpoint_data = {
                'version': 4,  # 升级版本号，包含 map_rotation
                'timestamp': datetime.now().isoformat(),
                'nodes': system_state.get('nodes', []),
                'edges': system_state.get('edges', []),
                'vehicle_types': system_state.get('vehicle_types', {}),
                'edge_directions': system_state.get('edge_directions', {}),
                'vehicle_counter': system_state.get('vehicle_counter', 1),
                'route_time_stats': system_state.get('route_time_stats', {}),
                'map_background': system_state.get('map_background'),
                'map_rotation': system_state.get('map_rotation', 0),  # 添加地图旋转角度
                # 不保存运行时数据（vehicles, drivers等），这些是临时状态
                # 训练数据单独保存到 travel_time_database.json
            }
            
            temp_file = str(Config.CHECKPOINT_FILE) + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            # 原子性替换
            if os.path.exists(Config.CHECKPOINT_FILE):
                os.replace(temp_file, Config.CHECKPOINT_FILE)
            else:
                os.rename(temp_file, Config.CHECKPOINT_FILE)
            
            logger.info(f"系统检查点已保存: {Config.CHECKPOINT_FILE}")
    except Exception as e:
        logger.error(f"保存检查点失败: {str(e)}")
        temp_file = str(Config.CHECKPOINT_FILE) + '.tmp'
        if 'temp_file' in locals() and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

def load_checkpoint() -> bool:
    """加载系统状态检查点"""
    if Config.CHECKPOINT_FILE is None or not os.path.exists(Config.CHECKPOINT_FILE):
        return False
    
    try:
        with open(Config.CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
        
        with system_state.lock:
            if 'nodes' in checkpoint_data:
                system_state.set('nodes', checkpoint_data['nodes'])
            if 'edges' in checkpoint_data:
                system_state.set('edges', checkpoint_data['edges'])
            if 'vehicle_types' in checkpoint_data:
                vehicle_types = system_state.get('vehicle_types', {})
                vehicle_types.update(checkpoint_data['vehicle_types'])
                system_state.set('vehicle_types', vehicle_types)
            if 'edge_directions' in checkpoint_data:
                system_state.set('edge_directions', checkpoint_data['edge_directions'])
            if 'vehicle_counter' in checkpoint_data:
                system_state.set('vehicle_counter', checkpoint_data['vehicle_counter'])
            if 'route_time_stats' in checkpoint_data:
                system_state.set('route_time_stats', checkpoint_data['route_time_stats'])
            if 'map_background' in checkpoint_data:
                system_state.set('map_background', checkpoint_data['map_background'])
            if 'map_rotation' in checkpoint_data:
                system_state.set('map_rotation', checkpoint_data['map_rotation'])
        
        logger.info(f"系统检查点已加载: {Config.CHECKPOINT_FILE}")
        return True
    except Exception as e:
        logger.error(f"加载检查点失败: {str(e)}")
        return False

def append_travel_time_record(record: dict) -> None:
    """保存行驶时间数据库记录，保留最近1000000条
    
    注意：此数据库用于DQN训练，限制为100万条以确保有足够的训练数据。
    如果数据量超过限制，会保留最近的数据（FIFO策略）。
    数据会自动持久化到文件（每50条记录保存一次）。
    """
    with system_state.lock:
        db = system_state.get('travel_time_database', [])
        if not isinstance(db, list):
            db = []
        db = list(db)  # 创建副本，避免直接修改
        db.append(record)
        max_records = Config.MAX_TRAVEL_TIME_RECORDS
        if len(db) > max_records:
            # 只保留最近的数据，但会记录日志提醒用户
            removed_count = len(db) - max_records
            db = db[-max_records:]
            logger.warning(f"travel_time_database 超过限制，已删除最旧的 {removed_count} 条记录。"
                          f"建议定期导出数据到Excel进行备份。")
        system_state.set('travel_time_database', db)
    
    # 自动保存到文件（每50条记录保存一次，或强制保存）
    save_travel_time_database(force=False)

def record_route_duration(
    start_node: str,
    target_node: str,
    duration_minutes: float,
    vehicle_type: str = None,
    custom_speed_kmph: float = None,
    distance_m: float = None,
    avg_speed_kmph: float = None
) -> None:
    """记录路线耗时统计（支持多维度分析）"""
    with system_state.lock:
        key = f'{start_node}->{target_node}'
        route_time_stats = system_state.get('route_time_stats', {})
        if not isinstance(route_time_stats, dict):
            route_time_stats = {}
        route_time_stats = dict(route_time_stats)  # 创建副本
        
        if key not in route_time_stats:
            route_time_stats[key] = {
                'count': 0,
                'total_minutes': 0.0,
                'average_minutes': 0.0,
                'last_updated': None
            }
        stats = route_time_stats[key]
        stats['count'] += 1
        stats['total_minutes'] += duration_minutes
        stats['average_minutes'] = round(stats['total_minutes'] / stats['count'], 2)
        stats['last_updated'] = datetime.now().isoformat()
        
        if distance_m is not None:
            if 'distance_summary' not in stats:
                stats['distance_summary'] = {
                    'count': 0,
                    'total_distance_m': 0.0,
                    'average_distance_m': 0.0
                }
            distance_summary = stats['distance_summary']
            distance_summary['count'] += 1
            distance_summary['total_distance_m'] += float(distance_m)
            distance_summary['average_distance_m'] = round(
                distance_summary['total_distance_m'] / distance_summary['count'], 3
            )
        
        if avg_speed_kmph is not None:
            if 'speed_summary' not in stats:
                stats['speed_summary'] = {
                    'count': 0,
                    'total_speed_kmph': 0.0,
                    'average_speed_kmph': 0.0
                }
            speed_summary = stats['speed_summary']
            speed_summary['count'] += 1
            speed_summary['total_speed_kmph'] += float(avg_speed_kmph)
            speed_summary['average_speed_kmph'] = round(
                speed_summary['total_speed_kmph'] / speed_summary['count'], 2
            )
        
        if vehicle_type:
            if 'vehicle_type_stats' not in stats:
                stats['vehicle_type_stats'] = {}
            vehicle_type_stats = stats['vehicle_type_stats']
            if vehicle_type not in vehicle_type_stats:
                vehicle_type_stats[vehicle_type] = {
                    'count': 0,
                    'total_minutes': 0.0,
                    'average_minutes': 0.0
                }
            vehicle_type_stats[vehicle_type]['count'] += 1
            vehicle_type_stats[vehicle_type]['total_minutes'] += duration_minutes
            vehicle_type_stats[vehicle_type]['average_minutes'] = round(
                vehicle_type_stats[vehicle_type]['total_minutes'] / vehicle_type_stats[vehicle_type]['count'], 2
            )
        
        if custom_speed_kmph is not None:
            if 'speed_custom_stats' not in stats:
                stats['speed_custom_stats'] = {}
            speed_custom_stats = stats['speed_custom_stats']
            speed_key = f"{custom_speed_kmph:.0f}kmph"
            if speed_key not in speed_custom_stats:
                speed_custom_stats[speed_key] = {
                    'count': 0,
                    'total_minutes': 0.0,
                    'average_minutes': 0.0
                }
            speed_custom_stats[speed_key]['count'] += 1
            speed_custom_stats[speed_key]['total_minutes'] += duration_minutes
            speed_custom_stats[speed_key]['average_minutes'] = round(
                speed_custom_stats[speed_key]['total_minutes'] / speed_custom_stats[speed_key]['count'], 2
            )
        
        system_state.set('route_time_stats', route_time_stats)


