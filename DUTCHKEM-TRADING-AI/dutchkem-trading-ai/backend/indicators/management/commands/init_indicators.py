from django.core.management.base import BaseCommand

from indicators.models import Indicator, IndicatorCategory


CATEGORIES = [
    {"name": "Trend", "description": "Trend-following indicators", "icon": "trending-up"},
    {"name": "Momentum", "description": "Momentum and oscillator indicators", "icon": "speed"},
    {"name": "Volatility", "description": "Volatility measurement indicators", "icon": "activity"},
    {"name": "Volume", "description": "Volume-based indicators", "icon": "bar-chart"},
    {"name": "Support/Resistance", "description": "Support and resistance level indicators", "icon": "layers"},
]

INDICATORS = [
    # Trend
    {"name": "EMA", "display_name": "Exponential Moving Average", "category": "Trend", "indicator_type": "TREND", "description": "Exponential Moving Average - gives more weight to recent prices", "default_parameters": {"periods": [5, 10, 20, 50, 100, 200]}},
    {"name": "SMA", "display_name": "Simple Moving Average", "category": "Trend", "indicator_type": "TREND", "description": "Simple Moving Average - equal weight to all prices in period", "default_parameters": {"periods": [10, 20, 50, 100, 200]}},
    {"name": "ICHIMOKU", "display_name": "Ichimoku Cloud", "category": "Trend", "indicator_type": "TREND", "description": "Ichimoku Kinko Hyo - comprehensive trend, support/resistance system", "default_parameters": {"tenkan": 9, "kijun": 26, "senkou": 52}},
    {"name": "SUPERTREND", "display_name": "Supertrend", "category": "Trend", "indicator_type": "TREND", "description": "Supertrend indicator based on ATR", "default_parameters": {"period": 10, "multiplier": 3.0}},
    {"name": "PSAR", "display_name": "Parabolic SAR", "category": "Trend", "indicator_type": "TREND", "description": "Parabolic Stop and Reverse - trend following indicator", "default_parameters": {"af_start": 0.02, "af_step": 0.02, "af_max": 0.2}},
    {"name": "ADX", "display_name": "Average Directional Index", "category": "Trend", "indicator_type": "TREND", "description": "Measures trend strength without direction", "default_parameters": {"period": 14}},
    {"name": "TEMA", "display_name": "Triple Exponential Moving Average", "category": "Trend", "indicator_type": "TREND", "description": "Triple EMA - reduces lag compared to standard EMA", "default_parameters": {"period": 20}},
    # Momentum
    {"name": "RSI", "display_name": "Relative Strength Index", "category": "Momentum", "indicator_type": "MOMENTUM", "description": "Measures speed and magnitude of price changes", "default_parameters": {"period": 14, "overbought": 70, "oversold": 30}},
    {"name": "MACD", "display_name": "MACD", "category": "Momentum", "indicator_type": "MOMENTUM", "description": "Moving Average Convergence Divergence", "default_parameters": {"fast": 12, "slow": 26, "signal": 9}},
    {"name": "STOCH", "display_name": "Stochastic Oscillator", "category": "Momentum", "indicator_type": "OSCILLATOR", "description": "Compares closing price to price range over a period", "default_parameters": {"k_period": 14, "d_period": 3, "smooth": 3}},
    {"name": "CCI", "display_name": "Commodity Channel Index", "category": "Momentum", "indicator_type": "OSCILLATOR", "description": "Identifies cyclical trends and overbought/oversold levels", "default_parameters": {"period": 20}},
    {"name": "WILLIAMS_R", "display_name": "Williams %R", "category": "Momentum", "indicator_type": "OSCILLATOR", "description": "Overbought/oversold indicator", "default_parameters": {"period": 14}},
    {"name": "MFI", "display_name": "Money Flow Index", "category": "Momentum", "indicator_type": "OSCILLATOR", "description": "Volume-weighted RSI", "default_parameters": {"period": 14}},
    # Volatility
    {"name": "BB", "display_name": "Bollinger Bands", "category": "Volatility", "indicator_type": "VOLATILITY", "description": "Price bands based on standard deviation", "default_parameters": {"period": 20, "std_dev": 2.0}},
    {"name": "ATR", "display_name": "Average True Range", "category": "Volatility", "indicator_type": "VOLATILITY", "description": "Measures market volatility", "default_parameters": {"period": 14}},
    {"name": "KELTNER", "display_name": "Keltner Channel", "category": "Volatility", "indicator_type": "VOLATILITY", "description": "ATR-based price channels", "default_parameters": {"ema_period": 20, "atr_period": 10, "multiplier": 2.0}},
    # Volume
    {"name": "OBV", "display_name": "On-Balance Volume", "category": "Volume", "indicator_type": "VOLUME", "description": "Cumulative volume indicator", "default_parameters": {}},
    {"name": "VWAP", "display_name": "Volume Weighted Average Price", "category": "Volume", "indicator_type": "VOLUME", "description": "Average price weighted by volume", "default_parameters": {}},
    # Support/Resistance
    {"name": "FIBONACCI", "display_name": "Fibonacci Retracement", "category": "Support/Resistance", "indicator_type": "CUSTOM", "description": "Key support/resistance levels based on Fibonacci ratios", "default_parameters": {"levels": [0.236, 0.382, 0.5, 0.618, 0.786]}},
    {"name": "PIVOT", "display_name": "Pivot Points", "category": "Support/Resistance", "indicator_type": "CUSTOM", "description": "Calculated support and resistance levels", "default_parameters": {"type": "standard"}},
]


class Command(BaseCommand):
    help = "Initialize technical indicators"

    def handle(self, *args, **options):
        # Create categories
        cat_created = 0
        for cat_data in CATEGORIES:
            _, was_created = IndicatorCategory.objects.update_or_create(
                name=cat_data["name"],
                defaults={"description": cat_data["description"], "icon": cat_data["icon"]},
            )
            if was_created:
                cat_created += 1

        # Create indicators
        ind_created = 0
        ind_updated = 0
        for data in INDICATORS:
            category = IndicatorCategory.objects.get(name=data["category"])
            _, was_created = Indicator.objects.update_or_create(
                name=data["name"],
                defaults={
                    "display_name": data["display_name"],
                    "category": category,
                    "indicator_type": data["indicator_type"],
                    "description": data["description"],
                    "default_parameters": data["default_parameters"],
                    "is_active": True,
                },
            )
            if was_created:
                ind_created += 1
            else:
                ind_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully initialized indicators: "
                f"{cat_created} categories, {ind_created} indicators created, {ind_updated} updated"
            )
        )
