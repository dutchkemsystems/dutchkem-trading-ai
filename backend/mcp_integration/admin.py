from django.contrib import admin

from .models import MCPConnection, MCPServer, MCPTool


@admin.register(MCPServer)
class MCPServerAdmin(admin.ModelAdmin):
    list_display = ["name", "display_name", "is_active", "tools_count", "is_healthy", "last_health_check"]
    list_filter = ["is_active", "is_healthy"]


@admin.register(MCPTool)
class MCPToolAdmin(admin.ModelAdmin):
    list_display = ["name", "server", "display_name", "category", "is_active"]
    list_filter = ["server", "category", "is_active"]
    search_fields = ["name", "display_name"]


@admin.register(MCPConnection)
class MCPConnectionAdmin(admin.ModelAdmin):
    list_display = [
        "server",
        "session_id",
        "status",
        "requests_count",
        "errors_count",
        "avg_response_time",
        "connected_at",
    ]
    list_filter = ["status"]
    date_hierarchy = "connected_at"
