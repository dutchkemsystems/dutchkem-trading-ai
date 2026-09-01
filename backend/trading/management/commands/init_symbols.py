from decimal import Decimal

from django.core.management.base import BaseCommand

from trading.models import Symbol


SYMBOLS = [
    # Major Pairs
    {"name": "EURUSD", "description": "Euro vs US Dollar", "category": "MAJOR", "base_currency": "EUR", "quote_currency": "USD", "pip_size": "0.0001", "spread": "1.0", "contract_size": "100000"},
    {"name": "GBPUSD", "description": "British Pound vs US Dollar", "category": "MAJOR", "base_currency": "GBP", "quote_currency": "USD", "pip_size": "0.0001", "spread": "1.2", "contract_size": "100000"},
    {"name": "USDJPY", "description": "US Dollar vs Japanese Yen", "category": "MAJOR", "base_currency": "USD", "quote_currency": "JPY", "pip_size": "0.01", "spread": "1.0", "contract_size": "100000"},
    {"name": "USDCHF", "description": "US Dollar vs Swiss Franc", "category": "MAJOR", "base_currency": "USD", "quote_currency": "CHF", "pip_size": "0.0001", "spread": "1.2", "contract_size": "100000"},
    {"name": "AUDUSD", "description": "Australian Dollar vs US Dollar", "category": "MAJOR", "base_currency": "AUD", "quote_currency": "USD", "pip_size": "0.0001", "spread": "1.0", "contract_size": "100000"},
    {"name": "USDCAD", "description": "US Dollar vs Canadian Dollar", "category": "MAJOR", "base_currency": "USD", "quote_currency": "CAD", "pip_size": "0.0001", "spread": "1.4", "contract_size": "100000"},
    {"name": "NZDUSD", "description": "New Zealand Dollar vs US Dollar", "category": "MAJOR", "base_currency": "NZD", "quote_currency": "USD", "pip_size": "0.0001", "spread": "1.5", "contract_size": "100000"},
    # Minor Pairs
    {"name": "EURGBP", "description": "Euro vs British Pound", "category": "MINOR", "base_currency": "EUR", "quote_currency": "GBP", "pip_size": "0.0001", "spread": "1.5", "contract_size": "100000"},
    {"name": "EURJPY", "description": "Euro vs Japanese Yen", "category": "MINOR", "base_currency": "EUR", "quote_currency": "JPY", "pip_size": "0.01", "spread": "1.5", "contract_size": "100000"},
    {"name": "GBPJPY", "description": "British Pound vs Japanese Yen", "category": "MINOR", "base_currency": "GBP", "quote_currency": "JPY", "pip_size": "0.01", "spread": "2.5", "contract_size": "100000"},
    {"name": "EURCHF", "description": "Euro vs Swiss Franc", "category": "MINOR", "base_currency": "EUR", "quote_currency": "CHF", "pip_size": "0.0001", "spread": "1.5", "contract_size": "100000"},
    {"name": "AUDJPY", "description": "Australian Dollar vs Japanese Yen", "category": "MINOR", "base_currency": "AUD", "quote_currency": "JPY", "pip_size": "0.01", "spread": "2.0", "contract_size": "100000"},
    {"name": "GBPAUD", "description": "British Pound vs Australian Dollar", "category": "MINOR", "base_currency": "GBP", "quote_currency": "AUD", "pip_size": "0.0001", "spread": "2.5", "contract_size": "100000"},
    # Exotic Pairs
    {"name": "USDNGN", "description": "US Dollar vs Nigerian Naira", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "NGN", "pip_size": "0.01", "spread": "50.0", "contract_size": "100000"},
    {"name": "USDZAR", "description": "US Dollar vs South African Rand", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "ZAR", "pip_size": "0.0001", "spread": "25.0", "contract_size": "100000"},
    {"name": "USDGHS", "description": "US Dollar vs Ghanaian Cedi", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "GHS", "pip_size": "0.0001", "spread": "30.0", "contract_size": "100000"},
    {"name": "USDKES", "description": "US Dollar vs Kenyan Shilling", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "KES", "pip_size": "0.01", "spread": "40.0", "contract_size": "100000"},
    # Commodities
    {"name": "XAUUSD", "description": "Gold vs US Dollar", "category": "COMMODITY", "base_currency": "XAU", "quote_currency": "USD", "pip_size": "0.01", "spread": "3.0", "contract_size": "100"},
    {"name": "XAGUSD", "description": "Silver vs US Dollar", "category": "COMMODITY", "base_currency": "XAG", "quote_currency": "USD", "pip_size": "0.001", "spread": "4.0", "contract_size": "5000"},
    {"name": "USOIL", "description": "US Crude Oil (WTI)", "category": "COMMODITY", "base_currency": "USD", "quote_currency": "OIL", "pip_size": "0.01", "spread": "3.0", "contract_size": "1000"},
    # Indices
    {"name": "US30", "description": "US Dow Jones 30", "category": "INDEX", "base_currency": "USD", "quote_currency": "30", "pip_size": "0.01", "spread": "2.0", "contract_size": "1"},
    {"name": "US500", "description": "US S&P 500", "category": "INDEX", "base_currency": "USD", "quote_currency": "500", "pip_size": "0.01", "spread": "0.5", "contract_size": "1"},
    {"name": "NASDAQ100", "description": "US Nasdaq 100", "category": "INDEX", "base_currency": "USD", "quote_currency": "100", "pip_size": "0.01", "spread": "1.0", "contract_size": "1"},
    {"name": "UK100", "description": "UK FTSE 100", "category": "INDEX", "base_currency": "GBP", "quote_currency": "100", "pip_size": "0.01", "spread": "1.0", "contract_size": "1"},
    {"name": "DE40", "description": "Germany DAX 40", "category": "INDEX", "base_currency": "EUR", "quote_currency": "40", "pip_size": "0.01", "spread": "1.5", "contract_size": "1"},
]


class Command(BaseCommand):
    help = "Initialize popular forex trading symbols"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for data in SYMBOLS:
            obj, was_created = Symbol.objects.update_or_create(
                name=data["name"],
                defaults={
                    "description": data["description"],
                    "category": data["category"],
                    "base_currency": data["base_currency"],
                    "quote_currency": data["quote_currency"],
                    "pip_size": Decimal(data["pip_size"]),
                    "spread": Decimal(data["spread"]),
                    "contract_size": Decimal(data["contract_size"]),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully initialized symbols: {created} created, {updated} updated")
        )
