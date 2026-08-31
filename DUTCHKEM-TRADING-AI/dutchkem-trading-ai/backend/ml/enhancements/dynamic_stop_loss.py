"""
DYNAMIC STOP-LOSS MANAGEMENT ENGINE
V6.5 Enhancement #6
"""

import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("ml.enhancements.dynamic_sl")


class DynamicStopLoss:
    """
    Adaptive stop-loss management using multiple methods.
    """

    def __init__(self):
        self.default_stop_distance = 0.001
        self.max_stop_distance = 0.005
        self.min_stop_distance = 0.0003

    def calculate_optimal_stop(self, symbol: str, entry_price: float, direction: str, data: Dict) -> Dict:
        try:
            stops = {}
            for name, fn in [("ATR", self.atr_stop), ("VOLATILITY", self.volatility_stop),
                             ("SUPPORT", self.support_stop), ("CHANDELIER", self.chandelier_stop)]:
                result = fn(entry_price, direction, data)
                if result is not None:
                    stops[name] = result

            best = self._select_best(stops, direction)
            dist = abs(best - entry_price)
            method = self._get_method(stops, best)
            return {
                "stop_loss": best, "distance": dist, "distance_pips": dist * 10000,
                "method": method, "alternative_stops": stops, "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error("Optimal stop failed: %s", e)
            sl = entry_price - self.default_stop_distance if direction == "BUY" else entry_price + self.default_stop_distance
            return {"stop_loss": sl, "distance": self.default_stop_distance, "distance_pips": self.default_stop_distance * 10000, "method": "DEFAULT"}

    def atr_stop(self, entry_price: float, direction: str, data: Dict) -> Optional[float]:
        try:
            atr = data.get("atr", 0.001)
            mult = data.get("atr_multiplier", 2.0)
            dist = atr * mult
            return entry_price - dist if direction == "BUY" else entry_price + dist
        except Exception:
            return None

    def volatility_stop(self, entry_price: float, direction: str, data: Dict) -> Optional[float]:
        try:
            vol = data.get("volatility_ratio", 1.0)
            dist = max(self.min_stop_distance, min(self.max_stop_distance, 0.001 * vol))
            return entry_price - dist if direction == "BUY" else entry_price + dist
        except Exception:
            return None

    def support_stop(self, entry_price: float, direction: str, data: Dict) -> Optional[float]:
        try:
            if direction == "BUY":
                zones = [z for z in data.get("support_zones", []) if z < entry_price]
                return max(zones) if zones else entry_price - self.default_stop_distance
            else:
                zones = [z for z in data.get("resistance_zones", []) if z > entry_price]
                return min(zones) if zones else entry_price + self.default_stop_distance
        except Exception:
            return None

    def chandelier_stop(self, entry_price: float, direction: str, data: Dict) -> Optional[float]:
        try:
            atr = data.get("atr", 0.001)
            if direction == "BUY":
                return data.get("highest_price", entry_price) - atr * 3
            return data.get("lowest_price", entry_price) + atr * 3
        except Exception:
            return None

    def update_trailing_stop(self, position: Dict, current_price: float) -> Dict:
        try:
            entry = position["entry_price"]
            direction = position["direction"]
            current_stop = position["stop_loss"]

            if direction == "BUY":
                profit_pips = (current_price - entry) * 10000
                if profit_pips < 5:
                    return {"stop_loss": current_stop, "action": "NO_CHANGE"}
                trail = 0.0005 if profit_pips < 10 else (0.0010 if profit_pips < 20 else (0.0015 if profit_pips < 50 else 0.0020))
                new_stop = current_price - trail
                if new_stop > current_stop:
                    return {"stop_loss": new_stop, "action": "TRAILED_UP", "distance_pips": trail * 10000}
            else:
                profit_pips = (entry - current_price) * 10000
                if profit_pips < 5:
                    return {"stop_loss": current_stop, "action": "NO_CHANGE"}
                trail = 0.0005 if profit_pips < 10 else (0.0010 if profit_pips < 20 else (0.0015 if profit_pips < 50 else 0.0020))
                new_stop = current_price + trail
                if new_stop < current_stop:
                    return {"stop_loss": new_stop, "action": "TRAILED_DOWN", "distance_pips": trail * 10000}

            return {"stop_loss": current_stop, "action": "NO_CHANGE"}
        except Exception as e:
            logger.error("Trailing stop failed: %s", e)
            return {"stop_loss": position.get("stop_loss", 0), "action": "ERROR"}

    def _select_best(self, stops: Dict, direction: str) -> float:
        valid = list(stops.values())
        if not valid:
            return self.default_stop_distance
        return max(valid) if direction == "BUY" else min(valid)

    def _get_method(self, stops: Dict, selected: float) -> str:
        for name, val in stops.items():
            if val == selected:
                return name
        return "DEFAULT"
