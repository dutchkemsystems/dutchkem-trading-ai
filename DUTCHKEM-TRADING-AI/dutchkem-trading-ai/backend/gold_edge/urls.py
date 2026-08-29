from django.urls import path

from . import views

urlpatterns = [
    # Config CRUD
    path(
        "config/",
        views.GoldEdgeConfigListView.as_view(),
        name="gold_edge_config_list",
    ),
    path(
        "config/<uuid:pk>/",
        views.GoldEdgeConfigDetailView.as_view(),
        name="gold_edge_config_detail",
    ),
    # Signals
    path(
        "signals/",
        views.GoldEdgeSignalListView.as_view(),
        name="gold_edge_signal_list",
    ),
    path(
        "signals/<uuid:pk>/",
        views.GoldEdgeSignalDetailView.as_view(),
        name="gold_edge_signal_detail",
    ),
    # On-demand analysis
    path(
        "analyze/",
        views.GoldEdgeAnalysisView.as_view(),
        name="gold_edge_analyze",
    ),
    # Batch scanner
    path(
        "scan/",
        views.GoldEdgeScanView.as_view(),
        name="gold_edge_scan",
    ),
    # Backtesting
    path(
        "backtests/",
        views.GoldEdgeBacktestListView.as_view(),
        name="gold_edge_backtest_list",
    ),
    path(
        "backtests/<uuid:pk>/",
        views.GoldEdgeBacktestDetailView.as_view(),
        name="gold_edge_backtest_detail",
    ),
]
