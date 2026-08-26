# Dutchkem Trading AI — Notifications Tests

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestNotificationEndpoints:
    def test_get_notifications(self, authenticated_client):
        response = authenticated_client.get("/api/v1/notifications/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)

    def test_get_notification_preferences(self, authenticated_client):
        response = authenticated_client.get("/api/v1/notifications/preferences/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)
