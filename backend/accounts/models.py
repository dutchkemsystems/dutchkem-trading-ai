import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=[
            ("TRADER", "Trader"),
            ("ADMIN", "Admin"),
            ("MANAGER", "Manager"),
            ("VIEWER", "Viewer"),
        ],
        default="TRADER",
    )

    # Profile
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    # Security
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=32, blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(blank=True, null=True)

    # KYC
    kyc_status = models.CharField(
        max_length=20,
        choices=[
            ("NOT_STARTED", "Not Started"),
            ("PENDING", "Pending"),
            ("VERIFIED", "Verified"),
            ("REJECTED", "Rejected"),
        ],
        default="NOT_STARTED",
    )
    kyc_submitted_at = models.DateTimeField(blank=True, null=True)
    kyc_verified_at = models.DateTimeField(blank=True, null=True)

    # Trading Account
    mt5_account = models.CharField(max_length=50, blank=True, null=True)
    mt5_server = models.CharField(max_length=100, blank=True, null=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    equity = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # Preferences
    preferred_currency = models.CharField(max_length=3, default="USD")
    timezone = models.CharField(max_length=50, default="UTC")
    notifications_enabled = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["kyc_status"]),
        ]

    def __str__(self):
        return f"{self.username} ({self.email})"

    def lock_account(self, duration_minutes=30):
        self.account_locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save()

    def is_account_locked(self):
        if self.account_locked_until and self.account_locked_until > timezone.now():
            return True
        return False


class TradingAccount(models.Model):
    """
    Multi-account manager for auto-scaling across ECN and Standard accounts.

    When the primary ECN account reaches $600,000 (Exness ECN max),
    profits are automatically distributed to additional accounts (ECN or Standard).

    V6.5 is always used as the default engine for all accounts.
    """

    ACCOUNT_TYPES = [
        ("ECN", "ECN — Tight spreads, commission-based"),
        ("STANDARD", "Standard — Wider spreads, no commission"),
    ]

    STATUS_CHOICES = [
        ("ACTIVE", "Active — Trading enabled"),
        ("INACTIVE", "Inactive — Trading paused"),
        ("SCALED", "Scaled — Receiving distributed funds"),
        ("FROZEN", "Frozen — Account locked"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="trading_accounts")

    # MT5 connection
    mt5_login = models.CharField(max_length=50, help_text="MT5 account number")
    mt5_password = models.CharField(max_length=200, help_text="MT5 password (encrypted)")
    mt5_server = models.CharField(max_length=100, help_text="MT5 broker server")
    mt5_name = models.CharField(max_length=200, blank=True, help_text="MT5 account name/alias")

    # Account type and status
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default="ECN")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")
    is_primary = models.BooleanField(default=False, help_text="Primary ECN account — auto-distributes at $600K")

    # Balance tracking
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    equity = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    last_balance_check = models.DateTimeField(blank=True, null=True)

    # Auto-scaling config
    scaling_threshold = models.DecimalField(
        max_digits=20, decimal_places=2, default=600000.0,
        help_text="Balance threshold to trigger auto-distribution (default: $600,000 for Exness ECN max)",
    )
    min_balance_after_scaling = models.DecimalField(
        max_digits=20, decimal_places=2, default=500000.0,
        help_text="Minimum balance to keep in primary account after distribution",
    )
    distribution_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=20.0,
        help_text="Percentage of excess balance to distribute per scaling event",
    )

    # Trading settings
    trading_engine = models.CharField(max_length=10, default="v6.5", help_text="Always V6.5 for all accounts")
    max_position_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0,
        help_text="Max position size as % of this account's balance",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_trade_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Trading Account"
        verbose_name_plural = "Trading Accounts"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["mt5_login", "mt5_server"]),
            models.Index(fields=["account_type", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["mt5_login", "mt5_server"], name="unique_mt5_account"),
        ]

    def __str__(self):
        return f"{self.mt5_name or self.mt5_login} ({self.account_type}) — ${self.balance}"

    def needs_scaling(self) -> bool:
        """Check if primary ECN account exceeds scaling threshold."""
        if not self.is_primary or self.account_type != "ECN":
            return False
        return float(self.balance) >= float(self.scaling_threshold)

    def excess_balance(self) -> float:
        """Calculate excess balance above minimum to keep after scaling."""
        if not self.needs_scaling():
            return 0.0
        return float(self.balance) - float(self.min_balance_after_scaling)

    def distribution_amount(self) -> float:
        """Calculate amount to distribute to other accounts."""
        excess = self.excess_balance()
        if excess <= 0:
            return 0.0
        return round(excess * float(self.distribution_pct) / 100.0, 2)

    def get_lots_for_balance(self) -> float:
        """Calculate appropriate lot size for this account's balance."""
        bal = float(self.balance)
        if bal <= 0:
            return 0.01
        # 1 lot per $100 balance, minimum 0.01
        return max(0.01, round(bal / 100.0, 2))


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"


class LoginHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_history")
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("SUCCESS", "Success"),
            ("FAILED", "Failed"),
            ("BLOCKED", "Blocked"),
        ],
    )
    failure_reason = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "login histories"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.status} - {self.created_at}"
