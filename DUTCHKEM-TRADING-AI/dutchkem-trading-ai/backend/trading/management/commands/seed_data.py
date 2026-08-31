from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed initial data for the trading platform"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Seed all data")
        parser.add_argument("--timeframes", action="store_true", help="Seed timeframes")
        parser.add_argument("--indicators", action="store_true", help="Seed indicators")
        parser.add_argument("--risk-params", action="store_true", help="Seed risk parameters")
        parser.add_argument("--payment-gateways", action="store_true", help="Seed payment gateways")

    def handle(self, *args, **options):
        if options["all"] or options["timeframes"]:
            self.seed_timeframes()
        if options["all"] or options["indicators"]:
            self.seed_indicators()
        if options["all"] or options["risk_params"]:
            self.seed_risk_parameters()
        if options["all"] or options["payment_gateways"]:
            self.seed_payment_gateways()

        self.stdout.write(self.style.SUCCESS("Seeding complete!"))

    def seed_timeframes(self):
        from indicators.models import Timeframe

        timeframes = [
            {"code": "M5", "name": "5 Minutes", "minutes": 5, "strategy_type": "scalping", "risk_level": "HIGH", "target_pips_min": 5, "target_pips_max": 15, "stop_loss_min": 8, "stop_loss_max": 20, "win_rate_target_min": "55.00", "win_rate_target_max": "70.00", "risk_reward_ratio": "1.50"},
            {"code": "M15", "name": "15 Minutes", "minutes": 15, "strategy_type": "scalping", "risk_level": "MEDIUM_HIGH", "target_pips_min": 10, "target_pips_max": 30, "stop_loss_min": 15, "stop_loss_max": 40, "win_rate_target_min": "50.00", "win_rate_target_max": "65.00", "risk_reward_ratio": "1.80"},
            {"code": "M30", "name": "30 Minutes", "minutes": 30, "strategy_type": "intraday", "risk_level": "MEDIUM", "target_pips_min": 20, "target_pips_max": 50, "stop_loss_min": 25, "stop_loss_max": 60, "win_rate_target_min": "48.00", "win_rate_target_max": "62.00", "risk_reward_ratio": "2.00"},
            {"code": "H1", "name": "1 Hour", "minutes": 60, "strategy_type": "intraday", "risk_level": "MEDIUM", "target_pips_min": 30, "target_pips_max": 80, "stop_loss_min": 30, "stop_loss_max": 80, "win_rate_target_min": "45.00", "win_rate_target_max": "60.00", "risk_reward_ratio": "2.00"},
            {"code": "H2", "name": "2 Hours", "minutes": 120, "strategy_type": "swing", "risk_level": "MEDIUM_LOW", "target_pips_min": 50, "target_pips_max": 120, "stop_loss_min": 40, "stop_loss_max": 100, "win_rate_target_min": "42.00", "win_rate_target_max": "58.00", "risk_reward_ratio": "2.50"},
            {"code": "H4", "name": "4 Hours", "minutes": 240, "strategy_type": "swing", "risk_level": "LOW_MEDIUM", "target_pips_min": 80, "target_pips_max": 200, "stop_loss_min": 60, "stop_loss_max": 150, "win_rate_target_min": "40.00", "win_rate_target_max": "55.00", "risk_reward_ratio": "2.50"},
        ]

        created = 0
        for data in timeframes:
            _, was_created = Timeframe.objects.update_or_create(
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

        self.stdout.write(self.style.SUCCESS(f"Timeframes: {created} created"))

    def seed_indicators(self):
        from indicators.models import Indicator, IndicatorCategory

        categories = [
            {"name": "Trend", "description": "Trend-following indicators"},
            {"name": "Momentum", "description": "Momentum and oscillators"},
            {"name": "Volatility", "description": "Volatility indicators"},
            {"name": "Volume", "description": "Volume-based indicators"},
        ]

        for cat_data in categories:
            IndicatorCategory.objects.get_or_create(
                name=cat_data["name"],
                defaults={"description": cat_data["description"]},
            )

        trend_cat = IndicatorCategory.objects.get(name="Trend")
        momentum_cat = IndicatorCategory.objects.get(name="Momentum")
        volatility_cat = IndicatorCategory.objects.get(name="Volatility")

        indicators = [
            {"name": "EMA", "display_name": "Exponential Moving Average", "category": trend_cat, "indicator_type": "TREND", "description": "Exponential Moving Average", "default_parameters": {"period": 20}},
            {"name": "SMA", "display_name": "Simple Moving Average", "category": trend_cat, "indicator_type": "TREND", "description": "Simple Moving Average", "default_parameters": {"period": 50}},
            {"name": "MACD", "display_name": "MACD", "category": momentum_cat, "indicator_type": "MOMENTUM", "description": "Moving Average Convergence Divergence", "default_parameters": {"fast": 12, "slow": 26, "signal": 9}},
            {"name": "RSI", "display_name": "Relative Strength Index", "category": momentum_cat, "indicator_type": "OSCILLATOR", "description": "Relative Strength Index", "default_parameters": {"period": 14, "overbought": 70, "oversold": 30}},
            {"name": "STOCH", "display_name": "Stochastic Oscillator", "category": momentum_cat, "indicator_type": "OSCILLATOR", "description": "Stochastic Oscillator", "default_parameters": {"k_period": 14, "d_period": 3, "smooth": 3}},
            {"name": "ATR", "display_name": "Average True Range", "category": volatility_cat, "indicator_type": "VOLATILITY", "description": "Average True Range", "default_parameters": {"period": 14}},
            {"name": "BB", "display_name": "Bollinger Bands", "category": volatility_cat, "indicator_type": "VOLATILITY", "description": "Bollinger Bands", "default_parameters": {"period": 20, "std_dev": 2}},
            {"name": "ADX", "display_name": "Average Directional Index", "category": trend_cat, "indicator_type": "TREND", "description": "Average Directional Index", "default_parameters": {"period": 14}},
        ]

        created = 0
        for data in indicators:
            _, was_created = Indicator.objects.get_or_create(
                name=data["name"],
                defaults={
                    "display_name": data["display_name"],
                    "category": data["category"],
                    "indicator_type": data["indicator_type"],
                    "description": data["description"],
                    "default_parameters": data["default_parameters"],
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Indicators: {created} created"))

    def seed_risk_parameters(self):
        from risk_management.models import RiskParameter

        RiskParameter.objects.get_or_create(
            name="Default Risk Parameters",
            defaults={
                "max_daily_loss": Decimal("2.00"),
                "daily_growth_target": Decimal("0.1400"),
                "daily_target_lock": Decimal("0.40"),
                "max_daily_trades": 10,
                "max_position_size": Decimal("1.00"),
                "max_open_positions": 5,
                "max_drawdown": Decimal("15.00"),
                "max_correlation": Decimal("0.70"),
                "min_risk_reward_ratio": Decimal("2.00"),
                "target_daily_growth": Decimal("0.1400"),
                "target_monthly_growth": Decimal("4.20"),
                "target_annual_growth": Decimal("50.00"),
                "is_active": True,
            },
        )

        self.stdout.write(self.style.SUCCESS("Risk parameters seeded"))

    def seed_payment_gateways(self):
        from payments.models import PaymentGateway

        gateways = [
            {
                "name": "KORAPAY",
                "display_name": "Korapay",
                "is_active": True,
                "supports_deposits": True,
                "supports_withdrawals": True,
                "min_deposit": Decimal("100.00"),
                "max_deposit": Decimal("10000000.00"),
                "min_withdrawal": Decimal("1000.00"),
                "max_withdrawal": Decimal("5000000.00"),
                "deposit_fee_percent": Decimal("1.50"),
                "withdrawal_fee_percent": Decimal("1.50"),
                "deposit_processing_time": "Instant",
                "withdrawal_processing_time": "1-3 Business Days",
                "supported_currencies": ["NGN", "GHS", "KES", "ZAR"],
                "supported_channels": ["card", "bank_transfer", "ussd", "mobile_money"],
            },
        ]

        created = 0
        for data in gateways:
            _, was_created = PaymentGateway.objects.get_or_create(
                name=data["name"],
                defaults=data,
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Payment gateways: {created} created"))
