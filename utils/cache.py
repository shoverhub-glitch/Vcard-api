import time
from typing import Optional, Any
from collections import defaultdict
import threading
import hashlib
import json


class Cache:
    def __init__(self, default_ttl: int = 300):
        self._cache: dict = {}
        self._timestamps: dict = {}
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            
            if time.time() > self._timestamps.get(key, 0):
                del self._cache[key]
                del self._timestamps[key]
                return None
            
            return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time() + (ttl or self._default_ttl)
    
    def delete(self, key: str):
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
    
    def clear(self):
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def clear_expired(self):
        now = time.time()
        with self._lock:
            keys_to_delete = [k for k, t in self._timestamps.items() if now > t]
            for key in keys_to_delete:
                del self._cache[key]
                del self._timestamps[key]


_cache = Cache(default_ttl=300)


def cache_key(*args) -> str:
    return hashlib.md5(json.dumps(args, sort_keys=True).encode()).hexdigest()


def get_cached(key: str) -> Optional[Any]:
    return _cache.get(key)


def set_cached(key: str, value: Any, ttl: int = 300):
    _cache.set(key, value, ttl)


def invalidate_cache(key: str):
    _cache.delete(key)


def clear_all_cache():
    _cache.clear()
