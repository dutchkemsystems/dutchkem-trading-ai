import logging
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')
django.setup()

logger = logging.getLogger(__name__)

from accounts.models import User

if User.objects.filter(username='admin').exists():
    logger.info('User admin already exists')
else:
    user = User.objects.create_superuser(
        username='admin',
        email='admin@dutchkem.com',
        password='admin123',
        first_name='Admin',
        last_name='User',
    )
    logger.info('Created superuser: %s (id=%s)', user.username, user.id)
