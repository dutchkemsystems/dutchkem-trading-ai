"""
SMART NEWS TRADING ENGINE
V6.5 Enhancement #2
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("ml.enhancements.news_trading")


class SmartNewsTrading:
    """
    Advanced news trading with pre/post-event strategies.
    """

    def __init__(self):
        self.impact_threshold = 3.0
        self.pre_event_window = 15
        self.post_event_window = 30
        self.hmr_active = False
        self.news_calendar: List[Dict] = []
        self.high_impact_events = [
            "Non-Farm Payrolls", "CPI", "Federal Funds Rate", "FOMC Statement",
            "GDP", "Unemployment Rate", "ECB Rate Decision", "BOE Rate Decision",
            "Retail Sales", "PMI", "Inflation Rate",
        ]
        self.load_economic_calendar()

    def load_economic_calendar(self):
        now = datetime.now()
        self.news_calendar = [
            {
                "name": "Non-Farm Payrolls", "country": "US", "impact": "HIGH",
                "time": now + timedelta(days=5, hours=13, minutes=30),
                "forecast": 175000, "previous": 143000, "actual": None,
            },
            {
                "name": "CPI", "country": "US", "impact": "HIGH",
                "time": now + timedelta(days=3, hours=13, minutes=30),
                "forecast": 3.2, "previous": 3.0, "actual": None,
            },
            {
                "name": "Federal Funds Rate", "country": "US", "impact": "HIGH",
                "time": now + timedelta(days=7, hours=19, minutes=0),
                "forecast": 5.50, "previous": 5.50, "actual": None,
            },
        ]

    def get_news_strategy(self, symbol: str, current_time: datetime) -> Dict:
        self.load_economic_calendar()
        relevant = self._get_relevant_events(symbol, current_time)
        for event in relevant:
            mins_until = (event["time"] - current_time).total_seconds() / 60
            if 0 < mins_until <= self.pre_event_window:
                return {
                    "strategy": "PRE_EVENT", "action": "REDUCE_RISK",
                    "risk_multiplier": 0.5, "confidence_multiplier": 0.7,
                    "description": f"Reducing risk before {event['name']}", "event": event,
                }
            elif -self.post_event_window <= mins_until <= 0:
                return {
                    "strategy": "DURING_EVENT", "action": "WAIT",
                    "risk_multiplier": 0.0, "confidence_multiplier": 0.0,
                    "description": f"Waiting during {event['name']}", "event": event,
                }
            elif -mins_until <= self.post_event_window:
                return {
                    "strategy": "POST_EVENT", "action": "TREND_FOLLOW",
                    "risk_multiplier": 0.8, "confidence_multiplier": 1.1,
                    "description": f"Following trend after {event['name']}", "event": event,
                }
        return {
            "strategy": "NORMAL", "action": "TRADE_NORMAL",
            "risk_multiplier": 1.0, "confidence_multiplier": 1.0,
            "description": "No news event",
        }

    def execute_news_trade(self, symbol: str, event: Dict, price_data: Dict) -> Optional[Dict]:
        try:
            name = event.get("name", "")
            if "Non-Farm Payrolls" in name:
                return self._trade_nfp(symbol, event)
            elif "CPI" in name:
                return self._trade_cpi(symbol, event)
            elif "Rate Decision" in name or "Federal Funds Rate" in name:
                return self._trade_rate_decision(symbol, event)
            return {"action": "WAIT", "confidence": 0.5, "reason": f"Waiting after {name}", "type": "NEWS_WAIT"}
        except Exception as e:
            logger.error("News trade execution failed: %s", e)
            return None

    def _trade_nfp(self, symbol: str, event: Dict) -> Optional[Dict]:
        actual, forecast = event.get("actual"), event.get("forecast")
        if actual is None:
            return None
        surprise = actual - forecast
        if abs(surprise) < 10000:
            return None
        if symbol in ("EURUSD", "GBPUSD", "AUDUSD"):
            direction = "SELL" if surprise > 0 else "BUY"
        else:
            direction = "BUY" if surprise > 0 else "SELL"
        return {"action": direction, "confidence": min(0.9, abs(surprise) / 50000 + 0.5), "reason": f"NFP surprise: {surprise:+,}", "type": "NEWS"}

    def _trade_cpi(self, symbol: str, event: Dict) -> Optional[Dict]:
        actual, forecast = event.get("actual"), event.get("forecast")
        if actual is None:
            return None
        surprise = actual - forecast
        if symbol in ("EURUSD", "GBPUSD", "AUDUSD"):
            direction = "SELL" if surprise > 0 else "BUY"
        else:
            direction = "BUY" if surprise > 0 else "SELL"
        return {"action": direction, "confidence": min(0.85, abs(surprise) * 0.5 + 0.5), "reason": f"CPI surprise: {surprise:+.1f}%", "type": "NEWS"}

    def _trade_rate_decision(self, symbol: str, event: Dict) -> Optional[Dict]:
        actual, previous = event.get("actual"), event.get("previous")
        if actual is None:
            return None
        change = actual - previous
        if change == 0:
            return None
        if symbol in ("EURUSD", "GBPUSD", "AUDUSD"):
            direction = "SELL" if change > 0 else "BUY"
        else:
            direction = "BUY" if change > 0 else "SELL"
        return {"action": direction, "confidence": 0.8, "reason": f"Rate change: {change:+.2f}%", "type": "NEWS"}

    def check_hmr_active(self, current_time: datetime) -> bool:
        for event in self._get_upcoming_events(current_time):
            mins = (event["time"] - current_time).total_seconds() / 60
            if 0 < mins <= 15 or -1.5 <= mins <= 0:
                self.hmr_active = True
                return True
        self.hmr_active = False
        return False

    def _get_relevant_events(self, symbol: str, current_time: datetime) -> List[Dict]:
        country_map = {
            "EURUSD": ["US", "EU"], "GBPUSD": ["US", "UK"], "USDJPY": ["US", "JP"],
            "XAUUSD": ["US", "EU"], "BTCUSD": ["US", "EU"],
        }
        countries = country_map.get(symbol, ["US"])
        return [e for e in self.news_calendar if e["country"] in countries and e["impact"] == "HIGH"]

    def _get_upcoming_events(self, current_time: datetime) -> List[Dict]:
        return [e for e in self.news_calendar if 0 <= (e["time"] - current_time).total_seconds() / 3600 <= 24]
