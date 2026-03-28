import time
from typing import Optional
from collections import defaultdict
import threading


class RateLimiter:
    def __init__(self):
        self._requests: dict = defaultdict(lambda: {"count": 0, "reset_at": 0})
        self._lock = threading.Lock()
    
    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        
        with self._lock:
            data = self._requests[key]
            
            if now > data["reset_at"]:
                data["count"] = 1
                data["reset_at"] = now + window_seconds
                return True, limit - 1
            
            if data["count"] >= limit:
                return False, 0
            
            data["count"] += 1
            return True, limit - data["count"]


_rate_limiter = RateLimiter()


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    return _rate_limiter.check(key, limit, window_seconds)


async def get_rate_limit_remaining(key: str, limit: int, window_seconds: int) -> int:
    return limit


async def get_redis_client():
    return None


async def close_redis_connection():
    pass
