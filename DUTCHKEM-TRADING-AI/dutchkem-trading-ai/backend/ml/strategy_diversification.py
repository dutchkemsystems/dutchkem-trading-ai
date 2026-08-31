"""
V6 Strategy Diversification — Multiple strategies running simultaneously.
V6 Orchestrator — Complete pipeline integrating all V1-V6 enhancements.
"""
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import numpy as np

logger = logging.getLogger('ml.strategy_diversification')


class ScalpingStrategy:
    """Short-term scalping strategy."""
    
    def generate_signal(self, data: Dict) -> Optional[Dict]:
        closes = data.get('close', [])
        if len(closes) < 10:
            return None
        
        arr = np.array(closes[-10:])
        momentum = (arr[-1] - arr[0]) / arr[0] if arr[0] != 0 else 0
        
        if momentum > 0.001:
            return {'action': 'BUY', 'confidence': min(0.9, abs(momentum) * 100)}
        elif momentum < -0.001:
            return {'action': 'SELL', 'confidence': min(0.9, abs(momentum) * 100)}
        return None


class TrendFollowingStrategy:
    """Trend following strategy using moving averages."""
    
    def generate_signal(self, data: Dict) -> Optional[Dict]:
        closes = data.get('close', [])
        if len(closes) < 50:
            return None
        
        arr = np.array(closes)
        sma20 = float(np.mean(arr[-20:]))
        sma50 = float(np.mean(arr[-50:]))
        current = arr[-1]
        
        if sma20 > sma50 and current > sma20:
            confidence = min(0.9, (sma20 - sma50) / sma50 * 100)
            return {'action': 'BUY', 'confidence': confidence}
        elif sma20 < sma50 and current < sma20:
            confidence = min(0.9, (sma50 - sma20) / sma50 * 100)
            return {'action': 'SELL', 'confidence': confidence}
        return None


class MeanReversionStrategy:
    """Mean reversion strategy using Bollinger Bands."""
    
    def generate_signal(self, data: Dict) -> Optional[Dict]:
        closes = data.get('close', [])
        if len(closes) < 20:
            return None
        
        arr = np.array(closes[-20:])
        mean = float(np.mean(arr))
        std = float(np.std(arr))
        current = arr[-1]
        
        if current < mean - 2 * std:
            return {'action': 'BUY', 'confidence': min(0.85, abs(current - mean) / (2 * std))}
        elif current > mean + 2 * std:
            return {'action': 'SELL', 'confidence': min(0.85, abs(current - mean) / (2 * std))}
        return None


class BreakoutStrategy:
    """Breakout strategy using support/resistance."""
    
    def generate_signal(self, data: Dict) -> Optional[Dict]:
        closes = data.get('close', [])
        highs = data.get('high', [])
        lows = data.get('low', [])
        
        if len(closes) < 20 or len(highs) < 20 or len(lows) < 20:
            return None
        
        resistance = float(np.max(highs[-20:]))
        support = float(np.min(lows[-20:]))
        current = closes[-1]
        
        if current > resistance:
            return {'action': 'BUY', 'confidence': 0.75}
        elif current < support:
            return {'action': 'SELL', 'confidence': 0.75}
        return None


class NewsMomentumStrategy:
    """News-driven momentum strategy."""
    
    def generate_signal(self, data: Dict) -> Optional[Dict]:
        sentiment = data.get('news_sentiment', 0)
        volume = data.get('volume', [])
        
        if not volume or len(volume) < 5:
            return None
        
        avg_vol = np.mean(volume[-20:]) if len(volume) >= 20 else np.mean(volume)
        recent_vol = np.mean(volume[-5:])
        vol_spike = recent_vol / avg_vol if avg_vol > 0 else 1.0
        
        if sentiment > 0.5 and vol_spike > 1.5:
            return {'action': 'BUY', 'confidence': min(0.85, sentiment * vol_spike / 2)}
        elif sentiment < -0.5 and vol_spike > 1.5:
            return {'action': 'SELL', 'confidence': min(0.85, abs(sentiment) * vol_spike / 2)}
        return None


class StrategyDiversification:
    """Multiple strategies running simultaneously with dynamic weight adjustment."""
    
    def __init__(self):
        self.strategies = {
            'scalping': ScalpingStrategy(),
            'trend_following': TrendFollowingStrategy(),
            'mean_reversion': MeanReversionStrategy(),
            'breakout': BreakoutStrategy(),
            'news_momentum': NewsMomentumStrategy(),
        }
        
        self.strategy_weights = {
            'scalping': 0.30,
            'trend_following': 0.25,
            'mean_reversion': 0.15,
            'breakout': 0.15,
            'news_momentum': 0.15,
        }
        
        self.performance_history = {name: [] for name in self.strategies}
    
    def get_signal_combined(self, data: Dict) -> Optional[Dict]:
        """Combine signals from all strategies."""
        signals = []
        
        for name, strategy in self.strategies.items():
            try:
                signal = strategy.generate_signal(data)
                if signal:
                    signal['strategy'] = name
                    signal['weight'] = self.strategy_weights[name]
                    signals.append(signal)
            except Exception as e:
                logger.warning("Strategy %s failed: %s", name, e)
        
        if not signals:
            return None
        
        combined_confidence = 0.0
        for signal in signals:
            if signal['action'] == 'BUY':
                combined_confidence += signal['confidence'] * signal['weight']
            else:
                combined_confidence -= signal['confidence'] * signal['weight']
        
        if combined_confidence > 0.30:
            combined_action = 'BUY'
        elif combined_confidence < -0.30:
            combined_action = 'SELL'
        else:
            return None
        
        return {
            'action': combined_action,
            'confidence': abs(combined_confidence),
            'strategies_used': [s['strategy'] for s in signals],
            'strategy_signals': signals,
            'combined_score': combined_confidence,
        }
    
    def adjust_weights(self, performance: Dict[str, float]):
        """Dynamically adjust strategy weights based on performance."""
        total_performance = 0.0
        
        for name in self.strategies:
            perf = performance.get(name, 0)
            self.strategy_weights[name] = max(0.05, perf)
            total_performance += self.strategy_weights[name]
        
        if total_performance > 0:
            for name in self.strategy_weights:
                self.strategy_weights[name] /= total_performance
        
        logger.info("Strategy weights adjusted: %s", self.strategy_weights)
    
    def get_strategy_report(self) -> Dict[str, Any]:
        """Get report of all strategies and their weights."""
        return {
            'strategies': list(self.strategies.keys()),
            'weights': self.strategy_weights.copy(),
            'performance_history': {
                name: hist[-10:] for name, hist in self.performance_history.items()
            },
        }
