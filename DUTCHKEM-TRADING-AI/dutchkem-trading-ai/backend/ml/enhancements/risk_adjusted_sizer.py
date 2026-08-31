"""
RISK-ADJUSTED POSITION SIZING ENGINE
V6.5 Enhancement #7
"""

import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger("ml.enhancements.risk_sizer")


class RiskAdjustedSizer:
    """
    Advanced position sizing using multiple risk metrics.
    """

    def __init__(self):
        self.max_risk = 0.01
        self.min_risk = 0.001
        self.default_risk = 0.005
        self.trade_history: List[Dict] = []
        self.max_loss_streak = 0

    def calculate_optimal_risk(self, account_equity: float, signal_confidence: float,
                               volatility: float, correlation: float, drawdown: float, regime: str) -> float:
        try:
            risk = self.default_risk
            risk *= 0.5 + (signal_confidence * 0.5)

            if volatility > 2.0:
                risk *= 0.6
            elif volatility > 1.5:
                risk *= 0.8
            elif volatility < 0.5:
                risk *= 1.2
            elif volatility < 0.3:
                risk *= 1.4

            if correlation > 0.5:
                risk *= 0.7
            elif correlation > 0.3:
                risk *= 0.85

            if drawdown > 0.10:
                risk *= 0.5
            elif drawdown > 0.05:
                risk *= 1 - (drawdown - 0.05) * 5
                risk = max(risk, self.min_risk)

            win_rate = self.get_recent_win_rate()
            if win_rate > 0.8:
                risk *= 1.1
            elif win_rate < 0.5:
                risk *= 0.7
            elif win_rate < 0.4:
                risk *= 0.5

            regime_mult = {"TRENDING": 1.2, "BREAKOUT": 1.1, "RANGING": 0.8, "VOLATILE": 0.7}
            risk *= regime_mult.get(regime, 1.0)

            return max(self.min_risk, min(self.max_risk, risk))
        except Exception as e:
            logger.error("Risk calc failed: %s", e)
            return self.default_risk

    def calculate_position_size(self, account_equity: float, risk_pct: float,
                                stop_loss_pips: float, pip_value: float = 10.0) -> float:
        try:
            risk_amount = account_equity * risk_pct
            lots = risk_amount / (stop_loss_pips * pip_value) if stop_loss_pips > 0 else 0.01
            lots = round(lots * 100) / 100
            return max(0.01, min(50.0, lots))
        except Exception as e:
            logger.error("Position size calc failed: %s", e)
            return 0.01

    def get_recent_win_rate(self, period: int = 20) -> float:
        if not self.trade_history:
            return 0.5
        recent = self.trade_history[-min(period, len(self.trade_history)):]
        wins = sum(1 for t in recent if t.get("profit", 0) > 0)
        return wins / len(recent) if recent else 0.5

    def update_trade_history(self, trade_result: Dict):
        self.trade_history.append({
            "profit": trade_result.get("profit", 0),
            "symbol": trade_result.get("symbol", ""),
            "entry_time": trade_result.get("entry_time", datetime.now()),
        })
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
        streak = max_streak = 0
        for t in self.trade_history:
            if t["profit"] < 0:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        self.max_loss_streak = max_streak
