import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Audit trail for all significant system actions.
    Tracks who did what, when, and what changed.
    """

    ACTION_CHOICES = [
        ("trade_opened", "Trade Opened"),
        ("trade_closed", "Trade Closed"),
        ("trade_modified", "Trade Modified"),
        ("signal_generated", "Signal Generated"),
        ("signal_acted", "Signal Acted Upon"),
        ("risk_check", "Risk Check"),
        ("circuit_breaker", "Circuit Breaker Triggered"),
        ("order_rejected", "Order Rejected"),
        ("settings_changed", "Settings Changed"),
        ("user_login", "User Login"),
        ("user_logout", "User Logout"),
        ("api_call", "API Call"),
        ("error", "Error"),
        ("system_event", "System Event"),
    ]

    SEVERITY_CHOICES = [
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
        ("CRITICAL", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100, choices=ACTION_CHOICES, db_index=True)
    resource_type = models.CharField(
        max_length=50, help_text="e.g., Trade, Signal, RiskParameter"
    )
    resource_id = models.CharField(max_length=100, blank=True, default="")
    changes = models.JSONField(default=dict, blank=True)
    severity = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, default="INFO"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else "system"
        return f"[{self.action}] {user_str} - {self.resource_type} ({self.timestamp})"

    @classmethod
    def log(cls, action, resource_type, resource_id="", changes=None,
            user=None, ip_address=None, user_agent="", severity="INFO"):
        """Convenience method to create an audit log entry."""
        return cls.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            changes=changes or {},
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
        )
