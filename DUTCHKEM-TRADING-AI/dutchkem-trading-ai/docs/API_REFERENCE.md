# Dutchkem Trading AI — API Reference

## Authentication

All endpoints require JWT authentication unless noted otherwise.

### Login
```http
POST /api/v1/auth/login/
Content-Type: application/json

{
  "username": "trader",
  "password": "password123"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "uuid",
    "username": "trader",
    "email": "trader@example.com"
  }
}
```

### Register
```http
POST /api/v1/auth/register/
Content-Type: application/json

{
  "username": "newtrader",
  "email": "trader@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Refresh Token
```http
POST /api/v1/auth/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## Trading

### List Symbols
```http
GET /api/v1/trading/symbols/

Response:
{
  "count": 28,
  "results": [
    {
      "id": "uuid",
      "name": "EURUSD",
      "description": "Euro vs US Dollar",
      "category": "MAJOR",
      "pip_size": "0.0001",
      "spread": "1.0"
    }
  ]
}
```

### List Trades
```http
GET /api/v1/trading/trades/

Response:
{
  "count": 15,
  "results": [
    {
      "id": "uuid",
      "symbol": "EURUSD",
      "position_type": "BUY",
      "volume": "0.1",
      "open_price": "1.1200",
      "status": "OPEN",
      "pnl": "50.00"
    }
  ]
}
```

### Create Order
```http
POST /api/v1/trading/orders/create/
Content-Type: application/json

{
  "symbol": "uuid",
  "order_type": "MARKET",
  "position_type": "BUY",
  "volume": "0.1",
  "price": "1.1200",
  "stop_loss": "1.1150",
  "take_profit": "1.1300"
}
```

## Signals

### List Signals
```http
GET /api/v1/signals/

Response:
{
  "count": 25,
  "results": [
    {
      "id": "uuid",
      "symbol": "EURUSD",
      "signal_type": "BUY",
      "strength": "85",
      "timeframe": "H1",
      "entry_price": "1.1200",
      "stop_loss": "1.1150",
      "take_profit": "1.1300"
    }
  ]
}
```

### Generate Signal
```http
POST /api/v1/signals/generate/
Content-Type: application/json

{
  "symbol": "uuid",
  "timeframe": "H1"
}
```

## Risk Management

### Get Risk Parameters
```http
GET /api/v1/risk/parameters/

Response:
{
  "max_daily_loss": "2.0",
  "daily_growth_target": "0.14",
  "max_drawdown": "15.0",
  "max_daily_trades": 10,
  "min_risk_reward_ratio": "2.0"
}
```

### Calculate Position Size
```http
POST /api/v1/risk/position-sizing/
Content-Type: application/json

{
  "symbol": "uuid",
  "stop_loss_pips": 50,
  "risk_per_trade": "1.0"
}

Response:
{
  "position_size": "0.02",
  "lot_size": 2000,
  "risk_amount": "100.00"
}
```

## Analytics

### Trading Performance
```http
GET /api/v1/analytics/performance/

Response:
{
  "today": {
    "total_trades": 8,
    "winning_trades": 5,
    "win_rate": 62.5,
    "total_pnl": 130.00
  },
  "week": { ... },
  "month": { ... },
  "daily_pnl": [
    { "date": "2026-08-26", "pnl": 130.00 },
    { "date": "2026-08-25", "pnl": -80.00 }
  ]
}
```

## WebSocket

### Connect to Market Data
```javascript
const ws = new WebSocket('ws://localhost/ws/market-data/EURUSD/');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'price_update') {
    console.log('Price:', data.data);
  }
};
```

### Connect to Signals
```javascript
const ws = new WebSocket('ws://localhost/ws/signals/');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'signal_generated') {
    console.log('New signal:', data.data);
  }
};
```
