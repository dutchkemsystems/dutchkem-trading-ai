from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "timestamp", "action", "user", "resource_type",
        "resource_id", "severity", "ip_address",
    ]
    list_filter = ["action", "severity", "resource_type", "timestamp"]
    search_fields = ["user__username", "resource_id", "action"]
    readonly_fields = [
        "id", "user", "action", "resource_type", "resource_id",
        "changes", "severity", "ip_address", "user_agent", "timestamp",
    ]
    ordering = ["-timestamp"]
    date_hierarchy = "timestamp"
