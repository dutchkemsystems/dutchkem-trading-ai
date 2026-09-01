"""
Genetic Algorithm Optimizer for Strategy Parameters.

Uses evolutionary optimization to tune Gold Edge strategy parameters,
risk parameters, and ensemble weights. Maximizes Sharpe ratio while
enforcing constraints on drawdown, win rate, and profit factor.

Usage::

    from ml.genetic_optimizer import ParameterTuner

    tuner = ParameterTuner()
    result = tuner.tune_gold_edge("XAUUSD", generations=50)
    print(result.best_params, result.best_fitness)
"""

import copy
import json
import logging
import math
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.genetic_optimizer")

SAVED_MODELS_DIR = Path(__file__).parent / "saved_models" / "optimization"


# ---------------------------------------------------------------------------
# Chromosome
# ---------------------------------------------------------------------------

class Chromosome:
    """
    Represents a candidate set of strategy parameters as a chromosome.

    Each gene maps a parameter name to a numeric value. The chromosome
    carries a fitness score evaluated by the objective function.
    """

    __slots__ = ("genes", "fitness", "_id")

    def __init__(self, genes: Optional[Dict[str, float]] = None, fitness: float = -np.inf):
        self.genes: Dict[str, float] = genes or {}
        self.fitness: float = fitness
        self._id: str = f"chr_{random.randint(0, 0xFFFFFF):06x}"

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "genes": {k: round(v, 8) for k, v in self.genes.items()},
            "fitness": round(self.fitness, 8),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chromosome":
        return cls(
            genes=data.get("genes", {}),
            fitness=data.get("fitness", -np.inf),
        )

    def clone(self) -> "Chromosome":
        return Chromosome(
            genes=copy.deepcopy(self.genes),
            fitness=self.fitness,
        )

    def __repr__(self) -> str:
        genes_str = ", ".join(f"{k}={v:.4f}" for k, v in self.genes.items())
        return f"Chromosome(fitness={self.fitness:.6f}, {genes_str})"

    def __lt__(self, other: "Chromosome") -> bool:
        return self.fitness < other.fitness


# ---------------------------------------------------------------------------
# Strategy Parameter Spaces
# ---------------------------------------------------------------------------

class StrategyParamSpace:
    """
    Pre-defined parameter spaces for Gold Edge strategy optimization.

    Each parameter has a (lower, upper) continuous bound. Discrete
    parameters should be rounded after mutation.
    """

    def __init__(self):
        self._bounds: Dict[str, Tuple[float, float]] = {}
        self._discrete: set = set()
        self._constraints: List[Callable[[Dict[str, float]], bool]] = []

    def get_bounds(self) -> Dict[str, Tuple[float, float]]:
        """Return the full parameter bounds dictionary."""
        return dict(self._bounds)

    def get_constraints(self) -> List[Callable[[Dict[str, float]], bool]]:
        """Return the list of constraint functions."""
        return list(self._constraints)

    def add_param(self, name: str, low: float, high: float, discrete: bool = False):
        self._bounds[name] = (low, high)
        if discrete:
            self._discrete.add(name)
        return self

    def is_discrete(self, name: str) -> bool:
        return name in self._discrete


class GoldEdgeParamSpace(StrategyParamSpace):
    """
    Parameter space for Gold Edge strategy.

    Covers:
      - GEC component weights (sum to 1.0)
      - ATR filter thresholds
      - ATR border multipliers
      - Entry score thresholds
      - Risk parameters
    """

    def __init__(self):
        super().__init__()
        self._setup_gec_weights()
        self._setup_atr_filter()
        self._setup_atr_borders()
        self._setup_entry_thresholds()
        self._setup_risk_params()
        self._setup_constraints()

    def _setup_gec_weights(self):
        self.add_param("momentum_weight", 0.0, 1.0)
        self.add_param("trend_weight", 0.0, 1.0)
        self.add_param("volatility_weight", 0.0, 1.0)
        self.add_param("dxy_correlation_weight", 0.0, 1.0)

    def _setup_atr_filter(self):
        self.add_param("atr_ratio_min", 0.10, 0.30)
        self.add_param("atr_ratio_max", 0.80, 1.50)

    def _setup_atr_borders(self):
        self.add_param("core_multiplier", 0.3, 0.7)
        self.add_param("inner_multiplier", 0.8, 1.2)
        self.add_param("outer_multiplier", 1.3, 1.7)
        self.add_param("extended_multiplier", 1.8, 2.2)

    def _setup_entry_thresholds(self):
        self.add_param("min_gec_score", 0.30, 0.80)
        self.add_param("min_combined_score", 0.40, 0.85)

    def _setup_risk_params(self):
        self.add_param("max_risk_pct", 0.01, 0.05)
        self.add_param("kelly_fraction", 0.1, 0.5)
        self.add_param("sl_atr_multiplier", 1.0, 3.5)
        self.add_param("tp_atr_multiplier", 1.5, 5.0)

    def _setup_constraints(self):
        self._constraints = [
            self._weights_sum_to_one,
            self._border_ordering,
            self._atr_filter_order,
            self._tp_greater_than_sl,
            self._entry_thresholds_order,
        ]

    @staticmethod
    def _weights_sum_to_one(genes: Dict[str, float]) -> bool:
        w = (
            genes.get("momentum_weight", 0.3)
            + genes.get("trend_weight", 0.3)
            + genes.get("volatility_weight", 0.2)
            + genes.get("dxy_correlation_weight", 0.2)
        )
        return abs(w - 1.0) < 0.02

    @staticmethod
    def _border_ordering(genes: Dict[str, float]) -> bool:
        return (
            genes.get("core_multiplier", 0.5) < genes.get("inner_multiplier", 1.0)
            < genes.get("outer_multiplier", 1.5)
            < genes.get("extended_multiplier", 2.0)
        )

    @staticmethod
    def _atr_filter_order(genes: Dict[str, float]) -> bool:
        return genes.get("atr_ratio_min", 0.15) < genes.get("atr_ratio_max", 1.0)

    @staticmethod
    def _tp_greater_than_sl(genes: Dict[str, float]) -> bool:
        return genes.get("tp_atr_multiplier", 3.0) > genes.get("sl_atr_multiplier", 2.0)

    @staticmethod
    def _entry_thresholds_order(genes: Dict[str, float]) -> bool:
        return genes.get("min_gec_score", 0.5) < genes.get("min_combined_score", 0.6)


