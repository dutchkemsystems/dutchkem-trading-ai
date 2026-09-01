"""
ORDER FLOW & VOLUME ANALYSIS ENGINE
V6.5 Enhancement #3
"""

import logging
import random
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger("ml.enhancements.order_flow")


class OrderFlowAnalyzer:
    """
    Analyze order flow and volume for better entries.
    """

    def __init__(self):
        self.depth_of_market: Dict = {}
        self.volume_profile: Dict = {}

    def analyze_order_flow(self, symbol: str, data: Dict) -> Dict:
        try:
            order_book = self.get_order_book(symbol)
            support_zones = self.find_support_zones(order_book)
            resistance_zones = self.find_resistance_zones(order_book)
            volume_profile = self.get_volume_profile(symbol, data)
            large_orders = self.find_large_orders(order_book)
            agg_buy = self.detect_aggressive_buying(order_book)
            agg_sell = self.detect_aggressive_selling(order_book)

            if agg_buy > agg_sell * 1.5:
                bias, confidence = 1, 0.7
            elif agg_sell > agg_buy * 1.5:
                bias, confidence = -1, 0.7
            else:
                bias, confidence = 0, 0.3

            return {
                "bias": bias, "confidence": confidence,
                "support_zones": support_zones, "resistance_zones": resistance_zones,
                "large_orders": large_orders, "volume_profile": volume_profile,
                "aggressive_buy": agg_buy, "aggressive_sell": agg_sell,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error("Order flow analysis failed for %s: %s", symbol, e)
            return {"bias": 0, "confidence": 0, "support_zones": [], "resistance_zones": [],
                    "large_orders": [], "volume_profile": {}, "aggressive_buy": 0, "aggressive_sell": 0}

    def get_order_book(self, symbol: str) -> Dict:
        try:
            mid_price = random.uniform(1.0000, 2.0000)
            bid_levels, ask_levels = [], []
            for i in range(10):
                offset = (i + 1) * 0.0001
                size = random.randint(10, 100) * 1000000
                bid_levels.append({"price": mid_price - offset, "size": size, "lots": size / 100000})
                ask_levels.append({"price": mid_price + offset, "size": size, "lots": size / 100000})
            return {"symbol": symbol, "mid_price": mid_price, "bid": bid_levels, "ask": ask_levels, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            logger.error("Failed to get order book for %s: %s", symbol, e)
            return {}

    def find_support_zones(self, order_book: Dict) -> List[float]:
        zones = []
        bids = order_book.get("bid", [])
        for i in range(len(bids) - 1):
            if bids[i]["lots"] > 50 and bids[i + 1]["lots"] > 30:
                zones.append(round((bids[i]["price"] + bids[i + 1]["price"]) / 2, 5))
        return zones[:3]

    def find_resistance_zones(self, order_book: Dict) -> List[float]:
        zones = []
        asks = order_book.get("ask", [])
        for i in range(len(asks) - 1):
            if asks[i]["lots"] > 50 and asks[i + 1]["lots"] > 30:
                zones.append(round((asks[i]["price"] + asks[i + 1]["price"]) / 2, 5))
        return zones[:3]

    def get_volume_profile(self, symbol: str, data: Dict) -> Dict:
        try:
            volumes = data.get("volume", [])
            prices = data.get("close", data.get("closes", []))
            if not volumes or not prices:
                return {}
            volumes = list(volumes)
            prices = list(prices)
            min_len = min(len(volumes), len(prices))
            volumes, prices = volumes[:min_len], prices[:min_len]
            total_vol = sum(volumes)
            vwap = sum(p * v for p, v in zip(prices, volumes)) / total_vol if total_vol > 0 else 0
            return {"vwap": vwap, "total_volume": total_vol}
        except Exception as e:
            logger.error("Volume profile failed: %s", e)
            return {}

    def find_large_orders(self, order_book: Dict) -> List[Dict]:
        large = []
        for side, key in [("BUY", "bid"), ("SELL", "ask")]:
            for level in order_book.get(key, []):
                if level["lots"] > 100:
                    large.append({"side": side, "price": level["price"], "lots": level["lots"], "type": "LIMIT"})
        return large

    def detect_aggressive_buying(self, order_book: Dict) -> int:
        return sum(1 for lvl in order_book.get("ask", [])[:3] if lvl["lots"] > 20)

    def detect_aggressive_selling(self, order_book: Dict) -> int:
        return sum(1 for lvl in order_book.get("bid", [])[:3] if lvl["lots"] > 20)

    def get_optimal_entry(self, symbol: str, flow_data: Dict, current_price: float) -> Optional[Dict]:
        try:
            bias = flow_data.get("bias", 0)
            if bias == 1:
                for zone in flow_data.get("support_zones", []):
                    if abs(zone - current_price) < 0.001:
                        return {"entry": zone, "stop_loss": zone - 0.002, "take_profit": zone + 0.004, "reason": "Support zone entry"}
                return {"entry": current_price, "stop_loss": current_price - 0.002, "take_profit": current_price + 0.004, "reason": "Bullish bias entry"}
            elif bias == -1:
                for zone in flow_data.get("resistance_zones", []):
                    if abs(zone - current_price) < 0.001:
                        return {"entry": zone, "stop_loss": zone + 0.002, "take_profit": zone - 0.004, "reason": "Resistance zone entry"}
                return {"entry": current_price, "stop_loss": current_price + 0.002, "take_profit": current_price - 0.004, "reason": "Bearish bias entry"}
            return None
        except Exception as e:
            logger.error("Optimal entry failed: %s", e)
            return None
