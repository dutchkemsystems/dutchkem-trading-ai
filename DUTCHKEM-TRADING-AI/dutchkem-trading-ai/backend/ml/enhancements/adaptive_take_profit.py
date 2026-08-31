"""
ADAPTIVE TAKE-PROFIT ENGINE
V6.5 Enhancement #9
"""

import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger("ml.enhancements.adaptive_tp")


class AdaptiveTakeProfit:
    """
    Dynamic take-profit based on market conditions.
    """

    def __init__(self):
        self.tp_multipliers = {"M1": 1.0, "M5": 1.5, "M15": 2.0, "M30": 2.5, "H1": 3.0, "H4": 4.0, "D1": 6.0}
        self.default_rr = 2.0
        self.max_rr = 4.0
        self.min_rr = 1.0

    def calculate_take_profit(self, entry_price: float, direction: str, stop_loss: float, data: Dict) -> Dict:
        try:
            base_dist = abs(entry_price - stop_loss)
            tp_dist = base_dist * self.default_rr

            atr = data.get("atr", 0.001)
            if atr > 0.003:
                tp_dist *= 1.3
            elif atr > 0.002:
                tp_dist *= 1.1
            elif atr < 0.0005:
                tp_dist *= 0.7

            vol_ratio = data.get("volatility_ratio", 1.0)
            if vol_ratio > 1.5:
                tp_dist *= 1.2
            elif vol_ratio < 0.5:
                tp_dist *= 0.8

            trend_str = data.get("trend_strength", 0)
            if trend_str > 0.7:
                tp_dist *= 1.3
            elif trend_str < 0.3:
                tp_dist *= 0.7

            tf = data.get("timeframe", "M15")
            tp_dist *= self.tp_multipliers.get(tf, 1.5)

            regime = data.get("regime", "NORMAL")
            regime_mult = {"TRENDING": 1.4, "BREAKOUT": 1.3, "RANGING": 0.7, "VOLATILE": 0.8, "NORMAL": 1.0}
            tp_dist *= regime_mult.get(regime, 1.0)

            conf = data.get("confidence", 0.7)
            if conf > 0.85:
                tp_dist *= 1.2
            elif conf < 0.65:
                tp_dist *= 0.8

            tp_dist = max(self.min_rr * base_dist, min(self.max_rr * base_dist, tp_dist))

            if direction == "BUY":
                tp1, tp2, tp3 = entry_price + tp_dist, entry_price + tp_dist * 1.5, entry_price + tp_dist * 2.0
            else:
                tp1, tp2, tp3 = entry_price - tp_dist, entry_price - tp_dist * 1.5, entry_price - tp_dist * 2.0

            return {
                "tp1": round(tp1, 5), "tp2": round(tp2, 5), "tp3": round(tp3, 5),
                "distance": tp_dist, "distance_pips": tp_dist * 10000,
                "rr_ratio": tp_dist / base_dist if base_dist > 0 else self.default_rr,
                "method": "ADAPTIVE", "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error("TP calc failed: %s", e)
            dist = abs(entry_price - stop_loss) * 2
            sign = 1 if direction == "BUY" else -1
            return {
                "tp1": entry_price + sign * dist, "tp2": entry_price + sign * dist * 1.5,
                "tp3": entry_price + sign * dist * 2.0, "distance": dist,
                "distance_pips": dist * 10000, "rr_ratio": 2.0, "method": "DEFAULT",
            }

    def execute_partial_closes(self, position: Dict, tp_levels: Dict, current_price: float) -> Dict:
        try:
            direction = position["direction"]
            if direction == "BUY":
                if current_price >= tp_levels["tp3"]:
                    return {"action": "FULL_CLOSE", "close_percentage": 1.0, "tp_levels": tp_levels, "current_price": current_price}
                elif current_price >= tp_levels["tp2"]:
                    return {"action": "PARTIAL_CLOSE", "close_percentage": 0.30, "tp_levels": tp_levels, "current_price": current_price}
                elif current_price >= tp_levels["tp1"]:
                    return {"action": "PARTIAL_CLOSE", "close_percentage": 0.40, "tp_levels": tp_levels, "current_price": current_price}
            else:
                if current_price <= tp_levels["tp3"]:
                    return {"action": "FULL_CLOSE", "close_percentage": 1.0, "tp_levels": tp_levels, "current_price": current_price}
                elif current_price <= tp_levels["tp2"]:
                    return {"action": "PARTIAL_CLOSE", "close_percentage": 0.30, "tp_levels": tp_levels, "current_price": current_price}
                elif current_price <= tp_levels["tp1"]:
                    return {"action": "PARTIAL_CLOSE", "close_percentage": 0.40, "tp_levels": tp_levels, "current_price": current_price}
            return {"action": "NO_CHANGE", "close_percentage": 0, "tp_levels": tp_levels, "current_price": current_price}
        except Exception as e:
            logger.error("Partial close failed: %s", e)
            return {"action": "NO_CHANGE", "close_percentage": 0}
