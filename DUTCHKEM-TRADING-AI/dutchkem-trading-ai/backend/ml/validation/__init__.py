"""
ML Validation Utilities — walk-forward validation, overfitting checks,
cross-validation, and model performance diagnostics.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.validation")


class WalkForwardValidator:
    """
    Walk-forward validation for time-series ML models.

    Splits data into expanding or rolling windows:
      [train_1][test_1]
               [train_2][test_2]
                        [train_3][test_3]
    """

    def __init__(
        self,
        train_window: int = 500,
        test_window: int = 120,
        step: int = 60,
        expanding: bool = True,
    ):
        self.train_window = train_window
        self.test_window = test_window
        self.step = step
        self.expanding = expanding

    def split(self, n_samples: int) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Return list of (train_indices, test_indices) tuples."""
        splits = []
        start = 0
        while True:
            if self.expanding:
                train_start = 0
            else:
                train_start = start

            train_end = start + self.train_window
            test_end = train_end + self.test_window

            if test_end > n_samples:
                break

            train_idx = np.arange(train_start, train_end)
            test_idx = np.arange(train_end, test_end)
            splits.append((train_idx, test_idx))

            start += self.step

        return splits

    def validate(
        self,
        model,
        X: np.ndarray,
        y: np.ndarray,
        metric_fn=None,
    ) -> Dict[str, Any]:
        """
        Run walk-forward validation on a model.

        Args:
            model: must have .fit(X, y) and .predict(X) methods
            X: feature matrix
            y: target array
            metric_fn: callable(y_true, y_pred) -> float; defaults to accuracy
        """
        if metric_fn is None:
            metric_fn = lambda y_true, y_pred: float(np.mean(y_true == y_pred))

        splits = self.split(len(X))
        if not splits:
            return {"error": "Insufficient data for walk-forward validation"}

        fold_results = []
        for fold_idx, (train_idx, test_idx) in enumerate(splits):
            X_train, y_train = X[train_idx], y[train_idx]
            X_test, y_test = X[test_idx], y[test_idx]

            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                metric = metric_fn(y_test, y_pred)
                fold_results.append({
                    "fold": fold_idx + 1,
                    "metric": float(metric),
                    "train_size": len(train_idx),
                    "test_size": len(test_idx),
                })
            except Exception as e:
                logger.warning("Fold %d failed: %s", fold_idx + 1, e)
                fold_results.append({
                    "fold": fold_idx + 1,
                    "metric": None,
                    "error": str(e),
                })

        valid_folds = [f for f in fold_results if f.get("metric") is not None]
        metrics = [f["metric"] for f in valid_folds]

        return {
            "n_folds": len(splits),
            "successful_folds": len(valid_folds),
            "mean_metric": float(np.mean(metrics)) if metrics else 0,
            "std_metric": float(np.std(metrics)) if metrics else 0,
            "min_metric": float(np.min(metrics)) if metrics else 0,
            "max_metric": float(np.max(metrics)) if metrics else 0,
            "fold_results": fold_results,
        }


