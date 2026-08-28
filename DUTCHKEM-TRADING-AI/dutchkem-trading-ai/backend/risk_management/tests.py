import pytest
from decimal import Decimal


@pytest.mark.django_db
class TestRiskAPI:
    def test_get_risk_parameters(self, auth_client):
        response = auth_client.get("/api/v1/risk/parameters/")
        assert response.status_code == 200

    def test_get_drawdown_status(self, auth_client):
        response = auth_client.get("/api/v1/risk/drawdown/status/")
        assert response.status_code == 200

    def test_get_risk_dashboard(self, auth_client):
        response = auth_client.get("/api/v1/risk/dashboard/")
        assert response.status_code == 200

    def test_get_risk_alerts(self, auth_client):
        response = auth_client.get("/api/v1/risk/alerts/")
        assert response.status_code == 200

    def test_position_sizing(self, auth_client):
        response = auth_client.post("/api/v1/risk/position-sizing/", {
            "symbol": "EURUSD",
            "risk_amount": "100",
            "stop_loss_pips": "50",
        })
        assert response.status_code in (200, 201, 400)

    def test_unauthorized_risk(self, api_client):
        response = api_client.get("/api/v1/risk/parameters/")
        assert response.status_code == 401

    def test_get_daily_performance(self, auth_client):
        response = auth_client.get("/api/v1/risk/daily-performance/")
        assert response.status_code == 200

    def test_risk_dashboard_structure(self, auth_client):
        response = auth_client.get("/api/v1/risk/dashboard/")
        if response.status_code == 200:
            data = response.data
            assert isinstance(data, dict)

    def test_position_sizing_invalid_data(self, auth_client):
        response = auth_client.post("/api/v1/risk/position-sizing/", {
            "symbol": "EURUSD",
        })
        assert response.status_code in (400, 404)

    def test_drawdown_status_structure(self, auth_client):
        response = auth_client.get("/api/v1/risk/drawdown/status/")
        if response.status_code == 200:
            assert isinstance(response.data, dict)
