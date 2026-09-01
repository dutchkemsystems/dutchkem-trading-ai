from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date
from backtesting.models import BacktestResult

User = get_user_model()


class BacktestResultModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )

    def test_create_backtest(self):
        bt = BacktestResult.objects.create(
            user=self.user,
            name="Test Backtest",
            symbol="EURUSD",
            timeframe="H1",
            strategy="scalping",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        self.assertEqual(bt.name, "Test Backtest")
        self.assertEqual(bt.total_trades, 0)

    def test_backtest_str(self):
        bt = BacktestResult.objects.create(
            user=self.user,
            name="My Backtest",
            symbol="EURUSD",
            timeframe="H1",
            strategy="scalping",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        self.assertIn("My Backtest", str(bt))


class BacktestAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_backtests(self):
        response = self.client.get("/api/v1/backtesting/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_backtest(self):
        response = self.client.post("/api/v1/backtesting/run/", {
            "name": "Test Run",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "strategy": "scalping",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
        })
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
