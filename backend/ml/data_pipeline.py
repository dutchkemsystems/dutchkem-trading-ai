import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.pipeline")


class DataPipeline:
    """
    Data ingestion from MT5 and InfluxDB.
    Fetches OHLCV data, stores features, and manages data flows.
    """

    def __init__(self):
        self._mt5_service = None

    @property
    def mt5(self):
        if self._mt5_service is None:
            from mcp_integration.services import mt5_service
            self._mt5_service = mt5_service
        return self._mt5_service

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "H1",
        count: int = 500,
    ) -> pd.DataFrame:
        candles = await self.mt5.get_candles(symbol, timeframe, count)

        if not candles:
            logger.warning("No candle data returned for %s %s", symbol, timeframe)
            return pd.DataFrame()

        df = pd.DataFrame(candles)

        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

        if "time" in df.columns:
            df["timestamp"] = pd.to_datetime(df["time"])
            df = df.sort_values("timestamp").reset_index(drop=True)
        elif "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)

        return df

    async def fetch_multi_timeframe(
        self,
        symbol: str,
        timeframes: Optional[List[str]] = None,
        count: int = 500,
    ) -> Dict[str, pd.DataFrame]:
        if timeframes is None:
            timeframes = ["M5", "M15", "M30", "H1", "H4"]

        data = {}
        for tf in timeframes:
            df = await self.fetch_ohlcv(symbol, tf, count)
            if not df.empty:
                data[tf] = df
            else:
                logger.warning("Empty data for %s %s", symbol, tf)

        return data

    async def fetch_with_features(
        self,
        symbol: str,
        timeframe: str = "H1",
        count: int = 500,
    ) -> pd.DataFrame:
        from ml.features import FeatureEngine

        df = await self.fetch_ohlcv(symbol, timeframe, count)
        if df.empty:
            return df

        engine = FeatureEngine()
        features = engine.compute_features(df)
        return pd.concat([df, features], axis=1)

    def store_features(
        self, symbol: str, timeframe: str, features_df: pd.DataFrame
    ):
        try:
            from market_data.models import MarketData
            from trading.models import Symbol
            from indicators.models import Timeframe

            sym = Symbol.objects.get(name=symbol)
            tf = Timeframe.objects.get(code=timeframe)

            records = []
            for _, row in features_df.iterrows():
                if "timestamp" in row:
                    ts = row["timestamp"]
                else:
                    continue

                records.append(MarketData(
                    symbol=sym,
                    timeframe=tf,
                    timestamp=ts,
                    open=row.get("open", 0),
                    high=row.get("high", 0),
                    low=row.get("low", 0),
                    close=row.get("close", 0),
                    volume=int(row.get("volume", 0)),
                ))

            if records:
                MarketData.objects.bulk_create(
                    records,
                    update_conflict=True,
                    unique_fields=["symbol", "timeframe", "timestamp"],
                    update_fields=["open", "high", "low", "close", "volume"],
                )
        except Exception as e:
            logger.error("Error storing features: %s", e)

    def prepare_training_data(
        self,
        features_df: pd.DataFrame,
        labels: pd.Series,
        sequence_length: int = 60,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> Dict[str, Any]:
        feature_cols = [c for c in features_df.columns if c not in [
            "open", "high", "low", "close", "volume", "timestamp",
        ]]

        X = features_df[feature_cols].values
        y = labels.values

        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X = X[mask]
        y = y[mask]

        X_seq, y_seq = self._create_sequences(X, y, sequence_length)

        n = len(X_seq)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        return {
            "X_train": X_seq[:train_end],
            "y_train": y_seq[:train_end],
            "X_val": X_seq[train_end:val_end],
            "y_val": y_seq[train_end:val_end],
            "X_test": X_seq[val_end:],
            "y_test": y_seq[val_end:],
            "feature_names": feature_cols,
            "sequence_length": sequence_length,
        }

    def _create_sequences(
        self, X: np.ndarray, y: np.ndarray, seq_length: int
    ) -> tuple:
        X_seq, y_seq = [], []
        for i in range(seq_length, len(X)):
            X_seq.append(X[i - seq_length:i])
            y_seq.append(y[i])
        return np.array(X_seq), np.array(y_seq)
