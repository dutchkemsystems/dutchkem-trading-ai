from django.urls import path

from . import views

urlpatterns = [
    path("parameters/", views.RiskParameterView.as_view(), name="risk_parameters"),
    path("position-sizing/", views.PositionSizingView.as_view(), name="position_sizing"),
    path("drawdown/", views.DrawdownMonitorView.as_view(), name="drawdown_monitor"),
    path("drawdown/status/", views.DrawdownStatusView.as_view(), name="drawdown_status"),
    path("alerts/", views.RiskAlertListView.as_view(), name="risk_alerts"),
    path("dashboard/", views.RiskDashboardView.as_view(), name="risk_dashboard"),
    path("daily-performance/", views.DailyPerformanceView.as_view(), name="daily_performance"),
    path("daily-target/", views.DailyTargetView.as_view(), name="daily_target"),
    path("daily-target/override/", views.DailyTargetOverrideView.as_view(), name="daily_target_override"),
]
