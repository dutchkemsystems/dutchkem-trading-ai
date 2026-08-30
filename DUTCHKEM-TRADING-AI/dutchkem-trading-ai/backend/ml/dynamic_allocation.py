"""
V6 Dynamic Asset Allocation — Allocate capital based on recent performance.
V6 Correlation Manager — Reduce position sizes when assets are highly correlated.
V6 Volatility Scaler — Scale position size based on current volatility.
"""
import logging
import math
from typing import Dict, Any, List, Optional
from collections import deque
import numpy as np

logger = logging.getLogger('ml.dynamic_allocation')


class DynamicAssetAllocation:
    """Allocate capital based on recent performance of each asset."""
    
    def __init__(self):
        self.asset_weights = {}
        self.performance_lookback = 20
        self.min_weight = 0.01
        self.max_weight = 0.25
    
    def calculate_weights(self, recent_performance: Dict[str, Dict]) -> Dict[str, float]:
        """Calculate optimal weights for each asset."""
        total_score = 0.0
        
        for asset, perf in recent_performance.items():
            score = (
                perf.get('sharpe_ratio', 0) * 0.35 +
                perf.get('win_rate', 0) * 0.25 +
                perf.get('profit_factor', 0) * 0.20 +
                perf.get('risk_reward', 0) * 0.20
            )
            self.asset_weights[asset] = max(0.0, score)
            total_score += self.asset_weights[asset]
        
        if total_score > 0:
            for asset in self.asset_weights:
                self.asset_weights[asset] /= total_score
                self.asset_weights[asset] = max(
                    self.min_weight,
                    min(self.max_weight, self.asset_weights[asset]),
                )
            
            total = sum(self.asset_weights.values())
            if total > 0:
                for asset in self.asset_weights:
                    self.asset_weights[asset] /= total
        
        return self.asset_weights
    
    def get_position_size_multiplier(self, symbol: str) -> float:
        """Get position size multiplier based on asset allocation."""
        weight = self.asset_weights.get(symbol, 0.05)
        
        if not self.asset_weights:
            return 1.0
        
        avg_weight = sum(self.asset_weights.values()) / len(self.asset_weights)
        if avg_weight == 0:
            return 1.0
        
        return weight / avg_weight


class CorrelationManager:
    """Reduce position sizes when assets are highly correlated."""
    
    def __init__(self):
        self.correlation_matrix = {}
        self.correlation_lookback = 50
        self.correlation_threshold = 0.70
        self.open_positions = []
    
    def update_correlations(self, price_data: Dict[str, List[float]]):
        """Update correlation matrix with latest data."""
        symbols = list(price_data.keys())
        
        for i, s1 in enumerate(symbols):
            for j, s2 in enumerate(symbols):
                if i < j:
                    p1 = price_data[s1].get('close', [])
                    p2 = price_data[s2].get('close', [])
                    
                    if len(p1) >= self.correlation_lookback and len(p2) >= self.correlation_lookback:
                        arr1 = np.array(p1[-self.correlation_lookback:])
                        arr2 = np.array(p2[-self.correlation_lookback:])
                        
                        if np.std(arr1) > 0 and np.std(arr2) > 0:
                            corr = float(np.corrcoef(arr1, arr2)[0, 1])
                        else:
                            corr = 0.0
                        
                        self.correlation_matrix[f"{min(s1,s2)}_{max(s1,s2)}"] = corr
    
    def calculate_correlation_penalty(self, symbol1: str, symbol2: str) -> float:
        """Calculate position size penalty for correlated assets."""
        key = f"{min(symbol1, symbol2)}_{max(symbol1, symbol2)}"
        corr = self.correlation_matrix.get(key, 0)
        
        if abs(corr) > self.correlation_threshold:
            penalty = 1.0 - (abs(corr) - self.correlation_threshold) / (1.0 - self.correlation_threshold)
            return max(0.3, penalty)
        return 1.0
    
    def get_adjusted_position_size(self, symbol: str, base_size: float) -> float:
        """Adjust position size based on correlations with open positions."""
        if not self.open_positions:
            return base_size
        
        total_penalty = 1.0
        count = 0
        
        for pos in self.open_positions:
            if pos.get('symbol') != symbol:
                penalty = self.calculate_correlation_penalty(symbol, pos['symbol'])
                total_penalty *= penalty
                count += 1
        
        if count > 0:
            total_penalty = total_penalty ** (1.0 / count)
        
        return base_size * total_penalty


class VolatilityScaler:
    """Scale position size based on current volatility."""
    
    def __init__(self):
        self.atr_multiplier = {
            'low': 1.2,
            'normal': 1.0,
            'high': 0.7,
            'extreme': 0.4,
        }
    
    def get_volatility_scale(self, symbol: str, current_atr: float, historical_atr_avg: float) -> float:
        """Calculate volatility scaling factor."""
        if historical_atr_avg <= 0:
            return 1.0
        
        ratio = current_atr / historical_atr_avg
        
        if ratio < 0.5:
            regime = 'low'
        elif ratio < 1.0:
            regime = 'normal'
        elif ratio < 1.8:
            regime = 'high'
        else:
            regime = 'extreme'
        
        return self.atr_multiplier[regime]
    
    def calculate_position_size(self, base_size: float, symbol: str, current_atr: float, historical_atr_avg: float) -> float:
        """Apply volatility scaling to position size."""
        scale = self.get_volatility_scale(symbol, current_atr, historical_atr_avg)
        return base_size * scale
