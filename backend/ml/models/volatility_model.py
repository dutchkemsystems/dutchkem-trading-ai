"""
Volatility Regime Classification Model.

Uses a GradientBoosting classifier to predict volatility regime from
ATR, Bollinger Band width, historical volatility, and volume features.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.models.volatility")


class VolatilityModel:
    """
    Predicts the current volatility regime from volatility-related features.

    Regimes:
      0 = low_vol     — compressed ATR, narrow BB, quiet market
      1 = normal_vol  — baseline volatility
      2 = high_vol    — expanded ATR, wide BB, active market
      3 = extreme_vol — ATR spike, potential breakout or news event
    """

    REGIMES = {
        0: "low_vol",
        1: "normal_vol",
        2: "high_vol",
        3: "extreme_vol",
    }

    REGIME_MULTIPLIERS = {
        "low_vol": 0.7,
        "normal_vol": 1.0,
        "high_vol": 1.5,
        "extreme_vol": 2.5,
    }

    FEATURE_NAMES = [
        "atr_14", "atr_20", "atr_normalized_14", "atr_normalized_20",
        "bb_width_14", "bb_width_20",
        "historical_vol_20",
        "keltner_width",
        "tr_ratio",
    ]

    def __init__(self, n_estimators: int = 150, max_depth: int = 5):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self._model = None
        self._feature_names: List[str] = []

    def build_model(self):
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            self._model = GradientBoostingClassifier(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=0.1,
                random_state=42,
            )
            logger.info("Volatility model built (GradientBoosting, %d estimators)", self.n_estimators)
            return self._model
        except ImportError:
            logger.error("scikit-learn not installed. Cannot build volatility model.")
            return None

    def label_volatility(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate volatility regime labels from OHLCV data.

        Uses rolling percentiles of ATR and Bollinger Band width.
        """
        labels = pd.Series(1, index=df.index, dtype=int)  # default: normal_vol

        atr_col = "atr_normalized_14" if "atr_normalized_14" in df.columns else None
        bb_col = "bb_width_20" if "bb_width_20" in df.columns else None

        if atr_col is None and bb_col is None:
            return labels

        # Combine ATR percentile and BB width percentile
        scores = pd.Series(0.5, index=df.index)

        if atr_col:
            atr_pct = df[atr_col].rolling(100, min_periods=20).rank(pct=True)
            scores = scores + atr_pct.fillna(0.5) * 0.5

        if bb_col:
            bb_pct = df[bb_col].rolling(100, min_periods=20).rank(pct=True)
            scores = scores + bb_pct.fillna(0.5) * 0.5

        labels[scores < 0.25] = 0   # low_vol
        labels[(scores >= 0.25) & (scores < 0.60)] = 1  # normal_vol
        labels[(scores >= 0.60) & (scores < 0.85)] = 2  # high_vol
        labels[scores >= 0.85] = 3  # extreme_vol

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
            target_names=list(self.REGIMES.values()),
            output_dict=True,
            zero_division=0,
        )

        logger.info("Volatility model trained: eval_accuracy=%.4f", eval_acc)
        return {"eval_accuracy": eval_acc, "classification_report": report}

    def predict(self, X: np.ndarray) -> Dict[str, Any]:
        if self._model is None:
            return {"error": "Model not loaded"}

        try:
            probabilities = self._model.predict_proba(X)
            predicted_class = np.argmax(probabilities, axis=1)
            confidence = np.max(probabilities, axis=1)

            regime = self.REGIMES.get(predicted_class[-1], "normal_vol")
            multiplier = self.REGIME_MULTIPLIERS.get(regime, 1.0)

            return {
                "regime": regime,
                "confidence": float(confidence[-1]),
                "volatility_multiplier": multiplier,
                "regime_id": int(predicted_class[-1]),
                "probabilities": {
                    self.REGIMES[i]: float(probabilities[-1][i])
                    for i in range(len(self.REGIMES))
                },
            }
        except Exception as e:
            logger.error("Volatility prediction error: %s", e)
            return {"error": str(e)}

    def save_model(self, path: str):
        if self._model is not None:
            import joblib
            joblib.dump({
                "model": self._model,
                "feature_names": self._feature_names,
            }, path)
            logger.info("Volatility model saved to %s", path)

    def load_model(self, path: str):
        try:
            import joblib
            data = joblib.load(path)
            self._model = data["model"]
            self._feature_names = data.get("feature_names", [])
            logger.info("Volatility model loaded from %s", path)
        except Exception as e:
            logger.error("Failed to load volatility model: %s", e)
