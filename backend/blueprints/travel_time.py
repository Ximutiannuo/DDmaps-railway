"""
行驶时间数据库相关 Blueprint
"""
from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state
from backend.config import Config
from backend.utils.logger import logger
from backend.utils.persistence import (
    save_travel_time_database,
    append_travel_time_record
)
import traceback
import os

bp = Blueprint('travel_time', __name__, url_prefix='/api/travel-time-database')

# 从服务层导入
from backend.services.travel_time_service import (
    parse_travel_time_excel,
    build_travel_time_excel,
    normalize_travel_time_records
)

# 从配置获取常量
TRAVEL_DB_FILE = Config.TRAVEL_DB_FILE
TRAVEL_DB_BACKUP_DIR = Config.TRAVEL_DB_BACKUP_DIR

def ensure_backup_dir():
    """确保备份目录存在"""
    if TRAVEL_DB_BACKUP_DIR and not os.path.exists(TRAVEL_DB_BACKUP_DIR):
        os.makedirs(TRAVEL_DB_BACKUP_DIR, exist_ok=True)


@bp.route('', methods=['GET'])
@api_handler
def list_travel_time_database():
    """获取行驶时间数据库（支持limit参数）"""
    limit = request.args.get('limit', type=int)
    records = system_state.get('travel_time_database', [])
    if limit and limit > 0:
        data = records[-limit:]
    else:
        data = records
    return jsonify({
        'success': True,
        'records': data,
        'total_count': len(records)
    })


@bp.route('/export', methods=['GET'])
@api_handler
def export_travel_time_database():
    """导出行驶时间数据库，支持 JSON 与 Excel"""
    records = system_state.get('travel_time_database', [])
    export_format = (request.args.get('format') or 'json').lower()

    if export_format in ('excel', 'xlsx'):
        try:
            stream = build_travel_time_excel(records)
        except RuntimeError as exc:
            return jsonify({'success': False, 'message': str(exc)}), 500

        filename = f"travel_time_database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            stream,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    return jsonify({
        'success': True,
        'records': records,
        'total_count': len(records)
    })


@bp.route('/save', methods=['POST'])
@api_handler
def save_travel_time_database_api():
    """手动保存训练数据到文件"""
    with system_state.lock:
        success = save_travel_time_database(force=True)
        if success:
            record_count = len(system_state.get('travel_time_database', []))
            return jsonify({
                'success': True,
                'message': f'训练数据已保存到文件（{record_count} 条记录）',
                'record_count': record_count,
                'file_path': TRAVEL_DB_FILE
            })
        else:
            return jsonify({
                'success': False,
                'message': '保存训练数据失败，请查看日志'
            }), 500