class RiskParamSpace(StrategyParamSpace):
    """Parameter space for risk management parameters only."""

    def __init__(self):
        super().__init__()
        self.add_param("max_risk_pct", 0.005, 0.10)
        self.add_param("kelly_fraction", 0.05, 0.75)
        self.add_param("sl_atr_multiplier", 0.5, 5.0)
        self.add_param("tp_atr_multiplier", 1.0, 8.0)
        self.add_param("max_daily_trades", 3, 20)
        self.add_param("max_correlation", 0.3, 0.9)

        self._constraints = [
            lambda g: g.get("tp_atr_multiplier", 3.0) > g.get("sl_atr_multiplier", 2.0),
        ]


class EnsembleWeightSpace(StrategyParamSpace):
    """Parameter space for ensemble model weights."""

    def __init__(self):
        super().__init__()
        self.add_param("lstm_weight", 0.0, 1.0)
        self.add_param("regime_weight", 0.0, 1.0)
        self.add_param("sr_levels_weight", 0.0, 1.0)
        self.add_param("volatility_weight", 0.0, 1.0)

        self._constraints = [
            lambda g: abs(
                g.get("lstm_weight", 0.25)
                + g.get("regime_weight", 0.25)
                + g.get("sr_levels_weight", 0.25)
                + g.get("volatility_weight", 0.25)
                - 1.0
            ) < 0.02,
        ]


# ---------------------------------------------------------------------------
# Fitness Function
# ---------------------------------------------------------------------------

