"""
ATR Border Grid — dynamic support/resistance zones using
EMA ± ATR multiples.

Creates a 4-layer border grid around the EMA midline:

    Layer 0 (core):     EMA ± 0.5 × ATR
    Layer 1 (inner):    EMA ± 1.0 × ATR
    Layer 2 (outer):    EMA ± 1.5 × ATR
    Layer 3 (extended): EMA ± 2.0 × ATR

The price's position relative to these borders determines the
ATR border layer and informs entry/exit decisions.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("gold_edge.atr_border")


@dataclass
class ATRBorderResult:
    """Result of an ATR border calculation."""

    ema_midline: float = 0.0
    atr_value: float = 0.0
    borders: Dict[str, Dict[str, float]] = field(default_factory=dict)
    current_layer: int = 0
    price_position_pct: float = 0.5  # 0 = at lower band, 1 = at upper band
    is_near_border: bool = False
    nearest_border_distance: float = 0.0
    nearest_border_name: str = ""

    def to_dict(self) -> dict:
        return {
            "ema_midline": round(self.ema_midline, 6),
            "atr_value": round(self.atr_value, 6),
            "borders": {
                k: {kk: round(vv, 6) for kk, vv in v.items()}
                for k, v in self.borders.items()
            },
            "current_layer": self.current_layer,
            "price_position_pct": round(self.price_position_pct, 4),
            "is_near_border": self.is_near_border,
            "nearest_border_distance": round(self.nearest_border_distance, 6),
            "nearest_border_name": self.nearest_border_name,
        }


class ATRBorderGrid:
    """
    Builds a dynamic 4-layer ATR border grid around an EMA midline.

    Usage::

        grid = ATRBorderGrid(ema_period=21, atr_period=14)
        result = grid.calculate(ohlcv_df)
        # result.current_layer → which zone the price is in
        # result.borders → dict of upper/lower for each layer
    """

    DEFAULT_MULTIPLIERS = [0.5, 1.0, 1.5, 2.0]
    LAYER_NAMES = ["core", "inner", "outer", "extended"]

    def __init__(
        self,
        ema_period: int = 21,
        atr_period: int = 14,
        multipliers: Optional[List[float]] = None,
        border_proximity_pct: float = 0.05,
    ):
        """
        Args:
            ema_period: EMA lookback for midline.
            atr_period: ATR lookback.
            multipliers: ATR multipliers for each layer.
            border_proximity_pct: price is "near" a border if within this
                fraction of ATR distance.
        """
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.multipliers = multipliers or self.DEFAULT_MULTIPLIERS.copy()
        self.border_proximity_pct = border_proximity_pct

    def _compute_ema(self, close: pd.Series) -> pd.Series:
        return close.ewm(span=self.ema_period, adjust=False).mean()

    def _compute_atr(self, df: pd.DataFrame) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        tr = pd.concat([
            h - l,
            (h - c.shift(1)).abs(),
            (l - c.shift(1)).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def calculate(
        self,
        ohlcv_df: pd.DataFrame,
        price: Optional[float] = None,
    ) -> ATRBorderResult:
        """
        Calculate the ATR border grid for the current bar.

        Args:
            ohlcv_df: DataFrame with [open, high, low, close, volume].
            price: override price (default: last close).

        Returns:
            ATRBorderResult with all border data.
        """
        if ohlcv_df is None or len(ohlcv_df) < max(self.ema_period, self.atr_period) + 5:
            logger.warning("Insufficient data for ATR border grid")
            return ATRBorderResult()

        ema = self._compute_ema(ohlcv_df["close"])
        atr = self._compute_atr(ohlcv_df)

        ema_val = float(ema.iloc[-1])
        atr_val = float(atr.iloc[-1])

        if np.isnan(ema_val) or np.isnan(atr_val) or atr_val <= 0:
            return ATRBorderResult(ema_midline=ema_val or 0, atr_value=0)

        current_price = price if price is not None else float(ohlcv_df["close"].iloc[-1])

        # Build border layers
        borders = {}
        for i, mult in enumerate(self.multipliers):
            layer_name = self.LAYER_NAMES[i] if i < len(self.LAYER_NAMES) else f"layer_{i}"
            borders[layer_name] = {
                "lower": ema_val - mult * atr_val,
                "upper": ema_val + mult * atr_val,
                "multiplier": mult,
            }

        # Determine current layer
        current_layer = 0
        for i, mult in enumerate(self.multipliers):
            lower = ema_val - mult * atr_val
            upper = ema_val + mult * atr_val
            if lower <= current_price <= upper:
                current_layer = i

        # Price position percentage (0 = at lowest border, 1 = at highest)
        lowest = ema_val - self.multipliers[-1] * atr_val
        highest = ema_val + self.multipliers[-1] * atr_val
        if highest > lowest:
            price_position_pct = (current_price - lowest) / (highest - lowest)
        else:
            price_position_pct = 0.5
        price_position_pct = float(np.clip(price_position_pct, 0, 1))

        # Find nearest border
        nearest_dist = float("inf")
        nearest_name = ""
        for name, b in borders.items():
            for side in ("lower", "upper"):
                dist = abs(current_price - b[side])
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_name = f"{name}_{side}"

        is_near = nearest_dist < atr_val * self.border_proximity_pct

        return ATRBorderResult(
            ema_midline=ema_val,
            atr_value=atr_val,
            borders=borders,
            current_layer=current_layer,
            price_position_pct=price_position_pct,
            is_near_border=is_near,
            nearest_border_distance=nearest_dist,
            nearest_border_name=nearest_name,
        )

    def get_border_signal(
        self, border_result: ATRBorderResult, direction: str
    ) -> Dict[str, any]:
        """
        Generate a trading signal based on border position.

        Args:
            border_result: result from ``calculate()``.
            direction: "LONG" or "SHORT".

        Returns:
            dict with ``action``, ``layer``, ``confidence``.
        """
        layer = border_result.current_layer
        pos = border_result.price_position_pct

        if direction == "LONG":
            # Prefer entering near lower borders (layer 1-2)
            if layer >= 2 and pos < 0.3:
                return {"action": "ENTRY", "layer": layer, "confidence": 0.85}
            elif layer == 1 and pos < 0.4:
                return {"action": "ENTRY", "layer": layer, "confidence": 0.70}
            elif border_result.is_near_border and "lower" in border_result.nearest_border_name:
                return {"action": "WATCH", "layer": layer, "confidence": 0.60}
        elif direction == "SHORT":
            # Prefer entering near upper borders (layer 1-2)
            if layer >= 2 and pos > 0.7:
                return {"action": "ENTRY", "layer": layer, "confidence": 0.85}
            elif layer == 1 and pos > 0.6:
                return {"action": "ENTRY", "layer": layer, "confidence": 0.70}
            elif border_result.is_near_border and "upper" in border_result.nearest_border_name:
                return {"action": "WATCH", "layer": layer, "confidence": 0.60}

        return {"action": "NO_ACTION", "layer": layer, "confidence": 0.3}
