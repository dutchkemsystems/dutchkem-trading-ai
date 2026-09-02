"""
Shared pytest fixtures for Dutchkem Trading AI test suite.
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a standard test user."""
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
        email="test@test.com",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin/staff test user."""
    return User.objects.create_user(
        username="admin",
        password="adminpass123",
        email="admin@test.com",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def api_client():
    """Unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture
def auth_client(test_user):
    """DRF API client authenticated as test_user."""
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client


@pytest.fixture
def admin_client(admin_user):
    """DRF API client authenticated as admin_user."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def test_symbol(db):
    """Create a test trading symbol (EURUSD)."""
    from trading.models import Symbol
    return Symbol.objects.create(
        name="EURUSD",
        display_name="Euro/US Dollar",
        category="MAJOR",
        pip_size=Decimal("0.0001"),
        contract_size=100000,
        is_active=True,
    )


@pytest.fixture
def test_symbol_gbpusd(db):
    """Create a second test trading symbol (GBPUSD)."""
    from trading.models import Symbol
    return Symbol.objects.create(
        name="GBPUSD",
        display_name="British Pound/US Dollar",
        category="MAJOR",
        pip_size=Decimal("0.0001"),
        contract_size=100000,
        is_active=True,
    )


@pytest.fixture
def test_trade(db, test_user, test_symbol):
    """Create a test trade."""
    from trading.models import Trade
    return Trade.objects.create(
        user=test_user,
        symbol=test_symbol,
        position_type="BUY",
        volume=Decimal("0.1"),
        open_price=Decimal("1.1200"),
        status="OPEN",
    )


@pytest.fixture
def sample_ohlcv():
    """Sample OHLCV data for testing indicators and strategies."""
    import random
    random.seed(42)
    base_price = 1.1200
    closes = []
    highs = []
    lows = []
    opens = []
    volumes = []

    for i in range(100):
        change = random.uniform(-0.002, 0.002)
        price = base_price + change * i
        h = price + random.uniform(0.0005, 0.002)
        l = price - random.uniform(0.0005, 0.002)
        o = price + random.uniform(-0.001, 0.001)
        closes.append(round(price, 6))
        highs.append(round(h, 6))
        lows.append(round(l, 6))
        opens.append(round(o, 6))
        volumes.append(random.randint(1000, 10000))

    return {
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }
