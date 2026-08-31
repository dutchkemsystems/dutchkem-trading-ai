"""
Gold Edge Matrix — combines GEC composite, ATR border grid,
and ATR ratio filter into a high-probability entry decision.

The matrix produces a combined score in [0, 1] and decides:
  - ENTRY: high-confidence trade setup
  - WATCH: near entry but not confirmed
  - NO_TRADE: conditions not met

Entry requirements:
  1. GEC composite must be above minimum threshold
  2. Price must be within the ideal ATR border layer
  3. ATR ratio filter must pass
  4. Combined matrix score must exceed entry threshold
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from .atr_border import ATRBorderGrid, ATRBorderResult
from .atr_filter import ATRRatioFilter, ATRFilterResult
from .ge_composite import GoldEdgeComposite, GECResult

logger = logging.getLogger("gold_edge.entry")


@dataclass
class GoldEdgeMatrixResult:
    """Full result of the Gold Edge entry matrix evaluation."""

    # GEC
    gec: Optional[GECResult] = None

    # ATR borders
    atr_border: Optional[ATRBorderResult] = None

    # ATR filter
    atr_filter: Optional[ATRFilterResult] = None

    # Matrix decision
    action: str = "NO_TRADE"  # ENTRY, WATCH, NO_TRADE
    combined_score: float = 0.0
    direction: str = "NEUTRAL"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward_ratio: float = 0.0
    confidence: float = 0.0

    # Sub-scores for transparency
    gec_score: float = 0.0
    border_score: float = 0.0
    filter_score: float = 0.0

    rejection_reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "direction": self.direction,
            "combined_score": round(self.combined_score, 4),
            "entry_price": round(self.entry_price, 6) if self.entry_price else 0,
            "stop_loss": round(self.stop_loss, 6) if self.stop_loss else 0,
            "take_profit": round(self.take_profit, 6) if self.take_profit else 0,
            "risk_reward_ratio": round(self.risk_reward_ratio, 2),
            "confidence": round(self.confidence, 2),
            "gec_score": round(self.gec_score, 4),
            "border_score": round(self.border_score, 4),
            "filter_score": round(self.filter_score, 4),
            "rejection_reasons": self.rejection_reasons,
            "gec": self.gec.to_dict() if self.gec else None,
            "atr_border": self.atr_border.to_dict() if self.atr_border else None,
            "atr_filter": self.atr_filter.to_dict() if self.atr_filter else None,
        }


class GoldEdgeMatrix:
    """
    Combines GEC + ATR borders + ATR filter to produce trade entries.

    Usage::

        matrix = GoldEdgeMatrix(
            min_gec_score=0.50,
            min_combined_score=0.60,
        )
        result = matrix.evaluate(ohlcv_df, dxy_series)
        if result.action == "ENTRY":
            # Execute trade
    """

    def __init__(
        self,
        # GEC weights
        momentum_weight: float = 0.30,
        trend_weight: float = 0.30,
        volatility_weight: float = 0.20,
        dxy_correlation_weight: float = 0.20,
        # ATR border settings
        ema_period: int = 21,
        atr_period: int = 14,
        atr_multipliers: Optional[list] = None,
        # ATR filter settings
        atr_sma_period: int = 50,
        atr_ratio_min: float = 0.15,
        atr_ratio_max: float = 1.0,
        # Entry thresholds
        min_gec_score: float = 0.50,
        min_combined_score: float = 0.60,
        # Risk parameters
        sl_atr_multiplier: float = 2.0,
        tp_atr_multiplier: float = 3.0,
    ):
        self.min_gec_score = min_gec_score
        self.min_combined_score = min_combined_score
        self.sl_atr_multiplier = sl_atr_multiplier
        self.tp_atr_multiplier = tp_atr_multiplier

        self.gec = GoldEdgeComposite(
            momentum_weight=momentum_weight,
            trend_weight=trend_weight,
            volatility_weight=volatility_weight,
            dxy_correlation_weight=dxy_correlation_weight,
        )
        self.atr_border_grid = ATRBorderGrid(
            ema_period=ema_period,
            atr_period=atr_period,
            multipliers=atr_multipliers,
        )
        self.atr_filter = ATRRatioFilter(
            atr_period=atr_period,
            sma_period=atr_sma_period,
            ratio_min=atr_ratio_min,
            ratio_max=atr_ratio_max,
        )

    def _compute_border_score(
        self, border_result: ATRBorderResult, direction: str
    ) -> float:
        """
        Score the border position: higher score when price is in a
        favourable border zone for the given direction.
        """
        if direction == "LONG":
            # Lower layer + lower price position = better entry
            layer = border_result.current_layer
            pos = border_result.price_position_pct
            if layer >= 2 and pos < 0.3:
                return 1.0
            elif layer >= 1 and pos < 0.4:
                return 0.8
            elif layer >= 1 and pos < 0.5:
                return 0.6
            elif layer == 0:
                return 0.4  # too close to midline
            return 0.2
        elif direction == "SHORT":
            layer = border_result.current_layer
            pos = border_result.price_position_pct
            if layer >= 2 and pos > 0.7:
                return 1.0
            elif layer >= 1 and pos > 0.6:
                return 0.8
            elif layer >= 1 and pos > 0.5:
                return 0.6
            elif layer == 0:
                return 0.4
            return 0.2
        return 0.3

    def _compute_filter_score(self, filter_result: ATRFilterResult) -> float:
        """Map filter zone to a score."""
        mapping = {
            "ideal": 1.0,
            "quiet": 0.5,
            "volatile": 0.6,
            "extreme": 0.0,
            "unknown": 0.2,
        }
        return mapping.get(filter_result.zone, 0.2)

    def _calculate_levels(
        self, price: float, atr: float, direction: str
    ) -> Dict[str, float]:
        """Calculate entry, SL, TP levels based on ATR."""
        if direction == "LONG":
            sl = price - self.sl_atr_multiplier * atr
            tp = price + self.tp_atr_multiplier * atr
        elif direction == "SHORT":
            sl = price + self.sl_atr_multiplier * atr
            tp = price - self.tp_atr_multiplier * atr
        else:
            return {"entry": price, "sl": 0, "tp": 0, "rr": 0}

        sl_dist = abs(price - sl)
        tp_dist = abs(tp - price)
        rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0

        return {"entry": price, "sl": sl, "tp": tp, "rr": rr}

    def evaluate(
        self,
        ohlcv_df: pd.DataFrame,
        dxy_series: Optional[pd.Series] = None,
        price_override: Optional[float] = None,
    ) -> GoldEdgeMatrixResult:
        """
        Run the full Gold Edge entry matrix.

        Args:
            ohlcv_df: OHLCV DataFrame.
            dxy_series: optional DXY series.
            price_override: override current price.

        Returns:
            GoldEdgeMatrixResult with decision and all sub-results.
        """
        result = GoldEdgeMatrixResult()
        rejection_reasons = []

        # --- Step 1: GEC ---
        gec_result = self.gec.calculate(ohlcv_df, dxy_series)
        result.gec = gec_result
        result.gec_score = abs(gec_result.composite_score)
        result.direction = gec_result.direction

        if gec_result.direction == "NEUTRAL":
            rejection_reasons.append("GEC direction is NEUTRAL")
        if abs(gec_result.composite_score) < self.min_gec_score:
            rejection_reasons.append(
                f"GEC score {abs(gec_result.composite_score):.3f} < min {self.min_gec_score}"
            )

        # --- Step 2: ATR borders ---
        border_result = self.atr_border_grid.calculate(ohlcv_df)
        result.atr_border = border_result
        border_score = self._compute_border_score(border_result, gec_result.direction)
        result.border_score = border_score

        # --- Step 3: ATR filter ---
        filter_result = self.atr_filter.calculate(ohlcv_df)
        result.atr_filter = filter_result
        filter_score = self._compute_filter_score(filter_result)
        result.filter_score = filter_score

        adjustment = self.atr_filter.get_entry_adjustment(filter_result)
        if not adjustment["allow_entry"]:
            rejection_reasons.append(f"ATR filter: {adjustment['reason']}")

        # --- Step 4: Combined matrix score ---
        combined = (
            0.50 * result.gec_score
            + 0.30 * border_score
            + 0.20 * filter_score
        )
        result.combined_score = round(combined, 4)
        result.confidence = round(combined * 100, 2)

        if combined < self.min_combined_score:
            rejection_reasons.append(
                f"Combined score {combined:.3f} < min {self.min_combined_score}"
            )

        # --- Step 5: Determine action ---
        result.rejection_reasons = rejection_reasons

        current_price = price_override or (
            float(ohlcv_df["close"].iloc[-1]) if ohlcv_df is not None and len(ohlcv_df) > 0 else 0
        )
        atr = border_result.atr_value if border_result else 0

        if (
            gec_result.direction != "NEUTRAL"
            and combined >= self.min_combined_score
            and adjustment["allow_entry"]
        ):
            result.action = "ENTRY"
            levels = self._calculate_levels(current_price, atr, gec_result.direction)
            result.entry_price = levels["entry"]
            result.stop_loss = levels["sl"]
            result.take_profit = levels["tp"]
            result.risk_reward_ratio = levels["rr"]
        elif (
            gec_result.direction != "NEUTRAL"
            and combined >= self.min_combined_score * 0.8
        ):
            result.action = "WATCH"
        else:
            result.action = "NO_TRADE"

        return result
