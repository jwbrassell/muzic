"""Redis caching implementation for the application."""
import json
from functools import wraps
from typing import Any, Callable, Optional, Union
import redis
from app.core.config import get_settings

def get_redis_client():
    """Get Redis client with current settings."""
    settings = get_settings()
    return redis.Redis(
        host=settings.cache.redis_host,
        port=settings.cache.redis_port,
        db=settings.cache.redis_db,
        decode_responses=True
    )

# Initialize Redis connection pool
redis_client = get_redis_client()

class CacheError(Exception):
    """Base exception for cache-related errors."""
    pass

def serialize_value(value: Any) -> str:
    """Serialize a value for storage in Redis."""
    try:
        return json.dumps(value)
    except (TypeError, ValueError) as e:
        raise CacheError(f"Failed to serialize value: {e}")

def deserialize_value(value: str) -> Any:
    """Deserialize a value from Redis storage."""
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise CacheError(f"Failed to deserialize value: {e}")

def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache."""
    try:
        value = redis_client.get(key)
        return deserialize_value(value) if value else None
    except redis.RedisError as e:
        raise CacheError(f"Redis error while getting key {key}: {e}")

def cache_set(key: str, value: Any, timeout: Optional[int] = None) -> None:
    """Set a value in cache with optional timeout."""
    try:
        serialized = serialize_value(value)
        if timeout:
            redis_client.setex(key, timeout, serialized)
        else:
            redis_client.set(key, serialized)
    except redis.RedisError as e:
        raise CacheError(f"Redis error while setting key {key}: {e}")

def cache_delete(key: str) -> None:
    """Delete a value from cache."""
    try:
        redis_client.delete(key)
    except redis.RedisError as e:
        raise CacheError(f"Redis error while deleting key {key}: {e}")

def cache_clear_pattern(pattern: str) -> None:
    """Clear all keys matching the given pattern."""
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except redis.RedisError as e:
        raise CacheError(f"Redis error while clearing pattern {pattern}: {e}")

def cached(
    key_prefix: str,
    timeout: Optional[int] = None,
    key_builder: Optional[Callable[..., str]] = None
) -> Callable:
    """
    Decorator for caching function results.
    
    Args:
        key_prefix: Prefix for the cache key
        timeout: Optional cache timeout in seconds
        key_builder: Optional function to build cache key from function arguments
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key
            if key_builder:
                cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            else:
                # Default key builder uses args and kwargs
                key_parts = [str(arg) for arg in args]
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{key_prefix}:{':'.join(key_parts)}"

            # Try to get from cache
            try:
                cached_value = cache_get(cache_key)
                if cached_value is not None:
                    return cached_value
            except CacheError:
                # Log error but continue with function execution
                pass

            # Execute function and cache result
            result = func(*args, **kwargs)
            try:
                cache_set(cache_key, result, timeout)
            except CacheError:
                # Log error but return result anyway
                pass

            return result
        return wrapper
    return decorator

def invalidate_cache(pattern: str) -> Callable:
    """
    Decorator to invalidate cache entries matching a pattern after function execution.
    
    Args:
        pattern: Pattern of cache keys to invalidate
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            try:
                cache_clear_pattern(pattern)
            except CacheError:
                # Log error but return result anyway
                pass
            return result
        return wrapper
    return decorator

def health_check() -> bool:
    """Check if Redis connection is healthy."""
    try:
        return redis_client.ping()
    except redis.RedisError:
        return False
