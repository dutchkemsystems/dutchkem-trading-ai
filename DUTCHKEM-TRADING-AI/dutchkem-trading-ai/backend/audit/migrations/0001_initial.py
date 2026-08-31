import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
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
                        ],
                        db_index=True,
                        max_length=100,
                    ),
                ),
                (
                    "resource_type",
                    models.CharField(
                        help_text="e.g., Trade, Signal, RiskParameter",
                        max_length=50,
                    ),
                ),
                (
                    "resource_id",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                ("changes", models.JSONField(blank=True, default=dict)),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("INFO", "Info"),
                            ("WARNING", "Warning"),
                            ("ERROR", "Error"),
                            ("CRITICAL", "Critical"),
                        ],
                        default="INFO",
                        max_length=10,
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                (
                    "user_agent",
                    models.CharField(blank=True, default="", max_length=500),
                ),
                (
                    "timestamp",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(
                        fields=["action", "timestamp"],
                        name="audit_audit_action_idx",
                    ),
                    models.Index(
                        fields=["user", "timestamp"],
                        name="audit_audit_user_idx",
                    ),
                    models.Index(
                        fields=["resource_type", "resource_id"],
                        name="audit_audit_res_idx",
                    ),
                ],
            },
        ),
    ]
