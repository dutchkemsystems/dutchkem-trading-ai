from django.urls import path

from . import views

urlpatterns = [
    path("", views.BacktestResultListView.as_view(), name="backtest_list"),
    path("<uuid:pk>/", views.BacktestResultDetailView.as_view(), name="backtest_detail"),
    path("run/", views.RunBacktestView.as_view(), name="run_backtest"),
]
