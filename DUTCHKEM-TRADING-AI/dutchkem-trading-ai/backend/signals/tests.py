import pytest
from unittest.mock import patch, MagicMock
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async

from market_data.consumers import SignalConsumer


@pytest.mark.django_db
class TestSignalsAPI:
    def test_get_signals(self, auth_client):
        response = auth_client.get("/api/v1/signals/")
        assert response.status_code == 200

    def test_get_active_signals(self, auth_client):
        response = auth_client.get("/api/v1/signals/active/")
        assert response.status_code == 200

    def test_get_confluence(self, auth_client):
        response = auth_client.get("/api/v1/signals/confluence/")
        assert response.status_code == 200

    def test_unauthorized_signals(self, api_client):
        response = api_client.get("/api/v1/signals/")
        assert response.status_code == 401

    def test_get_signals_with_filters(self, auth_client):
        response = auth_client.get("/api/v1/signals/?symbol=EURUSD&timeframe=H1")
        assert response.status_code == 200

    def test_get_signal_detail(self, auth_client):
        response = auth_client.get("/api/v1/signals/1/")
        assert response.status_code in (200, 404)


@pytest.mark.django_db
class TestSignalGeneration:
    @patch("signals.views.SignalService")
    def test_generate_signal(self, mock_service, auth_client):
        mock_instance = MagicMock()
        mock_instance.generate.return_value = {"signal": "BUY", "strength": 85}
        mock_service.return_value = mock_instance

        response = auth_client.post("/api/v1/signals/generate/", {
            "symbol": "EURUSD",
            "timeframe": "H1",
        }, format="json")
        assert response.status_code in (200, 201, 400)

    def test_generate_signal_unauthorized(self, api_client):
        response = api_client.post("/api/v1/signals/generate/", {
            "symbol": "EURUSD",
            "timeframe": "H1",
        }, format="json")
        assert response.status_code == 401

    def test_generate_signal_missing_params(self, auth_client):
        response = auth_client.post("/api/v1/signals/generate/", {}, format="json")
        assert response.status_code in (400, 404)


@pytest.mark.asyncio
class TestSignalWebSocket:
    async def test_signal_consumer_connection(self, db):
        communicator = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_signal_consumer_ping_pong(self, db):
        communicator = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        await communicator.connect()

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "pong"
        await communicator.disconnect()

    async def test_signal_consumer_broadcast(self, db):
        comm1 = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        comm2 = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        await comm1.connect()
        await comm2.connect()

        await comm1.send_input({
            "type": "signal_generated",
            "data": {"symbol": "EURUSD", "signal": "BUY", "strength": 85},
        })
        resp1 = await comm1.receive_json_from(timeout=5)
        resp2 = await comm2.receive_json_from(timeout=5)
        assert resp1["type"] == "signal_generated"
        assert resp2["type"] == "signal_generated"

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_signal_consumer_disconnection(self, db):
        communicator = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        await communicator.connect()
        await communicator.disconnect()

    async def test_signal_consumer_invalid_json(self, db):
        communicator = WebsocketCommunicator(SignalConsumer.as_asgi(), "/ws/signals/")
        await communicator.connect()
        await communicator.send_to(text_data="not json")
        await communicator.disconnect()
