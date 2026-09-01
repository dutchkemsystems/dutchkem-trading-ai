"""
Auto-Retraining Triggers for ML models.

Monitors model accuracy, detects data drift, and triggers
retraining when quality degrades or on a weekly schedule.
"""

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ml.auto_retrain")

# ── Optional Redis-backed persistence ───────────────────────────────────
try:
    import redis as _redis_mod

    _redis_client = None
    _redis_available = None  # None = untested, True/False after first ping

    def _get_redis():
        global _redis_client
        if _redis_client is None:
            try:
                from django.conf import settings
                url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            except Exception:
                url = "redis://localhost:6379/0"
            _redis_client = _redis_mod.from_url(url, decode_responses=True)
        return _redis_client

    def _redis_ok() -> bool:
        global _redis_available
        if _redis_available is not None:
            return _redis_available
        try:
            _get_redis().ping()
            _redis_available = True
        except Exception:
            _redis_available = False
        return _redis_available

except ImportError:
    _redis_available = False

    def _redis_ok() -> bool:
        return False

# In-memory fallback for dev/testing
_memory: Dict[str, str] = {}


def _store(key: str, value: str, ttl: int = 3600 * 24 * 30):
    if _redis_ok():
        try:
            _get_redis().setex(key, ttl, value)
        except Exception:
            _memory[key] = value
    else:
        _memory[key] = value


def _load(key: str) -> Optional[str]:
    if _redis_ok():
        try:
            return _get_redis().get(key)
        except Exception:
            return _memory.get(key)
    return _memory.get(key)


# ── Accuracy Tracker ───────────────────────────────────────────────────

class AccuracyTracker:
    """
    Tracks rolling prediction accuracy per model and triggers
    retraining when accuracy drops below a configurable threshold.
    """

    ROLLING_WINDOW = 100  # last N predictions to evaluate

    def __init__(
        self,
        model_name: str,
        accuracy_threshold: float = 0.55,
        window: int = ROLLING_WINDOW,
    ):
        self.model_name = model_name
        self.accuracy_threshold = accuracy_threshold
        self.window = window
        self._prefix = f"retrain:accuracy:{model_name}"

    def record_prediction(self, predicted: Any, actual: Any) -> None:
        """Record a single prediction outcome."""
        correct = 1 if predicted == actual else 0
        key = f"{self._prefix}:outcomes"
        try:
            if _redis_ok():
                client = _get_redis()
                client.rpush(key, correct)
                client.ltrim(key, -self.window - 1, -1)
                client.expire(key, 3600 * 24 * 30)
            else:
                outcomes = json.loads(_memory.get(key, "[]"))
                outcomes.append(correct)
                _memory[key] = json.dumps(outcomes[-self.window - 1:])
        except Exception as exc:
            logger.error("Failed to record prediction for %s: %s", self.model_name, exc)

    def get_rolling_accuracy(self) -> float:
        """Return accuracy over the rolling window (0.0–1.0)."""
        key = f"{self._prefix}:outcomes"
        try:
            if _redis_ok():
                raw = _get_redis().lrange(key, -self.window, -1)
                outcomes = [int(x) for x in raw] if raw else []
            else:
                outcomes = json.loads(_memory.get(key, "[]"))
        except Exception:
            outcomes = []

        if not outcomes:
            return 0.0
        return sum(outcomes) / len(outcomes)

    def should_retrain(self) -> bool:
        """Return True if rolling accuracy is below the threshold."""
        acc = self.get_rolling_accuracy()
        return acc < self.accuracy_threshold

    def get_status(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "rolling_accuracy": round(self.get_rolling_accuracy(), 4),
            "threshold": self.accuracy_threshold,
            "should_retrain": self.should_retrain(),
        }


# ── Data Drift Detection ───────────────────────────────────────────────

