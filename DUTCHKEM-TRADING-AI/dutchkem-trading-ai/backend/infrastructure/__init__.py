from django.apps import AppConfig


class InfrastructureConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'infrastructure'
    verbose_name = 'V4 Infrastructure — Always-On Resiliency'

    def ready(self):
        import logging
        logger = logging.getLogger('infrastructure')

        try:
            from .orchestrator import get_resiliency_orchestrator
            orchestrator = get_resiliency_orchestrator()
            orchestrator.initialize()
            logger.info("Resiliency Orchestrator initialized")
        except Exception as e:
            logger.warning("Orchestrator init failed: %s", e)

        try:
            from .self_healing import get_self_healing
            sh = get_self_healing()
            logger.info("Self-healing system ready")
        except Exception as e:
            logger.warning("Self-healing init failed: %s", e)

        try:
            from .health_monitor import get_health_monitor
            hm = get_health_monitor()
            logger.info("Health monitor ready")
        except Exception as e:
            logger.warning("Health monitor init failed: %s", e)

        try:
            from .alert_system import get_alert_system
            al = get_alert_system()
            logger.info("Alert system ready")
        except Exception as e:
            logger.warning("Alert system init failed: %s", e)

        logger.info("V4 Infrastructure — Always-On Resiliency ready")