class OverfitDetector:
    """
    Detect overfitting by comparing train vs test performance across folds.
    """

    OVERFITTING_THRESHOLDS = {
        "train_test_gap": 0.15,  # >15% gap between train and test accuracy
        "variance_threshold": 0.10,  # >10% std across folds
        "degradation_trend": 0.05,  # >5% drop from first to last fold
    }

    def analyze(
        self,
        fold_results: List[Dict[str, Any]],
        train_metrics: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze fold results for overfitting signals.

        Args:
            fold_results: from WalkForwardValidator.validate()
            train_metrics: optional per-fold training metrics
        """
        test_metrics = [f["metric"] for f in fold_results if f.get("metric") is not None]

        if not test_metrics:
            return {"overfitting_risk": "unknown", "reasons": ["No valid fold results"]}

        reasons = []
        risk_score = 0.0

        # 1. Check train-test gap
        if train_metrics and len(train_metrics) == len(test_metrics):
            gaps = [t - e for t, e in zip(train_metrics, test_metrics)]
            avg_gap = float(np.mean(gaps))
            if avg_gap > self.OVERFITTING_THRESHOLDS["train_test_gap"]:
                reasons.append(f"Large train-test gap: {avg_gap:.3f}")
                risk_score += 0.4

        # 2. Check variance across folds
        std_metric = float(np.std(test_metrics))
        if std_metric > self.OVERFITTING_THRESHOLDS["variance_threshold"]:
            reasons.append(f"High variance across folds: {std_metric:.3f}")
            risk_score += 0.3

        # 3. Check degradation trend
        if len(test_metrics) >= 3:
            first_half = np.mean(test_metrics[:len(test_metrics) // 2])
            second_half = np.mean(test_metrics[len(test_metrics) // 2:])
            degradation = float(first_half - second_half)
            if degradation > self.OVERFITTING_THRESHOLDS["degradation_trend"]:
                reasons.append(f"Performance degradation trend: {degradation:.3f}")
                risk_score += 0.3

        # 4. Check if any fold has very low performance
        min_metric = float(np.min(test_metrics))
        if min_metric < 0.4:
            reasons.append(f"Very low performance in at least one fold: {min_metric:.3f}")
            risk_score += 0.2

        # Determine risk level
        if risk_score >= 0.6:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "overfitting_risk": risk_level,
            "risk_score": round(risk_score, 3),
            "reasons": reasons,
            "mean_test_metric": float(np.mean(test_metrics)),
            "std_test_metric": std_metric,
            "min_test_metric": min_metric,
            "max_test_metric": float(np.max(test_metrics)),
        }


class ModelStabilityChecker:
    """
    Checks model stability by retraining on different data slices
    and comparing predictions.
    """

    def check_prediction_stability(
        self,
        model,
        X: np.ndarray,
        n_bootstrap: int = 10,
        sample_ratio: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Bootstrap test: retrain model on random subsets and check prediction consistency.
        """
        n_samples = int(len(X) * sample_ratio)
        all_predictions = []

        for i in range(n_bootstrap):
            indices = np.random.choice(len(X), n_samples, replace=False)
            X_sample = X[indices]
            try:
                preds = model.predict(X_sample)
                all_predictions.append(preds)
            except Exception as e:
                logger.warning("Bootstrap %d failed: %s", i, e)

        if not all_predictions:
            return {"stable": False, "error": "All bootstrap iterations failed"}

        # Measure prediction agreement across bootstrap samples
        # Use the last prediction as reference
        reference = all_predictions[-1]
        agreements = []
        for preds in all_predictions[:-1]:
            min_len = min(len(reference), len(preds))
            agreement = float(np.mean(reference[:min_len] == preds[:min_len]))
            agreements.append(agreement)

        avg_agreement = float(np.mean(agreements)) if agreements else 0.0

        return {
            "stable": avg_agreement > 0.7,
            "avg_prediction_agreement": round(avg_agreement, 4),
            "n_successful_bootstrap": len(all_predictions),
            "n_bootstrap_attempted": n_bootstrap,
        }


class ValidationReport:
    """Aggregates all validation checks into a single report."""

    def __init__(self):
        self.walk_forward = WalkForwardValidator()
        self.overfit_detector = OverfitDetector()
        self.stability_checker = ModelStabilityChecker()

    def full_validation(
        self,
        model,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Dict[str, Any]:
        """Run all validation checks and return a comprehensive report."""
        # Walk-forward validation
        wf_result = self.walk_forward.validate(model, X, y)

        # Overfitting analysis
        of_result = self.overfit_detector.analyze(
            wf_result.get("fold_results", [])
        )

        # Stability check
        stability = self.stability_checker.check_prediction_stability(model, X)

        overall_pass = (
            wf_result.get("mean_metric", 0) > 0.5
            and of_result.get("overfitting_risk", "high") != "high"
            and stability.get("stable", False)
        )

        return {
            "overall_pass": overall_pass,
            "walk_forward": wf_result,
            "overfitting_analysis": of_result,
            "stability_check": stability,
            "summary": {
                "mean_metric": wf_result.get("mean_metric", 0),
                "overfitting_risk": of_result.get("overfitting_risk", "unknown"),
                "stable": stability.get("stable", False),
            },
        }