class DataDriftDetector:
    """
    Detects data drift by computing the KL divergence between
    a reference feature distribution and the current one.
    """

    # Thresholds per metric
    KL_DIVERGENCE_THRESHOLD = 0.1  # above this → drift suspected

    @staticmethod
    def _normalize(distribution: List[float]) -> List[float]:
        """Convert to probability distribution."""
        total = sum(abs(v) for v in distribution)
        if total == 0:
            return [1.0 / len(distribution)] * len(distribution)
        return [abs(v) / total for v in distribution]

    @staticmethod
    def kl_divergence(p: List[float], q: List[float], epsilon: float = 1e-10) -> float:
        """
        Compute KL(p || q) with Laplace smoothing to avoid log(0).
        """
        p_norm = DataDriftDetector._normalize(p)
        q_norm = DataDriftDetector._normalize(q)

        # Ensure same length
        max_len = max(len(p_norm), len(q_norm))
        p_norm.extend([epsilon] * (max_len - len(p_norm)))
        q_norm.extend([epsilon] * (max_len - len(q_norm)))

        kl = 0.0
        for pi, qi in zip(p_norm, q_norm):
            pi = max(pi, epsilon)
            qi = max(qi, epsilon)
            kl += pi * math.log(pi / qi)
        return kl

    def check_drift(
        self,
        reference_features: List[float],
        current_features: List[float],
    ) -> Dict[str, Any]:
        """
        Compare current features against a reference distribution.

        Returns:
            dict with:
                kl_divergence  – float
                drifted        – bool
                severity       – "none" | "mild" | "moderate" | "severe"
        """
        kl = self.kl_divergence(reference_features, current_features)

        if kl < 0.05:
            severity = "none"
        elif kl < 0.1:
            severity = "mild"
        elif kl < 0.5:
            severity = "moderate"
        else:
            severity = "severe"

        return {
            "kl_divergence": round(kl, 6),
            "drifted": kl > self.KL_DIVERGENCE_THRESHOLD,
            "severity": severity,
        }


# ── Retrain Scheduler ──────────────────────────────────────────────────

class AutoRetrainManager:
    """
    Coordinates accuracy tracking, drift detection, and
    retrain triggering for all ML models.
    """

    WEEKLY_RETRAIN_HOUR = 2  # UTC hour on Sundays

    def __init__(self, models: Optional[List[str]] = None):
        self.model_names = models or ["lstm", "regime", "sr_levels", "volatility"]
        self.trackers: Dict[str, AccuracyTracker] = {}
        self.drift_detector = DataDriftDetector()

        for name in self.model_names:
            self.trackers[name] = AccuracyTracker(name)

        self._schedule_key = "retrain:last_scheduled"

    def record_outcome(self, model_name: str, predicted: Any, actual: Any) -> None:
        """Record a prediction outcome for a model."""
        tracker = self.trackers.get(model_name)
        if tracker:
            tracker.record_prediction(predicted, actual)

    def get_all_status(self) -> Dict[str, Any]:
        """Return status for every tracked model."""
        status = {}
        for name, tracker in self.trackers.items():
            status[name] = tracker.get_status()
        status["weekly_retrain_due"] = self.is_weekly_retrain_due()
        return status

    def get_retrain_candidates(self) -> List[str]:
        """Return list of model names that need retraining."""
        candidates = []
        for name, tracker in self.trackers.items():
            if tracker.should_retrain():
                candidates.append(name)
        return candidates

    def is_weekly_retrain_due(self) -> bool:
        """Check if a weekly scheduled retrain is due (Sunday 02:00 UTC)."""
        now = datetime.utcnow()
        last_raw = _load(self._schedule_key)

        if last_raw:
            try:
                last = datetime.fromisoformat(last_raw)
            except (ValueError, TypeError):
                last = datetime.min
        else:
            last = datetime.min

        # Is it Sunday after 02:00 UTC?
        if now.weekday() == 6 and now.hour >= self.WEEKLY_RETRAIN_HOUR:
            # Has it already been triggered this week?
            if (now - last).total_seconds() > 3600 * 24:
                return True

        return False

    def mark_weekly_retrain_done(self) -> None:
        """Mark the weekly retrain as completed."""
        _store(self._schedule_key, datetime.utcnow().isoformat())

    def should_retrain(self, model_name: Optional[str] = None) -> bool:
        """
        Determine if retraining is needed.

        Args:
            model_name: specific model, or None to check all
        Returns:
            True if any (or the specified) model needs retraining.
        """
        if model_name:
            tracker = self.trackers.get(model_name)
            if tracker and tracker.should_retrain():
                return True
            return self.is_weekly_retrain_due()

        # Check all models
        return bool(self.get_retrain_candidates()) or self.is_weekly_retrain_due()

    def check_drift(
        self,
        model_name: str,
        reference_features: List[float],
        current_features: List[float],
    ) -> Dict[str, Any]:
        """
        Check for data drift and store the result.

        If drift is detected, the model is automatically flagged
        for retraining via the AccuracyTracker.
        """
        result = self.drift_detector.check_drift(reference_features, current_features)

        _store(
            f"retrain:drift:{model_name}",
            json.dumps(result),
        )

        if result["drifted"]:
            logger.warning(
                "Data drift detected for %s: KL=%.4f severity=%s",
                model_name,
                result["kl_divergence"],
                result["severity"],
            )
            # Force the accuracy tracker to signal retrain
            tracker = self.trackers.get(model_name)
            if tracker:
                # Inject a few wrong predictions to lower rolling accuracy
                for _ in range(5):
                    tracker.record_prediction(0, 1)

        return result
