"""
Timeframe-specific trading strategies.
Each timeframe has its own optimal indicator combination and signal logic.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("strategies.timeframe_strategies")


def _sma(values: List[float], period: int) -> float:
    if len(values) < period:
        return values[-1] if values else 0
    return sum(values[-period:]) / period


def _ema(values: List[float], period: int) -> float:
    if not values:
        return 0
    if len(values) < period:
        return values[-1]
    multiplier = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for val in values[period:]:
        ema = (val - ema) * multiplier + ema
    return ema


def _rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    if len(closes) < 2:
        return 0.0001
    trs = []
    for i in range(1, len(closes)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < period:
        return sum(trs) / len(trs) if trs else 0.0001
    return sum(trs[-period:]) / period


def _bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2.0):
    if len(closes) < period:
        mid = closes[-1] if closes else 0
        return mid, mid, mid
    window = closes[-period:]
    mid = sum(window) / period
    variance = sum((x - mid) ** 2 for x in window) / period
    std = variance ** 0.5
    return mid - std_dev * std, mid, mid + std_dev * std


def _macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9):
    if len(closes) < slow:
        return 0, 0, 0
    fast_ema = _ema(closes, fast)
    slow_ema = _ema(closes, slow)
    macd_line = fast_ema - slow_ema
    signal_line = macd_line * 0.5
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# ---------------------------------------------------------------------------
# Timeframe strategies
# ---------------------------------------------------------------------------

TIMEFRAME_STRATEGIES = {
    "M5": {
        "name": "Scalping",
        "indicators": ["rsi", "ema_fast", "ema_slow", "stochastic"],
        "rsi_period": 7,
        "rsi_oversold": 25,
        "rsi_overbought": 75,
        "ema_fast": 5,
        "ema_slow": 13,
        "stop_loss_pips": 8,
        "take_profit_pips": 12,
        "min_strength": 65,
    },
    "M15": {
        "name": "Short-term Momentum",
        "indicators": ["rsi", "macd", "ema_cross", "bollinger"],
        "rsi_period": 10,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "ema_fast": 8,
        "ema_slow": 21,
        "stop_loss_pips": 15,
        "take_profit_pips": 25,
        "min_strength": 60,
    },
    "M30": {
        "name": "Intraday Momentum",
        "indicators": ["rsi", "macd", "ema_cross", "bollinger", "volume"],
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "ema_fast": 10,
        "ema_slow": 26,
        "stop_loss_pips": 20,
        "take_profit_pips": 40,
        "min_strength": 55,
    },
    "H1": {
        "name": "Swing Entry",
        "indicators": ["rsi", "macd", "ema_cross", "bollinger", "adx"],
        "rsi_period": 14,
        "rsi_oversold": 35,
        "rsi_overbought": 65,
        "ema_fast": 12,
        "ema_slow": 26,
        "stop_loss_pips": 30,
        "take_profit_pips": 60,
        "min_strength": 55,
    },
    "H2": {
        "name": "Intermediate Swing",
        "indicators": ["rsi", "macd", "ema_cross", "adx", "atr"],
        "rsi_period": 14,
        "rsi_oversold": 35,
        "rsi_overbought": 65,
        "ema_fast": 20,
        "ema_slow": 50,
        "stop_loss_pips": 40,
        "take_profit_pips": 80,
        "min_strength": 55,
    },
    "H4": {
        "name": "Trend Following",
        "indicators": ["rsi", "macd", "ema_cross", "adx", "bollinger"],
        "rsi_period": 14,
        "rsi_oversold": 35,
        "rsi_overbought": 65,
        "ema_fast": 20,
        "ema_slow": 50,
        "stop_loss_pips": 50,
        "take_profit_pips": 100,
        "min_strength": 50,
    },
}


def calculate_signal(timeframe: str, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate a trading signal for a given timeframe using OHLCV data.

    Returns a dict with:
        signal: BUY | SELL | NEUTRAL
        strength: 0-100 confidence score
        indicators: dict of individual indicator values
        stop_loss_pips: recommended SL distance
        take_profit_pips: recommended TP distance
    """
    config = TIMEFRAME_STRATEGIES.get(timeframe, TIMEFRAME_STRATEGIES["H1"])

    opens = ohlcv_data.get("open", [])
    highs = ohlcv_data.get("high", [])
    lows = ohlcv_data.get("low", [])
    closes = ohlcv_data.get("close", [])
    volumes = ohlcv_data.get("volume", [])

    if not closes or len(closes) < 5:
        return {
            "signal": "NEUTRAL",
            "strength": 0,
            "indicators": {},
            "stop_loss_pips": config["stop_loss_pips"],
            "take_profit_pips": config["take_profit_pips"],
        }

    rsi = _rsi(closes, config.get("rsi_period", 14))
    ema_fast = _ema(closes, config.get("ema_fast", 12))
    ema_slow = _ema(closes, config.get("ema_slow", 26))
    macd_line, signal_line, histogram = _macd(closes)
    bb_lower, bb_mid, bb_upper = _bollinger_bands(closes)
    atr = _atr(highs, lows, closes)

    current_price = closes[-1]
    indicators = {
        "rsi": round(rsi, 2),
        "ema_fast": round(ema_fast, 6),
        "ema_slow": round(ema_slow, 6),
        "macd": round(macd_line, 6),
        "macd_signal": round(signal_line, 6),
        "macd_histogram": round(histogram, 6),
        "bb_lower": round(bb_lower, 6),
        "bb_mid": round(bb_mid, 6),
        "bb_upper": round(bb_upper, 6),
        "atr": round(atr, 6),
        "current_price": round(current_price, 6),
    }

    buy_score = 0
    sell_score = 0
    total_weight = 0

    # RSI
    rsi_oversold = config.get("rsi_oversold", 30)
    rsi_overbought = config.get("rsi_overbought", 70)
    if rsi < rsi_oversold:
        buy_score += 25
    elif rsi > rsi_overbought:
        sell_score += 25
    elif rsi < 45:
        buy_score += 10
    elif rsi > 55:
        sell_score += 10
    total_weight += 25

    # EMA Cross
    if ema_fast > ema_slow:
        buy_score += 25
    else:
        sell_score += 25
    total_weight += 25

    # MACD
    if histogram > 0:
        buy_score += 20
    else:
        sell_score += 20
    total_weight += 20

    # Bollinger Bands
    if current_price < bb_lower:
        buy_score += 15
    elif current_price > bb_upper:
        sell_score += 15
    total_weight += 15

    # Price position in BB
    bb_range = bb_upper - bb_lower
    if bb_range > 0:
        bb_pct = (current_price - bb_lower) / bb_range
        if bb_pct < 0.3:
            buy_score += 5
        elif bb_pct > 0.7:
            sell_score += 5
    total_weight += 5

    if total_weight > 0:
        buy_pct = (buy_score / total_weight) * 100
        sell_pct = (sell_score / total_weight) * 100
    else:
        buy_pct = 0
        sell_pct = 0

    min_strength = config.get("min_strength", 55)

    if buy_pct > sell_pct and buy_pct >= min_strength:
        signal = "BUY"
        strength = min(buy_pct, 100)
    elif sell_pct > buy_pct and sell_pct >= min_strength:
        signal = "SELL"
        strength = min(sell_pct, 100)
    else:
        signal = "NEUTRAL"
        strength = max(buy_pct, sell_pct)

    return {
        "signal": signal,
        "strength": round(strength, 2),
        "indicators": indicators,
        "stop_loss_pips": config["stop_loss_pips"],
        "take_profit_pips": config["take_profit_pips"],
    }
