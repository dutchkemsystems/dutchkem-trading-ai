"""
Online / Incremental Learning Pipeline.

Provides concept-drift detection, sliding-window training,
A/B model testing, incremental ensembles, and integration with
the existing auto_retrain system.
"""

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from sklearn.base import BaseEstimator
except ImportError:
    BaseEstimator = object  # type: ignore[assignment,misc]
logger = logging.getLogger("ml.online_learning")


def _normal_cdf(x: float) -> float:
    """Approximation of the standard normal CDF using the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ── Drift Alert ─────────────────────────────────────────────────────────


@dataclass
class DriftAlert:
    """Structured alert raised when concept drift is detected."""
    drift_type: str          # "adwin" | "page_hinkley" | "ddm" | "none"
    severity: str            # "low" | "medium" | "high" | "critical"
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.recommended_action:
            self.recommended_action = self._default_action()

    def _default_action(self) -> str:
        actions = {
            "low": "Monitor closely; no immediate retrain needed.",
            "medium": "Schedule retrain within the next update window.",
            "high": "Retrain model immediately with recent data.",
            "critical": "Retrain now and consider rolling back to previous model.",
        }
        return actions.get(self.severity, "Investigate drift alert.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_type": self.drift_type,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "details": self.details,
            "recommended_action": self.recommended_action,
        }


# ── Concept Drift Detectors ────────────────────────────────────────────


class ConceptDriftDetector:
    """
    Ensemble of drift detection methods: ADWIN, Page-Hinkley, and DDM.
    """

    def __init__(
        self,
        adwin_delta: float = 0.002,
        ph_lambda: float = 50.0,
        ph_alpha: float = 0.005,
        ddm_warning_level: float = 2.0,
        ddm_drift_level: float = 3.0,
        ddm_min_samples: int = 30,
    ):
        self.adwin_delta = adwin_delta
        self.ph_lambda = ph_lambda
        self.ph_alpha = ph_alpha
        self.ddm_warning_level = ddm_warning_level
        self.ddm_drift_level = ddm_drift_level
        self.ddm_min_samples = ddm_min_samples

        # ADWIN state
        self._adwin_window: deque = deque()
        self._adwin_total: float = 0.0
        self._adwin_var: float = 0.0

        # Page-Hinkley state
        self._ph_sum: float = 0.0
        self._ph_min: float = float("inf")
        self._ph_count: int = 0

        # DDM state
        self._ddm_n: int = 0
        self._ddm_p: float = 0.0
        self._ddm_s: float = 0.0
        self._ddm_p_min: float = float("inf")
        self._ddm_s_min: float = float("inf")

    def reset(self) -> None:
        """Reset all detector states."""
        self._adwin_window.clear()
        self._adwin_total = 0.0
        self._adwin_var = 0.0
        self._ph_sum = 0.0
        self._ph_min = float("inf")
        self._ph_count = 0
        self._ddm_n = 0
        self._ddm_p = 0.0
        self._ddm_s = 0.0
        self._ddm_p_min = float("inf")
        self._ddm_s_min = float("inf")

    # ── ADWIN ───────────────────────────────────────────────────────────

    def _adwin_update(self, value: float) -> bool:
        """
        ADWIN: maintain a window and detect if the mean has changed
        significantly by testing all possible splits.
        """
        self._adwin_window.append(value)
        self._adwin_total += value
        n = len(self._adwin_window)

        if n < 10:
            return False

        # Check all possible splits
        arr = list(self._adwin_window)
        for split in range(5, n - 5):
            left = arr[:split]
            right = arr[split:]
            n0, n1 = len(left), len(right)
            mean0, mean1 = sum(left) / n0, sum(right) / n1
            var0 = sum((x - mean0) ** 2 for x in left) / max(n0, 1)
            var1 = sum((x - mean1) ** 2 for x in right) / max(n1, 1)

            m = 1.0 / n0 + 1.0 / n1
            eps = math.sqrt(2.0 * m * math.log(2.0 * n / self.adwin_delta) / 2.0)
            bound = math.sqrt(var0 * m) + eps + math.sqrt(var1 * m) + eps

            if abs(mean0 - mean1) > bound:
                # Drift detected — shrink window
                for _ in range(split):
                    removed = self._adwin_window.popleft()
                    self._adwin_total -= removed
                return True

        return False

    # ── Page-Hinkley ────────────────────────────────────────────────────

    def _page_hinkley_update(self, value: float) -> bool:
        """
        Page-Hinkley test: monitors the cumulative sum of deviations
        from the running mean.
        """
        self._ph_count += 1
        if self._ph_count == 1:
            self._ph_mean = value
            self._ph_sum = 0.0
            self._ph_min = 0.0
            return False

        self._ph_mean += (value - self._ph_mean) / self._ph_count
        self._ph_sum += value - self._ph_mean - self.ph_alpha
        self._ph_min = min(self._ph_min, self._ph_sum)

        if self._ph_sum - self._ph_min > self.ph_lambda:
            return True
        return False

    # ── DDM ─────────────────────────────────────────────────────────────

    def _ddm_update(self, error: float) -> Tuple[bool, bool]:
        """
        Drift Detection Method: tracks error rate and standard deviation.
        Returns (warning, drift).
        """
        self._ddm_n += 1
        self._ddm_p += (error - self._ddm_p) / self._ddm_n
        self._ddm_s = math.sqrt(self._ddm_p * (1 - self._ddm_p) / max(self._ddm_n, 1))

        if self._ddm_n < self.ddm_min_samples:
            return False, False

        if self._ddm_p + self._ddm_s < self._ddm_p_min + self._ddm_s_min:
            self._ddm_p_min = self._ddm_p
            self._ddm_s_min = self._ddm_s

        warning = self._ddm_p + self._ddm_s > self._ddm_p_min + self.ddm_warning_level * self._ddm_s_min
        drift = self._ddm_p + self._ddm_s > self._ddm_p_min + self.ddm_drift_level * self._ddm_s_min

        return warning, drift

    # ── Combined detection ──────────────────────────────────────────────

    def detect(
        self,
        old_predictions: np.ndarray,
        new_predictions: np.ndarray,
    ) -> Tuple[bool, str]:
        """
        Compare old vs new prediction distributions.

        Args:
            old_predictions: reference predictions (e.g., on training set).
            new_predictions: recent predictions (sliding window).

        Returns:
            (drift_detected, drift_type) where drift_type is one of
            "adwin", "page_hinkley", "ddm", or "none".
        """
        if len(old_predictions) < 10 or len(new_predictions) < 10:
            return False, "none"

        old_arr = np.asarray(old_predictions, dtype=np.float64)
        new_arr = np.asarray(new_predictions, dtype=np.float64)

        # Use absolute errors relative to the reference mean as input
        ref_mean = float(np.mean(old_arr))
        errors_old = np.abs(old_arr - ref_mean)
        errors_new = np.abs(new_arr - ref_mean)

        # ADWIN
        for e in errors_new:
            if self._adwin_update(float(e)):
                return True, "adwin"

        # Page-Hinkley
        for e in errors_new:
            if self._page_hinkley_update(float(e)):
                return True, "page_hinkley"

        # DDM — treat 0/1 error (correct/incorrect)
        old_cls = np.round(old_arr).astype(int)
        new_cls = np.round(new_arr).astype(int)
        for nc in new_cls:
            error_val = 1.0 if nc != int(np.median(old_cls)) else 0.0
            warning, drift = self._ddm_update(error_val)
            if drift:
                return True, "ddm"

        return False, "none"


# ── Online Learner ──────────────────────────────────────────────────────


class OnlineLearner:
    """
    Wraps scikit-learn models that support `partial_fit` for
    incremental / online learning.
    """

    SUPPORTED_TYPES = ("SGDClassifier", "SGDRegressor", "MiniBatchKMeans",
                       "Perceptron", "PassiveAggressiveClassifier",
                       "PassiveAggressiveRegressor")

    def __init__(self, drift_detector: Optional[ConceptDriftDetector] = None):
        self.drift_detector = drift_detector or ConceptDriftDetector()
        self._last_old_predictions: Optional[np.ndarray] = None
        self._recent_predictions: deque = deque(maxlen=500)

    def partial_fit(
        self,
        model: BaseEstimator,
        X_batch: np.ndarray,
        y_batch: np.ndarray,
        classes: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Incrementally fit the model with a new batch.

        Args:
            model: sklearn model with partial_fit method.
            X_batch: feature matrix (n_samples, n_features).
            y_batch: target vector (n_samples,).
            classes: unique class labels (required for classifiers on first call).

        Returns:
            dict with status info.
        """
        if not hasattr(model, "partial_fit"):
            raise TypeError(
                f"Model {type(model).__name__} does not support partial_fit"
            )

        X = np.asarray(X_batch, dtype=np.float32)
        y = np.asarray(y_batch)

        try:
            if classes is not None:
                model.partial_fit(X, y, classes=classes)
            else:
                model.partial_fit(X, y)

            # Track predictions for drift detection
            preds = model.predict(X)
            self._recent_predictions.extend(preds.tolist())

            return {
                "status": "success",
                "samples_seen": X.shape[0],
                "model_type": type(model).__name__,
            }
        except Exception as exc:
            logger.error("partial_fit failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    def detect_concept_drift(
        self,
        X_recent: np.ndarray,
        y_recent: np.ndarray,
        window: int = 100,
    ) -> DriftAlert:
        """
        Check for concept drift by comparing recent predictions
        against stored reference predictions.

        Args:
            X_recent: recent feature batch.
            y_recent: recent true labels.
            window: size of the recent prediction window.

        Returns:
            DriftAlert with detection results.
        """
        recent = np.array(list(self._recent_predictions)[-window:])

        if self._last_old_predictions is None:
            self._last_old_predictions = recent.copy()
            return DriftAlert(
                drift_type="none",
                severity="low",
                details={"message": "Reference predictions established."},
            )

        drift_detected, drift_type = self.drift_detector.detect(
            self._last_old_predictions, recent
        )

        if drift_detected:
            # Assess severity based on magnitude
            old_mean = float(np.mean(self._last_old_predictions))
            new_mean = float(np.mean(recent))
            diff = abs(new_mean - old_mean)

            if diff > 0.5:
                severity = "critical"
            elif diff > 0.3:
                severity = "high"
            elif diff > 0.15:
                severity = "medium"
            else:
                severity = "low"

            alert = DriftAlert(
                drift_type=drift_type,
                severity=severity,
                details={
                    "old_mean": old_mean,
                    "new_mean": new_mean,
                    "diff": diff,
                    "window": window,
                },
            )
            logger.warning(
                "Concept drift detected: type=%s severity=%s diff=%.4f",
                drift_type, severity, diff,
            )
            # Update reference
            self._last_old_predictions = recent.copy()
            self.drift_detector.reset()
            return alert

        return DriftAlert(
            drift_type="none",
            severity="low",
            details={"message": "No drift detected."},
        )

    def auto_retrain(
        self,
        model: BaseEstimator,
        X_train: np.ndarray,
        y_train: np.ndarray,
        drift_detected: bool,
        retrain_batch_size: int = 256,
        classes: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Conditionally retrain the model when drift is detected.

        Args:
            model: sklearn model with partial_fit.
            X_train: full training data.
            y_train: full training labels.
            drift_detected: whether drift was detected.
            retrain_batch_size: batch size for retraining.
            classes: class labels for classifiers.

        Returns:
            dict with retrain status.
        """
        if not drift_detected:
            return {"status": "no_retrain_needed"}

        logger.info("Auto-retrain triggered for %s", type(model).__name__)

        n_samples = X_train.shape[0]
        n_batches = math.ceil(n_samples / retrain_batch_size)
        total_samples = 0

        for i in range(n_batches):
            start = i * retrain_batch_size
            end = min(start + retrain_batch_size, n_samples)
            X_b = X_train[start:end]
            y_b = y_train[start:end]

            if i == 0 and classes is not None:
                self.partial_fit(model, X_b, y_b, classes=classes)
            else:
                self.partial_fit(model, X_b, y_b)
            total_samples += X_b.shape[0]

        logger.info("Retrain complete: %d samples in %d batches", total_samples, n_batches)

        return {
            "status": "retrained",
            "samples_used": total_samples,
            "n_batches": n_batches,
        }


# ── Sliding Window Trainer ─────────────────────────────────────────────


class SlidingWindowTrainer:
    """
    Maintains a sliding window of recent data and retrains
    a model when enough new samples accumulate.
    """

    def __init__(
        self,
        window_size: int = 2000,
        retrain_threshold: int = 200,
        min_samples: int = 100,
    ):
        self.window_size = window_size
        self.retrain_threshold = retrain_threshold
        self.min_samples = min_samples
        self._X_window: deque = deque(maxlen=window_size)
        self._y_window: deque = deque(maxlen=window_size)
        self._samples_since_train: int = 0
        self._total_samples_seen: int = 0
        self._total_retrains: int = 0

    def add_sample(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Add one or more samples to the sliding window.

        Args:
            X: feature array (n_samples, n_features) or (n_features,).
            y: label array (n_samples,) or scalar.
        """
        X = np.atleast_2d(X)
        y = np.atleast_1d(y)
        for xi, yi in zip(X, y):
            self._X_window.append(xi)
            self._y_window.append(yi)
        self._samples_since_train += len(y)
        self._total_samples_seen += len(y)

    def get_window_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return current window as numpy arrays."""
        if not self._X_window:
            return np.array([]), np.array([])
        X = np.array(list(self._X_window), dtype=np.float32)
        y = np.array(list(self._y_window))
        return X, y

    def train_if_needed(
        self,
        model: BaseEstimator,
        classes: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Retrain the model if enough new samples have accumulated.

        Returns:
            dict with training status.
        """
        n_in_window = len(self._X_window)

        if n_in_window < self.min_samples:
            return {
                "status": "insufficient_data",
                "window_size": n_in_window,
                "min_samples": self.min_samples,
            }

        if self._samples_since_train < self.retrain_threshold:
            return {
                "status": "waiting",
                "samples_since_train": self._samples_since_train,
                "threshold": self.retrain_threshold,
            }

        X, y = self.get_window_data()
        logger.info(
            "Sliding window retrain: %d samples, %d new since last",
            n_in_window, self._samples_since_train,
        )

        try:
            if hasattr(model, "partial_fit"):
                if classes is not None:
                    model.partial_fit(X, y, classes=classes)
                else:
                    model.partial_fit(X, y)
            else:
                model.fit(X, y)

            self._samples_since_train = 0
            self._total_retrains += 1

            return {
                "status": "retrained",
                "window_size": n_in_window,
                "total_retrains": self._total_retrains,
            }
        except Exception as exc:
            logger.error("Sliding window retrain failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "window_size": len(self._X_window),
            "total_samples_seen": self._total_samples_seen,
            "total_retrains": self._total_retrains,
            "samples_since_train": self._samples_since_train,
        }


# ── A/B Model Tester ───────────────────────────────────────────────────


class ABModelTester:
    """
    Maintains two model versions (A and B) and performs statistical
    comparison to decide whether to promote B.
    """

    def __init__(
        self,
        significance_level: float = 0.05,
        min_test_samples: int = 50,
    ):
        self.significance_level = significance_level
        self.min_test_samples = min_test_samples
        self.model_a: Optional[BaseEstimator] = None
        self.model_b: Optional[BaseEstimator] = None
        self._history_a: List[float] = []
        self._history_b: List[float] = []
        self._promoted_count: int = 0
        self._demoted_count: int = 0

    def set_models(
        self,
        model_a: BaseEstimator,
        model_b: BaseEstimator,
    ) -> None:
        """Set the current A and challenger B models."""
        self.model_a = model_a
        self.model_b = model_b
        self._history_a.clear()
        self._history_b.clear()

    def compare(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Evaluate both models on the same test set and perform
        a paired statistical comparison.

        Returns:
            dict with comparison results and promotion decision.
        """
        if self.model_a is None or self.model_b is None:
            return {"error": "Both models must be set before comparison."}

        X = np.asarray(X_test, dtype=np.float32)
        y = np.asarray(y_test)

        preds_a = self.model_a.predict(X)
        preds_b = self.model_b.predict(X)

        correct_a = (preds_a == y).astype(float)
        correct_b = (preds_b == y).astype(float)

        acc_a = float(np.mean(correct_a))
        acc_b = float(np.mean(correct_b))

        self._history_a.append(acc_a)
        self._history_b.append(acc_b)

        # Paired t-test on per-sample correctness
        n = len(y)
        if n < self.min_test_samples:
            return {
                "status": "insufficient_samples",
                "n": n,
                "min_required": self.min_test_samples,
                "accuracy_a": acc_a,
                "accuracy_b": acc_b,
            }

        diff = correct_b - correct_a
        mean_diff = float(np.mean(diff))
        std_diff = float(np.std(diff))

        if std_diff < 1e-10:
            t_stat = 0.0 if mean_diff == 0 else float("inf")
        else:
            t_stat = mean_diff / (std_diff / math.sqrt(n))

        # Approximate p-value from t-stat (two-tailed, normal approx for large n)
        p_value = 2.0 * (1.0 - _normal_cdf(abs(t_stat)))

        promote = (
            p_value < self.significance_level
            and mean_diff > 0
            and acc_b > acc_a
        )

        result = {
            "status": "compared",
            "n_samples": n,
            "accuracy_a": round(acc_a, 6),
            "accuracy_b": round(acc_b, 6),
            "mean_diff": round(mean_diff, 6),
            "t_statistic": round(t_stat, 4),
            "p_value": round(p_value, 6),
            "promote": promote,
            "history_a": self._history_a[-10:],
            "history_b": self._history_b[-10:],
        }

        if promote:
            result["recommendation"] = "PROMOTE model B — statistically significant improvement."
        elif mean_diff <= 0:
            result["recommendation"] = "KEEP model A — B is not better."
        else:
            result["recommendation"] = "INSUFFICIENT evidence — collect more data."

        logger.info(
            "A/B comparison: acc_a=%.4f acc_b=%.4f diff=%.4f p=%.4f promote=%s",
            acc_a, acc_b, mean_diff, p_value, promote,
        )
        return result

    def promote_model(self, model_b: BaseEstimator) -> Dict[str, Any]:
        """Replace model A with model B (promote the challenger)."""
        self.model_a = model_b
        self.model_b = None
        self._history_a.clear()
        self._history_b.clear()
        self._promoted_count += 1
        logger.info("Model promoted (total promotions: %d)", self._promoted_count)
        return {
            "status": "promoted",
            "promotions": self._promoted_count,
        }

    def demote_model(self) -> Dict[str, Any]:
        """Revert to the previous model A (demote the challenger)."""
        self.model_b = None
        self._history_b.clear()
        self._demoted_count += 1
        logger.info("Model demoted (total demotions: %d)", self._demoted_count)
        return {
            "status": "demoted",
            "demotions": self._demoted_count,
        }

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "has_model_a": self.model_a is not None,
            "has_model_b": self.model_b is not None,
            "promotions": self._promoted_count,
            "demotions": self._demoted_count,
            "history_a_length": len(self._history_a),
            "history_b_length": len(self._history_b),
        }


# ── Incremental Ensemble ───────────────────────────────────────────────


class IncrementalEnsemble:
    """
    Maintains multiple models with different update frequencies
    and weights them by recent performance. Auto-downweights
    models affected by concept drift.
    """

    def __init__(
        self,
        n_models: int = 3,
        initial_weight: float = 1.0,
        decay_factor: float = 0.9,
        min_weight: float = 0.05,
    ):
        self.n_models = n_models
        self.decay_factor = decay_factor
        self.min_weight = min_weight
        self.models: List[Optional[BaseEstimator]] = [None] * n_models
        self.weights = np.full(n_models, initial_weight / n_models, dtype=np.float64)
        self._performance_history: List[List[float]] = [[] for _ in range(n_models)]
        self._drift_flags: List[bool] = [False] * n_models

    def set_model(self, index: int, model: BaseEstimator) -> None:
        """Set a model at the given index."""
        if index < 0 or index >= self.n_models:
            raise IndexError(f"Model index must be 0..{self.n_models - 1}")
        self.models[index] = model

    def update_weights(self, performance_scores: List[float]) -> None:
        """
        Reweight models based on recent performance scores.

        Args:
            performance_scores: list of floats (e.g., accuracy) for each model.
                               Must match n_models.
        """
        if len(performance_scores) != self.n_models:
            raise ValueError(
                f"Expected {self.n_models} scores, got {len(performance_scores)}"
            )

        for i, score in enumerate(performance_scores):
            self._performance_history[i].append(score)
            # Downweight models flagged for drift
            if self._drift_flags[i]:
                self.weights[i] *= self.decay_factor * 0.5
            else:
                # Performance-based adjustment
                if score > 0.5:
                    self.weights[i] *= (1 + score * 0.1)
                else:
                    self.weights[i] *= self.decay_factor

            self.weights[i] = max(self.weights[i], self.min_weight)

        # Normalise
        total = self.weights.sum()
        if total > 0:
            self.weights /= total

    def flag_drift(self, index: int, drift: bool = True) -> None:
        """Flag a model as affected by concept drift."""
        if 0 <= index < self.n_models:
            self._drift_flags[index] = drift
            if drift:
                logger.warning("Model %d flagged for concept drift — weight reduced.", index)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Weighted ensemble prediction.

        For classifiers, returns majority vote weighted by model weights.
        For regressors, returns weighted average.
        """
        X = np.asarray(X, dtype=np.float32)
        all_preds: List[np.ndarray] = []
        active_weights: List[float] = []

        for i, model in enumerate(self.models):
            if model is None:
                continue
            try:
                preds = model.predict(X)
                all_preds.append(preds)
                active_weights.append(float(self.weights[i]))
            except Exception as exc:
                logger.error("Model %d prediction failed: %s", i, exc)

        if not all_preds:
            raise RuntimeError("No models available for prediction.")

        pred_matrix = np.array(all_preds)  # (n_models, n_samples)
        w = np.array(active_weights)
        w_sum = w.sum()
        if w_sum > 0:
            w /= w_sum

        # Check if numeric or categorical
        try:
            pred_matrix = pred_matrix.astype(float)
            # Weighted average
            ensemble_pred = np.average(pred_matrix, axis=0, weights=w)
            # If all predictions are integers, round
            if np.all(pred_matrix == pred_matrix.astype(int)):
                ensemble_pred = np.round(ensemble_pred).astype(int)
            return ensemble_pred
        except (ValueError, TypeError):
            # Categorical: weighted majority vote
            n_samples = pred_matrix.shape[1]
            result = np.empty(n_samples, dtype=object)
            for j in range(n_samples):
                votes = pred_matrix[:, j]
                unique = np.unique(votes)
                best_score = -1
                best_val = unique[0]
                for v in unique:
                    score = float(w[votes == v].sum())
                    if score > best_score:
                        best_score = score
                        best_val = v
                result[j] = best_val
            return result

    def get_stats(self) -> Dict[str, Any]:
        """Return ensemble statistics."""
        return {
            "n_models": self.n_models,
            "weights": self.weights.tolist(),
            "drift_flags": self._drift_flags,
            "active_models": sum(1 for m in self.models if m is not None),
        }


# ── Integration with auto_retrain ──────────────────────────────────────


def create_online_retrain_callback(
    online_learner: OnlineLearner,
    model: BaseEstimator,
    X_ref: np.ndarray,
    y_ref: np.ndarray,
    classes: Optional[np.ndarray] = None,
):
    """
    Create a callback function compatible with AutoRetrainManager
    that uses the online learning pipeline for retraining.

    Returns:
        A callable that the auto_retrain system can invoke.
    """

    def callback(drift_detected: bool = False) -> Dict[str, Any]:
        if drift_detected:
            return online_learner.auto_retrain(
                model=model,
                X_train=X_ref,
                y_train=y_ref,
                drift_detected=True,
                classes=classes,
            )
        return {"status": "no_action"}

    return callback
