import os

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
        "OPTIONS": {
            "db": "1",
        },
        "KEY_PREFIX": "dutchkem",
        "TIMEOUT": 300,
    },
    "trading": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/2"),
        "OPTIONS": {
            "db": "2",
        },
        "KEY_PREFIX": "trading",
        "TIMEOUT": 60,
    },
    "market_data": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/3"),
        "OPTIONS": {
            "db": "3",
        },
        "KEY_PREFIX": "market",
        "TIMEOUT": 30,
    },
    "sessions": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/4"),
        "OPTIONS": {
            "db": "4",
        },
        "KEY_PREFIX": "session",
        "TIMEOUT": 86400,
    },
}


def cache_trading_data(timeout=60):
    from django.core.cache import caches
    return caches["trading"]


def cache_market_data(timeout=30):
    from django.core.cache import caches
    return caches["market_data"]
