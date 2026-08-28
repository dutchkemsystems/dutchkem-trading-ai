"""
Strategy mapping module.
Provides concrete strategy implementations for each market regime.
"""

from typing import Any, Dict, List, Optional

from .regime_switcher import (
    MarketRegime,
    StrategyType,
    REGIME_STRATEGY_MAP,
    regime_switcher,
    strategy_map,
)


class StrategyConfig:
    def __init__(
        self,
        name: str,
        strategy_type: str,
        timeframe: str,
        risk_multiplier: float,
        entry_rules: Dict[str, Any],
        exit_rules: Dict[str, Any],
        position_rules: Dict[str, Any],
    ):
        self.name = name
        self.strategy_type = strategy_type
        self.timeframe = timeframe
        self.risk_multiplier = risk_multiplier
        self.entry_rules = entry_rules
        self.exit_rules = exit_rules
        self.position_rules = position_rules


STRATEGY_CONFIGS = {
    StrategyType.TREND_FOLLOWING: StrategyConfig(
        name="Trend Following",
        strategy_type=StrategyType.TREND_FOLLOWING,
        timeframe="H1",
        risk_multiplier=1.0,
        entry_rules={
            "indicators": ["adx", "ema_cross", "ichimoku"],
            "adx_threshold": 30,
            "require_cloud_break": True,
            "require_ema_alignment": True,
        },
        exit_rules={
            "trailing_stop": True,
            "trailing_distance": "2x_atr",
            "breakeven_at": "1r",
            "partial_close_at": "3r",
            "partial_close_pct": 0.5,
        },
        position_rules={
            "max_positions": 3,
            "max_risk_per_trade": 1.0,
            "allow_scaling": True,
            "scale_in_at": "1r",
        },
    ),
    StrategyType.MOMENTUM: StrategyConfig(
        name="Momentum",
        strategy_type=StrategyType.MOMENTUM,
        timeframe="M30",
        risk_multiplier=0.8,
        entry_rules={
            "indicators": ["rsi", "macd", "stochastic"],
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "require_macd_cross": True,
        },
        exit_rules={
            "fixed_tp": True,
            "tp_distance": "2r",
            "sl_distance": "1.5x_atr",
            "time_exit_bars": 20,
        },
        position_rules={
            "max_positions": 2,
            "max_risk_per_trade": 0.8,
            "allow_scaling": False,
        },
    ),
    StrategyType.MEAN_REVERSION: StrategyConfig(
        name="Mean Reversion",
        strategy_type=StrategyType.MEAN_REVERSION,
        timeframe="M5",
        risk_multiplier=0.7,
        entry_rules={
            "indicators": ["bollinger_bands", "rsi", "stochastic"],
            "bb_entry": "touch_band",
            "rsi_confirm": True,
            "require_reversal_candle": True,
        },
        exit_rules={
            "tp_at_bb_middle": True,
            "sl_outside_band": True,
            "max_bars_in_trade": 10,
        },
        position_rules={
            "max_positions": 2,
            "max_risk_per_trade": 0.7,
            "allow_scaling": False,
        },
    ),
    StrategyType.BREAKOUT: StrategyConfig(
        name="Breakout",
        strategy_type=StrategyType.BREAKOUT,
        timeframe="M15",
        risk_multiplier=0.5,
        entry_rules={
            "indicators": ["atr", "bollinger_bands", "volume"],
            "require_volume_spike": True,
            "atr_filter": "expanding",
            "breakout_confirmation": "close_beyond",
        },
        exit_rules={
            "trailing_stop": True,
            "trailing_distance": "2.5x_atr",
            "breakeven_at": "1.5r",
        },
        position_rules={
            "max_positions": 1,
            "max_risk_per_trade": 0.5,
            "allow_scaling": False,
        },
    ),
    StrategyType.SCALPING: StrategyConfig(
        name="Scalping",
        strategy_type=StrategyType.SCALPING,
        timeframe="M5",
        risk_multiplier=0.3,
        entry_rules={
            "indicators": ["stochastic", "ema", "spread"],
            "max_spread_pips": 2,
            "require_ema_touch": True,
        },
        exit_rules={
            "fixed_tp_pips": 5,
            "fixed_sl_pips": 8,
            "max_bars_in_trade": 5,
        },
        position_rules={
            "max_positions": 1,
            "max_risk_per_trade": 0.3,
            "allow_scaling": False,
        },
    ),
    StrategyType.PAUSE: StrategyConfig(
        name="Pause",
        strategy_type=StrategyType.PAUSE,
        timeframe=None,
        risk_multiplier=0.0,
        entry_rules={},
        exit_rules={},
        position_rules={
            "max_positions": 0,
            "max_risk_per_trade": 0.0,
            "allow_scaling": False,
            "close_all": True,
        },
    ),
}


def get_strategy_config(strategy_type: str) -> StrategyConfig:
    return STRATEGY_CONFIGS.get(strategy_type, STRATEGY_CONFIGS[StrategyType.MOMENTUM])


def get_regime_entry_rules(regime: str) -> Dict[str, Any]:
    config = regime_switcher.get_strategy()
    strategy_type = config.get("strategy", StrategyType.MOMENTUM)
    return STRATEGY_CONFIGS.get(strategy_type, STRATEGY_CONFIGS[StrategyType.MOMENTUM]).entry_rules


def get_regime_exit_rules(regime: str) -> Dict[str, Any]:
    config = regime_switcher.get_strategy()
    strategy_type = config.get("strategy", StrategyType.MOMENTUM)
    return STRATEGY_CONFIGS.get(strategy_type, STRATEGY_CONFIGS[StrategyType.MOMENTUM]).exit_rules


def get_regime_position_rules(regime: str) -> Dict[str, Any]:
    config = regime_switcher.get_strategy()
    strategy_type = config.get("strategy", StrategyType.MOMENTUM)
    return STRATEGY_CONFIGS.get(strategy_type, STRATEGY_CONFIGS[StrategyType.MOMENTUM]).position_rules
