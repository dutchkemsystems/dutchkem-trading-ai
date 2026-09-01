import uuid

from django.conf import settings
from django.db import models


class NotificationTemplate(models.Model):
    TEMPLATE_TYPES = [
        ("TRADE", "Trade Notification"),
        ("RISK", "Risk Alert"),
        ("PAYMENT", "Payment Notification"),
        ("SIGNAL", "Signal Alert"),
        ("EA", "EA Notification"),
        ("SYSTEM", "System Notification"),
        ("KYC", "KYC Notification"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=200)
    body_template = models.TextField()
    email_template = models.TextField(blank=True)
    push_template = models.TextField(blank=True)
    sms_template = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "notification templates"

    def __str__(self):
        return self.name


class Notification(models.Model):
    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("NORMAL", "Normal"),
        ("HIGH", "High"),
        ("URGENT", "Urgent"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NotificationTemplate.TEMPLATE_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="NORMAL")
    data = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    sent_email = models.BooleanField(default=False)
    sent_push = models.BooleanField(default=False)
    sent_sms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class UserNotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    email_trades = models.BooleanField(default=True)
    email_signals = models.BooleanField(default=True)
    email_risk_alerts = models.BooleanField(default=True)
    email_payments = models.BooleanField(default=True)
    push_trades = models.BooleanField(default=True)
    push_signals = models.BooleanField(default=True)
    push_risk_alerts = models.BooleanField(default=True)
    push_payments = models.BooleanField(default=False)
    sms_risk_alerts = models.BooleanField(default=True)
    quiet_hours_start = models.TimeField(blank=True, null=True)
    quiet_hours_end = models.TimeField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "user notification preferences"

    def __str__(self):
        return f"Preferences for {self.user.username}"
