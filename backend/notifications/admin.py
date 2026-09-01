from django.contrib import admin

from .models import Notification, NotificationTemplate, UserNotificationPreference


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "template_type", "subject", "is_active"]
    list_filter = ["template_type", "is_active"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "title",
        "notification_type",
        "priority",
        "is_read",
        "sent_email",
        "sent_push",
        "created_at",
    ]
    list_filter = ["notification_type", "priority", "is_read"]
    search_fields = ["user__username", "title"]
    date_hierarchy = "created_at"


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "email_trades", "email_signals", "email_risk_alerts", "push_trades", "push_signals"]
    search_fields = ["user__username"]
