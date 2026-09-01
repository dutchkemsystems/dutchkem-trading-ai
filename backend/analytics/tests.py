from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class TradingPerformanceViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)

    def test_get_performance(self):
        response = self.client.get("/api/v1/analytics/performance/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_performance_unauthorized(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/analytics/performance/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RiskAnalyticsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)

    def test_get_risk_analytics(self):
        response = self.client.get("/api/v1/analytics/risk/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SignalAnalyticsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)

    def test_get_signal_analytics(self):
        response = self.client.get("/api/v1/analytics/signals/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
