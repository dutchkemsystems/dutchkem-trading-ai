from decimal import Decimal

from django.core.management.base import BaseCommand

from trading.models import Symbol


SYMBOLS = [
    # ── Majors (7) ───────────────────────────────────────────────────
    {"name": "EURUSD", "description": "Euro vs US Dollar", "category": "MAJOR", "base_currency": "EUR", "quote_currency": "USD", "pip_size": "0.0001", "spread": "1.0", "contract_size": "100000"},
    {"name": "GBPUSD", "description": "British Pound vs US Dollar", "category": "MAJOR", "base_currency": "GBP", "quote_currency": "USD", "pip_size": "0.0001", "spread": "1.2", "contract_size": "100000"},
    {"name": "USDJPY", "description": "US Dollar vs Japanese Yen", "category": "MAJOR", "base_currency": "USD", "quote_currency": "JPY", "pip_size": "0.01", "spread": "1.0", "contract_size": "100000"},
    {"name": "USDCHF", "description": "US Dollar vs Swiss Franc", "category": "MAJOR", "base_currency": "USD", "quote_currency": "CHF", "pip_size": "0.0001", "spread": "1.2", "contract_size": "100000"},
    {"name": "AUDUSD", "description": "Australian Dollar vs US Dollar", "category": "MAJOR", "base_currency": "AUD", "quote_currency": "USD", "pip_size": "0.0001", "spread": "1.0", "contract_size": "100000"},
    {"name": "USDCAD", "description": "US Dollar vs Canadian Dollar", "category": "MAJOR", "base_currency": "USD", "quote_currency": "CAD", "pip_size": "0.0001", "spread": "1.4", "contract_size": "100000"},
    {"name": "NZDUSD", "description": "New Zealand Dollar vs US Dollar", "category": "MAJOR", "base_currency": "NZD", "quote_currency": "USD", "pip_size": "0.0001", "spread": "1.5", "contract_size": "100000"},
    # ── Crosses (7) ──────────────────────────────────────────────────
    {"name": "EURGBP", "description": "Euro vs British Pound", "category": "CROSS", "base_currency": "EUR", "quote_currency": "GBP", "pip_size": "0.0001", "spread": "1.5", "contract_size": "100000"},
    {"name": "EURJPY", "description": "Euro vs Japanese Yen", "category": "CROSS", "base_currency": "EUR", "quote_currency": "JPY", "pip_size": "0.01", "spread": "1.5", "contract_size": "100000"},
    {"name": "GBPJPY", "description": "British Pound vs Japanese Yen", "category": "CROSS", "base_currency": "GBP", "quote_currency": "JPY", "pip_size": "0.01", "spread": "2.5", "contract_size": "100000"},
    {"name": "AUDJPY", "description": "Australian Dollar vs Japanese Yen", "category": "CROSS", "base_currency": "AUD", "quote_currency": "JPY", "pip_size": "0.01", "spread": "2.0", "contract_size": "100000"},
    {"name": "EURAUD", "description": "Euro vs Australian Dollar", "category": "CROSS", "base_currency": "EUR", "quote_currency": "AUD", "pip_size": "0.0001", "spread": "2.0", "contract_size": "100000"},
    {"name": "EURCHF", "description": "Euro vs Swiss Franc", "category": "CROSS", "base_currency": "EUR", "quote_currency": "CHF", "pip_size": "0.0001", "spread": "1.5", "contract_size": "100000"},
    {"name": "GBPCAD", "description": "British Pound vs Canadian Dollar", "category": "CROSS", "base_currency": "GBP", "quote_currency": "CAD", "pip_size": "0.0001", "spread": "2.5", "contract_size": "100000"},
    # ── Exotics (4) ──────────────────────────────────────────────────
    {"name": "USDTRY", "description": "US Dollar vs Turkish Lira", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "TRY", "pip_size": "0.0001", "spread": "10.0", "contract_size": "100000"},
    {"name": "USDZAR", "description": "US Dollar vs South African Rand", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "ZAR", "pip_size": "0.0001", "spread": "25.0", "contract_size": "100000"},
    {"name": "USDMXN", "description": "US Dollar vs Mexican Peso", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "MXN", "pip_size": "0.0001", "spread": "15.0", "contract_size": "100000"},
    {"name": "USDCNH", "description": "US Dollar vs Chinese Yuan", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "CNH", "pip_size": "0.0001", "spread": "8.0", "contract_size": "100000"},
    # ── Metals (3) ───────────────────────────────────────────────────
    {"name": "XAUUSD", "description": "Gold vs US Dollar", "category": "COMMODITY", "base_currency": "XAU", "quote_currency": "USD", "pip_size": "0.01", "spread": "3.0", "contract_size": "100"},
    {"name": "XAGUSD", "description": "Silver vs US Dollar", "category": "COMMODITY", "base_currency": "XAG", "quote_currency": "USD", "pip_size": "0.001", "spread": "4.0", "contract_size": "5000"},
    {"name": "XAUEUR", "description": "Gold vs Euro", "category": "COMMODITY", "base_currency": "XAU", "quote_currency": "EUR", "pip_size": "0.01", "spread": "4.0", "contract_size": "100"},
    # ── Crypto (3) ───────────────────────────────────────────────────
    {"name": "BTCUSD", "description": "Bitcoin vs US Dollar", "category": "CRYPTO", "base_currency": "BTC", "quote_currency": "USD", "pip_size": "0.01", "spread": "50.0", "contract_size": "1"},
    {"name": "ETHUSD", "description": "Ethereum vs US Dollar", "category": "CRYPTO", "base_currency": "ETH", "quote_currency": "USD", "pip_size": "0.01", "spread": "3.0", "contract_size": "1"},
    {"name": "SOLUSD", "description": "Solana vs US Dollar", "category": "CRYPTO", "base_currency": "SOL", "quote_currency": "USD", "pip_size": "0.01", "spread": "2.0", "contract_size": "1"},
    # ── Indices (4) ──────────────────────────────────────────────────
    {"name": "US30", "description": "US Dow Jones 30", "category": "INDEX", "base_currency": "USD", "quote_currency": "30", "pip_size": "0.01", "spread": "2.0", "contract_size": "1"},
    {"name": "US500", "description": "US S&P 500", "category": "INDEX", "base_currency": "USD", "quote_currency": "500", "pip_size": "0.01", "spread": "0.5", "contract_size": "1"},
    {"name": "NAS100", "description": "US Nasdaq 100", "category": "INDEX", "base_currency": "USD", "quote_currency": "100", "pip_size": "0.01", "spread": "1.0", "contract_size": "1"},
    {"name": "GER40", "description": "Germany DAX 40", "category": "INDEX", "base_currency": "EUR", "quote_currency": "40", "pip_size": "0.01", "spread": "1.5", "contract_size": "1"},
    # ── African Exotics (extras, kept for regional trading) ───────────
    {"name": "USDNGN", "description": "US Dollar vs Nigerian Naira", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "NGN", "pip_size": "0.01", "spread": "50.0", "contract_size": "100000"},
    {"name": "USDGHS", "description": "US Dollar vs Ghanaian Cedi", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "GHS", "pip_size": "0.0001", "spread": "30.0", "contract_size": "100000"},
    {"name": "USDKES", "description": "US Dollar vs Kenyan Shilling", "category": "EXOTIC", "base_currency": "USD", "quote_currency": "KES", "pip_size": "0.01", "spread": "40.0", "contract_size": "100000"},
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
