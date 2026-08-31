"""
28+ Symbol Market Scanner for V6 Trading System.

Scans forex pairs, metals, crypto, and indices for trading opportunities.
Filters by spread, volume, and volatility, then scores each instrument
by opportunity quality (volume, spread, volatility, trend strength).
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ml.market_scanner")


class MarketScanner:
    """
    Scans 28+ instruments across multiple asset classes and ranks them
    by trading opportunity quality.

    Asset classes:
        - Majors (7): EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD
        - Crosses (7): EURGBP, EURJPY, GBPJPY, AUDJPY, EURAUD, EURCHF, GBPCAD
        - Exotics (4): USDTRY, USDZAR, USDMXN, USDCNH
        - Metals (3): XAUUSD, XAGUSD, XAUEUR
        - Crypto (3): BTCUSD, ETHUSD, SOLUSD
        - Indices (4): US30, US500, NAS100, GER40
    """

    DEFAULT_SYMBOLS = [
        # Majors (7)
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
        # Crosses (7)
        "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "EURCHF", "GBPCAD",
        # Exotics (4)
        "USDTRY", "USDZAR", "USDMXN", "USDCNH",
        # Metals (3)
        "XAUUSD", "XAGUSD", "XAUEUR",
        # Crypto (3)
        "BTCUSD", "ETHUSD", "SOLUSD",
        # Indices (4)
        "US30", "US500", "NAS100", "GER40",
    ]

    # Asset class metadata for scoring weights
    ASSET_CLASSES = {
        "majors": {"symbols": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"], "weight": 1.0},
        "crosses": {"symbols": ["EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "EURCHF", "GBPCAD"], "weight": 0.9},
        "exotics": {"symbols": ["USDTRY", "USDZAR", "USDMXN", "USDCNH"], "weight": 0.7},
        "metals": {"symbols": ["XAUUSD", "XAGUSD", "XAUEUR"], "weight": 0.85},
        "crypto": {"symbols": ["BTCUSD", "ETHUSD", "SOLUSD"], "weight": 0.75},
        "indices": {"symbols": ["US30", "US500", "NAS100", "GER40"], "weight": 0.8},
    }

    def __init__(
        self,
        max_spread: float = 0.5,
        min_volume: int = 100,
        min_volatility: float = 0.0,
    ):
        self.max_spread = max_spread
        self.min_volume = min_volume
        self.min_volatility = min_volatility
        self._last_scan_results: List[Dict[str, Any]] = []

    def scan_all_instruments(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scan all instruments in market_data, filter, score, and rank.

        Args:
            market_data: Dict mapping symbol -> market data dict with keys:
                spread, volume, volatility, candles, current_price, etc.

        Returns:
            List of opportunity dicts sorted by score (descending).
        """
        opportunities: List[Dict[str, Any]] = []

        for symbol, data in market_data.items():
            # Apply filters
            if not self._passes_filters(data):
                continue

            # Score the opportunity
            score = self.score_opportunity(data)

            # Get asset class weight
            asset_weight = self._get_asset_class_weight(symbol)

            # Adjust score by asset class liquidity/weight
            adjusted_score = score * asset_weight

            opportunities.append({
                "symbol": symbol,
                "data": data,
                "score": round(adjusted_score, 4),
                "raw_score": round(score, 4),
                "asset_class": self._get_asset_class(symbol),
                "spread": data.get("spread", 0),
                "volume": data.get("volume", 0),
                "volatility": data.get("volatility", 0),
            })

        # Sort by adjusted score descending
        opportunities.sort(key=lambda x: x["score"], reverse=True)

        self._last_scan_results = opportunities
        logger.info(
            "Market scan complete: %d symbols scanned, %d opportunities found",
            len(market_data), len(opportunities),
        )

        return opportunities

    def get_opportunities(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Return top N opportunities from the last scan.
        If no scan has been run, returns empty list.
        """
        return self._last_scan_results[:top_n]

    def filter_by_spread(
        self, symbols: List[Dict[str, Any]], max_spread: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Filter opportunities by maximum spread."""
        threshold = max_spread if max_spread is not None else self.max_spread
        return [s for s in symbols if s.get("spread", 999) <= threshold]

    def filter_by_volume(
        self, symbols: List[Dict[str, Any]], min_volume: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Filter opportunities by minimum volume."""
        threshold = min_volume if min_volume is not None else self.min_volume
        return [s for s in symbols if s.get("volume", 0) >= threshold]

    def score_opportunity(self, symbol_data: Dict[str, Any]) -> float:
        """
        Calculate opportunity score (0-100) for a symbol.

        Scoring components:
            - Volume score (30%): Higher volume = higher score
            - Spread score (25%): Lower spread = higher score
            - Volatility score (25%): Moderate volatility = highest score
            - Trend strength score (20%): Strong trend = higher score

        Args:
            symbol_data: Dict with keys: spread, volume, volatility,
                         optionally: trend_strength, candles

        Returns:
            Float score between 0 and 100.
        """
        # Volume score (0-100): normalize to 0-5000 volume range
        volume = symbol_data.get("volume", 0)
        volume_score = min(100.0, (volume / 5000.0) * 100.0)

        # Spread score (0-100): inverse relationship, 0 spread = 100
        spread = symbol_data.get("spread", 1.0)
        spread_score = max(0.0, 100.0 - (spread / 1.0) * 100.0)

        # Volatility score (0-100): bell curve centered at 1.0
        volatility = symbol_data.get("volatility", 0.0)
        if volatility <= 0:
            vol_score = 0.0
        elif volatility < 0.5:
            vol_score = volatility * 80.0  # Low vol = low score
        elif volatility <= 2.0:
            vol_score = 60.0 + (volatility - 0.5) * 26.67  # Sweet spot
        else:
            vol_score = max(0.0, 100.0 - (volatility - 2.0) * 20.0)  # Too volatile

        # Trend strength score (0-100)
        trend = symbol_data.get("trend_strength", 0.0)
        if trend == 0.0:
            # Try to compute from candles if available
            trend = self._compute_trend_strength(symbol_data)
        trend_score = min(100.0, abs(trend) * 100.0)

        # Weighted combination
        score = (
            volume_score * 0.30
            + spread_score * 0.25
            + vol_score * 0.25
            + trend_score * 0.20
        )

        return round(min(100.0, max(0.0, score)), 2)

    def get_symbol_details(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed info for one symbol from the last scan.

        Returns:
            Dict with symbol details or empty dict if not found.
        """
        for opp in self._last_scan_results:
            if opp["symbol"] == symbol:
                return opp
        return {}

    # ── Private helpers ────────────────────────────────────────────

    def _passes_filters(self, data: Dict[str, Any]) -> bool:
        """Check if symbol data passes all filters."""
        spread = data.get("spread", 999)
        volume = data.get("volume", 0)
        volatility = data.get("volatility", 0.0)

        if spread > self.max_spread:
            return False
        if volume < self.min_volume:
            return False
        if volatility > 0 and volatility < self.min_volatility:
            return False
        return True

    def _get_asset_class(self, symbol: str) -> str:
        """Determine the asset class for a symbol."""
        for class_name, info in self.ASSET_CLASSES.items():
            if symbol in info["symbols"]:
                return class_name
        return "unknown"

    def _get_asset_class_weight(self, symbol: str) -> float:
        """Get the scoring weight for a symbol's asset class."""
        asset_class = self._get_asset_class(symbol)
        return self.ASSET_CLASSES.get(asset_class, {}).get("weight", 0.8)

    def _compute_trend_strength(self, data: Dict[str, Any]) -> float:
        """
        Compute trend strength from candle data if not provided.
        Returns a value between -1.0 (strong downtrend) and 1.0 (strong uptrend).
        """
        candles = data.get("candles", [])
        if not candles or len(candles) < 20:
            return 0.0

        try:
            closes = [float(c.get("close", 0)) for c in candles[-20:]]
            if not closes or closes[-1] == 0:
                return 0.0

            # Simple trend: compare recent average to older average
            recent_avg = sum(closes[-5:]) / 5.0
            older_avg = sum(closes[-20:-15]) / 5.0

            if older_avg == 0:
                return 0.0

            pct_change = (recent_avg - older_avg) / older_avg
            # Clamp to [-1, 1]
            return max(-1.0, min(1.0, pct_change * 10.0))
        except (ValueError, ZeroDivisionError):
            return 0.0