@bp.route('/clear', methods=['POST'])
@api_handler
def clear_travel_time_database():
    """清除行驶时间数据库
    
    支持参数：
    - confirm: 必须为 'yes' 或 'true' 才能执行清除
    - mode: 'all' (清除所有) 或 'filter' (按条件清除)
    - filters: 过滤条件（仅在 mode='filter' 时有效）
      - before_date: 清除此日期之前的记录 (ISO格式)
      - after_date: 清除此日期之后的记录
      - driver_id: 清除指定司机的记录
      - vehicle_type: 清除指定车辆类型的记录
    """
    data = request.json or {}
    confirm = data.get('confirm', '').lower()
    
    # 安全检查：必须明确确认
    if confirm not in ['yes', 'true', '确认', '1']:
        return jsonify({
            'success': False,
            'message': '清除操作需要明确确认。请在请求中设置 confirm="yes" 或 confirm="true"'
        }), 400
    
    mode = data.get('mode', 'all').lower()
    filters = data.get('filters', {})
    
    try:
        with system_state.lock:
            db = system_state.get('travel_time_database', [])
            original_count = len(db)
            
            if mode == 'all':
                # 清除前先保存备份
                if original_count > 0:
                    backup_file = None
                    if TRAVEL_DB_BACKUP_DIR:
                        ensure_backup_dir()
                        backup_file = os.path.join(
                            TRAVEL_DB_BACKUP_DIR,
                            f"travel_db_backup_before_clear_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        )
                        try:
                            import shutil
                            if TRAVEL_DB_FILE and os.path.exists(TRAVEL_DB_FILE):
                                shutil.copy2(TRAVEL_DB_FILE, backup_file)
                                logger.info(f"清除前备份已创建: {backup_file}")
                        except Exception as e:
                            logger.warning(f"创建备份失败: {str(e)}")
                    
                    system_state.set('travel_time_database', [])
                    logger.info(f"已清除所有训练数据（{original_count} 条记录）")
                    
                    # 更新持久化文件
                    save_travel_time_database(force=True)
                    
                    return jsonify({
                        'success': True,
                        'message': f'已清除所有训练数据（{original_count} 条记录）',
                        'cleared_count': original_count,
                        'backup_file': backup_file
                    })
                else:
                    return jsonify({
                        'success': True,
                        'message': '数据库已为空，无需清除',
                        'cleared_count': 0
                    })
            
            elif mode == 'filter':
                # 按条件清除
                if not filters:
                    return jsonify({
                        'success': False,
                        'message': '使用 filter 模式时必须提供 filters 参数'
                    }), 400
                
                filtered_db = []
                cleared_count = 0
                
                for record in db:
                    should_remove = False
                    
                    # 按日期过滤
                    if 'before_date' in filters:
                        try:
                            before_date = datetime.fromisoformat(filters['before_date'].replace('Z', '+00:00'))
                            record_date_str = record.get('created_at') or record.get('arrival_time') or record.get('start_time')
                            if record_date_str:
                                record_date = datetime.fromisoformat(record_date_str.replace('Z', '+00:00'))
                                if record_date < before_date:
                                    should_remove = True
                        except (ValueError, TypeError, AttributeError):
                            pass
                    
                    if 'after_date' in filters:
                        try:
                            after_date = datetime.fromisoformat(filters['after_date'].replace('Z', '+00:00'))
                            record_date_str = record.get('created_at') or record.get('arrival_time') or record.get('start_time')
                            if record_date_str:
                                record_date = datetime.fromisoformat(record_date_str.replace('Z', '+00:00'))
                                if record_date > after_date:
                                    should_remove = True
                        except (ValueError, TypeError, AttributeError):
                            pass
                    
                    # 按司机ID过滤
                    if 'driver_id' in filters and record.get('driver_id') == filters['driver_id']:
                        should_remove = True
                    
                    # 按车辆类型过滤
                    if 'vehicle_type' in filters and record.get('vehicle_type') == filters['vehicle_type']:
                        should_remove = True
                    
                    if should_remove:
                        cleared_count += 1
                    else:
                        filtered_db.append(record)
                
                if cleared_count > 0:
                    system_state.set('travel_time_database', filtered_db)
                    logger.info(f"已按条件清除训练数据: {cleared_count} 条记录")
                    
                    # 更新持久化文件
                    save_travel_time_database(force=True)
                    
                    return jsonify({
                        'success': True,
                        'message': f'已按条件清除 {cleared_count} 条记录，剩余 {len(filtered_db)} 条',
                        'cleared_count': cleared_count,
                        'remaining_count': len(filtered_db),
                        'filters_applied': filters
                    })
                else:
                    return jsonify({
                        'success': True,
                        'message': '没有记录匹配清除条件',
                        'cleared_count': 0,
                        'remaining_count': len(db)
                    })
            else:
                return jsonify({
                    'success': False,
                    'message': f'无效的清除模式: {mode}。支持的模式: all, filter'
                }), 400
                
    except Exception as e:
        logger.error(f"清除训练数据失败: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'清除操作失败: {str(e)}'
        }), 500


