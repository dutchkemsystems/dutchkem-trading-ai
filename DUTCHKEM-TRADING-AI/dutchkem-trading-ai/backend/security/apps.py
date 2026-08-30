from django.apps import AppConfig


class SecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'security'
    verbose_name = 'V5 Security Layer'
    
    def ready(self):
        """Initialize security subsystems on startup."""
        import logging
        logger = logging.getLogger('security')
        
        # Initialize SIEM event bus
        try:
            from .siem import get_siem
            siem = get_siem()
            logger.info("SIEM initialized: %d active rules", len(siem.rules))
        except Exception as e:
            logger.warning("SIEM init failed: %s", e)
        
        # Initialize credential manager
        try:
            from .credential_manager import get_credential_manager
            cm = get_credential_manager()
            logger.info("Credential manager initialized")
        except Exception as e:
            logger.warning("Credential manager init failed: %s", e)
        
        # Initialize RASP
        try:
            from .rasp import get_rasp
            rasp = get_rasp()
            logger.info("RASP initialized: integrity=%s", rasp.verify_integrity())
        except Exception as e:
            logger.warning("RASP init failed: %s", e)
        
        logger.info("V5 Security Layer ready")
