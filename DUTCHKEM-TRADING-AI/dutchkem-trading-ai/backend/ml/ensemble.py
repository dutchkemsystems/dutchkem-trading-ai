import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("ml.ensemble")


class EnsemblePredictor:
    """
    Combines all ML models into a single weighted ensemble prediction.
    Models: LSTM (direction), XGBoost (regime), RF (S/R), GB (volatility)
    """

    DEFAULT_WEIGHTS = {
        "lstm": 0.35,
        "regime": 0.30,
        "sr_levels": 0.20,
        "volatility": 0.15,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._lstm_model = None
        self._regime_model = None
        self._sr_model = None
        self._volatility_model = None
        self._preprocessor = None

    def load_models(
        self,
        lstm_path: Optional[str] = None,
        regime_path: Optional[str] = None,
        sr_path: Optional[str] = None,
        volatility_path: Optional[str] = None,
        preprocessor_path: Optional[str] = None,
    ):
        if lstm_path:
            from ml.models.lstm_direction import LSTMDirectionModel
            self._lstm_model = LSTMDirectionModel()
            self._lstm_model.load_model(lstm_path)

        if regime_path:
            from ml.models.regime_detector import RegimeDetector
            self._regime_model = RegimeDetector()
            self._regime_model.load_model(regime_path)

        if sr_path:
            from ml.models.sr_model import SRLevelModel
            self._sr_model = SRLevelModel()
            self._sr_model.load_model(sr_path)

        if volatility_path:
            from ml.models.volatility_model import VolatilityModel
            self._volatility_model = VolatilityModel()
            self._volatility_model.load_model(volatility_path)

        if preprocessor_path:
            from ml.preprocessing import DataPreprocessor
            self._preprocessor = DataPreprocessor()
            self._preprocessor.load_preprocessor(preprocessor_path)

    def predict(
        self,
        features_sequence: np.ndarray,
        current_features: np.ndarray,
        sr_features: Optional[np.ndarray] = None,
        volatility_features: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        predictions = {}
        weighted_direction = np.zeros(3)
        total_weight = 0.0
        overall_confidence = 0.0

        if self._lstm_model is not None:
            try:
                lstm_pred = self._lstm_model.predict(features_sequence)
                if "error" not in lstm_pred:
                    probs = np.array(lstm_pred["probabilities"][-1])
                    weighted_direction += self.weights["lstm"] * probs
                    total_weight += self.weights["lstm"]
                    predictions["lstm"] = {
                        "direction": lstm_pred["direction"],
                        "confidence": lstm_pred["confidence_score"],
                        "probabilities": probs.tolist(),
                    }
            except Exception as e:
                logger.error("LSTM prediction error: %s", e)

        if self._regime_model is not None:
            try:
                regime_pred = self._regime_model.predict(current_features)
                if "error" not in regime_pred:
                    predictions["regime"] = {
                        "regime": regime_pred["regime"],
                        "confidence": regime_pred["confidence"],
                        "weight": regime_pred["regime_weight"],
                    }
                    adjusted_weight = self.weights["regime"] * regime_pred["regime_weight"]
                    total_weight += adjusted_weight
            except Exception as e:
                logger.error("Regime prediction error: %s", e)

        if total_weight > 0:
            normalized_direction = weighted_direction / total_weight
            overall_confidence = float(np.max(normalized_direction))
        else:
            normalized_direction = np.array([0.33, 0.34, 0.33])
            overall_confidence = 0.34

        direction_map = {0: "BEARISH", 1: "BULLISH", 2: "NEUTRAL"}
        final_direction = direction_map[np.argmax(normalized_direction)]

        regime = predictions.get("regime", {}).get("regime", "unknown")
        regime_confidence = predictions.get("regime", {}).get("confidence", 0.0)

        should_trade = overall_confidence > 0.65

        sr_levels = None
        if self._sr_model is not None:
            try:
                if sr_features is not None:
                    sr_pred = self._sr_model.predict(sr_features)
                else:
                    # Use current_features as fallback for SR prediction
                    sr_pred = self._sr_model.predict(current_features)
                sr_levels = sr_pred
                predictions["sr_levels"] = sr_pred
            except Exception as e:
                logger.error("S/R prediction error: %s", e)

        volatility_regime = None
        if self._volatility_model is not None:
            try:
                if volatility_features is not None:
                    vol_pred = self._volatility_model.predict(volatility_features)
                else:
                    # Use current_features as fallback for volatility prediction
                    vol_pred = self._volatility_model.predict(current_features)
                volatility_regime = vol_pred
                predictions["volatility"] = vol_pred
            except Exception as e:
                logger.error("Volatility prediction error: %s", e)

        return {
            "direction": final_direction,
            "confidence": round(overall_confidence, 4),
            "probabilities": {
                "bearish": round(float(normalized_direction[0]), 4),
                "bullish": round(float(normalized_direction[1]), 4),
                "neutral": round(float(normalized_direction[2]), 4),
            },
            "regime": regime,
            "regime_confidence": round(regime_confidence, 4),
            "should_trade": should_trade,
            "sr_levels": sr_levels,
            "volatility_regime": volatility_regime,
            "model_predictions": predictions,
            "weights_used": self.weights,
        }

    def adjust_weights_for_regime(self, regime: str) -> Dict[str, float]:
        adjusted = self.weights.copy()

        if regime == "trending_strong":
            adjusted["lstm"] = 0.45
            adjusted["regime"] = 0.25
            adjusted["sr_levels"] = 0.15
            adjusted["volatility"] = 0.15
        elif regime == "ranging":
            adjusted["lstm"] = 0.25
            adjusted["regime"] = 0.20
            adjusted["sr_levels"] = 0.35
            adjusted["volatility"] = 0.20
        elif regime == "volatile":
            adjusted["lstm"] = 0.20
            adjusted["regime"] = 0.35
            adjusted["sr_levels"] = 0.15
            adjusted["volatility"] = 0.30
        elif regime in ("news", "low_liquidity"):
            adjusted["lstm"] = 0.15
            adjusted["regime"] = 0.40
            adjusted["sr_levels"] = 0.15
            adjusted["volatility"] = 0.30

        return adjusted
