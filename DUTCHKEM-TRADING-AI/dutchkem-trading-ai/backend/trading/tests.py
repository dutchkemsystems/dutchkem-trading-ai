# Dutchkem Trading AI — Trading Tests

from decimal import Decimal

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestSymbolModel:
    def test_create_symbol(self):
        from trading.models import Symbol

        symbol = Symbol.objects.create(
            name="EURUSD",
            description="Euro vs US Dollar",
            category="MAJOR",
            base_currency="EUR",
            quote_currency="USD",
            pip_size=Decimal("0.0001"),
            spread=Decimal("1.0"),
            contract_size=Decimal("100000"),
        )
        assert symbol.name == "EURUSD"
        assert symbol.category == "MAJOR"
        assert symbol.is_active is True

    def test_symbol_str(self):
        from trading.models import Symbol

        symbol = Symbol.objects.create(
            name="EURUSD", description="Euro vs US Dollar", category="MAJOR", base_currency="EUR", quote_currency="USD"
        )
        assert "EURUSD" in str(symbol)


@pytest.mark.django_db
class TestTradeModel:
    def test_create_trade(self, user):
        from trading.models import Symbol, Trade

        symbol = Symbol.objects.create(
            name="EURUSD", description="Euro vs US Dollar", category="MAJOR", base_currency="EUR", quote_currency="USD"
        )
        trade = Trade.objects.create(
            user=user,
            symbol=symbol,
            position_type="BUY",
            volume=Decimal("0.1"),
            open_price=Decimal("1.1200"),
            stop_loss=Decimal("1.1150"),
            take_profit=Decimal("1.1300"),
            status="OPEN",
        )
        assert trade.user == user
        assert trade.symbol == symbol
        assert trade.position_type == "BUY"
        assert trade.status == "OPEN"


@pytest.mark.django_db
class TestTradingEndpoints:
    def test_get_symbols(self, authenticated_client):
        from trading.models import Symbol

        Symbol.objects.create(
            name="EURUSD", description="Euro vs US Dollar", category="MAJOR", base_currency="EUR", quote_currency="USD"
        )
        response = authenticated_client.get("/api/v1/trading/symbols/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_trades(self, authenticated_client, user):
        from trading.models import Symbol, Trade

        symbol = Symbol.objects.create(
            name="EURUSD", description="Euro vs US Dollar", category="MAJOR", base_currency="EUR", quote_currency="USD"
        )
        Trade.objects.create(
            user=user,
            symbol=symbol,
            position_type="BUY",
            volume=Decimal("0.1"),
            open_price=Decimal("1.1200"),
            status="OPEN",
        )
        response = authenticated_client.get("/api/v1/trading/trades/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_portfolio(self, authenticated_client, user):
        response = authenticated_client.get("/api/v1/trading/portfolio/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)