@bp.route('/import', methods=['POST'])
@api_handler
def import_travel_time_database():
    """导入行驶时间数据库"""
    try:
        normalized_records = []
        mode = 'append'

        if request.files:
            uploaded_file = request.files.get('file')
            mode = request.form.get('mode', 'append')
            if not uploaded_file:
                return jsonify({'success': False, 'message': '未找到上传的文件'}), 400
            
            # 检查文件扩展名
            filename = uploaded_file.filename or ''
            if not filename.lower().endswith(('.xlsx', '.xls')):
                return jsonify({'success': False, 'message': '不支持的文件格式，请上传 Excel (.xlsx) 文件'}), 400
            
            try:
                raw_records = parse_travel_time_excel(uploaded_file)
                if not raw_records:
                    return jsonify({'success': False, 'message': 'Excel 文件中未找到有效数据'}), 400
                normalized_records = normalize_travel_time_records(raw_records)
            except RuntimeError as exc:
                logger.error(f"Excel 解析运行时错误: {str(exc)}\n{traceback.format_exc()}")
                return jsonify({'success': False, 'message': f'Excel 解析失败: {str(exc)}'}), 500
            except ValueError as exc:
                logger.error(f"Excel 解析值错误: {str(exc)}\n{traceback.format_exc()}")
                return jsonify({'success': False, 'message': f'Excel 解析失败: {str(exc)}'}), 400
            except Exception as exc:
                logger.error(f"Excel 解析未知错误: {str(exc)}\n{traceback.format_exc()}")
                return jsonify({'success': False, 'message': f'Excel 解析失败: {str(exc)}'}), 500
        else:
            payload = request.json
            if payload is None:
                return jsonify({'success': False, 'message': '请提供 JSON 数据或上传 Excel 文件'}), 400
            
            records = payload.get('records')
            if records is None:
                # 尝试直接解析为数组
                if isinstance(payload, list):
                    records = payload
                else:
                    return jsonify({'success': False, 'message': '请提供 records 字段或直接提供记录数组'}), 400
            
            if not isinstance(records, list):
                return jsonify({'success': False, 'message': 'records 字段必须是列表'}), 400
            
            mode = payload.get('mode', 'append') if isinstance(payload, dict) else 'append'
            
            try:
                normalized_records = normalize_travel_time_records(records)
            except Exception as exc:
                logger.error(f"JSON 数据规范化失败: {str(exc)}\n{traceback.format_exc()}")
                return jsonify({'success': False, 'message': f'数据规范化失败: {str(exc)}'}), 400

        if not normalized_records:
            return jsonify({'success': False, 'message': '未找到有效的记录，请检查数据格式'}), 400

        with system_state.lock:
            if mode == 'replace':
                # 替换模式：直接替换整个数据库
                system_state.set('travel_time_database', normalized_records)
                # 使用与 append_travel_time_record 相同的限制（100万条）
                max_records = 1000000
                db = system_state.get('travel_time_database', [])
                if len(db) > max_records:
                    removed_count = len(db) - max_records
                    system_state.set('travel_time_database', db[-max_records:])
                    logger.warning(f"导入数据后超过限制，已删除最旧的 {removed_count} 条记录。"
                                  f"建议定期导出数据到Excel进行备份。")
                # 强制保存训练数据
                save_travel_time_database(force=True)
            else:
                # 追加模式：使用 append_travel_time_record，会自动处理限制和保存
                for rec in normalized_records:
                    append_travel_time_record(rec)
                # 追加完成后也强制保存一次
                save_travel_time_database(force=True)

        total_count = len(system_state.get('travel_time_database', []))
        logger.info(f"成功导入 {len(normalized_records)} 条记录，当前数据库共有 {total_count} 条记录")
        
        return jsonify({
            'success': True,
            'message': f'成功导入 {len(normalized_records)} 条记录',
            'imported_count': len(normalized_records),
            'total_count': total_count
        })
    except Exception as e:
        logger.error(f"导入行驶时间数据库失败: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'导入失败: {str(e)}'
        }), 500

