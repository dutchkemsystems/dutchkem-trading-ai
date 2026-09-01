from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from risk_management.models import RiskParameter, DrawdownMonitor, RiskAlert, DailyPerformance

User = get_user_model()


class RiskParameterTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com", is_staff=True
        )
        self.client.force_authenticate(user=self.user)
        self.risk_params = RiskParameter.objects.create(
            name="Default",
            max_daily_loss=2.0,
            max_drawdown=15.0,
            max_position_size=0.02,
            daily_growth_target=0.14,
            max_daily_trades=10,
        )

    def test_get_risk_parameters(self):
        response = self.client.get("/api/v1/risk/parameters/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_risk_parameter_model(self):
        self.assertEqual(self.risk_params.max_daily_loss, 2.0)
        self.assertTrue(self.risk_params.is_active)


class DrawdownMonitorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.monitor = DrawdownMonitor.objects.create(
            user=self.user,
            peak_equity=10000,
            current_equity=9500,
            starting_equity_today=10000,
            drawdown_percent=5.0,
        )

    def test_drawdown_calculation(self):
        self.assertEqual(self.monitor.drawdown_percent, 5.0)

    def test_drawdown_str(self):
        self.assertIn("testuser", str(self.monitor))


class RiskAlertTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )

    def test_create_alert(self):
        alert = RiskAlert.objects.create(
            user=self.user,
            alert_type="DAILY_LOSS",
            severity="HIGH",
            message="Daily loss limit reached",
        )
        self.assertEqual(alert.severity, "HIGH")
        self.assertFalse(alert.is_read)


class RiskDashboardAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)

    def test_get_dashboard(self):
        response = self.client.get("/api/v1/risk/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_alerts(self):
        response = self.client.get("/api/v1/risk/alerts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