class FitnessFunction:
    """
    Evaluates strategy parameter sets via backtest simulation.

    Uses Sharpe ratio as the primary fitness metric with penalties
    for excessive drawdown, poor win rate, and low profit factor.
    """

    def __init__(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_capital: float = 100000.0,
        data: Optional[Any] = None,
    ):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self._cached_data = data
        self._eval_count = 0

    def evaluate(self, params: Dict[str, float]) -> float:
        """
        Run a backtest with the given parameters and return a fitness score.

        Returns:
            Fitness score (higher is better). Negative values indicate
            constraint violations or failed backtests.
        """
        self._eval_count += 1

        try:
            metrics = self.backtest(params)
        except Exception as e:
            logger.debug("Backtest failed for params: %s — %s", params, e)
            return -10.0

        if metrics.get("total_trades", 0) < 5:
            return -5.0

        sharpe = metrics.get("sharpe_ratio", 0.0)
        fitness = sharpe

        # Penalties
        max_dd = metrics.get("max_drawdown", 0.0)
        if max_dd > 0.20:
            fitness -= (max_dd - 0.20) * 10.0

        win_rate = metrics.get("win_rate", 0.0)
        if win_rate < 0.30:
            fitness -= (0.30 - win_rate) * 5.0

        profit_factor = metrics.get("profit_factor", 0.0)
        if profit_factor < 1.5:
            fitness -= (1.5 - profit_factor) * 2.0

        return float(fitness)

    def backtest(self, params: Dict[str, float]) -> Dict[str, Any]:
        """
        Run a simplified backtest simulation.

        Simulates Gold Edge strategy signals over historical data and
        computes standard performance metrics.
        """
        ohlcv = self._get_data()
        if ohlcv is None or len(ohlcv) < 100:
            return {
                "total_trades": 0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
            }

        return self._simulate(ohlcv, params)

    def _get_data(self) -> Optional[Any]:
        """Retrieve OHLCV data for the symbol."""
        if self._cached_data is not None:
            return self._cached_data

        try:
            import pandas as pd

            data_dir = Path(__file__).parent / "data"
            csv_path = data_dir / f"{self.symbol}_H1.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                self._cached_data = df
                return df

            db_path = data_dir / f"{self.symbol}_H1.parquet"
            if db_path.exists():
                df = pd.read_parquet(db_path)
                self._cached_data = df
                return df
        except Exception as e:
            logger.debug("Could not load data for %s: %s", self.symbol, e)

        # Generate synthetic data as fallback for testing
        return self._generate_synthetic_data()

    def _generate_synthetic_data(self) -> Any:
        """Generate synthetic OHLCV data for testing."""
        import pandas as pd

        np.random.seed(42)
        n = 1000
        price = 2000.0 + np.cumsum(np.random.randn(n) * 5)
        high = price + np.abs(np.random.randn(n)) * 3
        low = price - np.abs(np.random.randn(n)) * 3
        open_ = price + np.random.randn(n) * 2
        volume = np.random.randint(100, 10000, size=n).astype(float)

        df = pd.DataFrame({
            "open": open_,
            "high": high,
            "low": low,
            "close": price,
            "volume": volume,
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h"),
        })
        self._cached_data = df
        return df

    def _simulate(self, ohlcv: Any, params: Dict[str, float]) -> Dict[str, Any]:
        """Core backtest simulation engine."""
        import pandas as pd

        close = ohlcv["close"].values
        high = ohlcv["high"].values
        low = ohlcv["low"].values
        n = len(close)

        momentum_w = params.get("momentum_weight", 0.3)
        trend_w = params.get("trend_weight", 0.3)
        volatility_w = params.get("volatility_weight", 0.2)
        dxy_w = params.get("dxy_correlation_weight", 0.2)
        total_w = momentum_w + trend_w + volatility_w + dxy_w
        if total_w > 0:
            momentum_w /= total_w
            trend_w /= total_w
            volatility_w /= total_w
            dxy_w /= total_w

        min_gec = params.get("min_gec_score", 0.50)
        min_combined = params.get("min_combined_score", 0.60)
        sl_mult = params.get("sl_atr_multiplier", 2.0)
        tp_mult = params.get("tp_atr_multiplier", 3.0)
        max_risk = params.get("max_risk_pct", 0.02)
        core_mult = params.get("core_multiplier", 0.5)
        inner_mult = params.get("inner_multiplier", 1.0)
        outer_mult = params.get("outer_multiplier", 1.5)

        equity = self.initial_capital
        equity_curve = [equity]
        trades: List[Dict[str, float]] = []

        lookback = 50
        for i in range(lookback, n - 1):
            window = close[i - lookback: i + 1]

            # RSI
            delta = np.diff(window)
            gain = np.where(delta > 0, delta, 0.0)
            loss = np.where(delta < 0, -delta, 0.0)
            avg_gain = np.mean(gain[-14:])
            avg_loss = np.mean(loss[-14:])
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100.0 - 100.0 / (1.0 + rs)
            rsi_norm = (rsi - 50.0) / 50.0

            # MACD
            ema_fast = self._ema(window, 12)
            ema_slow = self._ema(window, 26)
            macd_line = ema_fast - ema_slow
            signal_line = self._ema_from_arr(np.array([macd_line]), 9)
            hist = macd_line - signal_line
            hist_norm = np.clip(hist / (window[-1] * 0.01 + 1e-10), -1, 1)
            momentum_score = np.clip(0.6 * rsi_norm + 0.4 * float(hist_norm), -1, 1)

            # Trend: EMA crossover
            ema_f = self._ema(window, 9)
            ema_s = self._ema(window, 21)
            ema_diff = (ema_f - ema_s) / (window[-1] * 0.01 + 1e-10)
            trend_score = float(np.clip(ema_diff * 2, -1, 1))

            # Volatility: ATR proxy
            h_window = high[i - lookback: i + 1]
            l_window = low[i - lookback: i + 1]
            tr_vals = np.maximum(
                h_window - l_window,
                np.maximum(
                    np.abs(h_window - np.roll(close[i - lookback: i + 1], 1)),
                    np.abs(l_window - np.roll(close[i - lookback: i + 1], 1)),
                ),
            )
            atr_val = float(np.mean(tr_vals[-14:]))
            atr_pct = atr_val / (close[i] + 1e-10)
            if atr_pct < 0.003:
                vol_score = -0.3
            elif atr_pct < 0.01:
                vol_score = 0.5
            elif atr_pct < 0.02:
                vol_score = 0.8
            elif atr_pct < 0.04:
                vol_score = 0.3
            else:
                vol_score = -0.5
            vol_score = float(np.clip(vol_score, -1, 1))

            dxy_score = 0.0

            gec = momentum_w * momentum_score + trend_w * trend_score + volatility_w * vol_score + dxy_w * dxy_score
            gec = float(np.clip(gec, -1, 1))
            gec_abs = abs(gec)

            ema_mid = float(np.mean(window[-21:]))
            border_lower = ema_mid - outer_mult * atr_val
            border_upper = ema_mid + outer_mult * atr_val
            if border_upper > border_lower:
                price_pos = (close[i] - border_lower) / (border_upper - border_lower)
            else:
                price_pos = 0.5

            if gec > 0:
                border_score = max(0, 1.0 - abs(price_pos - 0.2) * 2)
            else:
                border_score = max(0, 1.0 - abs(price_pos - 0.8) * 2)
            border_score = float(np.clip(border_score, 0, 1))

            atr_ratio = atr_val / (float(np.mean(tr_vals[-50:])) + 1e-10)
            atr_ratio_min = params.get("atr_ratio_min", 0.15)
            atr_ratio_max = params.get("atr_ratio_max", 1.0)
            if atr_ratio_min <= atr_ratio <= atr_ratio_max:
                filter_score = 1.0
            elif atr_ratio < 0.5:
                filter_score = 0.5
            else:
                filter_score = 0.6

            combined = 0.50 * gec_abs + 0.30 * border_score + 0.20 * filter_score

            if gec_abs < min_gec or combined < min_combined:
                equity_curve.append(equity)
                continue

            direction = 1 if gec > 0 else -1

            entry_price = close[i]
            sl_dist = sl_mult * atr_val
            tp_dist = tp_mult * atr_val

            risk_amount = equity * max_risk
            sl_distance = max(sl_dist, 1e-6)
            tp_distance = max(tp_dist, 1e-6)

            # Simulate forward until SL/TP hit
            exit_price = entry_price
            hit_sl = False
            hit_tp = False
            for j in range(i + 1, min(i + 200, n)):
                if direction == 1:
                    if low[j] <= entry_price - sl_dist:
                        exit_price = entry_price - sl_dist
                        hit_sl = True
                        break
                    if high[j] >= entry_price + tp_dist:
                        exit_price = entry_price + tp_dist
                        hit_tp = True
                        break
                else:
                    if high[j] >= entry_price + sl_dist:
                        exit_price = entry_price + sl_dist
                        hit_sl = True
                        break
                    if low[j] <= entry_price - tp_dist:
                        exit_price = entry_price - tp_dist
                        hit_tp = True
                        break
                exit_price = close[j]

            if direction == 1:
                pnl_pct = (exit_price - entry_price) / (entry_price + 1e-10)
            else:
                pnl_pct = (entry_price - exit_price) / (entry_price + 1e-10)

            pnl_amount = equity * max_risk * pnl_pct * (tp_mult / sl_mult)
            equity += pnl_amount
            equity_curve.append(equity)

            trades.append({
                "direction": "LONG" if direction == 1 else "SHORT",
                "entry": entry_price,
                "exit": exit_price,
                "pnl": pnl_amount,
                "hit_tp": hit_tp,
            })

            i_next = i + 1

        return self._compute_metrics(equity_curve, trades)

    @staticmethod
    def _ema(series_arr: np.ndarray, span: int) -> float:
        """Exponential moving average — returns last value."""
        alpha = 2.0 / (span + 1)
        ema = series_arr[0]
        for val in series_arr[1:]:
            ema = alpha * val + (1 - alpha) * ema
        return float(ema)

    @staticmethod
    def _ema_from_arr(arr: np.ndarray, span: int) -> float:
        """EMA of a 1-element array (returns the value itself)."""
        if len(arr) == 0:
            return 0.0
        return float(arr[-1])

    @staticmethod
    def _compute_metrics(
        equity_curve: List[float], trades: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """Compute standard backtest performance metrics."""
        equity_arr = np.array(equity_curve)
        returns = np.diff(equity_arr) / (equity_arr[:-1] + 1e-10)
        returns = returns[np.isfinite(returns)]

        total_trades = len(trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
            }

        wins = sum(1 for t in trades if t["pnl"] > 0)
        losses = sum(1 for t in trades if t["pnl"] <= 0)
        win_rate = wins / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
        profit_factor = gross_profit / (gross_loss + 1e-10)

        peak = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - peak) / (peak + 1e-10)
        max_drawdown = float(abs(drawdown.min()))

        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252 * 24))
        else:
            sharpe = 0.0

        final_equity = float(equity_arr[-1])
        total_pnl_pct = (final_equity - equity_curve[0]) / (equity_curve[0] + 1e-10)

        return {
            "total_trades": total_trades,
            "winning_trades": wins,
            "losing_trades": losses,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "final_equity": final_equity,
            "total_pnl_pct": total_pnl_pct,
        }


