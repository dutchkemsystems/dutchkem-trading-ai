import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.models.regime")


class RegimeDetector:
    """
    XGBoost model for market regime classification.
    Regimes: trending_strong, trending_weak, ranging, volatile, news, low_liquidity
    """

    REGIMES = {
        0: "trending_strong",
        1: "trending_weak",
        2: "ranging",
        3: "volatile",
        4: "news",
        5: "low_liquidity",
    }

    REGIME_WEIGHTS = {
        "trending_strong": 1.0,
        "trending_weak": 0.8,
        "ranging": 0.7,
        "volatile": 0.5,
        "news": 0.0,
        "low_liquidity": 0.3,
    }

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 8,
        learning_rate: float = 0.1,
        confidence_threshold: float = 0.6,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.confidence_threshold = confidence_threshold
        self._model = None
        self._feature_importance = None
        self._feature_names = []

    def build_model(self):
        try:
            import xgboost as xgb

            self._model = xgb.XGBClassifier(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                objective="multi:softprob",
                num_class=6,
                eval_metric="mlogloss",
                use_label_encoder=False,
                random_state=42,
                n_jobs=-1,
            )
            logger.info("XGBoost regime model built")
            return self._model

        except ImportError:
            logger.error("xgboost not installed")
            return None

    def label_regimes(self, df: pd.DataFrame) -> pd.Series:
        labels = pd.Series(2, index=df.index, dtype=int)

        adx = df.get("adx_14", pd.Series(0, index=df.index))
        atr_norm = df.get("atr_normalized_14", pd.Series(0, index=df.index))
        bb_width = df.get("bb_width_20", pd.Series(0, index=df.index))
        volume_ratio = df.get("volume_ratio", pd.Series(1, index=df.index))
        spread_ratio = df.get("spread_ratio", pd.Series(1, index=df.index))

        bb_width_avg = bb_width.rolling(20).mean()
        atr_avg = atr_norm.rolling(20).mean()
        volume_avg = volume_ratio.rolling(20).mean()
        spread_avg = spread_ratio.rolling(20).mean()

        labels[(adx > 30)] = 0
        labels[(adx >= 20) & (adx <= 30)] = 1
        labels[(adx < 20) & (bb_width < bb_width_avg * 0.8)] = 2
        labels[(atr_norm > atr_avg * 1.5) & (bb_width > bb_width_avg * 2.0)] = 3
        labels[(volume_ratio > 3.0) & (spread_ratio > 2.0)] = 4
        labels[(spread_ratio > 3.0) | (volume_ratio < 0.5)] = 5

        return labels

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        eval_ratio: float = 0.2,
    ) -> Dict[str, Any]:
        if self._model is None:
            self.build_model()

        if self._model is None:
            return {"error": "Model not built"}

        self._feature_names = feature_names or [f"f_{i}" for i in range(X.shape[1])]

        split = int(len(X) * (1 - eval_ratio))
        X_train, X_eval = X[:split], X[split:]
        y_train, y_eval = y[:split], y[split:]

        self._model.fit(
            X_train, y_train,
            eval_set=[(X_eval, y_eval)],
            verbose=False,
        )

        self._feature_importance = dict(zip(
            self._feature_names,
            self._model.feature_importances_,
        ))

        eval_pred = self._model.predict(X_eval)
        eval_acc = np.mean(eval_pred == y_eval)

        from sklearn.metrics import classification_report
        report = classification_report(
            y_eval, eval_pred,
            target_names=list(self.REGIMES.values()),
            output_dict=True,
            zero_division=0,
        )

        logger.info("Regime model trained: eval_accuracy=%.4f", eval_acc)

        return {
            "eval_accuracy": float(eval_acc),
            "classification_report": report,
            "feature_importance_top10": dict(
                sorted(self._feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }

    def predict(self, X: np.ndarray) -> Dict[str, Any]:
        if self._model is None:
            return {"error": "Model not loaded"}

        try:
            probabilities = self._model.predict_proba(X)
            predicted_class = np.argmax(probabilities, axis=1)
            confidence = np.max(probabilities, axis=1)

            regime = self.REGIMES.get(predicted_class[-1], "unknown")
            conf = float(confidence[-1])

            return {
                "regime": regime,
                "confidence": conf,
                "is_confident": conf >= self.confidence_threshold,
                "regime_weight": self.REGIME_WEIGHTS.get(regime, 0.5),
                "probabilities": {
                    self.REGIMES[i]: float(probabilities[-1][i])
                    for i in range(len(self.REGIMES))
                },
            }

        except Exception as e:
            logger.error("Regime prediction error: %s", e)
            return {"error": str(e)}

    def predict_batch(self, X: np.ndarray) -> List[Dict[str, Any]]:
        if self._model is None:
            return [{"error": "Model not loaded"}]

        try:
            probabilities = self._model.predict_proba(X)
            predicted_class = np.argmax(probabilities, axis=1)
            confidence = np.max(probabilities, axis=1)

            results = []
            for i in range(len(predicted_class)):
                regime = self.REGIMES.get(predicted_class[i], "unknown")
                results.append({
                    "regime": regime,
                    "confidence": float(confidence[i]),
                    "is_confident": float(confidence[i]) >= self.confidence_threshold,
                    "regime_weight": self.REGIME_WEIGHTS.get(regime, 0.5),
                })
            return results

        except Exception as e:
            logger.error("Batch regime prediction error: %s", e)
            return [{"error": str(e)}] * len(X)

    def get_feature_importance(self, top_n: int = 20) -> Dict[str, float]:
        if self._feature_importance is None:
            return {}
        sorted_imp = sorted(
            self._feature_importance.items(), key=lambda x: x[1], reverse=True
        )
        return dict(sorted_imp[:top_n])

    def save_model(self, path: str):
        if self._model is not None:
            self._model.save_model(path)
            logger.info("Regime model saved to %s", path)

    def load_model(self, path: str):
        try:
            import xgboost as xgb
            self._model = xgb.XGBClassifier()
            self._model.load_model(path)
            logger.info("Regime model loaded from %s", path)
        except Exception as e:
            logger.error("Failed to load regime model: %s", e)
