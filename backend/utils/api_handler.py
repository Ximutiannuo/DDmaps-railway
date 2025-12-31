"""
API 路由装饰器
"""
import time
import traceback
from functools import wraps
from flask import request, jsonify
from backend.utils.rate_limiter import rate_limiter
from backend.utils.logger import logger

def api_handler(func):
    """API路由装饰器：限流、异常处理、日志记录"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 请求限流
        if not rate_limiter.is_allowed():
            logger.warning(f"请求限流触发: {request.path}")
            return jsonify({
                'success': False,
                'message': '请求过于频繁，请稍后再试'
            }), 429
        
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # 记录慢请求
            if duration > 1.0:
                logger.warning(f"慢请求: {request.path} 耗时 {duration:.2f}秒")
            
            return result
        except Exception as e:
            logger.error(f"API错误 {request.path}: {str(e)}\n{traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': f'服务器内部错误: {str(e)}'
            }), 500
    return wrapper


