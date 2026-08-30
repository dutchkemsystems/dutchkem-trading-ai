"""
Security models for the zero trust and encryption layers.
"""

import uuid

from django.conf import settings
from django.db import models


class BlockedIP(models.Model):
    """Manually or automatically blocked IP addresses."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(unique=True, db_index=True)
    reason = models.CharField(max_length=500, blank=True, default="")
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blocked_ips",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.ip_address} ({'active' if self.is_active else 'inactive'})"


class SecurityEvent(models.Model):
    """Audit log for all security-related verification events."""

    SEVERITY_CHOICES = [
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
        ("CRITICAL", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_events",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    trust_score = models.IntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    severity = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, default="INFO"
    )
    allowed = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["event_type", "timestamp"]),
            models.Index(fields=["user", "timestamp"]),
        ]

    def __str__(self) -> str:
        user_str = self.user.username if self.user else "anonymous"
        return f"[{self.event_type}] {user_str} - score={self.trust_score}"


class EncryptionKey(models.Model):
    """Versioned encryption keys for key rotation support."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.PositiveIntegerField(unique=True, db_index=True)
    encrypted_key = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self) -> str:
        return f"Key v{self.version} ({'active' if self.is_active else 'inactive'})"
