import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async

from market_data.consumers import (
    MarketDataConsumer,
    SignalConsumer,
    TradeConsumer,
    PortfolioConsumer,
)


def _make_scope(symbol=None, user=None):
    scope = {
        "type": "websocket",
        "path": f"/ws/market-data/{symbol}/" if symbol else "/ws/signals/",
        "query_string": b"",
        "headers": [],
        "url_route": {"kwargs": {"symbol": symbol}} if symbol else {"kwargs": {}},
        "user": user or MagicMock(is_anonymous=True),
        "session": {},
    }
    return scope


@pytest.mark.asyncio
class TestMarketDataConsumer:
    async def _connect_consumer(self, symbol="EURUSD"):
        application = MarketDataConsumer.as_asgi()
        communicator = WebsocketCommunicator(application, f"/ws/market-data/{symbol}/")
        communicator.scope["url_route"] = {"kwargs": {"symbol": symbol}}
        return communicator

    @patch("market_data.consumers.MarketDataConsumer._subscribe_to_mt5_ticks", new_callable=AsyncMock)
    @patch("market_data.consumers.MarketDataConsumer.get_live_prices", new_callable=AsyncMock, return_value=None)
    async def test_connection_established(self, mock_prices, mock_sub, db):
        communicator = await self._connect_consumer("EURUSD")
        connected, _ = await communicator.connect()
        assert connected

        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "connection_established"
        assert response["data"]["symbol"] == "EURUSD"

        await communicator.disconnect()

    @patch("market_data.consumers.MarketDataConsumer._subscribe_to_mt5_ticks", new_callable=AsyncMock)
    @patch("market_data.consumers.MarketDataConsumer.get_live_prices", new_callable=AsyncMock, return_value=None)
    async def test_ping_pong_heartbeat(self, mock_prices, mock_sub, db):
        communicator = await self._connect_consumer("EURUSD")
        await communicator.connect()
        await communicator.receive_json_from(timeout=5)

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "pong"

        await communicator.disconnect()

    @patch("market_data.consumers.MarketDataConsumer._subscribe_to_mt5_ticks", new_callable=AsyncMock)
    @patch("market_data.consumers.MarketDataConsumer.get_live_prices", new_callable=AsyncMock, return_value=None)
    async def test_invalid_json_handling(self, mock_prices, mock_sub, db):
        communicator = await self._connect_consumer("EURUSD")
        await communicator.connect()
        await communicator.receive_json_from(timeout=5)

        await communicator.send_to(text_data="not json")
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "error"

        await communicator.disconnect()

    @patch("market_data.consumers.MarketDataConsumer._get_candles", new_callable=AsyncMock, return_value=[])
    @patch("market_data.consumers.MarketDataConsumer._subscribe_to_mt5_ticks", new_callable=AsyncMock)
    @patch("market_data.consumers.MarketDataConsumer.get_live_prices", new_callable=AsyncMock, return_value=None)
    async def test_get_candles_request(self, mock_prices, mock_sub, mock_candles, db):
        communicator = await self._connect_consumer("EURUSD")
        await communicator.connect()
        await communicator.receive_json_from(timeout=5)

        await communicator.send_json_to({
            "type": "get_candles",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "count": 50,
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "candles"
        assert response["data"]["symbol"] == "EURUSD"

        await communicator.disconnect()

    @patch("market_data.consumers.MarketDataConsumer._unsubscribe_from_mt5_ticks", new_callable=AsyncMock)
    @patch("market_data.consumers.MarketDataConsumer._subscribe_to_mt5_ticks", new_callable=AsyncMock)
    @patch("market_data.consumers.MarketDataConsumer.get_live_prices", new_callable=AsyncMock, return_value=None)
    async def test_disconnect_cleanup(self, mock_prices, mock_sub, mock_unsub, db):
        communicator = await self._connect_consumer("EURUSD")
        await communicator.connect()
        await communicator.receive_json_from(timeout=5)

        await communicator.disconnect()
        mock_unsub.assert_called()

    @patch("market_data.consumers.MarketDataConsumer._subscribe_to_mt5_ticks", new_callable=AsyncMock)
    @patch("market_data.consumers.MarketDataConsumer.get_live_prices", new_callable=AsyncMock, return_value=None)
    async def test_price_update_event(self, mock_prices, mock_sub, db):
        communicator = await self._connect_consumer("EURUSD")
        await communicator.connect()
        await communicator.receive_json_from(timeout=5)

        await communicator.send_input({
            "type": "price_update",
            "data": {"symbol": "EURUSD", "bid": 1.1200, "ask": 1.1202},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "price_update"

        await communicator.disconnect()

    @patch("market_data.consumers.MarketDataConsumer._subscribe_to_mt5_ticks", new_callable=AsyncMock)
    @patch("market_data.consumers.MarketDataConsumer.get_live_prices", new_callable=AsyncMock, return_value=None)
    async def test_signal_update_event(self, mock_prices, mock_sub, db):
        communicator = await self._connect_consumer("EURUSD")
        await communicator.connect()
        await communicator.receive_json_from(timeout=5)

        await communicator.send_input({
            "type": "signal_update",
            "data": {"signal": "BUY", "strength": 85},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "signal_update"

        await communicator.disconnect()

    @patch("market_data.consumers.MarketDataConsumer._subscribe_to_mt5_ticks", new_callable=AsyncMock)
    @patch("market_data.consumers.MarketDataConsumer.get_live_prices", new_callable=AsyncMock, return_value=None)
    async def test_subscribe_to_additional_symbols(self, mock_prices, mock_sub, db):
        communicator = await self._connect_consumer("EURUSD")
        await communicator.connect()
        await communicator.receive_json_from(timeout=5)

        await communicator.send_json_to({
            "type": "subscribe",
            "symbols": ["GBPUSD", "USDJPY"],
        })
        await communicator.disconnect()


@pytest.mark.asyncio
class TestSignalConsumer:
    async def test_connection_established(self, db):
        communicator = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_ping_pong(self, db):
        communicator = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        await communicator.connect()

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "pong"

        await communicator.disconnect()

    async def test_signal_generated_event(self, db):
        communicator = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        await communicator.connect()

        await communicator.send_input({
            "type": "signal_generated",
            "data": {"symbol": "EURUSD", "signal": "STRONG_BUY", "strength": 92},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "signal_generated"

        await communicator.disconnect()

    async def test_confluence_update_event(self, db):
        communicator = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        await communicator.connect()

        await communicator.send_input({
            "type": "confluence_update",
            "data": {"confluence_score": 88, "indicators": ["RSI", "MACD"]},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "confluence_update"

        await communicator.disconnect()

    async def test_invalid_json(self, db):
        communicator = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        await communicator.connect()
        await communicator.send_to(text_data="invalid")
        await communicator.disconnect()

    async def test_multiple_clients_receive_broadcast(self, db):
        comm1 = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        comm2 = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        await comm1.connect()
        await comm2.connect()

        await comm1.send_input({
            "type": "signal_generated",
            "data": {"symbol": "EURUSD", "signal": "BUY"},
        })
        r1 = await comm1.receive_json_from(timeout=5)
        r2 = await comm2.receive_json_from(timeout=5)
        assert r1["type"] == "signal_generated"
        assert r2["type"] == "signal_generated"

        await comm1.disconnect()
        await comm2.disconnect()


@pytest.mark.asyncio
class TestTradeConsumer:
    async def _get_user(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        import uuid
        return await database_sync_to_async(User.objects.create_user)(
            username=f"tradeuser_{uuid.uuid4().hex[:8]}",
            email=f"trade_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123!",
        )

    async def test_anonymous_user_rejected(self, db):
        communicator = WebsocketCommunicator(TradeConsumer.as_asgi(), "/ws/trades/")
        connected, _ = await communicator.connect()
        assert not connected

    async def test_authenticated_user_connected(self, db):
        user = await self._get_user()
        communicator = WebsocketCommunicator(TradeConsumer.as_asgi(), "/ws/trades/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_ping_pong(self, db):
        user = await self._get_user()
        communicator = WebsocketCommunicator(TradeConsumer.as_asgi(), "/ws/trades/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "pong"

        await communicator.disconnect()

    async def test_trade_update_event(self, db):
        user = await self._get_user()
        communicator = WebsocketCommunicator(TradeConsumer.as_asgi(), "/ws/trades/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_input({
            "type": "trade_update",
            "data": {"trade_id": 1, "status": "CLOSED", "profit_loss": 150.00},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "trade_update"

        await communicator.disconnect()

    async def test_order_update_event(self, db):
        user = await self._get_user()
        communicator = WebsocketCommunicator(TradeConsumer.as_asgi(), "/ws/trades/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_input({
            "type": "order_update",
            "data": {"order_id": 1, "status": "FILLED"},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "order_update"

        await communicator.disconnect()


@pytest.mark.asyncio
class TestPortfolioConsumer:
    async def _get_user(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        import uuid
        return await database_sync_to_async(User.objects.create_user)(
            username=f"portuser_{uuid.uuid4().hex[:8]}",
            email=f"port_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123!",
        )

    async def test_anonymous_user_rejected(self, db):
        communicator = WebsocketCommunicator(PortfolioConsumer.as_asgi(), "/ws/portfolio/")
        connected, _ = await communicator.connect()
        assert not connected

    async def test_authenticated_user_connected(self, db):
        user = await self._get_user()
        communicator = WebsocketCommunicator(PortfolioConsumer.as_asgi(), "/ws/portfolio/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_ping_pong(self, db):
        user = await self._get_user()
        communicator = WebsocketCommunicator(PortfolioConsumer.as_asgi(), "/ws/portfolio/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "pong"

        await communicator.disconnect()

    async def test_portfolio_update_event(self, db):
        user = await self._get_user()
        communicator = WebsocketCommunicator(PortfolioConsumer.as_asgi(), "/ws/portfolio/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_input({
            "type": "portfolio_update",
            "data": {"equity": 105000, "balance": 100000, "margin": 5000},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "portfolio_update"

        await communicator.disconnect()

    async def test_risk_alert_event(self, db):
        user = await self._get_user()
        communicator = WebsocketCommunicator(PortfolioConsumer.as_asgi(), "/ws/portfolio/")
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_input({
            "type": "risk_alert",
            "data": {"alert_type": "HIGH_DRAWDOWN", "message": "Drawdown exceeded 10%"},
        })
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "risk_alert"

        await communicator.disconnect()
