import os

# Only import celery_app if not in test/local mode
if os.environ.get("DJANGO_SETTINGS_MODULE") not in (
    "config.test_settings",
    "config.local_settings",
):
    from .celery import app as celery_app

    __all__ = ("celery_app",)
