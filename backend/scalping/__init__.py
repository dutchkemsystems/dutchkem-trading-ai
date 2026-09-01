from django.apps import AppConfig


class ScalpingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scalping'
    verbose_name = 'V2 Scalping Engine'
    
    def ready(self):
        import logging
        logger = logging.getLogger('scalping')
        logger.info("V2 Scalping Engine ready")
