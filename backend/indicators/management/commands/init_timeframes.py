from django.core.management.base import BaseCommand

from indicators.models import Timeframe


TIMEFRAMES = [
    {
        "code": "M5",
        "name": "5 Minute",
        "minutes": 5,
        "strategy_type": "Scalping",
        "risk_level": "HIGH",
        "target_pips_min": 5,
        "target_pips_max": 10,
        "stop_loss_min": 10,
        "stop_loss_max": 15,
        "win_rate_target_min": "55.00",
        "win_rate_target_max": "65.00",
        "risk_reward_ratio": "1.50",
    },
    {
        "code": "M15",
        "name": "15 Minute",
        "minutes": 15,
        "strategy_type": "Momentum",
        "risk_level": "MEDIUM_HIGH",
        "target_pips_min": 10,
        "target_pips_max": 20,
        "stop_loss_min": 15,
        "stop_loss_max": 25,
        "win_rate_target_min": "50.00",
        "win_rate_target_max": "60.00",
        "risk_reward_ratio": "1.50",
    },
    {
        "code": "M30",
        "name": "30 Minute",
        "minutes": 30,
        "strategy_type": "Swing",
        "risk_level": "MEDIUM",
        "target_pips_min": 20,
        "target_pips_max": 40,
        "stop_loss_min": 25,
        "stop_loss_max": 50,
        "win_rate_target_min": "48.00",
        "win_rate_target_max": "58.00",
        "risk_reward_ratio": "1.75",
    },
    {
        "code": "H1",
        "name": "1 Hour",
        "minutes": 60,
        "strategy_type": "Trend",
        "risk_level": "MEDIUM_LOW",
        "target_pips_min": 40,
        "target_pips_max": 80,
        "stop_loss_min": 50,
        "stop_loss_max": 100,
        "win_rate_target_min": "45.00",
        "win_rate_target_max": "55.00",
        "risk_reward_ratio": "2.00",
    },
    {
        "code": "H2",
        "name": "2 Hour",
        "minutes": 120,
        "strategy_type": "Position",
        "risk_level": "LOW_MEDIUM",
        "target_pips_min": 80,
        "target_pips_max": 150,
        "stop_loss_min": 100,
        "stop_loss_max": 200,
        "win_rate_target_min": "42.00",
        "win_rate_target_max": "52.00",
        "risk_reward_ratio": "2.50",
    },
    {
        "code": "H4",
        "name": "4 Hour",
        "minutes": 240,
        "strategy_type": "Strategic",
        "risk_level": "LOW",
        "target_pips_min": 150,
        "target_pips_max": 300,
        "stop_loss_min": 200,
        "stop_loss_max": 400,
        "win_rate_target_min": "40.00",
        "win_rate_target_max": "50.00",
        "risk_reward_ratio": "3.00",
    },
]


class Command(BaseCommand):
    help = "Initialize trading timeframes (M5, M15, M30, H1, H2, H4)"

    def handle(self, *args, **options):
        from decimal import Decimal

        created = 0
        updated = 0
        for data in TIMEFRAMES:
            obj, was_created = Timeframe.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "minutes": data["minutes"],
                    "strategy_type": data["strategy_type"],
                    "risk_level": data["risk_level"],
                    "target_pips_min": data["target_pips_min"],
                    "target_pips_max": data["target_pips_max"],
                    "stop_loss_min": data["stop_loss_min"],
                    "stop_loss_max": data["stop_loss_max"],
                    "win_rate_target_min": Decimal(data["win_rate_target_min"]),
                    "win_rate_target_max": Decimal(data["win_rate_target_max"]),
                    "risk_reward_ratio": Decimal(data["risk_reward_ratio"]),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully initialized timeframes: {created} created, {updated} updated")
        )
