from django.urls import path

from . import views

urlpatterns = [
    path("servers/", views.MCPServerListView.as_view(), name="mcp_server_list"),
    path("servers/<uuid:pk>/", views.MCPServerDetailView.as_view(), name="mcp_server_detail"),
    path("tools/", views.MCPToolListView.as_view(), name="mcp_tool_list"),
    path("connections/", views.MCPConnectionListView.as_view(), name="mcp_connection_list"),
    path("call/", views.MCPCallView.as_view(), name="mcp_call"),
    path("health/", views.MCPHealthCheckView.as_view(), name="mcp_health"),
]
