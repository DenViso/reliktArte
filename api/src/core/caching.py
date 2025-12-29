import hashlib
import asyncio
import functools
import pickle
from typing import Any, Optional, Callable

from redis.asyncio import Redis

from .config import settings


class RedisCaching:
    _redis_instance: Optional[Redis] = None

    def __init__(self) -> None:
        if not RedisCaching._redis_instance:
            RedisCaching._redis_instance = Redis.from_url(settings.cache.redis_url)
        self.redis = RedisCaching._redis_instance

    @classmethod
    def init(cls):
        """Initialize Redis client"""
        if not cls._redis_instance:
            cls._redis_instance = Redis.from_url(settings.cache.redis_url)

    @classmethod
    def get_cache_key(
        cls,
        func: Callable,
        namespace: str = "",
        prefix: str = "",
    ) -> str:
        """
        Generates a hashed cache key based on the
        function name, prefix, and namespace.
        """
        prefix_str = f"{prefix}:{namespace}:" if prefix or namespace else ""
        key_raw = f"{func.__module__}:{func.__name__}"
        cache_key = prefix_str + hashlib.md5(key_raw.encode()).hexdigest()
        return cache_key

    async def _get_processed_value(self, value: Any) -> Any:
        return pickle.loads(value) if value else None

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        return await self._get_processed_value(value)

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = 15,
    ) -> None:
        serialized_value = pickle.dumps(value)
        if expire:
            await self.redis.setex(key, expire, serialized_value)
        else:
            await self.redis.set(key, serialized_value)


def init_caching():
    """Initialize the cache backend"""
    RedisCaching.init()


def cache(
    expire: int = 60,
    namespace: str = "",
    prefix: str = "",
) -> Callable:
    """
    Cache decorator to cache the result of the function.
    Works with both async and sync functions.
    """

    def wrapper(func: Callable) -> Callable:
        @functools.wraps(func)
        async def inner(*args, **kwargs) -> Any:
            redis_caching = RedisCaching()
            cache_key = RedisCaching.get_cache_key(func, namespace, prefix)

            cached_value = await redis_caching.get(cache_key)
            if cached_value is not None:
                return cached_value

            if asyncio.iscoroutinefunction(func):
                res = await func(*args, **kwargs)
            else:
                res = func(*args, **kwargs)

            await redis_caching.set(cache_key, res, expire)
            return res

        return inner

    return wrapper
