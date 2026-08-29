"""
Support & Resistance Level Detection Model.

Uses a lightweight RandomForest classifier trained on price-structure features
to identify nearby S/R zones and classify whether current price is near one.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.models.sr")


class SRLevelModel:
    """
    Predicts proximity to support/resistance levels from price-structure features.

    Features expected (subset of FeatureEngine output):
      - pivot_20, pivot_50, r1_20, s1_20, r1_50, s1_50
      - dist_to_r1_20, dist_to_s1_20, dist_to_r1_50, dist_to_s1_50
      - close_position_20, close_position_50

    Output:
      - levels: list of detected S/R levels with type & distance
      - proximity: "near_support" | "near_resistance" | "mid_range"
      - confidence: 0-1
    """

    FEATURE_NAMES = [
        "pivot_20", "pivot_50", "r1_20", "s1_20", "r1_50", "s1_50",
        "dist_to_r1_20", "dist_to_s1_20", "dist_to_r1_50", "dist_to_s1_50",
        "close_position_20", "close_position_50",
    ]

    PROXIMITY_CLASSES = {
        0: "mid_range",
        1: "near_support",
        2: "near_resistance",
    }

    def __init__(self, n_estimators: int = 100, max_depth: int = 6):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self._model = None
        self._feature_names: List[str] = []

    def build_model(self):
        """Build a lightweight RandomForest for S/R proximity classification."""
        try:
            from sklearn.ensemble import RandomForestClassifier
            self._model = RandomForestClassifier(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                random_state=42,
                n_jobs=-1,
            )
            logger.info("S/R model built (RandomForest, %d estimators)", self.n_estimators)
            return self._model
        except ImportError:
            logger.error("scikit-learn not installed. Cannot build S/R model.")
            return None

    def label_sr_proximity(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate labels from raw OHLCV data:
          0 = mid_range (price > 0.3% from nearest level)
          1 = near_support (within 0.3% of S1 or pivot below)
          2 = near_resistance (within 0.3% of R1 or pivot above)
        """
        labels = pd.Series(0, index=df.index, dtype=int)

        if "pivot_20" not in df.columns or "r1_20" not in df.columns:
            return labels

        close = df["close"]
        threshold = 0.003  # 0.3% proximity

        near_s1_20 = ((close - df["s1_20"]).abs() / (close + 1e-10)) < threshold
        near_s1_50 = ((close - df["s1_50"]).abs() / (close + 1e-10)) < threshold if "s1_50" in df.columns else False
        near_r1_20 = ((close - df["r1_20"]).abs() / (close + 1e-10)) < threshold
        near_r1_50 = ((close - df["r1_50"]).abs() / (close + 1e-10)) < threshold if "r1_50" in df.columns else False

        labels[near_s1_20 | near_s1_50] = 1
        labels[near_r1_20 | near_r1_50] = 2
        # If both match, support takes precedence (price approaching from above)
        both = (near_s1_20 | near_s1_50) & (near_r1_20 | near_r1_50)
        labels[both] = 0

        return labels

    def train(self, X: np.ndarray, y: np.ndarray, feature_names: Optional[List[str]] = None) -> Dict[str, Any]:
        if self._model is None:
            self.build_model()
        if self._model is None:
            return {"error": "Model not built"}

        self._feature_names = feature_names or [f"f_{i}" for i in range(X.shape[1])]

        split = int(len(X) * 0.8)
        X_train, X_eval = X[:split], X[split:]
        y_train, y_eval = y[:split], y[split:]

        self._model.fit(X_train, y_train)

        eval_pred = self._model.predict(X_eval)
        eval_acc = float(np.mean(eval_pred == y_eval))

        from sklearn.metrics import classification_report
        report = classification_report(
            y_eval, eval_pred,
            target_names=list(self.PROXIMITY_CLASSES.values()),
            output_dict=True,
            zero_division=0,
        )

        logger.info("S/R model trained: eval_accuracy=%.4f", eval_acc)
        return {"eval_accuracy": eval_acc, "classification_report": report}

    def predict(self, X: np.ndarray) -> Dict[str, Any]:
        if self._model is None:
            return {"error": "Model not loaded"}

        try:
            probabilities = self._model.predict_proba(X)
            predicted_class = np.argmax(probabilities, axis=1)
            confidence = np.max(probabilities, axis=1)

            proximity = self.PROXIMITY_CLASSES.get(predicted_class[-1], "mid_range")

            return {
                "proximity": proximity,
                "confidence": float(confidence[-1]),
                "probabilities": {
                    self.PROXIMITY_CLASSES[i]: float(probabilities[-1][i])
                    for i in range(len(self.PROXIMITY_CLASSES))
                },
                "sr_label": int(predicted_class[-1]),
            }
        except Exception as e:
            logger.error("S/R prediction error: %s", e)
            return {"error": str(e)}

    def save_model(self, path: str):
        if self._model is not None:
            import joblib
            joblib.dump({
                "model": self._model,
                "feature_names": self._feature_names,
            }, path)
            logger.info("S/R model saved to %s", path)

    def load_model(self, path: str):
        try:
            import joblib
            data = joblib.load(path)
            self._model = data["model"]
            self._feature_names = data.get("feature_names", [])
            logger.info("S/R model loaded from %s", path)
        except Exception as e:
            logger.error("Failed to load S/R model: %s", e)
