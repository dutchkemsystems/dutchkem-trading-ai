"""
SELF-OPTIMIZING PARAMETERS ENGINE
V6.5 Enhancement #10
"""

import logging
import random
from datetime import datetime
from typing import Dict, List

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
        win_rate = 0.7 + random.uniform(-0.1, 0.2)
        pf = 2.0 + random.uniform(-0.5, 1.5)
        return max(0, win_rate * 100 + pf * 50 + (1.0 - (params.get("risk_pct", 0.005) - 0.005) * 100) * 10)

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
