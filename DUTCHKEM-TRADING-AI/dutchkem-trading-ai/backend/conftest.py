import os
import sys

# Add the project root (parent of backend/) to sys.path so `strategies` and
# other non-Django-app packages are importable during tests.
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    user = User.objects.create_user(
        username="testtrader",
        email="trader@test.com",
        password="TestPass123!",
        first_name="Test",
        last_name="Trader",
        role="TRADER",
        balance=Decimal("100000"),
        equity=Decimal("100000"),
    )
    return user


@pytest.fixture
def auth_client(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="AdminPass123!",
        role="ADMIN",
    )


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def test_symbol(db):
    from trading.models import Symbol
    return Symbol.objects.create(
        name="EURUSD",
        description="Euro vs US Dollar",
        category="MAJOR",
        base_currency="EUR",
        quote_currency="USD",
        pip_size=0.0001,
        spread=1.0,
        contract_size=100000,
    )


@pytest.fixture
def test_trade(db, test_user, test_symbol):
    from trading.models import Trade
    return Trade.objects.create(
        user=test_user,
        symbol=test_symbol,
        position_type="BUY",
        volume=0.1,
        open_price=1.1200,
        status="OPEN",
    )


@pytest.fixture
def test_signal(db, test_symbol):
    from signals.models import Signal
    from indicators.models import Timeframe
    timeframe = Timeframe.objects.create(code="H1", name="1 Hour", minutes=60)
    return Signal.objects.create(
        symbol=test_symbol,
        timeframe=timeframe,
        signal_type="BUY",
        strength=Decimal("75.00"),
        confluence_score=Decimal("80.00"),
        entry_price=Decimal("1.1200"),
        stop_loss=Decimal("1.1150"),
        take_profit=Decimal("1.1300"),
        risk_reward_ratio=Decimal("2.00"),
        confidence=Decimal("85.00"),
        is_active=True,
        generated_by="system",
    )


@pytest.fixture
def mock_korapay():
    mock = MagicMock()
    mock.initialize_transaction.return_value = {
        "status": True,
        "data": {"authorization_url": "https://checkout.korapay.com/test", "access_code": "test"},
    }
    mock.verify_transaction.return_value = {
        "status": True,
        "data": {"status": "success", "channel": "card"},
    }
    mock.parse_webhook_event.return_value = {
        "event_type": "payment.success",
        "reference": "DK-TEST",
        "status": "success",
        "amount": 5000,
        "currency": "NGN",
        "channel": "card",
        "metadata": {},
        "paid_at": "2026-01-01T00:00:00Z",
    }
    return mock


@pytest.fixture
def mock_mt5():
    mock = MagicMock()
    mock.get_instance.return_value = mock
    mock.is_connected = True
    mock.stats = {
        "connected": True,
        "uptime": 100.0,
        "requests": 50,
        "errors": 0,
        "avg_latency_ms": 12.5,
    }
    mock.connect = AsyncMock(return_value={"success": True, "data": {"status": "connected"}})
    mock.disconnect = AsyncMock(return_value={"success": True})
    mock.health_check = AsyncMock(return_value={
        "status": "healthy",
        "connected": True,
        "latency_ms": 5.0,
        "stats": mock.stats,
    })
    mock.get_account_info = AsyncMock(return_value={
        "balance": 100000.0,
        "equity": 100000.0,
        "margin": 0.0,
        "free_margin": 100000.0,
        "leverage": 100,
    })
    mock.get_positions = AsyncMock(return_value=[])
    mock.get_orders = AsyncMock(return_value=[])
    mock.get_symbols = AsyncMock(return_value=[
        {"name": "EURUSD", "description": "Euro vs US Dollar"},
    ])
    mock.get_symbol_info = AsyncMock(return_value={
        "name": "EURUSD",
        "point": 0.0001,
        "digits": 5,
        "spread": 10,
    })
    mock.get_candles = AsyncMock(return_value=[
        {"time": "2026-01-01T00:00:00Z", "open": 1.1200, "high": 1.1250, "low": 1.1180, "close": 1.1230, "volume": 1000},
    ])
    mock.get_tick_data = AsyncMock(return_value={
        "bid": 1.1200, "ask": 1.1210, "spread": 10,
    })
    mock.open_position = AsyncMock(return_value={
        "success": True, "data": {"ticket": 12345}, "error": None,
    })
    mock.close_position = AsyncMock(return_value={"success": True, "data": {}})
    mock.modify_position = AsyncMock(return_value={"success": True, "data": {}})
    mock.place_pending_order = AsyncMock(return_value={"success": True, "data": {}})
    mock.cancel_order = AsyncMock(return_value={"success": True, "data": {}})
    mock.get_trade_history = AsyncMock(return_value=[])
    mock.get_performance_stats = AsyncMock(return_value={
        "total_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
    })
    mock.close = AsyncMock()
    return mock
