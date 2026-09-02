# Generated manually for TradingAccount multi-account scaling

from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TradingAccount",
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
                        on_delete=models.CASCADE,
                        related_name="trading_accounts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "mt5_login",
                    models.CharField(
                        help_text="MT5 account number",
                        max_length=50,
                    ),
                ),
                (
                    "mt5_password",
                    models.CharField(
                        help_text="MT5 password (encrypted)",
                        max_length=200,
                    ),
                ),
                (
                    "mt5_server",
                    models.CharField(
                        help_text="MT5 broker server",
                        max_length=100,
                    ),
                ),
                (
                    "mt5_name",
                    models.CharField(
                        blank=True,
                        help_text="MT5 account name/alias",
                        max_length=200,
                    ),
                ),
                (
                    "account_type",
                    models.CharField(
                        choices=[
                            ("ECN", "ECN - Tight spreads, commission-based"),
                            ("STANDARD", "Standard - Wider spreads, no commission"),
                        ],
                        default="ECN",
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active - Trading enabled"),
                            ("INACTIVE", "Inactive - Trading paused"),
                            ("SCALED", "Scaled - Receiving distributed funds"),
                            ("FROZEN", "Frozen - Account locked"),
                        ],
                        default="ACTIVE",
                        max_length=10,
                    ),
                ),
                (
                    "is_primary",
                    models.BooleanField(
                        default=False,
                        help_text="Primary ECN account - auto-distributes at $600K",
                    ),
                ),
                (
                    "balance",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=20,
                    ),
                ),
                (
                    "equity",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=20,
                    ),
                ),
                (
                    "last_balance_check",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "scaling_threshold",
                    models.DecimalField(
                        decimal_places=2,
                        default=600000.0,
                        help_text="Balance threshold to trigger auto-distribution (default: $600,000 for Exness ECN max)",
                        max_digits=20,
                    ),
                ),
                (
                    "min_balance_after_scaling",
                    models.DecimalField(
                        decimal_places=2,
                        default=500000.0,
                        help_text="Minimum balance to keep in primary account after distribution",
                        max_digits=20,
                    ),
                ),
                (
                    "distribution_pct",
                    models.DecimalField(
                        decimal_places=2,
                        default=20.0,
                        help_text="Percentage of excess balance to distribute per scaling event",
                        max_digits=5,
                    ),
                ),
                (
                    "trading_engine",
                    models.CharField(
                        default="v6.5",
                        help_text="Always V6.5 for all accounts",
                        max_length=10,
                    ),
                ),
                (
                    "max_position_pct",
                    models.DecimalField(
                        decimal_places=2,
                        default=1.0,
                        help_text="Max position size as %% of this account's balance",
                        max_digits=5,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "last_trade_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Trading Account",
                "verbose_name_plural": "Trading Accounts",
                "indexes": [
                    models.Index(
                        fields=["user", "status"],
                        name="accounts_tra_user_st_idx",
                    ),
                    models.Index(
                        fields=["mt5_login", "mt5_server"],
                        name="accounts_tra_login_srv_idx",
                    ),
                    models.Index(
                        fields=["account_type", "status"],
                        name="accounts_tra_type_st_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["mt5_login", "mt5_server"],
                        name="unique_mt5_account",
                    ),
                ],
            },
        ),
    ]
