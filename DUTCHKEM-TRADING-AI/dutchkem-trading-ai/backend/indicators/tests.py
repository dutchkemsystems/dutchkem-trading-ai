import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
class TestIndicatorsAPI:
    def test_get_timeframes(self, auth_client):
        response = auth_client.get("/api/v1/indicators/timeframes/")
        assert response.status_code == 200

    def test_get_indicators(self, auth_client):
        response = auth_client.get("/api/v1/indicators/")
        assert response.status_code == 200

    def test_get_indicator_values(self, auth_client):
        response = auth_client.get("/api/v1/indicators/values/")
        assert response.status_code == 200

    def test_unauthorized_indicators(self, api_client):
        response = api_client.get("/api/v1/indicators/")
        assert response.status_code == 401

    def test_get_indicators_with_symbol(self, auth_client):
        response = auth_client.get("/api/v1/indicators/?symbol=EURUSD")
        assert response.status_code == 200

    def test_calculate_indicators(self, auth_client):
        response = auth_client.post("/api/v1/indicators/calculate/", {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "indicators": ["RSI", "MACD"],
        }, format="json")
        assert response.status_code in (200, 201, 400)

    def test_calculate_indicators_unauthorized(self, api_client):
        response = api_client.post("/api/v1/indicators/calculate/", {
            "symbol": "EURUSD",
        }, format="json")
        assert response.status_code == 401

    def test_get_indicator_values_with_params(self, auth_client):
        response = auth_client.get("/api/v1/indicators/values/?symbol=EURUSD&timeframe=H1")
        assert response.status_code == 200
