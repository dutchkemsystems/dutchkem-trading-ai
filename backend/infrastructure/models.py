import uuid

from django.db import models
from django.utils import timezone


class NodeHealth(models.Model):
    """
    Track node health status across the cluster.
    """
    STATUS_CHOICES = [
        ("active", "Active"),
        ("standby", "Standby"),
        ("failed", "Failed"),
        ("recovering", "Recovering"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    node_id = models.CharField(max_length=100, unique=True, db_index=True)
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=14222)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="standby")
    cpu_usage = models.FloatField(default=0.0, help_text="CPU usage percentage")
    memory_usage = models.FloatField(default=0.0, help_text="Memory usage percentage")
    disk_usage = models.FloatField(default=0.0, help_text="Disk usage percentage")
    network_latency_ms = models.FloatField(default=0.0, help_text="Network latency in milliseconds")
    last_heartbeat = models.DateTimeField(auto_now=True)
    heartbeat_count = models.IntegerField(default=0)
    missed_heartbeats = models.IntegerField(default=0)
    failover_count = models.IntegerField(default=0)
    load_score = models.FloatField(default=0.0)
    error_message = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_heartbeat"]
        indexes = [
            models.Index(fields=["node_id", "status"]),
            models.Index(fields=["status", "last_heartbeat"]),
        ]

    def __str__(self):
        return f"{self.node_id} [{self.status}]"


class FailoverEvent(models.Model):
    """
    Log all failover events for audit and analysis.
    """
    EVENT_TYPES = [
        ("node_failure", "Node Failure"),
        ("leader_election", "Leader Election"),
        ("broker_failover", "Broker Failover"),
        ("mt5_reconnect", "MT5 Reconnect"),
        ("isp_failover", "ISP Failover"),
        ("power_event", "Power Event"),
        ("manual_failover", "Manual Failover"),
        ("recovery", "Recovery"),
    ]

    SEVERITY_CHOICES = [
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
        ("CRITICAL", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    source_node = models.CharField(max_length=100, blank=True, default="")
    target_node = models.CharField(max_length=100, blank=True, default="")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="INFO")
    description = models.TextField()
    duration_seconds = models.FloatField(default=0.0)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["severity", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.event_type}] {self.severity} - {self.created_at}"

    @classmethod
    def log(cls, event_type, description, source_node="", target_node="",
            severity="INFO", duration_seconds=0.0, success=True,
            error_message="", metadata=None):
        """Convenience method to create a failover event log entry."""
        return cls.objects.create(
            event_type=event_type,
            source_node=source_node,
            target_node=target_node,
            severity=severity,
            description=description,
            duration_seconds=duration_seconds,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )


class AlertLog(models.Model):
    """
    Log all alerts sent through the multi-channel alert system.
    """
    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("telegram", "Telegram"),
        ("slack", "Slack"),
        ("webhook", "Webhook"),
    ]

    LEVEL_CHOICES = [
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
        ("CRITICAL", "Critical"),
    ]

    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("pending", "Pending"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, db_index=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, db_index=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    recipient = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="sent")
    error_message = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["level", "sent_at"]),
            models.Index(fields=["channel", "status"]),
        ]

    def __str__(self):
        return f"[{self.level}] {self.channel}: {self.subject}"

    @classmethod
    def log(cls, level, channel, subject, message, recipient="",
            status="sent", error_message="", metadata=None):
        """Convenience method to create an alert log entry."""
        return cls.objects.create(
            level=level,
            channel=channel,
            subject=subject,
            message=message,
            recipient=recipient,
            status=status,
            error_message=error_message,
            metadata=metadata or {},
        )
