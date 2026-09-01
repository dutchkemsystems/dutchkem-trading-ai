import logging
import threading
from collections import defaultdict
from typing import Any, Dict, List, Optional

import numpy as np
from django.conf import settings

logger = logging.getLogger("ml.correlation")


class CorrelationManager:
    _instance: Optional["CorrelationManager"] = None
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
        self._threshold = getattr(settings, "CORRELATION_THRESHOLD", 0.70)
        self._lookback = getattr(settings, "CORRELATION_LOOKBACK", 50)
        self._cache: Dict[str, np.ndarray] = {}
        self._price_history: Dict[str, List[float]] = defaultdict(list)
        logger.info("CorrelationManager initialised (threshold=%.2f, lookback=%d)", self._threshold, self._lookback)

    def update_prices(self, symbol: str, price: float) -> None:
        history = self._price_history[symbol]
        history.append(price)
        if len(history) > self._lookback * 2:
            self._price_history[symbol] = history[-self._lookback * 2:]
        self._cache.pop(symbol, None)

    def get_correlation(self, symbol_a: str, symbol_b: str) -> float:
        cache_key = f"{symbol_a}:{symbol_b}"
        if cache_key in self._cache:
            return float(self._cache[cache_key])

        prices_a = self._price_history.get(symbol_a, [])
        prices_b = self._price_history.get(symbol_b, [])

        min_len = min(len(prices_a), len(prices_b))
        if min_len < self._lookback:
            return 0.0

        arr_a = np.array(prices_a[-min_len:])
        arr_b = np.array(prices_b[-min_len:])

        returns_a = np.diff(arr_a) / arr_a[:-1]
        returns_b = np.diff(arr_b) / arr_b[:-1]

        if len(returns_a) < 2 or np.std(returns_a) == 0 or np.std(returns_b) == 0:
            return 0.0

        corr = float(np.corrcoef(returns_a, returns_b)[0, 1])
        self._cache[cache_key] = corr
        return corr

    def get_correlation_matrix(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        matrix: Dict[str, Dict[str, float]] = {}
        for sym_a in symbols:
            matrix[sym_a] = {}
            for sym_b in symbols:
                if sym_a == sym_b:
                    matrix[sym_a][sym_b] = 1.0
                else:
                    matrix[sym_a][sym_b] = self.get_correlation(sym_a, sym_b)
        return matrix

    def get_uncorrelated_pairs(self, symbols: List[str]) -> List[tuple]:
        pairs = []
        for i, sym_a in enumerate(symbols):
            for sym_b in symbols[i + 1:]:
                corr = abs(self.get_correlation(sym_a, sym_b))
                if corr < self._threshold:
                    pairs.append((sym_a, sym_b, corr))
        return pairs

    def check_portfolio_correlation(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        symbols = [p.get("symbol", "") for p in positions if p.get("symbol")]
        if len(symbols) < 2:
            return {"max_correlation": 0.0, "over_correlated": False, "pairs": []}

        max_corr = 0.0
        high_corr_pairs = []
        for i, sym_a in enumerate(symbols):
            for sym_b in symbols[i + 1:]:
                corr = abs(self.get_correlation(sym_a, sym_b))
                if corr > max_corr:
                    max_corr = corr
                if corr >= self._threshold:
                    high_corr_pairs.append({"a": sym_a, "b": sym_b, "correlation": corr})

        return {
            "max_correlation": max_corr,
            "over_correlated": max_corr >= self._threshold,
            "pairs": high_corr_pairs,
            "symbols_checked": len(symbols),
        }

    def clear_cache(self) -> None:
        self._cache.clear()
