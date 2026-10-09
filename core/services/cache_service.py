"""
Cache Service - In-memory caching for performance optimization
"""

import time
import hashlib
import json
from typing import Optional, Any, Dict, Callable, TypeVar, cast
from functools import wraps
from threading import Lock
from datetime import datetime, timedelta


class CacheService:
    """In-memory cache service with TTL support"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_parts = [prefix]
        if args:
            key_parts.append(str(hash(str(args))))
        if kwargs:
            # Sort kwargs for consistent key generation
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(str(hash(str(sorted_kwargs))))
        
        key_string = ":".join(key_parts)
        # Use SHA256 instead of MD5 for better security (even for cache keys)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self._cache[key]
                self._stats["misses"] += 1
                return None
            
            self._stats["hits"] += 1
            return entry["value"]
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (0 = no expiration)
        """
        with self._lock:
            expires_at = time.time() + ttl if ttl > 0 else None
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time()
            }
            self._stats["sets"] += 1
    
    def delete(self, key: str):
        """Delete value from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["deletes"] += 1
    
    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
            self._stats["deletes"] += len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "deletes": self._stats["deletes"],
                "hit_rate_percent": round(hit_rate, 2),
                "size": len(self._cache)
            }
    
    def cleanup_expired(self):
        """Remove expired entries from cache"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry["expires_at"] and entry["expires_at"] < current_time
            ]
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)


# Global cache instance
_cache_service: Optional[CacheService] = None


def get_cache() -> CacheService:
    """Get global cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


F = TypeVar('F', bound=Callable[..., Any])

def cache_result(ttl: int = 3600, key_prefix: Optional[str] = None) -> Callable[[F], F]:
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Optional prefix for cache key (defaults to function name)
    
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            cache_key = cache._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            cache_key = cache._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)
    
    return decorator

