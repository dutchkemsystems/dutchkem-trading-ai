"""
Gold Edge Composite (GEC) Indicator.

Combines four weighted sub-components into a single score in the range
[-1, +1]:

  - Momentum  (30 %)
  - Trend     (30 %)
  - Volatility (20 %)
  - DXY Correlation (20 %)

Each sub-component produces a value in [-1, +1] where:
  -1 = strong bearish signal
   0 = neutral
  +1 = strong bullish signal
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("gold_edge.composite")


@dataclass
class GECResult:
    """Result of a GEC calculation."""

    composite_score: float = 0.0
    momentum_score: float = 0.0
    trend_score: float = 0.0
    volatility_score: float = 0.0
    dxy_correlation_score: float = 0.0
    direction: str = "NEUTRAL"
    confidence: float = 0.0
    components: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "composite_score": round(self.composite_score, 4),
            "momentum_score": round(self.momentum_score, 4),
            "trend_score": round(self.trend_score, 4),
            "volatility_score": round(self.volatility_score, 4),
            "dxy_correlation_score": round(self.dxy_correlation_score, 4),
            "direction": self.direction,
            "confidence": round(self.confidence, 4),
        }


class GoldEdgeComposite:
    """
    Calculates the Gold Edge Composite (GEC) indicator.

    Usage::

        gec = GoldEdgeComposite(
            momentum_weight=0.30,
            trend_weight=0.30,
            volatility_weight=0.20,
            dxy_correlation_weight=0.20,
        )
        result = gec.calculate(ohlcv_df, dxy_series)
    """

    def __init__(
        self,
        momentum_weight: float = 0.30,
        trend_weight: float = 0.30,
        volatility_weight: float = 0.20,
        dxy_correlation_weight: float = 0.20,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        ema_fast: int = 9,
        ema_slow: int = 21,
        atr_period: int = 14,
    ):
        total = momentum_weight + trend_weight + volatility_weight + dxy_correlation_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        self.momentum_weight = momentum_weight
        self.trend_weight = trend_weight
        self.volatility_weight = volatility_weight
        self.dxy_correlation_weight = dxy_correlation_weight

        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.atr_period = atr_period

    # ------------------------------------------------------------------
    # Sub-component calculators
    # ------------------------------------------------------------------

    def _momentum_score(self, df: pd.DataFrame) -> float:
        """
        RSI + MACD histogram combined momentum score in [-1, +1].
        """
        close = df["close"]

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(self.rsi_period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - 100 / (1 + rs)
        rsi_val = float(rsi.iloc[-1]) if not rsi.empty else 50.0
        # Normalise RSI to [-1, +1]: 50 -> 0, 0 -> -1, 100 -> +1
        rsi_norm = (rsi_val - 50) / 50

        # MACD histogram
        ema_f = close.ewm(span=self.macd_fast, adjust=False).mean()
        ema_s = close.ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = ema_f - ema_s
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        hist = macd_line - signal_line
        # Normalise by price scale
        price = float(close.iloc[-1]) if not close.empty else 1.0
        hist_norm = float(hist.iloc[-1]) / (price * 0.01 + 1e-10)
        hist_norm = np.clip(hist_norm, -1, 1)

        # Combined
        return float(np.clip(0.6 * rsi_norm + 0.4 * hist_norm, -1, 1))

    def _trend_score(self, df: pd.DataFrame) -> float:
        """
        EMA crossover + ADX trend strength → score in [-1, +1].
        """
        close = df["close"]
        ema_f = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_s = close.ewm(span=self.ema_slow, adjust=False).mean()

        # EMA crossover direction
        diff = float(ema_f.iloc[-1] - ema_s.iloc[-1])
        price = float(close.iloc[-1]) if not close.empty else 1.0
        ema_norm = np.clip(diff / (price * 0.01 + 1e-10), -1, 1)

        # ADX-like trend strength (simplified)
        h, l = df["high"], df["low"]
        plus_dm = h.diff()
        minus_dm = -l.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr = pd.concat([
            h - l,
            (h - close.shift(1)).abs(),
            (l - close.shift(1)).abs(),
        ], axis=1).max(axis=1)

        atr = tr.ewm(span=self.atr_period, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(span=self.atr_period, adjust=False).mean() / (atr + 1e-10)
        minus_di = 100 * minus_dm.ewm(span=self.atr_period, adjust=False).mean() / (atr + 1e-10)
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
        adx = dx.ewm(span=self.atr_period, adjust=False).mean()

        adx_val = float(adx.iloc[-1]) if not adx.empty else 20.0
        trend_strength = min(adx_val / 50.0, 1.0)  # cap at 1.0

        return float(np.clip(ema_norm * trend_strength * 2, -1, 1))

    def _volatility_score(self, df: pd.DataFrame) -> float:
        """
        ATR normalised + Bollinger width → score in [-1, +1].

        Higher volatility in the direction of the trend is positive.
        """
        close = df["close"]
        h, l = df["high"], df["low"]

        tr = pd.concat([
            h - l,
            (h - close.shift(1)).abs(),
            (l - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        atr_val = float(atr.iloc[-1]) if not atr.empty else 0.0
        price = float(close.iloc[-1]) if not close.empty else 1.0
        atr_pct = atr_val / (price + 1e-10)

        # Bollinger width
        sma = close.rolling(20).mean()
        std = close.rolling(20).std()
        bb_upper = sma + 2 * std
        bb_lower = sma - 2 * std
        bb_width = (bb_upper - bb_lower) / (sma + 1e-10)
        bb_val = float(bb_width.iloc[-1]) if not bb_width.empty else 0.02

        # Score: moderate volatility is ideal (0.005-0.02), extreme is penalised
        if atr_pct < 0.003:
            vol_score = -0.3  # too quiet
        elif atr_pct < 0.01:
            vol_score = 0.5  # ideal
        elif atr_pct < 0.02:
            vol_score = 0.8  # good
        elif atr_pct < 0.04:
            vol_score = 0.3  # elevated
        else:
            vol_score = -0.5  # extreme

        # Combine with BB width
        bb_score = np.clip((bb_val - 0.01) * 20, -1, 1)

        return float(np.clip(0.6 * vol_score + 0.4 * bb_score, -1, 1))

    def _dxy_correlation_score(
        self, df: pd.DataFrame, dxy_series: Optional[pd.Series] = None
    ) -> float:
        """
        DXY (US Dollar Index) correlation-based score.

        For gold-related instruments, a weakening DXY is bullish.
        Without DXY data, returns a neutral score.
        """
        if dxy_series is None or len(dxy_series) < 20:
            return 0.0

        close = df["close"]
        min_len = min(len(close), len(dxy_series))
        if min_len < 20:
            return 0.0

        gold_ret = close.iloc[-min_len:].pct_change().dropna()
        dxy_ret = dxy_series.iloc[-min_len:].pct_change().dropna()
        min_len = min(len(gold_ret), len(dxy_ret))

        if min_len < 10:
            return 0.0

        corr = np.corrcoef(
            gold_ret.iloc[-min_len:].values,
            dxy_ret.iloc[-min_len:].values,
        )[0, 1]

        if np.isnan(corr):
            return 0.0

        # Negative correlation with DXY is bullish for gold
        # So we invert: negative corr → positive score
        return float(np.clip(-corr, -1, 1))

    # ------------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------------

    def calculate(
        self,
        ohlcv_df: pd.DataFrame,
        dxy_series: Optional[pd.Series] = None,
    ) -> GECResult:
        """
        Compute the Gold Edge Composite from OHLCV data.

        Args:
            ohlcv_df: DataFrame with columns [open, high, low, close, volume].
            dxy_series: optional DXY close price series for correlation.

        Returns:
            GECResult with composite and sub-scores.
        """
        if ohlcv_df is None or len(ohlcv_df) < 30:
            logger.warning("Insufficient data for GEC calculation (%d rows)", len(ohlcv_df) if ohlcv_df is not None else 0)
            return GECResult()

        m = self._momentum_score(ohlcv_df)
        t = self._trend_score(ohlcv_df)
        v = self._volatility_score(ohlcv_df)
        d = self._dxy_correlation_score(ohlcv_df, dxy_series)

        composite = (
            self.momentum_weight * m
            + self.trend_weight * t
            + self.volatility_weight * v
            + self.dxy_correlation_weight * d
        )
        composite = float(np.clip(composite, -1, 1))

        if composite > 0.15:
            direction = "LONG"
        elif composite < -0.15:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"

        confidence = min(abs(composite) * 100, 100)

        return GECResult(
            composite_score=composite,
            momentum_score=m,
            trend_score=t,
            volatility_score=v,
            dxy_correlation_score=d,
            direction=direction,
            confidence=confidence,
            components={
                "momentum": m,
                "trend": t,
                "volatility": v,
                "dxy_correlation": d,
            },
        )
