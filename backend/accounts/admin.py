from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import LoginHistory, User, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "role", "kyc_status", "mfa_enabled", "is_active"]
    list_filter = ["role", "kyc_status", "mfa_enabled", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-created_at"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Profile", {"fields": ("phone_number", "avatar", "date_of_birth", "country")}),
        (
            "Security",
            {"fields": ("mfa_enabled", "mfa_secret", "last_login_ip", "failed_login_attempts", "account_locked_until")},
        ),
        ("KYC", {"fields": ("kyc_status", "kyc_submitted_at", "kyc_verified_at")}),
        ("Trading", {"fields": ("mt5_account", "mt5_server", "balance", "equity")}),
        ("Preferences", {"fields": ("preferred_currency", "timezone", "notifications_enabled")}),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "ip_address", "created_at", "last_active", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["user__username", "ip_address"]


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ["user", "ip_address", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__username", "ip_address"]
