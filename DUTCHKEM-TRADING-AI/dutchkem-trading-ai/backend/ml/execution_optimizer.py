import logging
import math
import threading
import time
from typing import Any, Dict, List, Optional

import numpy as np
from django.conf import settings

logger = logging.getLogger("ml.execution")


class ExecutionOptimizer:
    _instance: Optional["ExecutionOptimizer"] = None
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
        self._max_slippage = float(getattr(settings, "MAX_SLIPPAGE_PIPS", 0.5))
        self._max_spread = float(getattr(settings, "MAX_SPREAD_PIPS", 0.5))
        self._execution_history: List[Dict[str, Any]] = []
        self._latency_cache: Dict[str, List[float]] = {}
        logger.info("ExecutionOptimizer initialised (max_slippage=%.1f, max_spread=%.1f)", self._max_slippage, self._max_spread)

    def calculate_optimal_entry(self, symbol: str, current_price: float, spread_pips: float, slippage_history: Optional[List[float]] = None) -> Dict[str, Any]:
        if spread_pips > self._max_spread:
            return {
                "should_enter": False,
                "reason": "spread_too_wide",
                "spread_pips": spread_pips,
                "max_spread": self._max_spread,
            }

        avg_slippage = 0.0
        if slippage_history:
            avg_slippage = float(np.mean(slippage_history[-20:]))
        elif symbol in self._latency_cache:
            avg_slippage = float(np.mean(self._latency_cache[symbol][-20:]))

        adjusted_slippage = max(avg_slippage * 1.2, 0.1)

        return {
            "should_enter": True,
            "current_price": current_price,
            "spread_pips": spread_pips,
            "expected_slippage_pips": adjusted_slippage,
            "adjusted_entry": current_price + (adjusted_slippage * 0.0001 if "JPY" not in symbol.upper() else adjusted_slippage * 0.01),
        }

    def calculate_optimal_exit(self, symbol: str, entry_price: float, current_price: float, target_pips: float, current_spread_pips: float) -> Dict[str, Any]:
        net_pnl_pips = (current_price - entry_price) / (0.0001 if "JPY" not in symbol.upper() else 0.01)
        net_pnl_pips -= current_spread_pips

        should_exit = net_pnl_pips >= target_pips or net_pnl_pips <= -target_pips

        return {
            "should_exit": should_exit,
            "net_pnl_pips": net_pnl_pips,
            "target_pips": target_pips,
            "spread_cost": current_spread_pips,
            "reason": "target_hit" if net_pnl_pips >= target_pips else "stop_hit" if net_pnl_pips <= -target_pips else "hold",
        }

    def measure_latency(self, symbol: str, order_time: float, fill_time: float) -> float:
        latency_ms = (fill_time - order_time) * 1000
        if symbol not in self._latency_cache:
            self._latency_cache[symbol] = []
        self._latency_cache[symbol].append(latency_ms)
        if len(self._latency_cache[symbol]) > 100:
            self._latency_cache[symbol] = self._latency_cache[symbol][-100:]
        return latency_ms

    def get_average_latency(self, symbol: str) -> float:
        latencies = self._latency_cache.get(symbol, [])
        if not latencies:
            return 0.0
        return float(np.mean(latencies[-20:]))

    def evaluate_execution_quality(self, symbol: str, expected_price: float, actual_fill_price: float, volume: float) -> Dict[str, Any]:
        slippage = abs(actual_fill_price - expected_price)
        pip_size = 0.01 if "JPY" in symbol.upper() else 0.0001
        slippage_pips = slippage / pip_size

        quality = "excellent" if slippage_pips < 0.1 else "good" if slippage_pips < 0.3 else "fair" if slippage_pips < 0.5 else "poor"

        self._execution_history.append({
            "symbol": symbol,
            "slippage_pips": slippage_pips,
            "quality": quality,
            "volume": volume,
            "timestamp": time.time(),
        })

        return {
            "symbol": symbol,
            "expected_price": expected_price,
            "actual_fill_price": actual_fill_price,
            "slippage_pips": slippage_pips,
            "quality": quality,
            "volume": volume,
        }

    def get_execution_stats(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        history = self._execution_history
        if symbol:
            history = [h for h in history if h["symbol"] == symbol]

        if not history:
            return {"total_executions": 0, "avg_slippage_pips": 0, "quality_distribution": {}}

        slippages = [h["slippage_pips"] for h in history]
        quality_counts = {}
        for h in history:
            q = h["quality"]
            quality_counts[q] = quality_counts.get(q, 0) + 1

        return {
            "total_executions": len(history),
            "avg_slippage_pips": float(np.mean(slippages)),
            "max_slippage_pips": float(np.max(slippages)),
            "min_slippage_pips": float(np.min(slippages)),
            "quality_distribution": quality_counts,
        }

    def recommend_order_type(self, symbol: str, volume: float, current_spread_pips: float) -> Dict[str, Any]:
        if current_spread_pips > self._max_spread:
            return {"order_type": "limit", "reason": "spread_too_wide", "suggested_limit_offset_pips": current_spread_pips * 0.5}

        avg_latency = self.get_average_latency(symbol)
        if avg_latency > 500:
            return {"order_type": "limit", "reason": "high_latency", "suggested_limit_offset_pips": 0.2}

        return {"order_type": "market", "reason": "conditions_favorable"}

    def clear_history(self) -> None:
        self._execution_history.clear()
        self._latency_cache.clear()
