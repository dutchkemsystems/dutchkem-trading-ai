import os, sys, django
os.environ['DATABASE_URL'] = 'postgresql://postgres:7MoevMEs2IIX9e01TmRLP1Fc@dutchkem-trading-ai-slim-drain-pooler.cloud.layerbase.dev/dutchkem_trading_ai?sslmode=require'
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_production'
os.environ['USE_SQLITE'] = '0'
os.environ['SECRET_KEY'] = 'test-key-for-connection-check'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
django.setup()

from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT version()')
print('PostgreSQL version:', cursor.fetchone()[0])
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
tables = [row[0] for row in cursor.fetchall()]
print(f'Tables ({len(tables)}):')
for t in tables:
    print(f'  - {t}')
