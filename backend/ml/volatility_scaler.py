import logging
import math
import threading
from typing import Any, Dict, List, Optional

import numpy as np
from django.conf import settings

logger = logging.getLogger("ml.volatility")


class VolatilityScaler:
    _instance: Optional["VolatilityScaler"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialised = False
        return cls._instance

    def __init__(self):
        if self._initialised:
            return
        self._initialised = True
        self._volatility_history: Dict[str, List[float]] = {}
        self._atr_cache: Dict[str, float] = {}
        logger.info("VolatilityScaler initialised")

    def calculate_atr(self, symbol: str, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            return 0.0

        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return 0.0

        atr = float(np.mean(true_ranges[-period:]))
        self._atr_cache[symbol] = atr
        return atr

    def calculate_realized_volatility(self, prices: List[float], window: int = 20) -> float:
        if len(prices) < window + 1:
            return 0.0

        returns = np.diff(np.array(prices[-window - 1:])) / np.array(prices[-window - 1:-1])
        returns = returns[~np.isnan(returns)]
        if len(returns) < 2:
            return 0.0

        return float(np.std(returns) * math.sqrt(252))

    def calculate_volatility_regime(self, symbol: str, prices: List[float], short_window: int = 10, long_window: int = 50) -> str:
        short_vol = self.calculate_realized_volatility(prices, short_window)
        long_vol = self.calculate_realized_volatility(prices, long_window)

        if long_vol == 0:
            return "normal"

        ratio = short_vol / long_vol
        if ratio > 1.5:
            return "high"
        elif ratio < 0.5:
            return "low"
        return "normal"

    def scale_position_size(self, base_size: float, symbol: str, prices: List[float], target_volatility: float = 0.15) -> float:
        current_vol = self.calculate_realized_volatility(prices)
        if current_vol <= 0:
            return base_size

        scale_factor = target_volatility / current_vol
        scale_factor = max(0.25, min(scale_factor, 2.0))
        return round(base_size * scale_factor, 4)

    def scale_stop_loss(self, base_sl_pips: int, symbol: str, prices: List[float]) -> int:
        current_vol = self.calculate_realized_volatility(prices)
        long_vol = self.calculate_realized_volatility(prices, 50) if len(prices) > 50 else current_vol

        if long_vol <= 0:
            return base_sl_pips

        ratio = current_vol / long_vol
        scaled = int(base_sl_pips * max(0.5, min(ratio, 2.0)))
        return max(scaled, 5)

    def get_volatility_metrics(self, symbol: str, prices: List[float]) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "realized_vol_10": self.calculate_realized_volatility(prices, 10),
            "realized_vol_20": self.calculate_realized_volatility(prices, 20),
            "realized_vol_50": self.calculate_realized_volatility(prices, 50),
            "regime": self.calculate_volatility_regime(symbol, prices),
            "current_price": prices[-1] if prices else 0.0,
        }

    def clear_cache(self) -> None:
        self._atr_cache.clear()
