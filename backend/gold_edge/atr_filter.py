"""
ATR Ratio Filter — filters out bad entries when volatility
conditions are outside the ideal range.

The ATR Ratio Filter compares the current ATR value to a smoothed
ATR average to determine whether the market volatility is suitable
for entries.

  - ATR Ratio < 0.15: Too quiet — no momentum, likely choppy
  - 0.15 ≤ ATR Ratio ≤ 1.0: Ideal range for entries
  - ATR Ratio > 1.0: Too volatile — likely news/event driven

Usage::

    filt = ATRRatioFilter(ratio_min=0.15, ratio_max=1.0)
    result = filt.calculate(ohlcv_df)
    if result.passes_filter:
        # proceed with entry
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("gold_edge.atr_filter")


@dataclass
class ATRFilterResult:
    """Result of the ATR ratio filter check."""

    current_atr: float = 0.0
    atr_sma: float = 0.0
    ratio: float = 0.0
    passes_filter: bool = False
    zone: str = "unknown"  # "quiet", "ideal", "volatile", "extreme"
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "current_atr": round(self.current_atr, 6),
            "atr_sma": round(self.atr_sma, 6),
            "ratio": round(self.ratio, 4),
            "passes_filter": self.passes_filter,
            "zone": self.zone,
            "reason": self.reason,
        }


class ATRRatioFilter:
    """
    ATR-based volatility filter for Gold Edge entries.

    Args:
        atr_period: ATR lookback period.
        sma_period: SMA smoothing period for ATR average.
        ratio_min: Lower bound of ideal ATR ratio range.
        ratio_max: Upper bound of ideal ATR ratio range.
    """

    def __init__(
        self,
        atr_period: int = 14,
        sma_period: int = 50,
        ratio_min: float = 0.15,
        ratio_max: float = 1.0,
    ):
        self.atr_period = atr_period
        self.sma_period = sma_period
        self.ratio_min = ratio_min
        self.ratio_max = ratio_max

    def calculate(self, ohlcv_df: pd.DataFrame) -> ATRFilterResult:
        """
        Compute the ATR ratio and check if it passes the filter.

        Args:
            ohlcv_df: DataFrame with [open, high, low, close, volume].

        Returns:
            ATRFilterResult.
        """
        if ohlcv_df is None or len(ohlcv_df) < self.atr_period + self.sma_period:
            logger.warning("Insufficient data for ATR ratio filter")
            return ATRFilterResult(reason="insufficient_data")

        close = ohlcv_df["close"]
        high = ohlcv_df["high"]
        low = ohlcv_df["low"]

        # True Range
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)

        # Current ATR (period-based)
        atr = tr.rolling(self.atr_period).mean()
        atr_val = float(atr.iloc[-1]) if not atr.empty else 0.0

        # ATR SMA (longer smoothing)
        atr_sma = atr.rolling(self.sma_period).mean()
        atr_sma_val = float(atr_sma.iloc[-1]) if not atr_sma.empty else 0.0

        if atr_sma_val <= 0 or np.isnan(atr_sma_val):
            return ATRFilterResult(
                current_atr=atr_val,
                atr_sma=atr_sma_val,
                ratio=0,
                passes_filter=False,
                zone="unknown",
                reason="atr_sma_zero",
            )

        ratio = atr_val / atr_sma_val

        # Determine zone
        if ratio < 0.5:
            zone = "quiet"
            reason = f"ATR ratio {ratio:.3f} < 0.5 — low volatility, poor momentum"
        elif ratio < self.ratio_min:
            zone = "quiet"
            reason = f"ATR ratio {ratio:.3f} < min {self.ratio_min} — below ideal range"
        elif ratio <= self.ratio_max:
            zone = "ideal"
            reason = f"ATR ratio {ratio:.3f} in ideal range [{self.ratio_min}, {self.ratio_max}]"
        elif ratio <= 2.0:
            zone = "volatile"
            reason = f"ATR ratio {ratio:.3f} > max {self.ratio_max} — elevated volatility"
        else:
            zone = "extreme"
            reason = f"ATR ratio {ratio:.3f} > 2.0 — extreme volatility, likely news"

        passes = self.ratio_min <= ratio <= self.ratio_max

        return ATRFilterResult(
            current_atr=atr_val,
            atr_sma=atr_sma_val,
            ratio=ratio,
            passes_filter=passes,
            zone=zone,
            reason=reason,
        )

    def get_entry_adjustment(
        self, filter_result: ATRFilterResult
    ) -> dict:
        """
        Suggest risk adjustments based on the filter result.

        Returns:
            dict with ``allow_entry``, ``risk_multiplier``, ``reason``.
        """
        if filter_result.passes_filter:
            return {
                "allow_entry": True,
                "risk_multiplier": 1.0,
                "reason": "Volatility within ideal range",
            }

        if filter_result.zone == "quiet":
            return {
                "allow_entry": True,
                "risk_multiplier": 0.5,
                "reason": "Low volatility — reduce position size",
            }

        if filter_result.zone == "volatile":
            return {
                "allow_entry": True,
                "risk_multiplier": 0.7,
                "reason": "Elevated volatility — reduce position size",
            }

        if filter_result.zone == "extreme":
            return {
                "allow_entry": False,
                "risk_multiplier": 0.0,
                "reason": "Extreme volatility — skip entry",
            }

        return {
            "allow_entry": False,
            "risk_multiplier": 0.0,
            "reason": f"Unknown zone: {filter_result.zone}",
        }
