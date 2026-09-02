import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
django.setup()

from accounts.models import User, TradingAccount

# Create superuser
if not User.objects.filter(username='admin').exists():
    u = User.objects.create_superuser('admin', 'admin@dutchkem.com', 'Dutchkem@2026!')
    u.mt5_account = '161704951'
    u.mt5_server = 'Exness-MT5Real21'
    u.save()
    print(f'Superuser created: admin / Dutchkem@2026! (ID: {u.id})')

    # Register primary ECN account
    TradingAccount.objects.create(
        user=u,
        mt5_login='161704951',
        mt5_password='PLACEHOLDER',
        mt5_server='Exness-MT5Real21',
        mt5_name='Exness Standard Cent',
        account_type='ECN',
        is_primary=True,
        trading_engine='v6.5',
    )
    print('Primary ECN account registered: 161704951@Exness-MT5Real21')
else:
    u = User.objects.get(username='admin')
    print(f'Superuser already exists (ID: {u.id})')

    # Check if trading account exists
    if not TradingAccount.objects.filter(mt5_login='161704951').exists():
        TradingAccount.objects.create(
            user=u,
            mt5_login='161704951',
            mt5_password='PLACEHOLDER',
            mt5_server='Exness-MT5Real21',
            mt5_name='Exness Standard Cent',
            account_type='ECN',
            is_primary=True,
            trading_engine='v6.5',
        )
        print('Primary ECN account registered: 161704951@Exness-MT5Real21')

print('\nAll accounts:')
for a in TradingAccount.objects.all():
    print(f'  {a.mt5_login}@{a.mt5_server} ({a.account_type}) - V6.5 - Primary: {a.is_primary}')
