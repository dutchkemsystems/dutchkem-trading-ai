"""
Migration 0007: Add V6.5-managed profit target fields to RiskParameter.

Adds:
  - weekly_target (Decimal)
  - target_weekly_growth (Decimal)

V6.5 COMPULSORY: These fields store V6.5's dynamically computed targets.
All existing hardcoded daily/monthly/annual targets are updated to V6.5 defaults.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("risk_management", "0006_alter_trading_settings_active_symbols"),
    ]

    operations = [
        migrations.AddField(
            model_name="riskparameter",
            name="weekly_target",
            field=models.DecimalField(
                decimal_places=2,
                default=1.0,
                help_text="V6.5 default weekly growth target as percentage (dynamically overridden at runtime)",
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name="riskparameter",
            name="target_weekly_growth",
            field=models.DecimalField(
                decimal_places=2,
                default=1.0,
                help_text="V6.5 default weekly growth (compounded from daily, dynamically computed)",
                max_digits=5,
            ),
        ),
        # Update existing defaults to match V6.5 expectations
        migrations.AlterField(
            model_name="riskparameter",
            name="daily_growth_target",
            field=models.DecimalField(
                decimal_places=4,
                default=0.15,
                help_text="V6.5 default daily growth target (dynamically overridden at runtime)",
                max_digits=5,
            ),
        ),
        migrations.AlterField(
            model_name="riskparameter",
            name="target_daily_growth",
            field=models.DecimalField(
                decimal_places=4,
                default=0.15,
                help_text="V6.5 default daily growth (dynamically computed based on win rate, regime, drawdown)",
                max_digits=5,
            ),
        ),
        migrations.AlterField(
            model_name="riskparameter",
            name="target_annual_growth",
            field=models.DecimalField(
                decimal_places=2,
                default=50.0,
                help_text="V6.5 default annual growth (compounded from monthly, dynamically computed)",
                max_digits=5,
            ),
        ),
    ]
