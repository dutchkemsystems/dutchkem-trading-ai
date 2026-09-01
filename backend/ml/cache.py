import logging
from django.core.cache import caches

logger = logging.getLogger("ml.cache")


class MLCache:
    def __init__(self, cache_name="default"):
        self._cache = caches[cache_name]

    def get(self, key):
        return self._cache.get(key)

    def set(self, key, value, timeout=300):
        self._cache.set(key, value, timeout)

    def delete(self, key):
        self._cache.delete(key)

    def clear(self):
        self._cache.clear()
