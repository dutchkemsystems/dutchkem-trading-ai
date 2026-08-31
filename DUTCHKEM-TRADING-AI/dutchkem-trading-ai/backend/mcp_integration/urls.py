from django.urls import path

from . import views

urlpatterns = [
    path("servers/", views.MCPServerListView.as_view(), name="mcp_server_list"),
    path("servers/<uuid:pk>/", views.MCPServerDetailView.as_view(), name="mcp_server_detail"),
    path("tools/", views.MCPToolListView.as_view(), name="mcp_tool_list"),
    path("connections/", views.MCPConnectionListView.as_view(), name="mcp_connection_list"),
    path("call/", views.MCPCallView.as_view(), name="mcp_call"),
    path("health/", views.MCPHealthCheckView.as_view(), name="mcp_health"),
    path("mt5/connect/", views.MT5ConnectView.as_view(), name="mt5_connect"),
    path("mt5/disconnect/", views.MT5DisconnectView.as_view(), name="mt5_disconnect"),
    path("mt5/status/", views.MT5StatusView.as_view(), name="mt5_status"),
    path("mt5/symbols/", views.MT5SymbolsView.as_view(), name="mt5_symbols"),
    path("mt5/account/", views.MT5AccountInfoView.as_view(), name="mt5_account"),
    path("mt5/positions/", views.MT5PositionsView.as_view(), name="mt5_positions"),
    path("mt5/orders/", views.MT5OrdersView.as_view(), name="mt5_orders"),
    path("mt5/candles/", views.MT5CandlesView.as_view(), name="mt5_candles"),
    path("mt5/open/", views.MT5OpenPositionView.as_view(), name="mt5_open_position"),
    path("mt5/close/", views.MT5ClosePositionView.as_view(), name="mt5_close_position"),
    path("mt5/modify/", views.MT5ModifyPositionView.as_view(), name="mt5_modify_position"),
    path("mt5/history/", views.MT5TradeHistoryView.as_view(), name="mt5_trade_history"),
]
