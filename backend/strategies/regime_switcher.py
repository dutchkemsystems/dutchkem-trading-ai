import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("strategies.regime_switcher")


class MarketRegime:
    STRONG_TRENDING = "trending_strong"
    WEAK_TRENDING = "trending_weak"
    RANGING = "ranging"
    VOLATILE = "volatile"
    NEWS = "news"
    LOW_LIQUIDITY = "low_liquidity"


class StrategyType:
    TREND_FOLLOWING = "trend_following"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    PAUSE = "pause"


REGIME_STRATEGY_MAP = {
    MarketRegime.STRONG_TRENDING: {
        "strategy": StrategyType.TREND_FOLLOWING,
        "timeframe": "H1",
        "risk_multiplier": 1.0,
        "sl_method": "atr_wide",
        "tp_method": "trail",
        "description": "Full risk, wider stops, ride the trend",
    },
    MarketRegime.WEAK_TRENDING: {
        "strategy": StrategyType.MOMENTUM,
        "timeframe": "M30",
        "risk_multiplier": 0.8,
        "sl_method": "atr_medium",
        "tp_method": "fixed_2r",
        "description": "Reduced risk, tighter stops, quick profits",
    },
    MarketRegime.RANGING: {
        "strategy": StrategyType.MEAN_REVERSION,
        "timeframe": "M5",
        "risk_multiplier": 0.7,
        "sl_method": "bb_band",
        "tp_method": "bb_middle",
        "description": "Lowest risk, Bollinger bounces, quick scalps",
    },
    MarketRegime.VOLATILE: {
        "strategy": StrategyType.BREAKOUT,
        "timeframe": "M15",
        "risk_multiplier": 0.5,
        "sl_method": "atr_wide",
        "tp_method": "trail_wide",
        "description": "Half risk, larger stops, smaller positions",
    },
    MarketRegime.NEWS: {
        "strategy": StrategyType.PAUSE,
        "timeframe": None,
        "risk_multiplier": 0.0,
        "sl_method": None,
        "tp_method": None,
        "description": "No trading during news events",
    },
    MarketRegime.LOW_LIQUIDITY: {
        "strategy": StrategyType.SCALPING,
        "timeframe": "M5",
        "risk_multiplier": 0.3,
        "sl_method": "tight",
        "tp_method": "quick",
        "description": "Minimal risk, reduce size, quick exits",
    },
}


