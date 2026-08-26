# Dutchkem Trading AI — Strategies Package
# Contains timeframe-specific strategies, risk management, and confluence scoring

from .timeframe_strategies import (
    M5ScalpingStrategy,
    M15MomentumStrategy,
    M30SwingStrategy,
    H1TrendStrategy,
    H2PositionStrategy,
    H4StrategicStrategy,
    TIMEFRAME_STRATEGIES,
    get_strategy,
    calculate_signal
)

from .risk_manager import (
    DailyRiskManager,
    TradingStatus,
    DailyTradeRecord,
    RiskAlert
)

from .confluence import (
    MultiTimeframeConfluence,
    SignalDirection,
    ConfluenceLevel,
    TimeframeSignal,
    ConfluenceResult,
    confluence_engine
)

__all__ = [
    # Timeframe Strategies
    'M5ScalpingStrategy',
    'M15MomentumStrategy',
    'M30SwingStrategy',
    'H1TrendStrategy',
    'H2PositionStrategy',
    'H4StrategicStrategy',
    'TIMEFRAME_STRATEGIES',
    'get_strategy',
    'calculate_signal',
    
    # Risk Management
    'DailyRiskManager',
    'TradingStatus',
    'DailyTradeRecord',
    'RiskAlert',
    
    # Confluence
    'MultiTimeframeConfluence',
    'SignalDirection',
    'ConfluenceLevel',
    'TimeframeSignal',
    'ConfluenceResult',
    'confluence_engine'
]
