import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("ml.inference")


class PredictionService:
    """Service for making predictions using trained ML models"""

    def __init__(self):
        self.models = {}
        self.pipeline = None

    def load_models(self):
        """Load all trained models"""
        try:
            from ml.pipeline import PredictionPipeline
            self.pipeline = PredictionPipeline()
            self.pipeline.initialize()
            logger.info("ML models loaded successfully")
        except Exception as exc:
            logger.error("Failed to load ML models: %s", exc)

    def predict(self, symbol: str, timeframe: str, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a prediction for a symbol.

        The prediction pipeline's predict() is async and expects (symbol, timeframe, lookback).
        We derive the lookback count from the length of the provided OHLCV data.
        """
        if not self.pipeline:
            self.load_models()

        if not self.pipeline:
            return {"error": "ML pipeline not available"}

        try:
            # Derive lookback from the number of candles supplied
            if ohlcv_data and isinstance(ohlcv_data, dict):
                first_key = next((k for k in ("close", "open", "high", "low") if k in ohlcv_data), None)
                lookback = len(ohlcv_data[first_key]) if first_key else 500
            else:
                lookback = 500

            # pipeline.predict is async — run in an event loop
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    self.pipeline.predict(symbol, timeframe, lookback)
                )
            finally:
                loop.close()

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "prediction": result.get("direction", "NEUTRAL"),
                "confidence": result.get("confidence", 0),
                "regime": result.get("regime", "unknown"),
                "model_version": result.get("model_version", "unknown"),
            }
        except Exception as exc:
            logger.error("Prediction failed for %s %s: %s", symbol, timeframe, exc)
            return {"error": str(exc)}


prediction_service = PredictionService()
