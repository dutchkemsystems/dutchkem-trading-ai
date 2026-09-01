# Dutchkem Trading AI — Caching Configuration

import hashlib
import json
from functools import wraps

from django.core.cache import cache
from django.core.cache.backends.cache import CacheHandler


def cache_response(timeout=300, key_prefix="view"):
    """Decorator to cache view responses"""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Generate cache key from request
            cache_key = f"{key_prefix}:{request.user.id}:{request.path}:{request.GET.urlencode()}"
            cache_key_hash = hashlib.md5(cache_key.encode()).hexdigest()

            # Try to get from cache
            response = cache.get(cache_key_hash)
            if response is not None:
                return response

            # Get fresh response
            response = view_func(request, *args, **kwargs)

            # Cache the response
            if hasattr(response, "data"):
                cache.set(cache_key_hash, response, timeout)

            return response

        return _wrapped_view

    return decorator


def cache_result(timeout=600, key_prefix="func"):
    """Decorator to cache function results"""

    def decorator(func):
        @wraps(func)
        def _wrapped_func(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(a) for a in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Compute result
            result = func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result, timeout)

            return result

        return _wrapped_func

    return decorator


# Cache keys
CACHE_KEYS = {
    "SYMBOL_LIST": "symbols:list",
    "TIMEFRAME_LIST": "timeframes:list",
    "INDICATOR_LIST": "indicators:list",
    "RISK_PARAMETERS": "risk:parameters",
    "USER_PORTFOLIO": "portfolio:{user_id}",
    "MARKET_DATA": "market:{symbol}",
    "SIGNAL_LIST": "signals:active",
    "EA_LIST": "eas:list:{user_id}",
}


def invalidate_cache(pattern):
    """Invalidate all cache keys matching pattern"""
    from django.core.cache import cache

    try:
        # For Redis backend
        cache.delete_pattern(f"*{pattern}*")
    except AttributeError:
        # For non-Redis backends, clear entire cache
        cache.clear()


def get_cached_or_set(key, callable, timeout=300):
    """Get from cache or compute and cache"""
    result = cache.get(key)
    if result is None:
        result = callable()
        cache.set(key, result, timeout)
    return result
