"""
V6 Meta-Learning — Learns optimal learning strategy per market regime.
Dynamically adjusts AI model learning rates based on market conditions.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('ml.meta_learner')


class MetaLearner:
    """Learns the optimal learning strategy for each market regime."""
    
    def __init__(self):
        self.regime_learning_rates = {
            'trending_strong': 0.001,
            'trending_weak': 0.0008,
            'ranging': 0.0005,
            'volatile': 0.0001,
            'breakout': 0.0008,
            'low_liquidity': 0.002,
            'news': 0.0003,
        }
        self.performance_history = []
        self.adaptation_threshold = 0.95
        self.architecture_history = []
    
    def adjust_learning_rate(self, regime: str, recent_performance: float) -> float:
        """Adjust AI model learning rate based on regime and recent performance."""
        base_rate = self.regime_learning_rates.get(regime, 0.001)
        
        if recent_performance > self.adaptation_threshold:
            adjusted = base_rate * 0.8
        else:
            adjusted = base_rate * 1.2
        
        self.performance_history.append({
            'regime': regime,
            'performance': recent_performance,
            'base_rate': base_rate,
            'adjusted_rate': adjusted,
        })
        
        logger.info(
            "Meta-learning: regime=%s perf=%.3f rate=%.6f -> %.6f",
            regime, recent_performance, base_rate, adjusted,
        )
        return adjusted
    
    def adapt_architecture(self, performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt AI model architecture based on performance."""
        win_rate = performance_metrics.get('win_rate', 0.0)
        
        if win_rate < 0.60:
            changes = {
                'increase_hidden_layers': True,
                'adjust_dropout': 0.3,
                'new_activation': 'leaky_relu',
                'reason': f'Win rate {win_rate:.1%} below 60% threshold',
            }
        elif win_rate < 0.70:
            changes = {
                'increase_hidden_layers': False,
                'adjust_dropout': 0.2,
                'new_activation': 'relu',
                'reason': f'Win rate {win_rate:.1%} moderate, minor tuning',
            }
        else:
            changes = {'no_change': True, 'reason': f'Win rate {win_rate:.1%} optimal'}
        
        self.architecture_history.append(changes)
        logger.info("Architecture adaptation: %s", changes.get('reason', 'unknown'))
        return changes
    
    def get_regime_stats(self) -> Dict[str, Dict]:
        """Get performance statistics per regime."""
        stats = {}
        for entry in self.performance_history:
            regime = entry['regime']
            if regime not in stats:
                stats[regime] = {'count': 0, 'avg_performance': 0, 'avg_rate': 0}
            stats[regime]['count'] += 1
            stats[regime]['avg_performance'] += entry['performance']
            stats[regime]['avg_rate'] += entry['adjusted_rate']
        
        for regime in stats:
            count = stats[regime]['count']
            stats[regime]['avg_performance'] /= count
            stats[regime]['avg_rate'] /= count
        
        return stats
