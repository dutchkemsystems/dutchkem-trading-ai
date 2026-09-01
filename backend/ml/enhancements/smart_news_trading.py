"""
SMART NEWS TRADING ENGINE
V6.5 Enhancement #2

Economic calendar uses absolute timestamps and persists to a local
JSON cache so events survive restarts and are only re-fetched once
per day.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ml.enhancements.news_trading")

# Default cache path (next to this module)
_DEFAULT_CACHE_PATH = Path(__file__).resolve().parent / ".economic_calendar.json"


class SmartNewsTrading:
    """
    Advanced news trading with pre/post-event strategies.
    """

    def __init__(self, cache_path: Optional[str] = None):
        self.impact_threshold = 3.0
        self.pre_event_window = 15
        self.post_event_window = 30
        self.hmr_active = False
        self.news_calendar: List[Dict] = []
        self._cache_path = Path(cache_path) if cache_path else _DEFAULT_CACHE_PATH
        self._last_load_date: Optional[str] = None
        self.high_impact_events = [
            "Non-Farm Payrolls", "CPI", "Federal Funds Rate", "FOMC Statement",
            "GDP", "Unemployment Rate", "ECB Rate Decision", "BOE Rate Decision",
            "Retail Sales", "PMI", "Inflation Rate",
        ]
        self.load_economic_calendar()

    # ── Calendar loading ────────────────────────────────────────────

    def load_economic_calendar(self):
        """Load economic calendar with persistence and daily refresh."""
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Skip reload if already loaded today
        if self._last_load_date == today_str and self.news_calendar:
            return

        # 1. Try loading from cache file
        cached = self._load_from_cache()
        if cached is not None:
            self.news_calendar = cached
            self._last_load_date = today_str
            logger.debug("Economic calendar loaded from cache (%d events)", len(cached))
            return

        # 2. Try fetching from external API
        fetched = self._fetch_from_external_api()
        if fetched is not None:
            self.news_calendar = fetched
            self._last_load_date = today_str
            self._save_to_cache(fetched)
            logger.info("Economic calendar fetched from external API (%d events)", len(fetched))
            return

        # 3. Fall back to built-in static calendar with ABSOLUTE timestamps
        now = datetime.now()
        self.news_calendar = [
            {
                "name": "Non-Farm Payrolls", "country": "US", "impact": "HIGH",
                # First Friday of next month at 13:30 UTC
                "time": self._next_first_friday(now).replace(hour=13, minute=30).isoformat(),
                "forecast": 175000, "previous": 143000, "actual": None,
            },
            {
                "name": "CPI", "country": "US", "impact": "HIGH",
                # ~12th of next month at 13:30 UTC
                "time": (now.replace(day=1) + timedelta(days=32)).replace(day=12, hour=13, minute=30).isoformat(),
                "forecast": 3.2, "previous": 3.0, "actual": None,
            },
            {
                "name": "Federal Funds Rate", "country": "US", "impact": "HIGH",
                # ~8 weeks out at 19:00 UTC
                "time": (now + timedelta(weeks=8)).replace(hour=19, minute=0).isoformat(),
                "forecast": 5.50, "previous": 5.50, "actual": None,
            },
            {
                "name": "ECB Rate Decision", "country": "EU", "impact": "HIGH",
                "time": (now + timedelta(weeks=6)).replace(hour=14, minute=15).isoformat(),
                "forecast": 4.50, "previous": 4.50, "actual": None,
            },
            {
                "name": "GDP", "country": "US", "impact": "HIGH",
                "time": (now + timedelta(weeks=4)).replace(hour=13, minute=30).isoformat(),
                "forecast": 2.1, "previous": 2.0, "actual": None,
            },
        ]
        self._last_load_date = today_str
        self._save_to_cache(self.news_calendar)
        logger.info("Economic calendar loaded from defaults (%d events)", len(self.news_calendar))

    # ── External API fetch ──────────────────────────────────────────

    def _fetch_from_external_api(self) -> Optional[List[Dict]]:
        """Attempt to fetch upcoming events from a public API.

        Tries ForexFactory CSV first, then falls back to investing.com
        JSON endpoint. Returns ``None`` on any failure so the caller can
        fall back to defaults.
        """
        # --- Attempt 1: ForexFactory CSV (simple, no auth) ---
        try:
            import urllib.request
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            req = urllib.request.Request(url, headers={"User-Agent": "DutchkemTradingAI/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            events = []
            for item in raw:
                impact = item.get("impact", "").upper()
                if impact not in ("HIGH", "MEDIUM"):
                    continue
                time_str = item.get("date", "")
                # Parse ISO-like datetime
                try:
                    event_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    continue
                events.append({
                    "name": item.get("title", "Unknown"),
                    "country": item.get("country", "US"),
                    "impact": impact,
                    "time": event_time.isoformat(),
                    "forecast": item.get("forecast"),
                    "previous": item.get("previous"),
                    "actual": item.get("actual"),
                })
            if events:
                return events
        except Exception as e:
            logger.debug("ForexFactory fetch failed (expected in dev): %s", e)

        # --- Attempt 2: Investing.com RSS-like endpoint ---
        try:
            import urllib.request
            url = "https://sslecal2.investing.com/events/eventsList"
            req = urllib.request.Request(url, headers={
                "User-Agent": "DutchkemTradingAI/1.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            events = []
            for item in (raw if isinstance(raw, list) else []):
                impact = str(item.get("importance", "")).count("*")
                if impact < 3:
                    continue
                events.append({
                    "name": item.get("event", "Unknown"),
                    "country": item.get("country", "US"),
                    "impact": "HIGH",
                    "time": item.get("date", datetime.now().isoformat()),
                    "forecast": item.get("forecast"),
                    "previous": item.get("previous"),
                    "actual": item.get("actual"),
                })
            if events:
                return events
        except Exception as e:
            logger.debug("Investing.com fetch failed (expected in dev): %s", e)

        return None

    # ── Cache persistence ───────────────────────────────────────────

    def _load_from_cache(self) -> Optional[List[Dict]]:
        """Load events from the local JSON cache if it exists and is fresh."""
        try:
            if not self._cache_path.exists():
                return None
            with open(self._cache_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Validate structure
            if not isinstance(data, list) or not data:
                return None
            # Check if cache was written today
            first_event = data[0]
            cache_date = first_event.get("_cached_date", "")
            if cache_date == datetime.now().strftime("%Y-%m-%d"):
                return data
            return None  # Stale
        except Exception as e:
            logger.debug("Cache read failed: %s", e)
            return None

    def _save_to_cache(self, events: List[Dict]):
        """Persist events to local JSON cache."""
        try:
            # Stamp each event with cache date for staleness check
            cached = [{**e, "_cached_date": datetime.now().strftime("%Y-%m-%d")} for e in events]
            with open(self._cache_path, "w", encoding="utf-8") as fh:
                json.dump(cached, fh, indent=2, default=str)
            logger.debug("Economic calendar cached to %s", self._cache_path)
        except Exception as e:
            logger.warning("Failed to cache economic calendar: %s", e)

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _next_first_friday(now: datetime) -> datetime:
        """Return the datetime of the first Friday of the next month."""
        first_next = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        days_until_friday = (4 - first_next.weekday()) % 7
        return first_next + timedelta(days=days_until_friday)

    def get_news_strategy(self, symbol: str, current_time: datetime) -> Dict:
        # Ensure calendar is up-to-date (no-op if already loaded today)
        self.load_economic_calendar()
        relevant = self._get_relevant_events(symbol, current_time)
        for event in relevant:
            event_time = self._parse_event_time(event)
            if event_time is None:
                continue
            mins_until = (event_time - current_time).total_seconds() / 60
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

    @staticmethod
    def _parse_event_time(event: Dict) -> Optional[datetime]:
        """Parse the 'time' field which may be a datetime, ISO string, or epoch."""
        raw = event.get("time")
        if isinstance(raw, datetime):
            return raw
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw)
            except (ValueError, TypeError):
                return None
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw)
        return None

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
            event_time = self._parse_event_time(event)
            if event_time is None:
                continue
            mins = (event_time - current_time).total_seconds() / 60
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
        upcoming = []
        for e in self.news_calendar:
            event_time = self._parse_event_time(e)
            if event_time is None:
                continue
            hours_until = (event_time - current_time).total_seconds() / 3600
            if 0 <= hours_until <= 24:
                upcoming.append(e)
        return upcoming
