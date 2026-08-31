from django.contrib import admin

from .models import KYCVerification, PaymentGateway, Transaction, UserPaymentMethod


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "display_name",
        "is_active",
        "supports_deposits",
        "supports_withdrawals",
        "min_deposit",
        "max_deposit",
    ]
    list_filter = ["is_active", "supports_deposits", "supports_withdrawals"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "transaction_type",
        "amount",
        "currency",
        "status",
        "gateway",
        "fee",
        "net_amount",
        "created_at",
    ]
    list_filter = ["transaction_type", "status", "currency"]
    search_fields = ["user__username", "gateway_reference"]
    date_hierarchy = "created_at"


@admin.register(KYCVerification)
class KYCVerificationAdmin(admin.ModelAdmin):
    list_display = ["user", "level", "status", "document_type", "submitted_at", "verified_at"]
    list_filter = ["level", "status"]
    search_fields = ["user__username"]
    date_hierarchy = "submitted_at"


@admin.register(UserPaymentMethod)
class UserPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["user", "gateway", "method_type", "display_name", "last_four", "is_default", "is_verified"]
    list_filter = ["gateway", "method_type", "is_default"]
    search_fields = ["user__username"]
