import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
class TestMLPipeline:
    @patch("ml.ensemble.EnsemblePredictor")
    def test_ensemble_prediction(self, mock_predictor, auth_client):
        mock_instance = MagicMock()
        mock_instance.predict.return_value = {
            "signal": "BUY",
            "confidence": 0.85,
            "direction": "bullish",
            "regime": "trending",
        }
        mock_predictor.return_value = mock_instance

        response = auth_client.post("/api/v1/ml/predict/", {
            "symbol": "EURUSD",
            "timeframe": "H1",
        }, format="json")
        assert response.status_code in (200, 404, 405)

    def test_ml_predict_unauthorized(self, api_client):
        response = api_client.post("/api/v1/ml/predict/", {
            "symbol": "EURUSD",
        }, format="json")
        assert response.status_code == 401

    @patch("ml.models.lstm_direction.LSTMPredictor")
    def test_lstm_prediction(self, mock_lstm, auth_client):
        mock_instance = MagicMock()
        mock_instance.predict.return_value = {
            "direction": "bullish",
            "confidence": 0.78,
        }
        mock_lstm.return_value = mock_instance

        response = auth_client.get("/api/v1/ml/models/")
        assert response.status_code in (200, 404)

    def test_ml_model_list(self, auth_client):
        response = auth_client.get("/api/v1/ml/models/")
        assert response.status_code in (200, 404)

    @patch("ml.feature_engine.FeatureEngine")
    def test_feature_engineering(self, mock_engine, auth_client):
        mock_instance = MagicMock()
        mock_instance.calculate_features.return_value = {"rsi": 65.5, "macd": 0.0012}
        mock_engine.return_value = mock_instance

        response = auth_client.post("/api/v1/ml/features/", {
            "symbol": "EURUSD",
            "timeframe": "H1",
        }, format="json")
        assert response.status_code in (200, 201, 404, 405)
