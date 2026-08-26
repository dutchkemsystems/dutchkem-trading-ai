import uuid

from django.conf import settings
from django.db import models


class PaymentGateway(models.Model):
    GATEWAY_TYPES = [
        ("PAYSTACK", "Paystack"),
        ("FLUTTERWAVE", "Flutterwave"),
        ("STRIPE", "Stripe"),
        ("COINBASE", "Coinbase"),
        ("PAYPAL", "PayPal"),
        ("SKRILL", "Skrill"),
        ("NETELLER", "Neteller"),
        ("MPESA", "M-Pesa"),
        ("BANK_TRANSFER", "Bank Transfer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, choices=GATEWAY_TYPES)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    supports_deposits = models.BooleanField(default=True)
    supports_withdrawals = models.BooleanField(default=True)
    min_deposit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    max_deposit = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    min_withdrawal = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    max_withdrawal = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    deposit_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    withdrawal_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    deposit_processing_time = models.CharField(max_length=50, default="Instant")
    withdrawal_processing_time = models.CharField(max_length=50, default="1-3 Business Days")
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    config = models.JSONField(default=dict)

    class Meta:
        verbose_name_plural = "payment gateways"

    def __str__(self):
        return self.display_name


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("DEPOSIT", "Deposit"),
        ("WITHDRAWAL", "Withdrawal"),
        ("TRADING_PROFIT", "Trading Profit"),
        ("TRADING_LOSS", "Trading Loss"),
        ("COMMISSION", "Commission"),
        ("SWAP", "Swap"),
        ("BONUS", "Bonus"),
        ("REFUND", "Refund"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
        ("REFUNDED", "Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.SET_NULL, null=True, blank=True)
    gateway_reference = models.CharField(max_length=255, blank=True)
    gateway_response = models.JSONField(default=dict)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=20, decimal_places=2)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "transaction_type", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency} - {self.status}"


class KYCVerification(models.Model):
    KYC_LEVELS = [
        ("BASIC", "Basic"),
        ("ADVANCED", "Advanced"),
        ("FULL", "Full"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kyc_verifications")
    level = models.CharField(max_length=20, choices=KYC_LEVELS)
    status = models.CharField(
        max_length=20,
        choices=[
            ("NOT_STARTED", "Not Started"),
            ("PENDING", "Pending"),
            ("VERIFIED", "Verified"),
            ("REJECTED", "Rejected"),
        ],
        default="NOT_STARTED",
    )
    document_type = models.CharField(max_length=50, blank=True)
    document_number = models.CharField(max_length=100, blank=True)
    document_front = models.ImageField(upload_to="kyc/front/", blank=True, null=True)
    document_back = models.ImageField(upload_to="kyc/back/", blank=True, null=True)
    selfie = models.ImageField(upload_to="kyc/selfie/", blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.user.username} - {self.level} - {self.status}"


class UserPaymentMethod(models.Model):
    """Saved payment methods for users"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_methods")
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE)
    method_type = models.CharField(max_length=50)  # card, bank_account, crypto_wallet, mobile_money
    display_name = models.CharField(max_length=100)
    last_four = models.CharField(max_length=4, blank=True)
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    details_encrypted = models.TextField()  # Encrypted payment details
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.display_name}"
