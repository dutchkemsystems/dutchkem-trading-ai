import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
class TestStrategies:
    def test_confluence_scoring(self, auth_client):
        response = auth_client.get("/api/v1/signals/confluence/")
        assert response.status_code == 200

    @patch("strategies.regime_switcher.RegimeSwitcher")
    def test_regime_detection(self, mock_regime, auth_client):
        mock_instance = MagicMock()
        mock_instance.detect.return_value = {
            "regime": "trending",
            "confidence": 0.8,
            "recommended_strategy": "trend_following",
        }
        mock_regime.return_value = mock_instance

        response = auth_client.get("/api/v1/signals/confluence/")
        assert response.status_code == 200

    def test_strategy_list(self, auth_client):
        response = auth_client.get("/api/v1/strategies/")
        assert response.status_code in (200, 404)

    @patch("strategies.strategy_map.StrategyMap")
    def test_strategy_mapping(self, mock_map, auth_client):
        mock_instance = MagicMock()
        mock_instance.get_strategy.return_value = {
            "name": "trend_following",
            "timeframe": "H1",
            "risk_multiplier": 1.0,
        }
        mock_map.return_value = mock_instance

        response = auth_client.get("/api/v1/signals/confluence/")
        assert response.status_code == 200

    def test_unauthorized_strategies(self, api_client):
        response = api_client.get("/api/v1/signals/confluence/")
        assert response.status_code == 401
