"""
Multi-timeframe confluence engine.
Aggregates signals across M5, M15, M30, H1, H2, H4 into a single directional score.
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger("strategies.confluence")


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


@dataclass
class TimeframeSignal:
    timeframe: str
    signal_type: str
    strength: Decimal
    indicators: Dict[str, Any] = field(default_factory=dict)
    stop_loss_pips: int = 50
    take_profit_pips: int = 100


@dataclass
class ConfluenceResult:
    symbol: str
    timeframe_scores: Dict[str, float] = field(default_factory=dict)
    total_score: Decimal = Decimal("0")
    direction: Direction = Direction.NEUTRAL
    higher_tf_agreement: bool = False
    all_tf_aligned: bool = False
    risk_reward_ratio: float = 0.0
    confidence: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


TIMEFRAME_WEIGHTS = {
    "M5": 0.10,
    "M15": 0.15,
    "M30": 0.20,
    "H1": 0.25,
    "H2": 0.15,
    "H4": 0.15,
}

HIGHER_TF = {"H2", "H4"}
MID_TF = {"H1", "M30"}
LOWER_TF = {"M5", "M15"}


class ConfluenceEngine:
    def __init__(self, min_score: float = 55.0, min_agreement_pct: float = 0.6):
        self.min_score = min_score
        self.min_agreement_pct = min_agreement_pct

    def calculate_confluence(
        self, symbol: str, timeframe_signals: Dict[str, TimeframeSignal]
    ) -> ConfluenceResult:
        result = ConfluenceResult(symbol=symbol)

        if not timeframe_signals:
            return result

        long_score = 0.0
        short_score = 0.0
        total_weight = 0.0

        for tf, ts in timeframe_signals.items():
            weight = TIMEFRAME_WEIGHTS.get(tf, 0.1)
            strength = float(ts.strength)

            if ts.signal_type in ("BUY", "STRONG_BUY"):
                score = strength * weight
                long_score += score
                result.timeframe_scores[tf] = score
            elif ts.signal_type in ("SELL", "STRONG_SELL"):
                score = strength * weight
                short_score += score
                result.timeframe_scores[tf] = -score
            else:
                result.timeframe_scores[tf] = 0.0

            total_weight += weight

        if total_weight > 0:
            long_score = (long_score / total_weight) * 100
            short_score = (short_score / total_weight) * 100

        # Determine direction
        if long_score > short_score and long_score > 0:
            result.direction = Direction.LONG
            result.total_score = Decimal(str(round(long_score, 2)))
        elif short_score > long_score and short_score > 0:
            result.direction = Direction.SHORT
            result.total_score = Decimal(str(round(short_score, 2)))
        else:
            result.direction = Direction.NEUTRAL
            result.total_score = Decimal("0")

        # Check alignment
        long_tfs = set()
        short_tfs = set()
        neutral_tfs = set()

        for tf, ts in timeframe_signals.items():
            if ts.signal_type in ("BUY", "STRONG_BUY"):
                long_tfs.add(tf)
            elif ts.signal_type in ("SELL", "STRONG_SELL"):
                short_tfs.add(tf)
            else:
                neutral_tfs.add(tf)

        # Higher TF agreement
        higher_long = long_tfs & HIGHER_TF
        higher_short = short_tfs & HIGHER_TF
        result.higher_tf_agreement = len(higher_long) >= 1 or len(higher_short) >= 1

        # All aligned
        aligned_long = long_tfs >= HIGHER_TF | MID_TF
        aligned_short = short_tfs >= HIGHER_TF | MID_TF
        result.all_tf_aligned = aligned_long or aligned_short

        # Risk-reward ratio
        sl_pips = max(ts.stop_loss_pips for ts in timeframe_signals.values()) if timeframe_signals else 50
        tp_pips = max(ts.take_profit_pips for ts in timeframe_signals.values()) if timeframe_signals else 100
        result.risk_reward_ratio = round(tp_pips / sl_pips, 2) if sl_pips > 0 else 0

        # Confidence
        aligned_count = len(long_tfs | short_tfs)
        total_tfs = len(timeframe_signals)
        agreement_pct = aligned_count / total_tfs if total_tfs > 0 else 0
        result.confidence = round(
            float(result.total_score) * 0.7 + agreement_pct * 30, 2
        )

        result.details = {
            "long_score": round(long_score, 2),
            "short_score": round(short_score, 2),
            "long_timeframes": sorted(long_tfs),
            "short_timeframes": sorted(short_tfs),
            "neutral_timeframes": sorted(neutral_tfs),
            "total_tfs": total_tfs,
        }

        logger.info(
            "Confluence %s: %s score=%.2f confidence=%.1f%% aligned=%s",
            symbol, result.direction.value, float(result.total_score),
            result.confidence, result.all_tf_aligned,
        )

        return result

    def should_trade(self, result: ConfluenceResult) -> bool:
        if result.direction == Direction.NEUTRAL:
            return False
        if float(result.total_score) < self.min_score:
            return False
        if not result.higher_tf_agreement:
            return False
        return True


confluence_engine = ConfluenceEngine()