# ---------------------------------------------------------------------------
# Parallel Evaluator
# ---------------------------------------------------------------------------

class ParallelEvaluator:
    """
    Evaluates a population of chromosomes in parallel using
    ``concurrent.futures.ProcessPoolExecutor``.
    """

    def __init__(self, n_workers: int = 4):
        self.n_workers = n_workers
        self._executor: Optional[ProcessPoolExecutor] = None

    def _get_executor(self) -> ProcessPoolExecutor:
        if self._executor is None:
            self._executor = ProcessPoolExecutor(max_workers=self.n_workers)
        return self._executor

    def evaluate_population(
        self,
        population: List[Chromosome],
        fitness_func: FitnessFunction,
        n_workers: Optional[int] = None,
    ) -> List[float]:
        """
        Evaluate all chromosomes in the population.

        Args:
            population: list of Chromosome objects to evaluate.
            fitness_func: FitnessFunction instance.
            n_workers: override worker count.

        Returns:
            List of fitness scores in the same order as the population.
        """
        if n_workers is not None:
            self.n_workers = n_workers

        if len(population) <= 10 or self.n_workers <= 1:
            return self._evaluate_sequential(population, fitness_func)

        return self._evaluate_parallel(population, fitness_func)

    def _evaluate_sequential(
        self, population: List[Chromosome], fitness_func: FitnessFunction
    ) -> List[float]:
        scores = []
        for chrom in population:
            score = fitness_func.evaluate(chrom.genes)
            chrom.fitness = score
            scores.append(score)
        return scores

    def _evaluate_parallel(
        self, population: List[Chromosome], fitness_func: FitnessFunction
    ) -> List[float]:
        executor = self._get_executor()
        future_to_idx = {}

        for idx, chrom in enumerate(population):
            params = copy.deepcopy(chrom.genes)
            future = executor.submit(fitness_func.evaluate, params)
            future_to_idx[future] = idx

        scores = [0.0] * len(population)
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                score = future.result(timeout=60)
            except Exception as e:
                logger.warning("Parallel evaluation failed for idx %d: %s", idx, e)
                score = -10.0
            population[idx].fitness = score
            scores[idx] = score

        return scores

    def shutdown(self):
        if self._executor is not None:
            self._executor.shutdown(wait=False)
            self._executor = None

    def __del__(self):
        self.shutdown()


# ---------------------------------------------------------------------------
# Convergence Analyzer
# ---------------------------------------------------------------------------