class RegimeSwitcher:
    """
    Detects current market regime and selects optimal strategy.
    Adjusts parameters dynamically based on regime changes.
    """

    def __init__(self, use_ml: bool = True, confidence_threshold: float = 0.6):
        self.use_ml = use_ml
        self.confidence_threshold = confidence_threshold
        self._current_regime = MarketRegime.WEAK_TRENDING
        self._regime_history: List[Dict[str, Any]] = []
        self._ml_pipeline = None

    @property
    def current_regime(self) -> str:
        return self._current_regime

    @property
    def current_strategy(self) -> Dict[str, Any]:
        return REGIME_STRATEGY_MAP.get(self._current_regime, REGIME_STRATEGY_MAP[MarketRegime.WEAK_TRENDING])

    def detect_regime(
        self, df: pd.DataFrame, ml_prediction: Optional[Dict] = None
    ) -> Dict[str, Any]:
        if ml_prediction and self.use_ml:
            return self._detect_from_ml(ml_prediction)
        return self._detect_from_indicators(df)

    def _detect_from_ml(self, ml_prediction: Dict) -> Dict[str, Any]:
        regime = ml_prediction.get("regime", "unknown")
        confidence = ml_prediction.get("confidence", 0.0)
        is_confident = ml_prediction.get("is_confident", False)

        if is_confident and confidence >= self.confidence_threshold:
            old_regime = self._current_regime
            self._current_regime = regime
            strategy_config = REGIME_STRATEGY_MAP.get(regime, REGIME_STRATEGY_MAP[MarketRegime.WEAK_TRENDING])

            if old_regime != regime:
                self._log_regime_change(old_regime, regime, confidence)

            return {
                "regime": regime,
                "confidence": confidence,
                "strategy": strategy_config["strategy"],
                "config": strategy_config,
                "source": "ml",
                "regime_changed": old_regime != regime,
            }

        return {
            "regime": self._current_regime,
            "confidence": confidence,
            "strategy": self.current_strategy["strategy"],
            "config": self.current_strategy,
            "source": "ml_low_confidence",
            "regime_changed": False,
            "note": "Low ML confidence, maintaining current regime",
        }

    def _detect_from_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        adx = self._get_indicator(df, "adx_14", 14)
        atr_norm = self._get_indicator(df, "atr_normalized_14", 14)
        bb_width = self._get_indicator(df, "bb_width_20", 20)
        volume_ratio = self._get_indicator(df, "volume_ratio", 1)
        spread_ratio = self._get_indicator(df, "spread_ratio", 1)

        bb_width_avg = bb_width.rolling(20).mean().iloc[-1] if len(bb_width) >= 20 else 1.0
        atr_avg = atr_norm.rolling(20).mean().iloc[-1] if len(atr_norm) >= 20 else 1.0

        regime = MarketRegime.WEAK_TRENDING
        confidence = 0.6

        if spread_ratio.iloc[-1] > 3.0 or volume_ratio.iloc[-1] < 0.5:
            regime = MarketRegime.LOW_LIQUIDITY
            confidence = 0.85
        elif atr_norm.iloc[-1] > atr_avg * 1.5 and bb_width.iloc[-1] > bb_width_avg * 2.0:
            regime = MarketRegime.VOLATILE
            confidence = 0.8
        elif adx.iloc[-1] > 30:
            regime = MarketRegime.STRONG_TRENDING
            confidence = 0.85
        elif 20 <= adx.iloc[-1] <= 30:
            regime = MarketRegime.WEAK_TRENDING
            confidence = 0.75
        elif adx.iloc[-1] < 20 and bb_width.iloc[-1] < bb_width_avg * 0.8:
            regime = MarketRegime.RANGING
            confidence = 0.8

        old_regime = self._current_regime
        self._current_regime = regime
        strategy_config = REGIME_STRATEGY_MAP.get(regime, REGIME_STRATEGY_MAP[MarketRegime.WEAK_TRENDING])

        if old_regime != regime:
            self._log_regime_change(old_regime, regime, confidence)

        return {
            "regime": regime,
            "confidence": confidence,
            "strategy": strategy_config["strategy"],
            "config": strategy_config,
            "source": "indicators",
            "regime_changed": old_regime != regime,
            "indicators": {
                "adx": float(adx.iloc[-1]),
                "atr_normalized": float(atr_norm.iloc[-1]),
                "bb_width": float(bb_width.iloc[-1]),
                "volume_ratio": float(volume_ratio.iloc[-1]),
                "spread_ratio": float(spread_ratio.iloc[-1]),
            },
        }

    def get_adjusted_parameters(
        self, base_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        config = self.current_strategy
        risk_mult = config["risk_multiplier"]

        adjusted = base_params.copy()
        adjusted["risk_per_trade"] = base_params.get("risk_per_trade", 1.0) * risk_mult
        adjusted["strategy"] = config["strategy"]
        adjusted["timeframe"] = config["timeframe"]
        adjusted["sl_method"] = config["sl_method"]
        adjusted["tp_method"] = config["tp_method"]
        adjusted["risk_multiplier"] = risk_mult

        if config["strategy"] == StrategyType.PAUSE:
            adjusted["allow_trading"] = False
        else:
            adjusted["allow_trading"] = True

        return adjusted

    def calculate_stop_loss(
        self,
        entry_price: float,
        position_type: str,
        atr_value: float,
        bb_lower: float = 0,
        bb_upper: float = 0,
    ) -> float:
        config = self.current_strategy
        method = config.get("sl_method", "atr_medium")

        if method == "atr_wide":
            distance = atr_value * 2.0
        elif method == "atr_medium":
            distance = atr_value * 1.5
        elif method == "tight":
            distance = atr_value * 0.8
        elif method == "bb_band":
            if position_type == "BUY":
                return bb_lower
            else:
                return bb_upper
        else:
            distance = atr_value * 1.5

        if position_type == "BUY":
            return entry_price - distance
        else:
            return entry_price + distance

    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        position_type: str,
        atr_value: float = 0,
    ) -> float:
        config = self.current_strategy
        method = config.get("tp_method", "fixed_2r")

        risk = abs(entry_price - stop_loss)

        if method == "fixed_2r":
            tp_distance = risk * 2.0
        elif method == "trail":
            tp_distance = risk * 3.0
        elif method == "trail_wide":
            tp_distance = risk * 2.5
        elif method == "quick":
            tp_distance = risk * 1.5
        elif method == "bb_middle":
            tp_distance = risk * 1.8
        else:
            tp_distance = risk * 2.0

        if position_type == "BUY":
            return entry_price + tp_distance
        else:
            return entry_price - tp_distance

    def get_regime_history(self) -> List[Dict[str, Any]]:
        return self._regime_history.copy()

    def _get_indicator(self, df: pd.DataFrame, col: str, default: float) -> pd.Series:
        if col in df.columns:
            return df[col]
        return pd.Series(default, index=df.index)

    def _log_regime_change(self, old_regime: str, new_regime: str, confidence: float):
        entry = {
            "timestamp": time.time(),
            "old_regime": old_regime,
            "new_regime": new_regime,
            "confidence": confidence,
            "strategy": REGIME_STRATEGY_MAP.get(new_regime, {}).get("strategy", "unknown"),
        }
        self._regime_history.append(entry)
        if len(self._regime_history) > 1000:
            self._regime_history = self._regime_history[-500:]
        logger.info(
            "Regime change: %s → %s (confidence=%.2f, strategy=%s)",
            old_regime, new_regime, confidence, entry["strategy"],
        )


class StrategyMap:
    """
    Maps regimes to concrete strategy configurations.
    """

    def __init__(self):
        self._strategies = REGIME_STRATEGY_MAP

    def get_strategy(self, regime: str) -> Dict[str, Any]:
        return self._strategies.get(regime, self._strategies[MarketRegime.WEAK_TRENDING])

    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        return self._strategies.copy()

    def get_risk_multiplier(self, regime: str) -> float:
        return self._strategies.get(regime, {}).get("risk_multiplier", 0.8)

    def get_timeframe(self, regime: str) -> Optional[str]:
        return self._strategies.get(regime, {}).get("timeframe", "M30")

    def should_trade(self, regime: str) -> bool:
        config = self._strategies.get(regime, {})
        return config.get("strategy") != StrategyType.PAUSE


regime_switcher = RegimeSwitcher()
strategy_map = StrategyMap()
