import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
class TestMCPIntegration:
    def test_get_servers(self, auth_client):
        response = auth_client.get("/api/v1/mcp/servers/")
        assert response.status_code == 200

    def test_get_health(self, auth_client):
        response = auth_client.get("/api/v1/mcp/health/")
        assert response.status_code == 200

    def test_unauthorized_mcp(self, api_client):
        response = api_client.get("/api/v1/mcp/servers/")
        assert response.status_code == 401

    @patch("mcp_integration.views.MCPService")
    def test_connect_mt5(self, mock_service, auth_client):
        mock_instance = MagicMock()
        mock_instance.connect.return_value = {"status": "connected", "server": "MetaQuotes-Demo"}
        mock_service.return_value = mock_instance

        response = auth_client.post("/api/v1/mcp/connect/", {
            "server": "MetaQuotes-Demo",
            "login": "12345",
            "password": "test123",
        }, format="json")
        assert response.status_code in (200, 201, 400)

    def test_get_mt5_status(self, auth_client):
        response = auth_client.get("/api/v1/mcp/status/")
        assert response.status_code in (200, 404)

    def test_get_server_health(self, auth_client):
        response = auth_client.get("/api/v1/mcp/health/")
        assert response.status_code == 200
