# Exploration Report — Dutchkem Trading AI

## Date: 2026-08-28

---

## 1. Project Structure Analysis

### Root Level
- `config/settings.py` - Bare Django 6.1 default (SQLite, no apps) - CONFLICT
- `manage.py` - Points to `config.settings` - WRONG
- `dutchkem-trading-ai/` - Actual project directory

### Backend (`dutchkem-trading-ai/backend/`)
- `config/settings.py` - Real production config (PostgreSQL, all apps, Redis, Celery)
- `manage.py` - Points to `config.settings` - CORRECT
- 11 Django apps fully defined

### Frontend (`dutchkem-trading-ai/frontend/`)
- React 18 app with Redux store
- 10 page components exist
- 5 feature slices (auth, trading, signals, risk, market)

---

## 2. Issue Deep Dive

### 2.1 Root Config Conflict
**File**: `config/settings.py` (root)
- Default Django 6.1 settings
- SQLite database
- No INSTALLED_APPS beyond defaults
- No REST framework, no Celery, no Channels

**File**: `dutchkem-trading-ai/backend/config/settings.py`
- Full production config
- PostgreSQL with dj_database_url
- 30+ installed apps
- Redis, Celery, Channels configured
- JWT auth, CORS, rate limiting

**Resolution**: The root config is a leftover from project init. The backend config is the real one.

### 2.2 Missing Migrations
**Apps WITH migrations**: trading, signals, indicators
**Apps WITHOUT migrations**: accounts, risk_management, payments, expert_advisors, mcp_integration, market_data, notifications, analytics

### 2.3 Analytics Bug
**File**: `analytics/views.py:31-33`
```python
today_trades = all_trades.filter(close_time__date=today)  # BUG: should be closed_at
week_trades = all_trades.filter(close_time__date__gte=week_ago)  # BUG
month_trades = all_trades.filter(close_time__date__gte=month_ago)  # BUG
```

**File**: `analytics/views.py:50-56`
```python
wins = trades.filter(pnl__gt=0)  # BUG: should be profit_loss
losses = trades.filter(pnl__lt=0)  # BUG
total_pnl = sum(t.pnl or 0 for t in trades)  # BUG
```

**File**: `analytics/views.py:75-89`
```python
symbol_pnl[symbol]["pnl"] += float(trade.pnl or 0)  # BUG
tf_pnl[tf]["pnl"] += float(trade.pnl or 0)  # BUG
```

**File**: `analytics/views.py:95-96`
```python
day_trades = all_trades.filter(close_time__date=date)  # BUG
day_pnl = sum(float(t.pnl or 0) for t in day_trades)  # BUG
```

**File**: `analytics/views.py:192`
```python
active_signals = all_signals.filter(status="ACTIVE")  # BUG: Signal has no status field
```

### 2.4 N+1 Queries
**File**: `trading/views.py:36-46`
```python
class TradeListView(generics.ListAPIView):
    def get_queryset(self):
        queryset = Trade.objects.filter(user=self.request.user)  # Missing select_related
```

### 2.5 Hardcoded Secrets
**File**: `backend/config/settings.py:113`
```python
"PASSWORD": os.getenv("DB_PASSWORD", "dutchkem_secure_2024"),  # Hardcoded default
```

**File**: `backend/config/settings.py:11`
```python
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-this-in-production")  # Hardcoded default
```

### 2.6 Rate Limiting
**File**: `backend/config/settings.py:235`
```python
RATELIMIT_FAIL_OPEN = True  # Should be False for production
```

### 2.7 Korapay Webhook
**File**: `payments/gateways/korapay.py:106-110`
```python
def verify_webhook_signature(self, payload_body: bytes, signature: str) -> bool:
    secret = self.webhook_secret or self.secret_key
    if not secret:
        logger.warning("KORA_WEBHOOK_SECRET not set, skipping webhook verification")
        return True  # SECURITY ISSUE: Should reject when no secret
```

### 2.8 Missing Analytics Models
**File**: `analytics/` directory
- No `models.py` file exists
- Views exist but no caching models for expensive queries
- Need to add caching models

---

## 3. Frontend Analysis

### Existing Pages
1. Dashboard.js
2. Trading.js
3. Signals.js
4. RiskManagement.js
5. Payments.js
6. ExpertAdvisors.js
7. Analytics.js
8. Settings.js
9. Login.js
10. Register.js

### Missing Redux Slices
- payments slice
- eas (expert advisors) slice
- analytics slice
- notifications slice
- settings slice

### Store Configuration
Current slices: auth, trading, signals, risk, market
Missing: payments, eas, analytics, notifications, settings
