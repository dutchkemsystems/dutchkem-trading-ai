import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.utils import timezone
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async

from market_data.consumers import TradeConsumer, PortfolioConsumer


@pytest.mark.django_db
class TestSymbolModel:
    def test_create_symbol(self, test_symbol):
        assert test_symbol.name == "EURUSD"
        assert test_symbol.category == "MAJOR"
        assert test_symbol.is_active

    def test_symbol_str(self, test_symbol):
        assert str(test_symbol) == "EURUSD"

    def test_symbol_pip_size(self, test_symbol):
        assert test_symbol.pip_size == Decimal("0.0001")

    def test_symbol_contract_size(self, test_symbol):
        assert test_symbol.contract_size == 100000


@pytest.mark.django_db
class TestTradeModel:
    def test_create_trade(self, test_trade, test_user, test_symbol):
        assert test_trade.user == test_user
        assert test_trade.symbol == test_symbol
        assert test_trade.position_type == "BUY"
        assert test_trade.volume == Decimal("0.1")
        assert test_trade.status == "OPEN"

    def test_trade_str(self, test_trade):
        assert "BUY" in str(test_trade)
        assert "EURUSD" in str(test_trade)

    def test_trade_duration(self, test_trade):
        duration = test_trade.duration
        assert duration is not None
        assert duration.total_seconds() >= 0

    def test_trade_profit_loss_default(self, test_trade):
        assert test_trade.profit_loss == Decimal("0")

    def test_close_trade(self, test_trade):
        test_trade.status = "CLOSED"
        test_trade.close_price = Decimal("1.1300")
        test_trade.closed_at = timezone.now()
        test_trade.profit_loss = Decimal("100.50")
        test_trade.save()
        test_trade.refresh_from_db()
        assert test_trade.status == "CLOSED"
        assert test_trade.close_price == Decimal("1.1300")
        assert test_trade.profit_loss == Decimal("100.50")

    def test_trade_types(self, db, test_user, test_symbol):
        from trading.models import Trade
        for ptype in ["BUY", "SELL"]:
            trade = Trade.objects.create(
                user=test_user,
                symbol=test_symbol,
                position_type=ptype,
                volume=0.05,
                open_price=1.1200,
                status="OPEN",
            )
            assert trade.position_type == ptype


@pytest.mark.django_db
class TestTradingAPI:
    def test_get_symbols(self, auth_client, test_symbol):
        response = auth_client.get("/api/v1/trading/symbols/")
        assert response.status_code == 200

    def test_get_trades(self, auth_client, test_trade):
        response = auth_client.get("/api/v1/trading/trades/")
        assert response.status_code == 200

    def test_get_positions(self, auth_client):
        response = auth_client.get("/api/v1/trading/positions/")
        assert response.status_code == 200

    def test_create_trade(self, auth_client, test_symbol):
        response = auth_client.post("/api/v1/trading/trades/create/", {
            "symbol": str(test_symbol.id),
            "position_type": "SELL",
            "volume": "0.05",
            "open_price": "1.1300",
        })
        assert response.status_code in (200, 201)

    def test_create_trade_invalid_symbol(self, auth_client):
        import uuid
        response = auth_client.post("/api/v1/trading/trades/create/", {
            "symbol": str(uuid.uuid4()),
            "position_type": "BUY",
            "volume": "0.05",
            "open_price": "1.1300",
        })
        assert response.status_code in (400, 404)

    def test_close_trade(self, auth_client, test_trade):
        response = auth_client.post(f"/api/v1/trading/trades/{test_trade.id}/close/")
        assert response.status_code in (200, 400)

    def test_get_portfolio(self, auth_client):
        response = auth_client.get("/api/v1/trading/portfolio/")
        assert response.status_code == 200

    def test_unauthorized_trades(self, api_client):
        response = api_client.get("/api/v1/trading/trades/")
        assert response.status_code == 401

    def test_get_orders(self, auth_client):
        response = auth_client.get("/api/v1/trading/orders/")
        assert response.status_code == 200

    def test_create_order(self, auth_client, test_symbol):
        response = auth_client.post("/api/v1/trading/orders/create/", {
            "symbol": str(test_symbol.id),
            "order_type": "LIMIT",
            "position_type": "BUY",
            "volume": "0.05",
            "price": "1.1100",
        })
        assert response.status_code in (200, 201, 400)


@pytest.mark.asyncio
class TestTradeWebSocket:
    async def test_anonymous_rejected(self, db):
        communicator = WebsocketCommunicator(TradeConsumer.as_asgi(), "/ws/trades/")
        connected, _ = await communicator.connect()
        assert not connected

    async def test_authenticated_connection(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = await database_sync_to_async(User.objects.create_user)(
            username="tradews", email="trade@test.com", password="TestPass123!"
        )

        communicator = WebsocketCommunicator(TradeConsumer.as_asgi(), "/ws/trades/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_trade_consumer_ping_pong(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = await database_sync_to_async(User.objects.create_user)(
            username="tradews2", email="trade2@test.com", password="TestPass123!"
        )

        communicator = WebsocketCommunicator(TradeConsumer.as_asgi(), "/ws/trades/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "pong"
        await communicator.disconnect()

    async def test_trade_update_broadcast(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = await database_sync_to_async(User.objects.create_user)(
            username="tradews3", email="trade3@test.com", password="TestPass123!"
        )

        communicator = WebsocketCommunicator(TradeConsumer.as_asgi(), "/ws/trades/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_input({
            "type": "trade_update",
            "data": {"trade_id": 1, "status": "CLOSED", "pnl": 250.00},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "trade_update"
        await communicator.disconnect()

    async def test_order_update_broadcast(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = await database_sync_to_async(User.objects.create_user)(
            username="tradews4", email="trade4@test.com", password="TestPass123!"
        )

        communicator = WebsocketCommunicator(TradeConsumer.as_asgi(), "/ws/trades/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_input({
            "type": "order_update",
            "data": {"order_id": 1, "type": "LIMIT", "status": "FILLED"},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "order_update"
        await communicator.disconnect()


@pytest.mark.asyncio
class TestPortfolioWebSocket:
    async def test_anonymous_rejected(self, db):
        communicator = WebsocketCommunicator(PortfolioConsumer.as_asgi(), "/ws/portfolio/")
        connected, _ = await communicator.connect()
        assert not connected

    async def test_authenticated_connection(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = await database_sync_to_async(User.objects.create_user)(
            username="portws", email="port@test.com", password="TestPass123!"
        )

        communicator = WebsocketCommunicator(PortfolioConsumer.as_asgi(), "/ws/portfolio/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_portfolio_update_event(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = await database_sync_to_async(User.objects.create_user)(
            username="portws2", email="port2@test.com", password="TestPass123!"
        )

        communicator = WebsocketCommunicator(PortfolioConsumer.as_asgi(), "/ws/portfolio/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_input({
            "type": "portfolio_update",
            "data": {"equity": 105000, "margin_level": 200},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "portfolio_update"
        await communicator.disconnect()

    async def test_risk_alert_event(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = await database_sync_to_async(User.objects.create_user)(
            username="portws3", email="port3@test.com", password="TestPass123!"
        )

        communicator = WebsocketCommunicator(PortfolioConsumer.as_asgi(), "/ws/portfolio/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_input({
            "type": "risk_alert",
            "data": {"alert": "MAX_DRAWDOWN", "level": "CRITICAL"},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "risk_alert"
        await communicator.disconnect()
