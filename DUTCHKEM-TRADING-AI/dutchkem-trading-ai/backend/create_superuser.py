import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')
django.setup()

from accounts.models import User

if User.objects.filter(username='admin').exists():
    print('User admin already exists')
else:
    user = User.objects.create_superuser(
        username='admin',
        email='admin@dutchkem.com',
        password='admin123',
        first_name='Admin',
        last_name='User',
    )
    print(f'Created superuser: {user.username} (id={user.id})')
