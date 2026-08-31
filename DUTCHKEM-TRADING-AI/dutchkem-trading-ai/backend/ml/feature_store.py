"""
Feature Store — Redis-backed feature cache for ML models.

Stores and retrieves pre-computed feature vectors keyed by
(symbol, timeframe, timestamp) so that the ensemble predictor
can access consistent, up-to-date inputs without re-computing
indicators on every prediction cycle.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("ml.feature_store")

# Try Redis; fall back to an in-memory dict for local dev / testing.
try:
    import redis as _redis_mod

    _redis_url = None  # resolved lazily from Django settings
    _redis_client = None
    _redis_available = None  # None = not tested, True/False after first use

    def _get_redis():
        global _redis_url, _redis_client, _redis_available
        if _redis_client is None:
            try:
                from django.conf import settings
                _redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            except Exception:
                _redis_url = "redis://localhost:6379/0"
            _redis_client = _redis_mod.from_url(_redis_url, decode_responses=True)
        return _redis_client

    def _redis_ok() -> bool:
        """Return True only if Redis is actually reachable."""
        global _redis_available
        if _redis_available is not None:
            return _redis_available
        try:
            _get_redis().ping()
            _redis_available = True
        except Exception:
            _redis_available = False
            logger.info("Redis not reachable — FeatureStore using in-memory fallback")
        return _redis_available

    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False
    _redis_available = False
    logger.info("redis package not installed — FeatureStore using in-memory fallback")

    def _redis_ok() -> bool:
        return False

# In-memory fallback
_memory_store: Dict[str, str] = {}
_memory_timestamps: Dict[str, float] = {}


def _build_key(symbol: str, timeframe: str, timestamp: str) -> str:
    return f"features:{symbol.upper()}:{timeframe.upper()}:{timestamp}"


def _build_pattern(symbol: str, timeframe: str) -> str:
    return f"features:{symbol.upper()}:{timeframe.upper()}:*"


class FeatureStore:
    """
    Redis-backed feature store for ML feature vectors.

    Features are stored as JSON-serialized dicts containing:
    - "values": list of floats (the feature vector)
    - "metadata": dict with optional info (model version, drift score, etc.)
    - "timestamp": ISO-8601 string
    """

    DEFAULT_TTL = 3600 * 4  # 4 hours

    def __init__(self, ttl: int = DEFAULT_TTL):
        self.ttl = ttl

    # ── Core CRUD ───────────────────────────────────────────────────────

    def store_features(
        self,
        symbol: str,
        timeframe: str,
        timestamp: str,
        features: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store a feature vector in the cache.

        Args:
            symbol:    e.g. "EURUSD"
            timeframe: e.g. "H1"
            timestamp: ISO-8601 string identifying the bar
            features:  numpy array, list, or dict of feature values
            metadata:  optional dict with extra info
        Returns:
            True on success, False on failure.
        """
        key = _build_key(symbol, timeframe, timestamp)

        if isinstance(features, np.ndarray):
            features = features.tolist()

        payload = json.dumps({
            "values": features,
            "metadata": metadata or {},
            "timestamp": timestamp,
        })

        try:
            if _redis_ok():
                _get_redis().setex(key, self.ttl, payload)
            else:
                _memory_store[key] = payload
            return True
        except Exception as exc:
            logger.error("Failed to store features for %s/%s@%s: %s", symbol, timeframe, timestamp, exc)
            return False

    def get_features(
        self,
        symbol: str,
        timeframe: str,
        timestamp: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a previously stored feature vector.

        Returns:
            dict with "values", "metadata", "timestamp" or None if not found.
        """
        key = _build_key(symbol, timeframe, timestamp)

        try:
            if _redis_ok():
                raw = _get_redis().get(key)
            else:
                raw = _memory_store.get(key)
        except Exception as exc:
            logger.error("Failed to get features for %s/%s@%s: %s", symbol, timeframe, timestamp, exc)
            return None

        if raw is None:
            return None

        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def get_latest_features(
        self,
        symbol: str,
        timeframe: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recently stored feature vector for a symbol/timeframe
        by scanning keys (Redis) or sorting in-memory.
        """
        pattern = _build_pattern(symbol, timeframe)

        try:
            if _redis_ok():
                client = _get_redis()
                keys = sorted(client.keys(pattern))
                if not keys:
                    return None
                raw = client.get(keys[-1])
            else:
                matching = {k: v for k, v in _memory_store.items() if k.startswith(f"features:{symbol.upper()}:{timeframe.upper()}:")}
                if not matching:
                    return None
                latest_key = max(matching.keys())
                raw = matching[latest_key]

            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.error("Failed to get latest features for %s/%s: %s", symbol, timeframe, exc)
            return None

    # ── Bulk helpers ────────────────────────────────────────────────────

    def store_features_batch(
        self,
        symbol: str,
        timeframe: str,
        entries: List[Dict[str, Any]],
    ) -> int:
        """
        Store multiple feature vectors at once.

        Args:
            entries: list of dicts with keys "timestamp", "values", optional "metadata"
        Returns:
            Number of entries successfully stored.
        """
        stored = 0
        for entry in entries:
            ts = entry.get("timestamp")
            vals = entry.get("values")
            meta = entry.get("metadata")
            if ts is not None and vals is not None:
                if self.store_features(symbol, timeframe, ts, vals, meta):
                    stored += 1
        return stored

    def get_features_range(
        self,
        symbol: str,
        timeframe: str,
        start_ts: str,
        end_ts: str,
    ) -> List[Dict[str, Any]]:
        """Retrieve all stored features for a symbol/timeframe within a timestamp range."""
        pattern = _build_pattern(symbol, timeframe)

        try:
            if _redis_ok():
                keys = sorted(_get_redis().keys(pattern))
                raw_items = [_get_redis().get(k) for k in keys]
            else:
                matching = {k: v for k, v in _memory_store.items() if k.startswith(pattern.rstrip("*"))}
                raw_items = [matching[k] for k in sorted(matching.keys())]

            results = []
            for raw in raw_items:
                if raw is None:
                    continue
                try:
                    obj = json.loads(raw)
                    ts = obj.get("timestamp", "")
                    if start_ts <= ts <= end_ts:
                        results.append(obj)
                except (json.JSONDecodeError, TypeError):
                    continue
            return results
        except Exception as exc:
            logger.error("Failed range query for %s/%s: %s", symbol, timeframe, exc)
            return []

    # ── Data-quality check ──────────────────────────────────────────────

    def has_enough_data(
        self,
        symbol: str,
        timeframe: str,
        min_bars: int = 50,
    ) -> bool:
        """
        Check whether the store has at least *min_bars* feature vectors
        for the given symbol/timeframe. Useful to decide if a model
        can be safely invoked.
        """
        pattern = _build_pattern(symbol, timeframe)

        try:
            if _redis_ok():
                count = len(_get_redis().keys(pattern))
            else:
                count = sum(1 for k in _memory_store if k.startswith(pattern.rstrip("*")))
            return count >= min_bars
        except Exception as exc:
            logger.error("Data-count check failed for %s/%s: %s", symbol, timeframe, exc)
            return False

    def clear(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> int:
        """Delete matching keys.  Returns number of keys deleted."""
        if symbol and timeframe:
            pattern = _build_pattern(symbol, timeframe)
        elif symbol:
            pattern = f"features:{symbol.upper()}:*"
        else:
            pattern = "features:*"

        try:
            if _redis_ok():
                keys = _get_redis().keys(pattern)
                if keys:
                    return _get_redis().delete(*keys)
                return 0
            else:
                to_delete = [k for k in _memory_store if k.startswith(pattern.rstrip("*"))]
                for k in to_delete:
                    del _memory_store[k]
                return len(to_delete)
        except Exception as exc:
            logger.error("Failed to clear features: %s", exc)
            return 0
