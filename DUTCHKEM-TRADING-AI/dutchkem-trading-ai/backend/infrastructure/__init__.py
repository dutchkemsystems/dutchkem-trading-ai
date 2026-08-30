from django.apps import AppConfig


class InfrastructureConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'infrastructure'
    verbose_name = 'V4 Infrastructure'
    
    def ready(self):
        import logging
        logger = logging.getLogger('infrastructure')
        try:
            from .self_healing import get_self_healing
            sh = get_self_healing()
            logger.info("Self-healing system initialized")
        except Exception as e:
            logger.warning("Self-healing init failed: %s", e)
        logger.info("V4 Infrastructure ready")
