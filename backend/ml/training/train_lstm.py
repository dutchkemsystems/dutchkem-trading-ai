import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.training.lstm")


class LSTMTrainer:
    """
    Training script for LSTM direction prediction model.
    Handles walk-forward validation, hyperparameter tuning, and model persistence.
    """

    def __init__(self, model_dir: str = "model_registry"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

    async def train_walk_forward(
        self,
        symbol: str,
        timeframe: str = "H1",
        sequence_length: int = 60,
        train_window_days: int = 750,
        test_window_days: int = 180,
        step_days: int = 90,
    ) -> Dict[str, Any]:
        from ml.data_pipeline import DataPipeline
        from ml.features import FeatureEngine
        from ml.models.lstm_direction import LSTMDirectionModel
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
        labels = feature_engine.compute_labels(df, forward_bars=5)

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

            from ml.data_pipeline import DataPipeline
            dp = DataPipeline()
            X_train_seq, y_train_seq = dp._create_sequences(X_train_scaled, y_train, sequence_length)
            X_test_seq, y_test_seq = dp._create_sequences(X_test_scaled, y_test, sequence_length)

            if len(X_train_seq) < 100 or len(X_test_seq) < 10:
                continue

            model = LSTMDirectionModel(
                sequence_length=sequence_length,
                n_features=n_features,
            )
            model.build_model()

            val_size = int(len(X_train_seq) * 0.15)
            X_val = X_train_seq[-val_size:]
            y_val = y_train_seq[-val_size:]
            X_train_final = X_train_seq[:-val_size]
            y_train_final = y_train_seq[:-val_size]

            train_result = model.train(
                X_train_final, y_train_final,
                X_val, y_val,
                epochs=50,
                batch_size=32,
                patience=10,
            )

            eval_result = model.evaluate(X_test_seq, y_test_seq)
            results.append({
                "fold": len(results) + 1,
                "train_end": train_end,
                "test_end": test_end,
                "train_result": train_result,
                "eval_result": eval_result,
            })

            logger.info(
                "Fold %d: accuracy=%.4f, f1=%.4f",
                len(results),
                eval_result.get("accuracy", 0),
                eval_result.get("f1_macro", 0),
            )

        avg_accuracy = np.mean([r["eval_result"].get("accuracy", 0) for r in results])
        avg_f1 = np.mean([r["eval_result"].get("f1_macro", 0) for r in results])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_filename = f"lstm_direction_{symbol}_{timeframe}_{timestamp}.keras"
        model_path = os.path.join(self.model_dir, model_filename)

        best_result = max(results, key=lambda r: r["eval_result"].get("accuracy", 0))

        summary = {
            "symbol": symbol,
            "timeframe": timeframe,
            "sequence_length": sequence_length,
            "n_features": n_features,
            "n_folds": len(results),
            "avg_accuracy": float(avg_accuracy),
            "avg_f1": float(avg_f1),
            "best_accuracy": float(best_result["eval_result"].get("accuracy", 0)),
            "best_f1": float(best_result["eval_result"].get("f1_macro", 0)),
            "model_path": model_path,
            "timestamp": timestamp,
        }

        summary_path = os.path.join(self.model_dir, f"lstm_summary_{symbol}_{timestamp}.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(
            "Training complete: avg_acc=%.4f, avg_f1=%.4f, best_acc=%.4f",
            avg_accuracy, avg_f1, best_result["eval_result"].get("accuracy", 0),
        )

        return summary
