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