class ConvergenceAnalyzer:
    """Analyzes optimization convergence and detects stagnation."""

    def analyze(self, history: List[Tuple[int, float, float, float]]) -> Dict[str, Any]:
        """
        Compute convergence metrics from optimization history.

        Args:
            history: list of (generation, best_fitness, avg_fitness, worst_fitness).

        Returns:
            Dict with convergence metrics.
        """
        if len(history) < 2:
            return {
                "converged": False,
                "convergence_generation": -1,
                "improvement_rate": 0.0,
                "total_improvement": 0.0,
                "plateau_length": 0,
            }

        best_values = [h[1] for h in history]
        total_improvement = best_values[-1] - best_values[0]
        improvement_rate = total_improvement / len(history) if len(history) > 0 else 0.0

        # Detect convergence: no improvement in last 10% of generations
        plateau_window = max(5, len(history) // 10)
        recent = best_values[-plateau_window:]
        improvement_in_plateau = recent[-1] - recent[0]
        converged = abs(improvement_in_plateau) < 0.001

        convergence_gen = -1
        if converged:
            for gen_idx in range(len(best_values) - 1, plateau_window - 1, -1):
                window = best_values[gen_idx - plateau_window: gen_idx]
                if window[-1] - window[0] > 0.001:
                    convergence_gen = gen_idx
                    break

        plateau_length = 0
        for v in reversed(best_values):
            if abs(v - best_values[-1]) < 0.001:
                plateau_length += 1
            else:
                break

        return {
            "converged": converged,
            "convergence_generation": convergence_gen,
            "improvement_rate": improvement_rate,
            "total_improvement": total_improvement,
            "plateau_length": plateau_length,
        }

    def detect_premature_convergence(
        self, population: List[Chromosome], threshold: float = 0.05
    ) -> bool:
        """
        Detect if the population has converged prematurely.

        Checks if the standard deviation of fitness scores is below
        the threshold, indicating lack of diversity.
        """
        if len(population) < 5:
            return False

        fitness_vals = np.array([c.fitness for c in population])
        std = float(np.std(fitness_vals))
        mean = float(np.mean(fitness_vals))

        if abs(mean) < 1e-10:
            return std < threshold

        return std / (abs(mean) + 1e-10) < threshold

    def suggest_restart(self, history: List[Tuple[int, float, float, float]]) -> Tuple[bool, str]:
        """
        Suggest whether to restart the optimization.

        Returns:
            Tuple of (should_restart, reason).
        """
        if len(history) < 10:
            return False, "Not enough history to evaluate"

        metrics = self.analyze(history)

        if metrics["plateau_length"] > len(history) * 0.3:
            return True, (
                f"Plateau of {metrics['plateau_length']} generations "
                f"({metrics['plateau_length'] / len(history) * 100:.0f}% of total)"
            )

        if len(history) > 20:
            first_half = [h[1] for h in history[: len(history) // 2]]
            second_half = [h[1] for h in history[len(history) // 2:]]
            if max(second_half) <= max(first_half):
                return True, "No improvement in second half of optimization"

        return False, "Optimization appears healthy"


# ---------------------------------------------------------------------------
# Optimization Result
# ---------------------------------------------------------------------------

@dataclass
class OptimizationResult:
    """
    Complete result of a genetic optimization run.

    Stores the best parameters found, fitness history, and metadata.
    """

    best_params: Dict[str, float] = field(default_factory=dict)
    best_fitness: float = -np.inf
    history: List[Tuple[int, float, float, float]] = field(default_factory=list)
    convergence_generation: int = -1
    total_evaluations: int = 0
    param_space_name: str = ""
    symbol: str = ""
    elapsed_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "best_params": {k: round(v, 8) for k, v in self.best_params.items()},
            "best_fitness": round(self.best_fitness, 8),
            "history": [
                {
                    "generation": h[0],
                    "best_fitness": round(h[1], 8),
                    "avg_fitness": round(h[2], 8),
                    "worst_fitness": round(h[3], 8),
                }
                for h in self.history
            ],
            "convergence_generation": self.convergence_generation,
            "total_evaluations": self.total_evaluations,
            "param_space_name": self.param_space_name,
            "symbol": self.symbol,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "metadata": self.metadata,
            "saved_at": datetime.now().isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OptimizationResult":
        history = [
            (
                h["generation"],
                h["best_fitness"],
                h["avg_fitness"],
                h["worst_fitness"],
            )
            for h in data.get("history", [])
        ]
        return cls(
            best_params=data.get("best_params", {}),
            best_fitness=data.get("best_fitness", -np.inf),
            history=history,
            convergence_generation=data.get("convergence_generation", -1),
            total_evaluations=data.get("total_evaluations", 0),
            param_space_name=data.get("param_space_name", ""),
            symbol=data.get("symbol", ""),
            elapsed_seconds=data.get("elapsed_seconds", 0.0),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, path: str) -> "OptimizationResult":
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save(self, path: Optional[str] = None) -> str:
        """
        Save the result to a JSON file.

        Returns:
            Path to the saved file.
        """
        if path is None:
            SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"opt_{self.symbol}_{self.param_space_name}_{timestamp}.json"
            path = str(SAVED_MODELS_DIR / filename)

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        logger.info("Optimization result saved to %s", path)
        return path

    def load(self, path: str):
        """Load result from a JSON file in-place."""
        with open(path, "r") as f:
            data = json.load(f)

        loaded = self.from_dict(data)
        self.best_params = loaded.best_params
        self.best_fitness = loaded.best_fitness
        self.history = loaded.history
        self.convergence_generation = loaded.convergence_generation
        self.total_evaluations = loaded.total_evaluations
        self.param_space_name = loaded.param_space_name
        self.symbol = loaded.symbol
        self.elapsed_seconds = loaded.elapsed_seconds
        self.metadata = loaded.metadata


# ---------------------------------------------------------------------------
# Genetic Optimizer
# ---------------------------------------------------------------------------

class GeneticOptimizer:
    """
    Genetic algorithm optimizer for continuous parameter spaces.

    Implements selection, crossover, mutation, and elitism to evolve
    a population of parameter sets toward the optimal solution.
    """

    def __init__(
        self,
        population_size: int = 50,
        generations: int = 100,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        elite_ratio: float = 0.1,
    ):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_ratio = elite_ratio
        self._history: List[Tuple[int, float, float, float]] = []
        self._best_ever: Optional[Chromosome] = None

    def optimize(
        self,
        fitness_func: FitnessFunction,
        param_bounds: Dict[str, Tuple[float, float]],
        constraints: Optional[List[Callable[[Dict[str, float]], bool]]] = None,
        n_workers: int = 4,
    ) -> OptimizationResult:
        """
        Run the full genetic optimization.

        Args:
            fitness_func: FitnessFunction to evaluate candidates.
            param_bounds: dict mapping param names to (lower, upper).
            constraints: optional list of constraint functions.
            n_workers: parallel workers for evaluation.

        Returns:
            OptimizationResult with best parameters and history.
        """
        start_time = time.time()
        constraints = constraints or []
        total_evaluations = 0

        # Initialize population
        population = self._initialize_population(param_bounds)
        logger.info(
            "Initialized population of %d with %d parameters",
            self.population_size,
            len(param_bounds),
        )

        evaluator = ParallelEvaluator(n_workers=n_workers)

        for gen in range(self.generations):
            # Evaluate population
            scores = evaluator.evaluate_population(population, fitness_func)
            total_evaluations += len(scores)

            # Apply constraints — penalize invalid chromosomes
            for chrom in population:
                if not self._check_constraints(chrom.genes, constraints):
                    chrom.fitness -= 5.0

            # Track statistics
            fitness_vals = [c.fitness for c in population]
            best_fitness = max(fitness_vals)
            avg_fitness = float(np.mean(fitness_vals))
            worst_fitness = min(fitness_vals)

            self._history.append((gen, best_fitness, avg_fitness, worst_fitness))

            # Update best ever
            current_best = max(population, key=lambda c: c.fitness)
            if self._best_ever is None or current_best.fitness > self._best_ever.fitness:
                self._best_ever = current_best.clone()

            # Logging every 10 generations
            if gen % 10 == 0 or gen == self.generations - 1:
                logger.info(
                    "Gen %d/%d | Best: %.4f | Avg: %.4f | Worst: %.4f | Evals: %d",
                    gen + 1,
                    self.generations,
                    best_fitness,
                    avg_fitness,
                    worst_fitness,
                    total_evaluations,
                )

            # Evolve
            if gen < self.generations - 1:
                population = self._evolve(population, param_bounds, constraints)

        evaluator.shutdown()

        elapsed = time.time() - start_time

        # Normalize GEC weights in best result
        best_params = copy.deepcopy(self._best_ever.genes)
        best_params = self._normalize_gec_weights(best_params)

        analyzer = ConvergenceAnalyzer()
        conv_metrics = analyzer.analyze(self._history)
        conv_gen = conv_metrics.get("convergence_generation", -1)

        result = OptimizationResult(
            best_params=best_params,
            best_fitness=self._best_ever.fitness,
            history=self._history,
            convergence_generation=conv_gen,
            total_evaluations=total_evaluations,
            symbol=fitness_func.symbol,
            elapsed_seconds=elapsed,
            metadata={
                "population_size": self.population_size,
                "generations": self.generations,
                "mutation_rate": self.mutation_rate,
                "crossover_rate": self.crossover_rate,
                "elite_ratio": self.elite_ratio,
            },
        )

        logger.info(
            "Optimization complete: best_fitness=%.4f, evals=%d, elapsed=%.1fs",
            result.best_fitness,
            total_evaluations,
            elapsed,
        )

        return result

    def evolve(
        self,
        population: List[Chromosome],
        param_bounds: Dict[str, Tuple[float, float]],
        constraints: Optional[List[Callable]] = None,
    ) -> List[Chromosome]:
        """
        Evolve the population by one generation.

        Returns a new population of the same size.
        """
        constraints = constraints or []

        # Sort by fitness (descending)
        population = sorted(population, key=lambda c: c.fitness, reverse=True)

        # Elitism: carry over top individuals
        n_elite = max(1, int(len(population) * self.elite_ratio))
        new_population: List[Chromosome] = [p.clone() for p in population[:n_elite]]

        # Selection + crossover + mutation
        while len(new_population) < len(population):
            parent1 = self.select_parents(population, [c.fitness for c in population])
            parent2 = self.select_parents(population, [c.fitness for c in population])

            if random.random() < self.crossover_rate:
                child_genes = self.crossover(parent1, parent2)
            else:
                child_genes = parent1.genes.copy()

            # Mutate
            child_genes = self.mutate(child_genes, param_bounds)

            child = Chromosome(genes=child_genes)

            # Enforce constraints via projection
            self._project_to_feasible(child.genes, param_bounds, constraints)

            new_population.append(child)

        return new_population

    def select_parents(
        self,
        population: List[Chromosome],
        fitness_scores: List[float],
        tournament_size: int = 3,
    ) -> Chromosome:
        """
        Tournament selection: pick tournament_size random individuals
        and return the one with the highest fitness.
        """
        n = len(population)
        indices = random.sample(range(n), min(tournament_size, n))
        best_idx = max(indices, key=lambda i: fitness_scores[i])
        return population[best_idx]

    def crossover(
        self,
        parent1: Chromosome,
        parent2: Chromosome,
    ) -> Dict[str, float]:
        """
        Uniform crossover: for each gene, randomly pick from one parent.
        """
        child_genes = {}
        all_keys = set(parent1.genes.keys()) | set(parent2.genes.keys())

        for key in all_keys:
            if random.random() < 0.5:
                child_genes[key] = parent1.genes.get(key, parent2.genes.get(key, 0.0))
            else:
                child_genes[key] = parent2.genes.get(key, parent1.genes.get(key, 0.0))

        return child_genes

    def mutate(
        self,
        individual: Dict[str, float],
        bounds: Dict[str, Tuple[float, float]],
    ) -> Dict[str, float]:
        """
        Gaussian mutation within bounds.

        Each gene is mutated with probability ``self.mutation_rate``.
        The mutation magnitude is scaled to 20% of the gene's range.
        """
        mutated = dict(individual)

        for gene_name, (low, high) in bounds.items():
            if random.random() < self.mutation_rate:
                current = mutated.get(gene_name, (low + high) / 2)
                gene_range = high - low
                sigma = gene_range * 0.20
                new_val = current + random.gauss(0, sigma)
                new_val = max(low, min(high, new_val))
                mutated[gene_name] = new_val

        return mutated

    def _initialize_population(
        self, param_bounds: Dict[str, Tuple[float, float]]
    ) -> List[Chromosome]:
        """Create initial random population within bounds."""
        population = []
        for _ in range(self.population_size):
            genes = {}
            for name, (low, high) in param_bounds.items():
                genes[name] = random.uniform(low, high)
            population.append(Chromosome(genes=genes))
        return population

    def _check_constraints(
        self,
        genes: Dict[str, float],
        constraints: List[Callable[[Dict[str, float]], bool]],
    ) -> bool:
        """Check if a chromosome satisfies all constraints."""
        for constraint in constraints:
            if not constraint(genes):
                return False
        return True

    def _project_to_feasible(
        self,
        genes: Dict[str, float],
        param_bounds: Dict[str, Tuple[float, float]],
        constraints: List[Callable],
        max_attempts: int = 20,
    ):
        """
        Project a chromosome to the feasible region by random
        perturbation until all constraints are satisfied.
        """
        for _ in range(max_attempts):
            if self._check_constraints(genes, constraints):
                return

            # Try to fix weights (most common constraint violation)
            weight_keys = ["momentum_weight", "trend_weight", "volatility_weight", "dxy_correlation_weight"]
            if all(k in genes for k in weight_keys):
                total = sum(genes[k] for k in weight_keys)
                if total > 0:
                    for k in weight_keys:
                        genes[k] /= total

            # Fix border ordering
            border_keys = ["core_multiplier", "inner_multiplier", "outer_multiplier", "extended_multiplier"]
            if all(k in genes for k in border_keys):
                vals = sorted([genes[k] for k in border_keys])
                for i, k in enumerate(border_keys):
                    genes[k] = vals[i]

            # Fix ATR filter ordering
            if "atr_ratio_min" in genes and "atr_ratio_max" in genes:
                if genes["atr_ratio_min"] >= genes["atr_ratio_max"]:
                    genes["atr_ratio_min"] = genes["atr_ratio_max"] - 0.05

            # Fix TP > SL
            if "tp_atr_multiplier" in genes and "sl_atr_multiplier" in genes:
                if genes["tp_atr_multiplier"] <= genes["sl_atr_multiplier"]:
                    genes["tp_atr_multiplier"] = genes["sl_atr_multiplier"] + 0.5

        # Final bounds enforcement
        for name, (low, high) in param_bounds.items():
            if name in genes:
                genes[name] = max(low, min(high, genes[name]))

    def _normalize_gec_weights(self, params: Dict[str, float]) -> Dict[str, float]:
        """Normalize GEC weights to sum to 1.0."""
        weight_keys = ["momentum_weight", "trend_weight", "volatility_weight", "dxy_correlation_weight"]
        if not all(k in params for k in weight_keys):
            return params

        total = sum(params[k] for k in weight_keys)
        if total > 0:
            for k in weight_keys:
                params[k] = round(params[k] / total, 4)

        return params

    def get_history(self) -> List[Tuple[int, float, float, float]]:
        """Return the convergence history."""
        return list(self._history)


# ---------------------------------------------------------------------------
# Parameter Tuner (High-Level Interface)
# ---------------------------------------------------------------------------

class ParameterTuner:
    """
    High-level interface for optimizing Gold Edge and other strategy
    parameters using the genetic optimizer.
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else SAVED_MODELS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tune_gold_edge(
        self,
        symbol: str,
        generations: int = 50,
        population_size: int = 40,
        data: Optional[Any] = None,
    ) -> OptimizationResult:
        """
        Optimize Gold Edge strategy parameters for a given symbol.

        Optimizes GEC weights, ATR thresholds, border multipliers,
        entry scores, and risk parameters.
        """
        logger.info(
            "Tuning Gold Edge for %s (%d gen, pop=%d)",
            symbol, generations, population_size,
        )

        space = GoldEdgeParamSpace()
        fitness = FitnessFunction(symbol=symbol, data=data)

        optimizer = GeneticOptimizer(
            population_size=population_size,
            generations=generations,
            mutation_rate=0.12,
            crossover_rate=0.75,
            elite_ratio=0.1,
        )

        result = optimizer.optimize(
            fitness_func=fitness,
            param_bounds=space.get_bounds(),
            constraints=space.get_constraints(),
            n_workers=min(4, os.cpu_count() or 1),
        )

        result.param_space_name = "gold_edge"
        result.symbol = symbol

        save_path = self._save_result(result, "gold_edge", symbol)
        logger.info("Gold Edge optimization complete. Saved to %s", save_path)

        return result

    def tune_risk_params(
        self,
        symbol: str,
        generations: int = 30,
        population_size: int = 30,
        data: Optional[Any] = None,
    ) -> OptimizationResult:
        """
        Optimize risk management parameters for a given symbol.
        """
        logger.info(
            "Tuning risk params for %s (%d gen, pop=%d)",
            symbol, generations, population_size,
        )

        space = RiskParamSpace()
        fitness = FitnessFunction(symbol=symbol, data=data)

        optimizer = GeneticOptimizer(
            population_size=population_size,
            generations=generations,
            mutation_rate=0.15,
            crossover_rate=0.7,
            elite_ratio=0.15,
        )

        result = optimizer.optimize(
            fitness_func=fitness,
            param_bounds=space.get_bounds(),
            constraints=space.get_constraints(),
            n_workers=min(4, os.cpu_count() or 1),
        )

        result.param_space_name = "risk_params"
        result.symbol = symbol

        save_path = self._save_result(result, "risk", symbol)
        logger.info("Risk param optimization complete. Saved to %s", save_path)

        return result

    def tune_ensemble_weights(
        self,
        symbol: str,
        generations: int = 40,
        population_size: int = 30,
        data: Optional[Any] = None,
    ) -> OptimizationResult:
        """
        Optimize ensemble model weights for a given symbol.
        """
        logger.info(
            "Tuning ensemble weights for %s (%d gen, pop=%d)",
            symbol, generations, population_size,
        )

        space = EnsembleWeightSpace()
        fitness = FitnessFunction(symbol=symbol, data=data)

        optimizer = GeneticOptimizer(
            population_size=population_size,
            generations=generations,
            mutation_rate=0.15,
            crossover_rate=0.8,
            elite_ratio=0.1,
        )

        result = optimizer.optimize(
            fitness_func=fitness,
            param_bounds=space.get_bounds(),
            constraints=space.get_constraints(),
            n_workers=min(4, os.cpu_count() or 1),
        )

        result.param_space_name = "ensemble_weights"
        result.symbol = symbol

        save_path = self._save_result(result, "ensemble", symbol)
        logger.info("Ensemble weight optimization complete. Saved to %s", save_path)

        return result

    def compare_strategies(
        self,
        symbols: List[str],
        generations: int = 20,
        population_size: int = 25,
    ) -> Dict[str, OptimizationResult]:
        """
        Run Gold Edge optimization across multiple symbols and
        compare results.
        """
        logger.info(
            "Comparing strategies across %d symbols (%d gen each)",
            len(symbols), generations,
        )

        results: Dict[str, OptimizationResult] = {}
        for symbol in symbols:
            try:
                result = self.tune_gold_edge(
                    symbol=symbol,
                    generations=generations,
                    population_size=population_size,
                )
                results[symbol] = result
                logger.info(
                    "Symbol %s: best_fitness=%.4f, evals=%d",
                    symbol,
                    result.best_fitness,
                    result.total_evaluations,
                )
            except Exception as e:
                logger.error("Failed to optimize %s: %s", symbol, e)

        # Cross-symbol comparison summary
        if results:
            ranked = sorted(results.items(), key=lambda x: x[1].best_fitness, reverse=True)
            logger.info("=== Cross-Symbol Comparison ===")
            for rank, (sym, res) in enumerate(ranked, 1):
                logger.info(
                    "  #%d %s: fitness=%.4f, sharpe≈%.2f, dd=%.1f%%",
                    rank,
                    sym,
                    res.best_fitness,
                    res.best_params.get("min_combined_score", 0),
                    res.metadata.get("max_drawdown", 0) * 100,
                )

        return results

    def _save_result(
        self, result: OptimizationResult, category: str, symbol: str
    ) -> str:
        """Save an optimization result to disk."""
        category_dir = self.output_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{timestamp}.json"
        save_path = str(category_dir / filename)

        return result.save(save_path)

    def load_latest(
        self, category: str, symbol: str
    ) -> Optional[OptimizationResult]:
        """Load the most recent optimization result for a symbol."""
        category_dir = self.output_dir / category
        if not category_dir.exists():
            return None

        pattern = f"{symbol}_*.json"
        files = sorted(category_dir.glob(pattern), key=lambda f: f.stat().st_mtime)

        if not files:
            return None

        return OptimizationResult.from_json(str(files[-1]))

    def load_best_params(
        self, category: str, symbol: str
    ) -> Optional[Dict[str, float]]:
        """Load only the best parameters from the latest optimization."""
        result = self.load_latest(category, symbol)
        if result is None:
            return None
        return result.best_params


# ---------------------------------------------------------------------------
# Module-level convenience instances
# ---------------------------------------------------------------------------

_default_tuner: Optional[ParameterTuner] = None


def get_tuner() -> ParameterTuner:
    """Get or create the default ParameterTuner singleton."""
    global _default_tuner
    if _default_tuner is None:
        _default_tuner = ParameterTuner()
    return _default_tuner


def optimize_gold_edge(
    symbol: str,
    generations: int = 50,
    population_size: int = 40,
) -> OptimizationResult:
    """Convenience function: optimize Gold Edge for a symbol."""
    return get_tuner().tune_gold_edge(symbol, generations, population_size)


def optimize_risk(
    symbol: str,
    generations: int = 30,
    population_size: int = 30,
) -> OptimizationResult:
    """Convenience function: optimize risk params for a symbol."""
    return get_tuner().tune_risk_params(symbol, generations, population_size)


def optimize_ensemble(
    symbol: str,
    generations: int = 40,
    population_size: int = 30,
) -> OptimizationResult:
    """Convenience function: optimize ensemble weights for a symbol."""
    return get_tuner().tune_ensemble_weights(symbol, generations, population_size)
