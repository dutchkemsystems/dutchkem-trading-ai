# Trading Rules & Risk Management

## Core Risk Parameters

### Position Sizing
| Parameter | Value | Description |
|-----------|-------|-------------|
| MAX_POSITION_SIZE | 2% | Maximum risk per individual position |
| MAX_OPEN_POSITIONS | 5 | Maximum concurrent open positions |
| MAX_CORRELATION | 0.7 | Maximum correlation between open positions |

### Portfolio Protection
| Parameter | Value | Description |
|-----------|-------|-------------|
| MAX_DRAWDOWN | 15% | Maximum portfolio drawdown before trading halt |
| MAX_DAILY_LOSS | 3% | Maximum loss allowed per trading day |
| TARGET_ANNUAL_GROWTH | 40% | Annual return target |

### Entry Rules
| Parameter | Value | Description |
|-----------|-------|-------------|
| MIN_RISK_REWARD_RATIO | 2.0 | Minimum risk:reward ratio for trade entry |

## Trading Symbols

### Categories
1. **MAJOR** - Major forex pairs (EURUSD, GBPUSD, USDJPY, etc.)
2. **MINOR** - Minor forex pairs (EURGBP, EURJPY, etc.)
3. **EXOTIC** - Exotic forex pairs (USDTRY, USDZAR, etc.)
4. **COMMODITY** - Commodities (XAUUSD, XAGUSD, XAUUSD)
5. **CRYPTO** - Cryptocurrencies (BTCUSD, ETHUSD)
6. **INDEX** - Stock indices (US30, SPX500, NAS100)

### Symbol Attributes
Each trading symbol has:
- `pip_size` - Minimum price movement
- `spread` - Average spread in pips
- `contract_size` - Standard contract size
- `margin_requirement` - Margin requirement percentage

## Order Types

### Supported Orders
1. **MARKET** - Immediate execution at current market price
2. **LIMIT** - Execute at specified price or better
3. **STOP** - Execute when price reaches specified level
4. **STOP_LIMIT** - Conditional limit order

### Order Statuses
```
PENDING → FILLED / PARTIALLY_FILLED / CANCELLED / EXPIRED
```

### Trade Lifecycle
```
PENDING → OPEN → CLOSED / CANCELLED / REJECTED
```

## Risk Management Rules

### Entry Conditions
1. Risk:Reward ratio must be ≥ 2.0
2. Maximum position size ≤ 2% of equity
3. Total open positions ≤ 5
4. Correlation with existing positions ≤ 0.7
5. No trading during high-impact news events (configurable)

### Exit Conditions
1. Stop loss hit
2. Take profit hit
3. Trailing stop triggered
4. Manual close
5. Risk management system intervention

### Daily Risk Checks
1. Daily P&L ≤ -3% of starting equity → Trading halted
2. Maximum drawdown ≤ -15% of peak equity → Trading halted
3. Maximum open positions ≤ 5 → No new entries
4. Correlation check before each new entry

### Position Monitoring
- Real-time unrealized P&L calculation
- Margin level monitoring
- Automatic stop loss adjustment
- Trailing stop management

## Signal Types

### Signal Strength Levels
1. **STRONG_BUY** - High confidence buy signal
2. **BUY** - Moderate confidence buy signal
3. **NEUTRAL** - No clear direction
4. **SELL** - Moderate confidence sell signal
5. **STRONG_SELL** - High confidence sell signal

### Signal Generation
- 100+ technical indicators via OpenAlgo
- 68+ MT5 tools via SYNX-MT5-MCP
- 23 specialized AI agents from @gstack
- Multi-timeframe analysis
- Pattern recognition
- Sentiment analysis

### Signal Validation
1. Indicator confluence check
2. Multi-timeframe alignment
3. Risk:reward validation
4. Correlation analysis
5. Volatility assessment

## Expert Advisors (EAs)

### EA Statuses
1. **INACTIVE** - Not running
2. **BACKTESTING** - Running historical simulation
3. **LIVE** - Trading with real funds
4. **PAUSED** - Temporarily stopped
5. **ERROR** - Encountered error

### EA Management
- Create and configure EAs
- Backtest with historical data
- Deploy to live trading
- Monitor performance
- Pause/resume trading
- Emergency stop

### EA Performance Metrics
- Win rate
- Profit factor
- Sharpe ratio
- Maximum drawdown
- Average trade duration
- Risk-adjusted returns

## Portfolio Management

### Equity Tracking
- Real-time balance updates
- Unrealized P&L calculation
- Margin level monitoring
- Free margin tracking

### Performance Analytics
- Daily/Weekly/Monthly returns
- Win/Loss ratio
- Average win/loss size
- Maximum consecutive wins/losses
- Risk-adjusted metrics

### Reporting
- Trade history export
- Performance reports
- Risk analytics
- Custom date ranges

## Trading Schedule

### Market Hours
- Forex: 24/5 (Sunday 5pm - Friday 5pm EST)
- Commodities: Follow exchange hours
- Crypto: 24/7
- Indices: Follow exchange hours

### Trading Sessions
1. **Asian Session** - 7pm - 4am EST
2. **London Session** - 3am - 12pm EST
3. **New York Session** - 8am - 5pm EST

### News Events
- High-impact news avoidance (configurable)
- Pre-news position management
- Post-news entry rules
