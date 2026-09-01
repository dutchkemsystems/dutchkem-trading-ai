import logging
import threading
from typing import Any, Dict, List, Optional

import numpy as np
from django.conf import settings

logger = logging.getLogger("ml.dynamic_kelly")


class DynamicKelly:
    _instance: Optional["DynamicKelly"] = None
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
        self._half_kelly = True
        self._max_fraction = 0.25
        self._min_fraction = 0.01
        self._trade_history: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("DynamicKelly initialised")

    def record_trade(self, symbol: str, won: bool, pnl_pct: float) -> None:
        if symbol not in self._trade_history:
            self._trade_history[symbol] = []
        self._trade_history[symbol].append({"won": won, "pnl_pct": pnl_pct})
        if len(self._trade_history[symbol]) > 200:
            self._trade_history[symbol] = self._trade_history[symbol][-200:]

    def calculate_kelly(self, symbol: str) -> float:
        trades = self._trade_history.get(symbol, [])
        if len(trades) < 10:
            return self._min_fraction

        wins = [t for t in trades if t["won"]]
        losses = [t for t in trades if not t["won"]]

        if not wins or not losses:
            return self._min_fraction

        win_rate = len(wins) / len(trades)
        avg_win = np.mean([t["pnl_pct"] for t in wins])
        avg_loss = abs(np.mean([t["pnl_pct"] for t in losses]))

        if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
            return self._min_fraction

        b = avg_win / avg_loss
        kelly = (b * win_rate - (1 - win_rate)) / b
        kelly = max(0.0, kelly)

        if self._half_kelly:
            kelly *= 0.5

        return float(np.clip(kelly, self._min_fraction, self._max_fraction))

    def calculate_dynamic_position_size(self, symbol: str, equity: float, stop_loss_pips: int, contract_size: float = 100000.0, pip_size: float = 0.0001) -> float:
        kelly_fraction = self.calculate_kelly(symbol)
        risk_amount = equity * kelly_fraction

        if stop_loss_pips <= 0:
            return 0.0

        pip_value = contract_size * pip_size
        position_size = risk_amount / (stop_loss_pips * pip_value)
        return round(position_size, 2)

    def get_kelly_breakdown(self, symbol: str) -> Dict[str, Any]:
        trades = self._trade_history.get(symbol, [])
        if not trades:
            return {"symbol": symbol, "kelly_fraction": self._min_fraction, "trades_analyzed": 0}

        wins = [t for t in trades if t["won"]]
        losses = [t for t in trades if not t["won"]]

        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = float(np.mean([t["pnl_pct"] for t in wins])) if wins else 0
        avg_loss = abs(float(np.mean([t["pnl_pct"] for t in losses]))) if losses else 0

        return {
            "symbol": symbol,
            "kelly_fraction": self.calculate_kelly(symbol),
            "win_rate": win_rate,
            "avg_win_pct": avg_win,
            "avg_loss_pct": avg_loss,
            "trades_analyzed": len(trades),
            "total_wins": len(wins),
            "total_losses": len(losses),
            "half_kelly": self._half_kelly,
        }

    def get_portfolio_kelly(self, equity: float, allocations: Dict[str, float]) -> Dict[str, Any]:
        total_risk = 0.0
        breakdowns = {}
        for symbol, weight in allocations.items():
            kelly = self.calculate_kelly(symbol)
            risk = equity * weight * kelly
            total_risk += risk
            breakdowns[symbol] = {"kelly_fraction": kelly, "weight": weight, "risk_amount": risk}

        return {
            "total_risk": total_risk,
            "risk_percentage": (total_risk / equity * 100) if equity > 0 else 0,
            "breakdowns": breakdowns,
        }

    def clear_history(self, symbol: Optional[str] = None) -> None:
        if symbol:
            self._trade_history.pop(symbol, None)
        else:
            self._trade_history.clear()
