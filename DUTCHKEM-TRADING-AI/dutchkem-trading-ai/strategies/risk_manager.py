# Dutchkem Trading AI — Daily Risk Management Engine
# Targets: 0.14% daily growth, 2% max daily loss, 15% max drawdown

from decimal import Decimal
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class TradingStatus(Enum):
    ALLOWED = "TRADING_ALLOWED"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT_REACHED"
    DAILY_TRADES_LIMIT = "MAX_DAILY_TRADES_REACHED"
    DAILY_TARGET_REACHED = "DAILY_TARGET_REACHED"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT_REACHED"
    MARGIN_CALL = "MARGIN_CALL"


@dataclass
class DailyTradeRecord:
    trade_id: str
    symbol: str
    timeframe: str
    position_type: str
    entry_price: Decimal
    exit_price: Decimal
    volume: Decimal
    pnl: Decimal
    timestamp: datetime


@dataclass
class RiskAlert:
    alert_type: str
    severity: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime


class DailyRiskManager:
    """
    Daily Risk Management Engine for Dutchkem Trading AI
    
    Targets:
    - Daily Equity Growth: 0.14% (40% annualized / 365)
    - Monthly Equity Growth: ~4.2%
    - Annual Equity Growth: ~50%+ (compounded daily)
    - Max Daily Loss: 2%
    - Max Drawdown: 15%
    - Max Position Size: 1% per trade
    - Max Daily Trades: 10
    - Daily Target Lock: Trading stops at 0.4% daily gain
    """
    
    def __init__(self, account_equity: Decimal, account_id: str):
        self.equity = account_equity
        self.account_id = account_id
        
        # Daily targets
        self.daily_growth_target = Decimal('0.0014')  # 0.14% per day
        self.daily_loss_limit = Decimal('0.02')  # 2% max daily loss
        self.daily_target_lock = Decimal('0.004')  # 0.4% lock target
        
        # Position sizing
        self.max_position_size = Decimal('0.01')  # 1% per trade
        
        # Trade limits
        self.max_daily_trades = 10
        self.max_open_positions = 5
        
        # Drawdown limits
        self.max_drawdown = Decimal('0.15')  # 15%
        
        # Daily tracking
        self.current_daily_pnl = Decimal('0')
        self.daily_trades_count = 0
        self.daily_trades: List[DailyTradeRecord] = []
        self.peak_equity = account_equity
        
        # Status
        self.stop_trading = False
        self.stop_reason = None
        self.alerts: List[RiskAlert] = []
    
    def check_daily_limits(self) -> TradingStatus:
        """Check if trading is allowed based on daily limits"""
        
        # Check daily loss limit
        if self.current_daily_pnl < -(self.daily_loss_limit * self.equity):
            self.stop_trading = True
            self.stop_reason = TradingStatus.DAILY_LOSS_LIMIT
            self._add_alert(
                'DAILY_LOSS_LIMIT',
                'CRITICAL',
                f'Daily loss limit reached: {self.current_daily_pnl:.2f} ({abs(self.current_daily_pnl/self.equity*100):.2f}%)',
                {'daily_pnl': str(self.current_daily_pnl), 'limit': str(self.daily_loss_limit)}
            )
            return TradingStatus.DAILY_LOSS_LIMIT
        
        # Check max daily trades
        if self.daily_trades_count >= self.max_daily_trades:
            self.stop_trading = True
            self.stop_reason = TradingStatus.DAILY_TRADES_LIMIT
            self._add_alert(
                'DAILY_TRADES_LIMIT',
                'HIGH',
                f'Max daily trades reached: {self.daily_trades_count}',
                {'trades_count': self.daily_trades_count, 'limit': self.max_daily_trades}
            )
            return TradingStatus.DAILY_TRADES_LIMIT
        
        # Check daily target lock (stop trading after reaching target)
        if self.current_daily_pnl >= (self.daily_target_lock * self.equity):
            self.stop_trading = True
            self.stop_reason = TradingStatus.DAILY_TARGET_REACHED
            self._add_alert(
                'DAILY_TARGET_REACHED',
                'INFO',
                f'Daily target reached: {self.current_daily_pnl:.2f} ({self.current_daily_pnl/self.equity*100:.2f}%)',
                {'daily_pnl': str(self.current_daily_pnl), 'target': str(self.daily_target_lock)}
            )
            return TradingStatus.DAILY_TARGET_REACHED
        
        # Check max drawdown
        drawdown = self._calculate_drawdown()
        if drawdown >= self.max_drawdown:
            self.stop_trading = True
            self.stop_reason = TradingStatus.DRAWDOWN_LIMIT
            self._add_alert(
                'DRAWDOWN_LIMIT',
                'CRITICAL',
                f'Max drawdown reached: {drawdown*100:.2f}%',
                {'drawdown': str(drawdown), 'limit': str(self.max_drawdown)}
            )
            return TradingStatus.DRAWDOWN_LIMIT
        
        self.stop_trading = False
        self.stop_reason = None
        return TradingStatus.ALLOWED
    
    def calculate_position_size(
        self,
        stop_loss_pips: int,
        risk_per_trade: Decimal = Decimal('0.01'),
        symbol: str = ''
    ) -> Decimal:
        """
        Calculate position size based on daily risk budget
        
        Args:
            stop_loss_pips: Stop loss in pips
            risk_per_trade: Risk per trade (default 1%)
            symbol: Trading symbol
            
        Returns:
            Position size in lots
        """
        # Calculate risk amount (1% of equity per trade)
        risk_amount = self.equity * risk_per_trade
        
        # Adjust based on remaining daily loss budget
        remaining_daily_budget = (self.daily_loss_limit * self.equity) + self.current_daily_pnl
        if remaining_daily_budget < risk_amount:
            risk_amount = remaining_daily_budget
        
        # Calculate position size
        if stop_loss_pips > 0:
            position_size = risk_amount / Decimal(str(stop_loss_pips))
        else:
            position_size = Decimal('0')
        
        # Cap at max position size
        max_size = self.equity * self.max_position_size
        if position_size > max_size:
            position_size = max_size
        
        return round(position_size, 2)
    
    def update_daily_pnl(self, trade: DailyTradeRecord) -> None:
        """Update daily P&L after a trade closes"""
        self.current_daily_pnl += trade.pnl
        self.daily_trades_count += 1
        self.daily_trades.append(trade)
        
        # Update equity
        self.equity += trade.pnl
        
        # Update peak equity for drawdown calculation
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
    
    def reset_daily(self) -> None:
        """Reset daily counters (call at start of each trading day)"""
        self.current_daily_pnl = Decimal('0')
        self.daily_trades_count = 0
        self.daily_trades = []
        self.stop_trading = False
        self.stop_reason = None
        self.alerts = []
    
    def get_daily_status(self) -> Dict[str, Any]:
        """Get current daily risk status"""
        drawdown = self._calculate_drawdown()
        daily_growth = self.current_daily_pnl / self.equity * 100 if self.equity > 0 else 0
        
        return {
            'account_id': self.account_id,
            'equity': str(self.equity),
            'daily_pnl': str(self.current_daily_pnl),
            'daily_growth_percent': round(daily_growth, 4),
            'daily_trades_count': self.daily_trades_count,
            'max_daily_trades': self.max_daily_trades,
            'daily_loss_limit_percent': float(self.daily_loss_limit * 100),
            'daily_growth_target_percent': float(self.daily_growth_target * 100),
            'daily_target_lock_percent': float(self.daily_target_lock * 100),
            'max_drawdown_percent': float(self.max_drawdown * 100),
            'current_drawdown_percent': round(drawdown * 100, 2),
            'peak_equity': str(self.peak_equity),
            'stop_trading': self.stop_trading,
            'stop_reason': self.stop_reason.value if self.stop_reason else None,
            'remaining_daily_budget': str((self.daily_loss_limit * self.equity) + self.current_daily_pnl),
            'trading_status': self.check_daily_limits().value
        }
    
    def get_timeframe_allocation(self) -> Dict[str, Dict[str, Any]]:
        """Get recommended trade allocation per timeframe"""
        return {
            'M5': {
                'strategy': 'Scalping',
                'daily_trades': '5-10',
                'win_rate_target': '60-65%',
                'risk_reward': '1:1.5',
                'daily_growth_contribution': '1-2%',
                'max_risk_per_trade': '0.5%'
            },
            'M15': {
                'strategy': 'Momentum',
                'daily_trades': '3-5',
                'win_rate_target': '58-63%',
                'risk_reward': '1:1.8',
                'daily_growth_contribution': '0.8-1.5%',
                'max_risk_per_trade': '0.75%'
            },
            'M30': {
                'strategy': 'Swing',
                'daily_trades': '2-3',
                'win_rate_target': '55-60%',
                'risk_reward': '1:2',
                'daily_growth_contribution': '0.5-1%',
                'max_risk_per_trade': '1%'
            },
            'H1': {
                'strategy': 'Trend',
                'daily_trades': '1-2',
                'win_rate_target': '52-58%',
                'risk_reward': '1:2.5',
                'daily_growth_contribution': '0.3-0.6%',
                'max_risk_per_trade': '1%'
            },
            'H2': {
                'strategy': 'Position',
                'daily_trades': '0-1',
                'win_rate_target': '50-55%',
                'risk_reward': '1:3',
                'daily_growth_contribution': '0.2-0.4%',
                'max_risk_per_trade': '1%'
            },
            'H4': {
                'strategy': 'Strategic',
                'daily_trades': '0-1',
                'win_rate_target': '48-52%',
                'risk_reward': '1:4',
                'daily_growth_contribution': '0.1-0.3%',
                'max_risk_per_trade': '1%'
            }
        }
    
    def _calculate_drawdown(self) -> Decimal:
        """Calculate current drawdown from peak equity"""
        if self.peak_equity == 0:
            return Decimal('0')
        return (self.peak_equity - self.equity) / self.peak_equity
    
    def _add_alert(self, alert_type: str, severity: str, message: str, data: Dict) -> None:
        """Add a risk alert"""
        alert = RiskAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            data=data,
            timestamp=datetime.now()
        )
        self.alerts.append(alert)
    
    def can_trade(self, timeframe: str, symbol: str) -> bool:
        """Check if we can trade a specific symbol/timeframe"""
        if self.stop_trading:
            return False
        
        status = self.check_daily_limits()
        return status == TradingStatus.ALLOWED
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk report"""
        status = self.get_daily_status()
        allocation = self.get_timeframe_allocation()
        
        # Calculate expected daily performance
        expected_daily = Decimal('0')
        for tf, config in allocation.items():
            min_trades = int(config['daily_trades'].split('-')[0])
            max_trades = int(config['daily_trades'].split('-')[1])
            avg_trades = (min_trades + max_trades) / 2
            
            growth_min = Decimal(config['daily_growth_contribution'].split('-')[0].replace('%', '')) / 100
            growth_max = Decimal(config['daily_growth_contribution'].split('-')[1].replace('%', '')) / 100
            avg_growth = (growth_min + growth_max) / 2
            
            expected_daily += avg_growth
        
        return {
            'status': status,
            'timeframe_allocation': allocation,
            'expected_daily_growth': f"{expected_daily*100:.2f}%",
            'risk_parameters': {
                'daily_loss_limit': '2%',
                'daily_growth_target': '0.14%',
                'daily_target_lock': '0.4%',
                'max_drawdown': '15%',
                'max_position_size': '1%',
                'max_daily_trades': 10,
                'min_risk_reward': '1:2'
            },
            'performance_targets': {
                'daily': '0.14%',
                'monthly': '4.2%',
                'annual': '50%+'
            }
        }
