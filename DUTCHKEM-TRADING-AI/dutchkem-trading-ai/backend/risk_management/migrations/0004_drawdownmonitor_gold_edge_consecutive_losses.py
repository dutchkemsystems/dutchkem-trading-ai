# Migration to add Gold Edge consecutive losses tracking to DrawdownMonitor

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("risk_management", "0003_add_gold_edge_risk_parameter"),
    ]

    operations = [
        migrations.AddField(
            model_name="drawdownmonitor",
            name="gold_edge_consecutive_losses",
            field=models.IntegerField(
                default=0,
                help_text="Current consecutive Gold Edge losses",
            ),
        ),
    ]
