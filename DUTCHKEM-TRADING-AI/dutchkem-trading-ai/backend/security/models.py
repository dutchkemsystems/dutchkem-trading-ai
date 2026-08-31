import hashlib
import uuid

from django.conf import settings
from django.db import models


class BlockedIP(models.Model):
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
    blocked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    threat_level = models.IntegerField(default=3)

    class Meta:
        ordering = ["-blocked_at"]

    def __str__(self) -> str:
        return f"{self.ip_address} ({'active' if self.is_active else 'inactive'})"

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at


class SecurityEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100, db_index=True)
    threat_level = models.IntegerField(default=0)
    user_id = models.CharField(max_length=100, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    endpoint = models.CharField(max_length=500, blank=True, default="")
    method = models.CharField(max_length=10, blank=True, default="")
    action_taken = models.CharField(max_length=50, default="allowed")
    event_hash = models.CharField(max_length=64, blank=True, default="")
    previous_hash = models.CharField(max_length=64, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["event_type", "timestamp"]),
            models.Index(fields=["ip_address", "timestamp"]),
            models.Index(fields=["user_id", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"[{self.event_type}] {self.user_id or 'anon'} - level={self.threat_level}"

    def save(self, *args, **kwargs):
        if not self.event_hash:
            payload = f"{self.event_type}:{self.user_id}:{self.ip_address}:{self.timestamp}:{self.details}"
            self.event_hash = hashlib.sha256(payload.encode()).hexdigest()
        if not self.previous_hash:
            prev = SecurityEvent.objects.exclude(pk=self.pk).order_by('-timestamp').values_list('event_hash', flat=True).first()
            self.previous_hash = prev or ""
        super().save(*args, **kwargs)


class EncryptionKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.PositiveIntegerField(unique=True, db_index=True)
    encrypted_key = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self) -> str:
        return f"Key v{self.version} ({'active' if self.is_active else 'inactive'})"


class CredentialVault(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    credential_type = models.CharField(max_length=50, default="secret")
    encrypted_value = models.BinaryField()
    value_hash = models.CharField(max_length=64, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    rotated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(null=True, blank=True)
    access_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.credential_type})"

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
