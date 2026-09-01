# Dutchkem Trading AI — Analytics URLs

from django.urls import path

from . import views

urlpatterns = [
    path("performance/", views.TradingPerformanceView.as_view(), name="trading_performance"),
    path("risk/", views.RiskAnalyticsView.as_view(), name="risk_analytics"),
    path("signals/", views.SignalAnalyticsView.as_view(), name="signal_analytics"),
]
