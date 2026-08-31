import logging
import os

from celery import Celery

logger = logging.getLogger("celery")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("dutchkem_trading")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    logger.debug("Request: %s", self.request)
