from rest_framework import serializers

from .models import KYCVerification, PaymentGateway, Transaction, UserPaymentMethod


class PaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = [
            "id", "name", "display_name", "is_active",
            "supports_deposits", "supports_withdrawals",
            "min_deposit", "max_deposit", "min_withdrawal", "max_withdrawal",
            "deposit_fee_percent", "withdrawal_fee_percent",
            "deposit_processing_time", "withdrawal_processing_time",
            "supported_currencies", "supported_channels",
        ]


class TransactionSerializer(serializers.ModelSerializer):
    gateway_name = serializers.CharField(source="gateway.display_name", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id", "user", "transaction_type", "amount", "currency", "status",
            "gateway", "gateway_name", "korapay_ref", "channel",
            "gateway_reference", "fee", "net_amount", "description",
            "metadata", "created_at", "updated_at", "completed_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class KYCVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCVerification
        fields = [
            "id", "user", "level", "status", "document_type", "document_number",
            "document_front", "document_back", "selfie",
            "submitted_at", "verified_at", "rejection_reason",
        ]
        read_only_fields = ["id", "user", "submitted_at", "verified_at"]


class UserPaymentMethodSerializer(serializers.ModelSerializer):
    gateway_name = serializers.CharField(source="gateway.display_name", read_only=True)

    class Meta:
        model = UserPaymentMethod
        fields = [
            "id", "user", "gateway", "gateway_name", "method_type",
            "display_name", "last_four", "is_default", "is_verified", "created_at",
        ]
        read_only_fields = ["id", "user"]


class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, min_value=100)
    gateway = serializers.UUIDField(required=False)
    currency = serializers.ChoiceField(choices=["NGN", "GHS", "KES", "ZAR"], default="NGN")
    channel = serializers.ChoiceField(
        choices=["card", "bank_transfer", "ussd", "mobile_money"],
        required=False, default=""
    )
    redirect_url = serializers.URLField(required=False, default="")


class WithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, min_value=100)
    gateway = serializers.UUIDField(required=False)
    currency = serializers.ChoiceField(choices=["NGN", "GHS", "KES", "ZAR"], default="NGN")
    channel = serializers.ChoiceField(
        choices=["card", "bank_transfer", "ussd", "mobile_money"],
        required=False, default=""
    )
