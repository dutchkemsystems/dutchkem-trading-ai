import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BacktestResult",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("symbol", models.CharField(max_length=20)),
                ("timeframe", models.CharField(max_length=10)),
                ("strategy", models.CharField(max_length=100)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("initial_balance", models.DecimalField(decimal_places=2, default=10000, max_digits=20)),
                ("final_balance", models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ("total_pnl", models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ("total_pnl_percent", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("total_trades", models.IntegerField(default=0)),
                ("winning_trades", models.IntegerField(default=0)),
                ("losing_trades", models.IntegerField(default=0)),
                ("win_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("profit_factor", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("max_drawdown", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("sharpe_ratio", models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ("parameters", models.JSONField(default=dict)),
                ("trades", models.JSONField(default=list)),
                ("equity_curve", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="backtest_results", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
