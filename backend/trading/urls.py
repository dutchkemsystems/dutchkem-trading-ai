from django.urls import path

from . import views

urlpatterns = [
    path("symbols/", views.SymbolListView.as_view(), name="symbol_list"),
    path("symbols/<uuid:pk>/", views.SymbolDetailView.as_view(), name="symbol_detail"),
    path("trades/", views.TradeListView.as_view(), name="trade_list"),
    path("trades/<uuid:pk>/", views.TradeDetailView.as_view(), name="trade_detail"),
    path("trades/create/", views.TradeCreateView.as_view(), name="trade_create"),
    path("trades/<uuid:trade_id>/close/", views.TradeCloseView.as_view(), name="trade_close"),
    path("trades/<uuid:trade_id>/modify/", views.TradeModifyView.as_view(), name="trade_modify"),
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path("orders/create/", views.OrderCreateView.as_view(), name="order_create"),
    path("orders/<uuid:order_id>/cancel/", views.OrderCancelView.as_view(), name="order_cancel"),
    path("positions/", views.PositionListView.as_view(), name="position_list"),
    path("portfolio/", views.PortfolioSummaryView.as_view(), name="portfolio_summary"),
    path("history/", views.TradeHistoryView.as_view(), name="trade_history"),
]
