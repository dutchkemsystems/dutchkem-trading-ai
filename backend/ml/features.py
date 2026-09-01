import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.features")


class FeatureEngine:
    """
    Feature engineering pipeline producing 150+ features per symbol.
    Covers technical, volume, microstructure, statistical, and time features.
    """

    TIMEFRAME_MAP = {
        "M1": 1, "M5": 5, "M15": 15, "M30": 30,
        "H1": 60, "H2": 120, "H4": 240, "D1": 1440,
    }

    def __init__(self, lookback_periods: Optional[List[int]] = None):
        self.lookback_periods = lookback_periods or [5, 10, 20, 50, 100, 200]

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all features from OHLCV data.

        Args:
            df: DataFrame with columns [open, high, low, close, volume, spread, timestamp]
        Returns:
            DataFrame with 150+ feature columns
        """
        if len(df) < 200:
            logger.warning("Insufficient data: %d rows, need at least 200", len(df))

        features = pd.DataFrame(index=df.index)

        features = self._price_action_features(df, features)
        features = self._momentum_features(df, features)
        features = self._trend_features(df, features)
        features = self._volatility_features(df, features)
        features = self._volume_features(df, features)
        features = self._microstructure_features(df, features)
        features = self._statistical_features(df, features)
        features = self._time_features(df, features)
        features = self._support_resistance_features(df, features)

        return features

    def compute_labels(
        self, df: pd.DataFrame, forward_bars: int = 5, threshold: float = 0.0002
    ) -> pd.Series:
        """
        Compute target variable: next N-bar return direction.
        1 = bullish, 0 = bearish, 2 = neutral
        """
        future_return = df["close"].shift(-forward_bars) / df["close"] - 1
        labels = pd.Series(2, index=df.index, dtype=int)
        labels[future_return > threshold] = 1
        labels[future_return < -threshold] = 0
        return labels

    def _price_action_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        c, h, l, o = df["close"], df["high"], df["low"], df["open"]

        features["body"] = c - o
        features["body_pct"] = features["body"] / o
        features["upper_wick"] = h - pd.concat([c, o], axis=1).max(axis=1)
        features["lower_wick"] = pd.concat([c, o], axis=1).min(axis=1) - l
        features["wick_ratio"] = features["upper_wick"] / (features["lower_wick"] + 1e-10)
        features["range"] = h - l
        features["range_pct"] = features["range"] / o

        for period in [5, 10, 20]:
            features[f"close_ma_{period}"] = c.rolling(period).mean()
            features[f"close_ma_ratio_{period}"] = c / features[f"close_ma_{period}"]
            features[f"high_{period}_max"] = h.rolling(period).max()
            features[f"low_{period}_min"] = l.rolling(period).min()
            features[f"close_position_{period}"] = (
                (c - features[f"low_{period}_min"]) /
                (features[f"high_{period}_max"] - features[f"low_{period}_min"] + 1e-10)
            )

        features["higher_high"] = (h > h.shift(1)).astype(int)
        features["lower_low"] = (l < l.shift(1)).astype(int)
        features["higher_low"] = (l > l.shift(1)).astype(int)
        features["lower_high"] = (h < h.shift(1)).astype(int)

        features["hh_count_20"] = features["higher_high"].rolling(20).sum()
        features["ll_count_20"] = features["lower_low"].rolling(20).sum()
        features["hl_count_20"] = features["higher_low"].rolling(20).sum()
        features["lh_count_20"] = features["lower_high"].rolling(20).sum()

        return features

    def _momentum_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        c = df["close"]

        for period in [7, 14, 21]:
            delta = c.diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / (loss + 1e-10)
            features[f"rsi_{period}"] = 100 - (100 / (1 + rs))

        for fast, slow, signal in [(12, 26, 9)]:
            ema_fast = c.ewm(span=fast, adjust=False).mean()
            ema_slow = c.ewm(span=slow, adjust=False).mean()
            features[f"macd_{fast}_{slow}"] = ema_fast - ema_slow
            features[f"macd_signal_{signal}"] = features[f"macd_{fast}_{slow}"].ewm(span=signal, adjust=False).mean()
            features[f"macd_hist_{fast}_{slow}"] = features[f"macd_{fast}_{slow}"] - features[f"macd_signal_{signal}"]

        for period in [14, 20]:
            sma = c.rolling(period).mean()
            std = c.rolling(period).std()
            features[f"bb_upper_{period}"] = sma + 2 * std
            features[f"bb_lower_{period}"] = sma - 2 * std
            features[f"bb_pct_{period}"] = (c - features[f"bb_lower_{period}"]) / (
                features[f"bb_upper_{period}"] - features[f"bb_lower_{period}"] + 1e-10
            )
            features[f"bb_width_{period}"] = (features[f"bb_upper_{period}"] - features[f"bb_lower_{period}"]) / sma

        for period in [5, 14]:
            features[f"stoch_k_{period}"] = self._stochastic_k(df, period)
            features[f"stoch_d_{period}"] = features[f"stoch_k_{period}"].rolling(3).mean()

        for period in [14, 20]:
            tp = (df["high"] + df["low"] + c) / 3
            features[f"cci_{period}"] = (tp - tp.rolling(period).mean()) / (0.015 * tp.rolling(period).std())

        features["williams_r_14"] = self._williams_r(df, 14)

        for period in [5, 10, 20]:
            features[f"roc_{period}"] = c.pct_change(period)

        features["momentum_10"] = c / c.shift(10) - 1
        features["momentum_20"] = c / c.shift(20) - 1

        return features

    def _trend_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        c, h, l = df["close"], df["high"], df["low"]

        features["adx_14"] = self._adx(df, 14)
        features["di_plus_14"] = self._di_plus(df, 14)
        features["di_minus_14"] = self._di_minus(df, 14)
        features["di_diff_14"] = features["di_plus_14"] - features["di_minus_14"]

        ichimoku = self._ichimoku(df)
        for key, val in ichimoku.items():
            features[f"ichimoku_{key}"] = val
        features["ichimoku_cloud_top"] = pd.concat(
            [ichimoku["senkou_a"], ichimoku["senkou_b"]], axis=1
        ).max(axis=1)
        features["ichimoku_cloud_bottom"] = pd.concat(
            [ichimoku["senkou_a"], ichimoku["senkou_b"]], axis=1
        ).min(axis=1)
        features["price_vs_cloud"] = (c - features["ichimoku_cloud_top"]) / (
            features["ichimoku_cloud_top"] - features["ichimoku_cloud_bottom"] + 1e-10
        )

        supertrend = self._supertrend(df, 10, 3)
        features["supertrend"] = supertrend
        features["supertrend_signal"] = np.where(c > supertrend, 1, -1)

        for fast, slow in [(5, 10), (20, 50), (50, 200)]:
            ema_fast = c.ewm(span=fast, adjust=False).mean()
            ema_slow = c.ewm(span=slow, adjust=False).mean()
            features[f"ema_cross_{fast}_{slow}"] = np.where(ema_fast > ema_slow, 1, -1)
            features[f"ema_distance_{fast}_{slow}"] = (ema_fast - ema_slow) / ema_slow

        features["psar"] = self._parabolic_sar(df)
        features["psar_signal"] = np.where(c > features["psar"], 1, -1)

        return features

    def _volatility_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        c, h, l = df["close"], df["high"], df["low"]

        for period in [14, 20]:
            tr = pd.concat([
                h - l,
                (h - c.shift(1)).abs(),
                (l - c.shift(1)).abs(),
            ], axis=1).max(axis=1)
            features[f"atr_{period}"] = tr.rolling(period).mean()
            features[f"atr_normalized_{period}"] = features[f"atr_{period}"] / c

        features["historical_vol_20"] = c.pct_change().rolling(20).std() * np.sqrt(252)

        features["keltner_upper"] = c.ewm(span=20, adjust=False).mean() + 1.5 * features.get("atr_14", c.rolling(14).std())
        features["keltner_lower"] = c.ewm(span=20, adjust=False).mean() - 1.5 * features.get("atr_14", c.rolling(14).std())
        features["keltner_width"] = (features["keltner_upper"] - features["keltner_lower"]) / c

        features["true_range"] = pd.concat([
            h - l,
            (h - c.shift(1)).abs(),
            (l - c.shift(1)).abs(),
        ], axis=1).max(axis=1)
        features["tr_ratio"] = features["true_range"] / features["true_range"].rolling(20).mean()

        return features

    def _volume_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        c, v = df["close"], df["volume"]

        obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
        features["obv"] = obv
        features["obv_slope_10"] = obv.rolling(10).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True
        )

        typical_price = (df["high"] + df["low"] + c) / 3
        features["vwap"] = (typical_price * v).cumsum() / v.cumsum()
        features["price_vs_vwap"] = (c - features["vwap"]) / features["vwap"]

        features["volume_sma_20"] = v.rolling(20).mean()
        features["volume_ratio"] = v / (features["volume_sma_20"] + 1)
        features["volume_spike"] = (v > 2 * features["volume_sma_20"]).astype(int)

        features["volume_trend_10"] = v.rolling(10).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True
        )

        delta = c.diff()
        buy_volume = v.where(delta > 0, 0)
        sell_volume = v.where(delta < 0, 0)
        features["buy_sell_ratio"] = buy_volume.rolling(20).sum() / (sell_volume.rolling(20).sum() + 1)
        features["volume_delta"] = (buy_volume - sell_volume).rolling(20).sum()

        return features

    def _microstructure_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        if "spread" in df.columns:
            spread = df["spread"]
            features["spread"] = spread
            features["spread_sma_20"] = spread.rolling(20).mean()
            features["spread_ratio"] = spread / (features["spread_sma_20"] + 1e-10)
            features["spread_percentile"] = spread.rolling(100).rank(pct=True)

        features["tick_count_proxy"] = df["volume"].rolling(5).mean()

        bid_ask_imbalance = (df["close"] - df["low"]) / (df["high"] - df["low"] + 1e-10)
        features["price_imbalance"] = bid_ask_imbalance
        features["imbalance_sma_10"] = bid_ask_imbalance.rolling(10).mean()

        features["amihud_illiquidity"] = df["close"].pct_change().abs() / (df["volume"] + 1)

        return features

    def _statistical_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        c = df["close"]
        returns = c.pct_change()

        features["returns_1"] = returns
        features["returns_5"] = c.pct_change(5)
        features["returns_10"] = c.pct_change(10)
        features["returns_20"] = c.pct_change(20)

        for period in [10, 20, 50]:
            features[f"volatility_{period}"] = returns.rolling(period).std()
            features[f"skewness_{period}"] = returns.rolling(period).skew()
            features[f"kurtosis_{period}"] = returns.rolling(period).kurt()

        features["z_score_20"] = (c - c.rolling(20).mean()) / (c.rolling(20).std() + 1e-10)
        features["z_score_50"] = (c - c.rolling(50).mean()) / (c.rolling(50).std() + 1e-10)

        features["autocorr_1"] = returns.rolling(50).apply(
            lambda x: x.autocorr(lag=1) if len(x) > 1 else 0, raw=False
        )

        features["max_drawdown_20"] = c.rolling(20).apply(
            lambda x: (x / x.cummax() - 1).min(), raw=True
        )

        features["return_dispersion_20"] = returns.rolling(20).std() / (returns.rolling(20).mean() + 1e-10)

        return features

    def _time_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        if "timestamp" in df.columns:
            ts = pd.to_datetime(df["timestamp"])
        else:
            ts = df.index

        if hasattr(ts, "hour"):
            features["hour"] = ts.hour
            features["hour_sin"] = np.sin(2 * np.pi * ts.hour / 24)
            features["hour_cos"] = np.cos(2 * np.pi * ts.hour / 24)

            features["day_of_week"] = ts.dayofweek
            features["dow_sin"] = np.sin(2 * np.pi * ts.dayofweek / 5)
            features["dow_cos"] = np.cos(2 * np.pi * ts.dayofweek / 5)

            features["month"] = ts.month
            features["month_sin"] = np.sin(2 * np.pi * ts.month / 12)
            features["month_cos"] = np.cos(2 * np.pi * ts.month / 12)

            hour = ts.hour
            features["session_asian"] = ((hour >= 0) & (hour < 8)).astype(int)
            features["session_london"] = ((hour >= 7) & (hour < 16)).astype(int)
            features["session_ny"] = ((hour >= 13) & (hour < 22)).astype(int)
            features["session_overlap"] = ((hour >= 13) & (hour < 16)).astype(int)

            features["is_friday"] = (ts.dayofweek == 4).astype(int)
            features["is_monday"] = (ts.dayofweek == 0).astype(int)

        return features

    def _support_resistance_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        c, h, l = df["close"], df["high"], df["low"]

        for period in [20, 50]:
            features[f"pivot_{period}"] = (h.rolling(period).max() + l.rolling(period).min() + c) / 3
            features[f"r1_{period}"] = 2 * features[f"pivot_{period}"] - l.rolling(period).min()
            features[f"s1_{period}"] = 2 * features[f"pivot_{period}"] - h.rolling(period).max()
            features[f"dist_to_r1_{period}"] = (features[f"r1_{period}"] - c) / c
            features[f"dist_to_s1_{period}"] = (c - features[f"s1_{period}"]) / c

        features["distance_to_52w_high"] = (c - h.rolling(252).max()) / (h.rolling(252).max() + 1e-10)
        features["distance_to_52w_low"] = (c - l.rolling(252).min()) / (l.rolling(252).min() + 1e-10)

        return features

    def _stochastic_k(self, df: pd.DataFrame, period: int) -> pd.Series:
        low_min = df["low"].rolling(period).min()
        high_max = df["high"].rolling(period).max()
        return 100 * (df["close"] - low_min) / (high_max - low_min + 1e-10)

    def _williams_r(self, df: pd.DataFrame, period: int) -> pd.Series:
        high_max = df["high"].rolling(period).max()
        low_min = df["low"].rolling(period).min()
        return -100 * (high_max - df["close"]) / (high_max - low_min + 1e-10)

    def _adx(self, df: pd.DataFrame, period: int) -> pd.Series:
        plus_dm = df["high"].diff()
        minus_dm = -df["low"].diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
        adx = dx.ewm(span=period, adjust=False).mean()
        return adx

    def _di_plus(self, df: pd.DataFrame, period: int) -> pd.Series:
        plus_dm = df["high"].diff()
        minus_dm = -df["low"].diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)

        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()
        return 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)

    def _di_minus(self, df: pd.DataFrame, period: int) -> pd.Series:
        plus_dm = df["high"].diff()
        minus_dm = -df["low"].diff()
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()
        return 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

    def _ichimoku(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        tenkan = (df["high"].rolling(9).max() + df["low"].rolling(9).min()) / 2
        kijun = (df["high"].rolling(26).max() + df["low"].rolling(26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2).shift(26)
        chikou = df["close"].shift(-26)

        return {
            "tenkan": tenkan,
            "kijun": kijun,
            "senkou_a": senkou_a,
            "senkou_b": senkou_b,
            "chikou": chikou,
        }

    def _supertrend(self, df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.Series:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()
        hl2 = (df["high"] + df["low"]) / 2
        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr

        supertrend = pd.Series(np.nan, index=df.index)
        direction = pd.Series(1, index=df.index)

        for i in range(period, len(df)):
            if df["close"].iloc[i] > upper.iloc[i - 1]:
                direction.iloc[i] = 1
            elif df["close"].iloc[i] < lower.iloc[i - 1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i - 1]

            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lower.iloc[i]
            else:
                supertrend.iloc[i] = upper.iloc[i]

        return supertrend

    def _parabolic_sar(self, df: pd.DataFrame, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
        length = len(df)
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        psar = np.zeros(length)
        af = af_start
        bull = True
        ep = low[0]
        hp = high[0]
        lp = low[0]

        psar[0] = high[0]

        for i in range(1, length):
            if bull:
                psar[i] = psar[i - 1] + af * (ep - psar[i - 1])
                psar[i] = min(psar[i], low[i - 1], low[max(0, i - 2)])

                if low[i] < psar[i]:
                    bull = False
                    psar[i] = ep
                    lp = low[i]
                    af = af_start
                else:
                    if high[i] > hp:
                        hp = high[i]
                        ep = hp
                        af = min(af + af_step, af_max)
            else:
                psar[i] = psar[i - 1] + af * (ep - psar[i - 1])
                psar[i] = max(psar[i], high[i - 1], high[max(0, i - 2)])

                if high[i] > psar[i]:
                    bull = True
                    psar[i] = ep
                    hp = high[i]
                    af = af_start
                else:
                    if low[i] < lp:
                        lp = low[i]
                        ep = lp
                        af = min(af + af_step, af_max)

        return pd.Series(psar, index=df.index)
