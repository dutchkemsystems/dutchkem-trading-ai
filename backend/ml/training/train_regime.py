import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

import numpy as np

logger = logging.getLogger("ml.training.regime")


class RegimeTrainer:
    """
    Training script for XGBoost regime detection model.
    """

    def __init__(self, model_dir: str = "model_registry"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

    async def train_walk_forward(
        self,
        symbol: str,
        timeframe: str = "H1",
        train_window_days: int = 500,
        test_window_days: int = 120,
        step_days: int = 60,
    ) -> Dict[str, Any]:
        from ml.data_pipeline import DataPipeline
        from ml.features import FeatureEngine
        from ml.models.regime_detector import RegimeDetector
        from ml.preprocessing import DataPreprocessor

        pipeline = DataPipeline()
        feature_engine = FeatureEngine()
        preprocessor = DataPreprocessor()

        total_days_needed = train_window_days + test_window_days + 100
        count = total_days_needed * 24

        df = await pipeline.fetch_ohlcv(symbol, timeframe, count)
        if df.empty:
            return {"error": "No data fetched"}

        features = feature_engine.compute_features(df)
        labels = feature_engine.label_regimes(df)

        feature_cols = [c for c in features.columns if c not in [
            "open", "high", "low", "close", "volume", "timestamp",
        ]]
        X_all = features[feature_cols].values
        y_all = labels.values

        mask = ~(np.isnan(X_all).any(axis=1) | np.isnan(y_all))
        X_all = X_all[mask]
        y_all = y_all[mask]

        n_features = X_all.shape[1]
        results = []

        step = step_days * 24
        for start in range(0, len(X_all) - train_window_days - test_window_days, step):
            train_end = start + train_window_days * 24
            test_end = train_end + test_window_days * 24

            if test_end > len(X_all):
                break

            X_train_raw = X_all[start:train_end]
            y_train = y_all[start:train_end]
            X_test_raw = X_all[train_end:test_end]
            y_test = y_all[train_end:test_end]

            X_train_scaled = preprocessor.fit_transform(X_train_raw, feature_cols)
            X_test_scaled = preprocessor.transform(X_test_raw)

            model = RegimeDetector()
            model.build_model()
            train_result = model.train(X_train_scaled, y_train, feature_cols)

            eval_pred = model._model.predict(X_test_scaled)
            eval_acc = np.mean(eval_pred == y_test)

            results.append({
                "fold": len(results) + 1,
                "eval_accuracy": float(eval_acc),
                "train_result": train_result,
            })

            logger.info("Fold %d: accuracy=%.4f", len(results), eval_acc)

        avg_accuracy = np.mean([r["eval_accuracy"] for r in results])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        model_filename = f"regime_{symbol}_{timeframe}_{timestamp}.json"
        model_path = os.path.join(self.model_dir, model_filename)

        summary = {
            "symbol": symbol,
            "timeframe": timeframe,
            "n_features": n_features,
            "n_folds": len(results),
            "avg_accuracy": float(avg_accuracy),
            "model_path": model_path,
            "timestamp": timestamp,
        }

        summary_path = os.path.join(self.model_dir, f"regime_summary_{symbol}_{timestamp}.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info("Regime training complete: avg_accuracy=%.4f", avg_accuracy)
        return summary
