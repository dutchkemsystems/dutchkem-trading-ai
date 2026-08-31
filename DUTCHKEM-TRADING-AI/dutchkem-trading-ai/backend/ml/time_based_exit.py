"""
V6 Time-Based Exit — Exit trades that haven't reached target within time limit.
V6 Dynamic Kelly — Dynamic position sizing using Kelly Criterion.
V6 Execution Optimizer — Optimize execution with slippage and spread management.
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Deque
from collections import deque

logger = logging.getLogger('ml.execution')


class TimeBasedExit:
    """Exit trades that haven't reached their target within a time limit."""
    
    def __init__(self):
        self.max_holding_time = {
            'scalp': 30,
            'swing': 180,
            'trend': 720,
        }
    
    def should_exit(self, entry_time: datetime, trade_type: str) -> Dict[str, Any]:
        """Determine if trade should be closed due to time."""
        max_time = self.max_holding_time.get(trade_type, 60)
        minutes_held = (datetime.now() - entry_time).total_seconds() / 60
        
        if minutes_held > max_time:
            return {'exit': True, 'reason': 'TIME_LIMIT', 'minutes_held': minutes_held}
        
        return {'exit': False, 'minutes_held': minutes_held, 'remaining': max_time - minutes_held}
    
    def get_progressive_exit(self, entry_time: datetime, trade_type: str, current_price: float, entry_price: float) -> Dict[str, Any]:
        """Progressive exit logic — close portions at time milestones."""
        minutes_held = (datetime.now() - entry_time).total_seconds() / 60
        max_time = self.max_holding_time.get(trade_type, 60)
        
        if minutes_held > max_time * 0.75:
            return {'close_percentage': 1.00, 'reason': '75%_TIME_LIMIT'}
        elif minutes_held > max_time * 0.5:
            return {'close_percentage': 0.50, 'reason': '50%_TIME_LIMIT'}
        
        return {'close_percentage': 0, 'reason': 'WITHIN_TIME'}


class DynamicKelly:
    """Dynamic position sizing using Kelly Criterion."""
    
    def __init__(self):
        self.trade_history: Deque[Dict] = deque(maxlen=100)
        self.win_rate = 0.0
        self.avg_win = 0.0
        self.avg_loss = 0.0
    
    def update_stats(self, trade: Dict):
        """Update win rate, average win, average loss."""
        self.trade_history.append(trade)
        
        if len(self.trade_history) >= 10:
            wins = [t for t in self.trade_history if t.get('profit', 0) > 0]
            losses = [t for t in self.trade_history if t.get('profit', 0) < 0]
            
            if wins:
                self.win_rate = len(wins) / len(self.trade_history)
                self.avg_win = sum(t['profit'] for t in wins) / len(wins)
            
            if losses:
                self.avg_loss = abs(sum(t['profit'] for t in losses) / len(losses))
    
    def calculate_kelly_fraction(self) -> float:
        """Calculate optimal Kelly fraction: f* = (p * b - q) / b."""
        if self.avg_loss == 0 or self.win_rate == 0:
            return 0.01
        
        b = self.avg_win / self.avg_loss
        f = (self.win_rate * b - (1 - self.win_rate)) / b
        return max(0.01, min(0.10, f))
    
    def get_position_size_multiplier(self) -> float:
        """Get position size multiplier based on Kelly fraction."""
        kelly_fraction = self.calculate_kelly_fraction()
        
        if self.win_rate > 0.70:
            return min(1.2, kelly_fraction * 100)
        elif self.win_rate > 0.60:
            return min(1.0, kelly_fraction * 80)
        else:
            return min(0.8, kelly_fraction * 60)
    
    def get_stats(self) -> Dict[str, float]:
        """Get current Kelly statistics."""
        return {
            'win_rate': self.win_rate,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'kelly_fraction': self.calculate_kelly_fraction(),
            'multiplier': self.get_position_size_multiplier(),
            'trade_count': len(self.trade_history),
        }


class ExecutionOptimizer:
    """Optimize execution with slippage and spread management."""
    
    def __init__(self):
        self.max_allowed_slippage = 0.5
        self.max_allowed_spread = 0.5
        self.min_required_liquidity = 5.0
    
    PIP_SIZES = {
        'JPY': 0.01, 'XAU': 0.1, 'XAG': 0.01,
        'BTC': 1.0, 'ETH': 0.1,
    }
    DEFAULT_PIP_SIZE = 0.0001
    
    SPREAD_MULTIPLIERS = {
        'forex_majors': 1.0,
        'forex_minors': 1.5,
        'commodities': 2.0,
        'indices': 2.5,
        'crypto': 3.0,
    }
    
    def get_pip_size(self, instrument: str) -> float:
        for key, pip in self.PIP_SIZES.items():
            if key in instrument.upper():
                return pip
        return self.DEFAULT_PIP_SIZE
    
    def get_spread_multiplier(self, instrument: str) -> float:
        inst_upper = instrument.upper()
        if any(x in inst_upper for x in ['EUR', 'GBP', 'USD', 'JPY']):
            return self.SPREAD_MULTIPLIERS['forex_majors']
        elif any(x in inst_upper for x in ['XAU', 'XAG', 'OIL']):
            return self.SPREAD_MULTIPLIERS['commodities']
        elif any(x in inst_upper for x in ['BTC', 'ETH', 'SOL']):
            return self.SPREAD_MULTIPLIERS['crypto']
        return self.SPREAD_MULTIPLIERS['indices']
    
    def check_slippage(self, expected_price: float, actual_price: float, instrument: str) -> Dict[str, Any]:
        """Check if slippage is acceptable."""
        pip_size = self.get_pip_size(instrument)
        slippage_pips = abs(actual_price - expected_price) / pip_size
        
        if slippage_pips > self.max_allowed_slippage:
            return {
                'acceptable': False,
                'slippage': slippage_pips,
                'recommendation': 'REJECT_ORDER',
            }
        return {
            'acceptable': True,
            'slippage': slippage_pips,
            'recommendation': 'ACCEPT_ORDER',
        }
    
    def check_spread(self, current_spread: float, instrument: str) -> Dict[str, Any]:
        """Check if spread is acceptable."""
        max_spread = self.max_allowed_spread * self.get_spread_multiplier(instrument)
        
        if current_spread > max_spread:
            return {
                'acceptable': False,
                'spread': current_spread,
                'max_spread': max_spread,
                'recommendation': 'WAIT_FOR_BETTER_SPREAD',
            }
        return {
            'acceptable': True,
            'spread': current_spread,
            'recommendation': 'EXECUTE_ORDER',
        }
    
    def get_optimal_order_type(self, liquidity: float) -> str:
        """Choose between market, limit, or stop orders."""
        if liquidity > self.min_required_liquidity:
            return 'MARKET'
        return 'LIMIT'
