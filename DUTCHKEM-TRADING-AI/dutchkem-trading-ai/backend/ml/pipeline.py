import logging
import time
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.pipeline")


class PredictionPipeline:
    """
    End-to-end prediction pipeline.
    Takes raw OHLCV data → feature engineering → model inference → ensemble output.
    """

    def __init__(
        self,
        lstm_path: Optional[str] = None,
        regime_path: Optional[str] = None,
        preprocessor_path: Optional[str] = None,
    ):
        self._ensemble = None
        self._feature_engine = None
        self._data_pipeline = None
        self._preprocessor = None
        self._lstm_path = lstm_path
        self._regime_path = regime_path
        self._preprocessor_path = preprocessor_path
        self._initialized = False

    def initialize(self):
        from ml.ensemble import EnsemblePredictor
        from ml.features import FeatureEngine
        from ml.data_pipeline import DataPipeline

        self._ensemble = EnsemblePredictor()
        self._ensemble.load_models(
            lstm_path=self._lstm_path,
            regime_path=self._regime_path,
            preprocessor_path=self._preprocessor_path,
        )
        self._feature_engine = FeatureEngine()
        self._data_pipeline = DataPipeline()
        self._initialized = True
        logger.info("Prediction pipeline initialized")

    async def predict(
        self,
        symbol: str,
        timeframe: str = "H1",
        lookback: int = 500,
    ) -> Dict[str, Any]:
        if not self._initialized:
            self.initialize()

        start_time = time.time()

        df = await self._data_pipeline.fetch_ohlcv(symbol, timeframe, lookback)
        if df.empty:
            return {"error": "No data available", "symbol": symbol}

        features = self._feature_engine.compute_features(df)

        feature_cols = [c for c in features.columns if c not in [
            "open", "high", "low", "close", "volume", "timestamp",
        ]]

        X_all = features[feature_cols].values
        mask = ~np.isnan(X_all).any(axis=1)
        X_clean = X_all[mask]

        if len(X_clean) < 60:
            return {"error": "Insufficient clean data", "symbol": symbol}

        if self._preprocessor is not None:
            X_scaled = self._preprocessor.transform(X_clean)
        else:
            from ml.preprocessing import DataPreprocessor
            self._preprocessor = DataPreprocessor()
            X_scaled = self._preprocessor.fit_transform(X_clean, feature_cols)

        sequence_length = 60
        X_sequence = X_scaled[-sequence_length:].reshape(1, sequence_length, -1)
        X_current = X_scaled[-1:].reshape(1, -1)

        result = self._ensemble.predict(
            features_sequence=X_sequence,
            current_features=X_current,
        )

        result["symbol"] = symbol
        result["timeframe"] = timeframe
        result["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        result["data_points"] = len(X_clean)
        result["timestamp"] = time.time()

        logger.info(
            "Prediction for %s: %s (%.2f%% confidence, regime=%s, %.1fms)",
            symbol, result["direction"], result["confidence"] * 100,
            result["regime"], result["latency_ms"],
        )

        return result

    async def predict_multi_symbol(
        self,
        symbols: list,
        timeframe: str = "H1",
    ) -> Dict[str, Dict[str, Any]]:
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = await self.predict(symbol, timeframe)
            except Exception as e:
                results[symbol] = {"error": str(e), "symbol": symbol}
        return results

    def get_pipeline_info(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "lstm_path": self._lstm_path,
            "regime_path": self._regime_path,
            "preprocessor_path": self._preprocessor_path,
            "has_lstm": self._ensemble._lstm_model is not None if self._ensemble else False,
            "has_regime": self._ensemble._regime_model is not None if self._ensemble else False,
        }


pipeline = PredictionPipeline()
