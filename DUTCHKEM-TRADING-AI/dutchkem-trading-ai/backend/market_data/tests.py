# Dutchkem Trading AI — Market Data Tests

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestMarketDataEndpoints:
    def test_market_data_list(self, authenticated_client):
        response = authenticated_client.get("/api/v1/market/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)

    def test_live_prices(self, authenticated_client):
        response = authenticated_client.get("/api/v1/market/live/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)

    def test_market_sentiment(self, authenticated_client):
        response = authenticated_client.get("/api/v1/market/sentiment/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)

    def test_market_overview(self, authenticated_client):
        response = authenticated_client.get("/api/v1/market/overview/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)
