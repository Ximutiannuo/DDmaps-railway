"""
请求限流器
"""
import time
import threading
from collections import deque
from backend.config import Config

class RateLimiter:
    """基于时间窗口的请求限流器"""
    
    def __init__(self, max_requests: int = None, window_seconds: int = None):
        self.max_requests = max_requests or Config.RATE_LIMIT_MAX_REQUESTS
        self.window_seconds = window_seconds or Config.RATE_LIMIT_WINDOW_SECONDS
        self.requests = deque()
        self.lock = threading.Lock()
    
    def is_allowed(self) -> bool:
        """检查是否允许请求"""
        with self.lock:
            now = time.time()
            # 清理过期请求
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            if len(self.requests) >= self.max_requests:
                return False
            
            self.requests.append(now)
            return True

# 全局限流器实例
rate_limiter = RateLimiter()


