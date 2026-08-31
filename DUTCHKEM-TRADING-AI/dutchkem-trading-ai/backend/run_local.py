import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.local_settings")

import django

django.setup()

from django.core.management import call_command

call_command("runserver", "0.0.0.0:8000", "--noreload")
