"""Кэширование данных для улучшения производительности."""
from typing import Optional, Any, Dict
import json
import time
from functools import wraps
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Redis не установлен. Используется in-memory кэш.")

class MemoryCache:
    """In-memory кэш с TTL."""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша."""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["value"]
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Сохранить значение в кэш."""
        self.cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
    
    def invalidate(self, key: str) -> None:
        """Инвалидировать кэш по ключу."""
        if key in self.cache:
            del self.cache[key]
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Инвалидировать кэш по паттерну."""
        keys_to_delete = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.cache[key]


class RedisCache:
    """Redis кэш."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_seconds: int = 300):
        self.client = redis.from_url(redis_url)
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из Redis."""
        value = self.client.get(key)
        if value:
            return json.loads(value)
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Сохранить значение в Redis."""
        self.client.setex(key, self.ttl, json.dumps(value))
    
    def invalidate(self, key: str) -> None:
        """Удалить ключ из Redis."""
        self.client.delete(key)
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Удалить ключи по паттерну."""
        for key in self.client.scan_iter(match=pattern):
            self.client.delete(key)


Cache = RedisCache if REDIS_AVAILABLE else MemoryCache
cache = Cache()


def cached(ttl_seconds: int = 300):
    """Декоратор для кэширования результатов функций."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = await func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern: str = "*"):
    """Инвалидировать кэш по паттерну."""
    cache.invalidate_pattern(pattern)