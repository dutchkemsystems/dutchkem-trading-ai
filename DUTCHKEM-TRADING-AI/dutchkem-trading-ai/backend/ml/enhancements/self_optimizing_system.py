"""
SELF-OPTIMIZING PARAMETERS ENGINE
V6.5 Enhancement #10

Optimizes trading parameters via genetic algorithm using real OHLCV
backtesting — no random simulation.
"""

import logging
import random
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger("ml.enhancements.self_optimizer")


class SelfOptimizingSystem:
    """
    Continuous parameter optimization using genetic algorithms.
    """

    def __init__(self):
        self.parameters = {
            "rsi_period": 14, "stoch_period": 14, "macd_fast": 12, "macd_slow": 26,
            "bb_period": 20, "risk_pct": 0.005, "stop_loss_atr": 1.5,
            "take_profit_ratio": 2.0, "confidence_threshold": 0.65,
            "max_positions": 5, "trailing_stop_trigger": 5, "partial_close_percentage": 0.40,
        }
        self.param_ranges = {
            "rsi_period": (7, 21), "stoch_period": (7, 21), "macd_fast": (8, 16),
            "macd_slow": (20, 32), "bb_period": (14, 26), "risk_pct": (0.002, 0.01),
            "stop_loss_atr": (1.0, 2.5), "take_profit_ratio": (1.5, 3.0),
            "confidence_threshold": (0.55, 0.80), "max_positions": (3, 8),
            "trailing_stop_trigger": (3, 10), "partial_close_percentage": (0.20, 0.60),
        }
        self.optimization_interval = 86400
        self.last_optimization = None
        self.population_size = 20
        self.generations = 10
        self.best_fitness = 0
        self.best_params = self.parameters.copy()
        self.performance_history: List[Dict] = []

    def run_optimization(self, historical_data: List[Dict]) -> Dict:
        try:
            population = self._generate_population(self.population_size)
            fitness = [self._evaluate(p, historical_data) for p in population]

            for _ in range(self.generations):
                best_idx = np.argsort(fitness)[-5:]
                children = self._crossover([population[i] for i in best_idx])
                mutated = self._mutate(children)
                worst_idx = np.argsort(fitness)[:len(mutated)]
                for i, idx in enumerate(worst_idx):
                    population[idx] = mutated[i] if i < len(mutated) else mutated[0]
                for idx in worst_idx:
                    fitness[idx] = self._evaluate(population[idx], historical_data)
                best = np.argmax(fitness)
                if fitness[best] > self.best_fitness:
                    self.best_fitness = fitness[best]
                    self.best_params = population[best].copy()

            self.parameters = self.best_params.copy()
            self.last_optimization = datetime.now()
            self.performance_history.append({
                "timestamp": datetime.now().isoformat(), "best_fitness": self.best_fitness,
                "parameters": self.parameters.copy(),
            })
            return {"optimized": True, "parameters": self.parameters.copy(), "fitness_score": self.best_fitness,
                    "generations_used": self.generations, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            logger.error("Optimization failed: %s", e)
            return {"optimized": False, "parameters": self.parameters.copy(), "error": str(e)}

    def _generate_population(self, size: int) -> List[Dict]:
        pop = []
        for _ in range(size):
            p = {}
            for k, (lo, hi) in self.param_ranges.items():
                if isinstance(self.parameters[k], int):
                    p[k] = random.randint(int(lo), int(hi))
                else:
                    p[k] = random.uniform(lo, hi)
            pop.append(p)
        return pop

    def _evaluate(self, params: Dict, data: List[Dict]) -> float:
        """Evaluate a parameter set by backtesting against historical OHLCV data.

        Returns a composite fitness score: win_rate * profit_factor *
        (1 - max_drawdown) * sharpe_ratio.  All components are normalised
        to [0, 1] so the final score is in [0, 1].  A penalty is applied
        for excessive risk to discourage over-fitted, high-risk parameter sets.

        If insufficient data is provided the method returns 0.
        """
        if not data or len(data) < 60:
            return 0.0

        try:
            closes = np.array([float(c.get("close", 0)) for c in data], dtype=np.float64)
            highs = np.array([float(c.get("high", 0)) for c in data], dtype=np.float64)
            lows = np.array([float(c.get("low", 0)) for c in data], dtype=np.float64)
        except (KeyError, TypeError, ValueError):
            logger.warning("Could not parse OHLCV data for fitness evaluation")
            return 0.0

        # ── Compute indicators with candidate parameters ────────────────
        rsi_period = int(params.get("rsi_period", 14))
        macd_fast = int(params.get("macd_fast", 12))
        macd_slow = int(params.get("macd_slow", 26))
        bb_period = int(params.get("bb_period", 20))
        stop_loss_atr = params.get("stop_loss_atr", 1.5)
        take_profit_ratio = params.get("take_profit_ratio", 2.0)
        risk_pct = params.get("risk_pct", 0.005)
        confidence_threshold = params.get("confidence_threshold", 0.65)

        rsi = self._compute_rsi(closes, rsi_period)
        macd_line, signal_line = self._compute_macd(closes, macd_fast, macd_slow)
        upper_bb, lower_bb = self._compute_bollinger(closes, bb_period)
        atr = self._compute_atr(highs, lows, closes)

        # ── Bar-by-bar simulation ───────────────────────────────────────
        balance = 10000.0
        initial_balance = balance
        peak_equity = balance
        max_drawdown = 0.0
        trades: List[Dict[str, Any]] = []
        position = None  # None | {"dir": 1/-1, "entry": float, "sl": float, "tp": float}
        warmup = max(rsi_period, macd_slow, bb_period, 14) + 5

        for i in range(warmup, len(closes)):
            price = closes[i]
            cur_atr = atr[i] if atr[i] > 0 else 1e-6

            # ── Manage open position ────────────────────────────────────
            if position is not None:
                hit_sl = False
                hit_tp = False
                if position["dir"] == 1:
                    hit_sl = lows[i] <= position["sl"]
                    hit_tp = highs[i] >= position["tp"]
                else:
                    hit_sl = highs[i] >= position["sl"]
                    hit_tp = lows[i] <= position["tp"]

                if hit_sl or hit_tp:
                    exit_price = position["sl"] if hit_sl else position["tp"]
                    pnl = (exit_price - position["entry"]) * position["dir"]
                    balance += pnl * (balance * risk_pct / max(abs(position["entry"] - position["sl"]), 1e-8))
                    trades.append({"pnl": pnl, "outcome": "WIN" if pnl > 0 else "LOSS"})
                    position = None

            # ── Track equity ────────────────────────────────────────────
            unrealized = 0.0
            if position is not None:
                unrealized = (price - position["entry"]) * position["dir"]
            current_equity = balance + unrealized * (balance * risk_pct / max(abs(position["entry"] - position["sl"]), 1e-8)) if position else balance
            if current_equity > peak_equity:
                peak_equity = current_equity
            if peak_equity > 0:
                dd = (peak_equity - current_equity) / peak_equity
                if dd > max_drawdown:
                    max_drawdown = dd

            # ── Generate signal from indicators ─────────────────────────
            if position is None:
                rsi_val = rsi[i]
                macd_val = macd_line[i] - signal_line[i]
                prev_macd_val = macd_line[i - 1] - signal_line[i - 1]
                price_vs_bb = (price - lower_bb[i]) / max(upper_bb[i] - lower_bb[i], 1e-8)

                # Composite confidence from indicator agreement
                indicators_agree = 0
                total_indicators = 0
                direction = 0

                # RSI signal
                if rsi_val < 30:
                    indicators_agree += 1
                    direction += 1
                elif rsi_val > 70:
                    indicators_agree += 1
                    direction -= 1
                total_indicators += 1

                # MACD crossover
                if prev_macd_val <= 0 and macd_val > 0:
                    indicators_agree += 1
                    direction += 1
                elif prev_macd_val >= 0 and macd_val < 0:
                    indicators_agree += 1
                    direction -= 1
                total_indicators += 1

                # Bollinger Band position
                if price_vs_bb < 0.2:
                    indicators_agree += 1
                    direction += 1
                elif price_vs_bb > 0.8:
                    indicators_agree += 1
                    direction -= 1
                total_indicators += 1

                confidence = indicators_agree / total_indicators if total_indicators > 0 else 0

                if confidence >= confidence_threshold and direction != 0:
                    entry_price = price
                    sl_distance = cur_atr * stop_loss_atr
                    tp_distance = sl_distance * take_profit_ratio
                    sl = entry_price - sl_distance if direction > 0 else entry_price + sl_distance
                    tp = entry_price + tp_distance if direction > 0 else entry_price - tp_distance
                    position = {"dir": direction, "entry": entry_price, "sl": sl, "tp": tp}

        # ── Close any remaining position ────────────────────────────────
        if position is not None:
            exit_price = closes[-1]
            pnl = (exit_price - position["entry"]) * position["dir"]
            balance += pnl * (balance * risk_pct / max(abs(position["entry"] - position["sl"]), 1e-8))
            trades.append({"pnl": pnl, "outcome": "WIN" if pnl > 0 else "LOSS"})

        # ── Compute metrics ─────────────────────────────────────────────
        if not trades:
            return 0.0

        wins = sum(1 for t in trades if t["outcome"] == "WIN")
        total_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        total_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))

        win_rate = wins / len(trades) if trades else 0.0
        profit_factor = total_profit / total_loss if total_loss > 0 else (2.0 if total_profit > 0 else 0.0)
        profit_factor = min(profit_factor, 5.0)  # Cap to avoid runaway scores

        # Sharpe ratio (simplified from per-trade returns)
        returns = [t["pnl"] / max(abs(t["pnl"]), 1e-8) for t in trades]
        avg_ret = np.mean(returns) if returns else 0.0
        std_ret = np.std(returns) if len(returns) > 1 else 1.0
        sharpe = avg_ret / std_ret if std_ret > 0 else 0.0
        sharpe = max(-1.0, min(1.0, sharpe))  # Bound to [-1, 1]

        # ── Composite fitness (all components ~[0,1]) ───────────────────
        fitness = (
            min(win_rate, 1.0) *
            min(profit_factor / 3.0, 1.0) *       # PF of 3.0 → 1.0
            max(0.0, 1.0 - max_drawdown) *         # Lower DD → higher score
            max(0.0, (sharpe + 1.0) / 2.0)         # Sharpe in [-1,1] → [0,1]
        )

        # Penalise excessively risky parameter sets
        risk_penalty = 1.0 - max(0.0, (risk_pct - 0.005) * 50.0)
        risk_penalty = max(0.5, risk_penalty)
        fitness *= risk_penalty

        return max(0.0, fitness)

    # ── Indicator helpers ───────────────────────────────────────────────

    @staticmethod
    def _compute_rsi(closes: np.ndarray, period: int) -> np.ndarray:
        """Wilder RSI via exponential moving average."""
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        rsi = np.full(len(closes), 50.0)
        if len(gains) < period:
            return rsi

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
            rsi[i + 1] = 100.0 - (100.0 / (1.0 + rs))

        return rsi

    @staticmethod
    def _compute_macd(closes: np.ndarray, fast: int, slow: int) -> tuple:
        """MACD line and signal line (9-period EMA of MACD)."""
        def _ema(arr, period):
            ema = np.zeros_like(arr, dtype=np.float64)
            ema[period - 1] = np.mean(arr[:period])
            mult = 2.0 / (period + 1)
            for i in range(period, len(arr)):
                ema[i] = arr[i] * mult + ema[i - 1] * (1 - mult)
            return ema

        ema_fast = _ema(closes, fast)
        ema_slow = _ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = _ema(macd_line, 9)
        return macd_line, signal_line

    @staticmethod
    def _compute_bollinger(closes: np.ndarray, period: int) -> tuple:
        """Upper and lower Bollinger Bands (2 standard deviations)."""
        upper = np.full(len(closes), closes[-1] if len(closes) > 0 else 0.0)
        lower = np.full(len(closes), closes[-1] if len(closes) > 0 else 0.0)
        for i in range(period - 1, len(closes)):
            window = closes[i - period + 1: i + 1]
            sma = np.mean(window)
            std = np.std(window)
            upper[i] = sma + 2.0 * std
            lower[i] = sma - 2.0 * std
        return upper, lower

    @staticmethod
    def _compute_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Average True Range."""
        atr = np.zeros(len(closes))
        tr = np.zeros(len(closes))
        tr[0] = highs[0] - lows[0]
        for i in range(1, len(closes)):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        if len(tr) >= period:
            atr[period - 1] = np.mean(tr[:period])
            for i in range(period, len(tr)):
                atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        return atr

    def _crossover(self, parents: List[Dict]) -> List[Dict]:
        children = []
        for i in range(len(parents) - 1):
            child = {k: parents[i][k] if random.random() > 0.5 else parents[i + 1][k] for k in parents[i]}
            children.append(child)
        return children

    def _mutate(self, pop: List[Dict]) -> List[Dict]:
        for params in pop:
            for k in params:
                if random.random() < 0.15:
                    lo, hi = self.param_ranges[k]
                    if isinstance(params[k], int):
                        params[k] = max(int(lo), min(int(hi), params[k] + random.randint(-2, 2)))
                    else:
                        params[k] = max(lo, min(hi, params[k] + random.uniform(-0.1, 0.1) * (hi - lo)))
        return pop

    def get_parameters(self) -> Dict:
        return self.parameters.copy()

    def update_from_trade(self, trade_result: Dict):
        try:
            if trade_result.get("profit", 0) > 0:
                self.parameters["confidence_threshold"] = max(
                    self.param_ranges["confidence_threshold"][0],
                    self.parameters["confidence_threshold"] * 0.999,
                )
            else:
                self.parameters["confidence_threshold"] = min(
                    self.param_ranges["confidence_threshold"][1],
                    self.parameters["confidence_threshold"] * 1.001,
                )
        except Exception as e:
            logger.error("Parameter update failed: %s", e)

    def should_optimize(self) -> bool:
        if self.last_optimization is None:
            return True
        return (datetime.now() - self.last_optimization).total_seconds() >= self.optimization_interval
