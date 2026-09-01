"""
V4 Resiliency Orchestrator — Coordinates all resiliency components.
"""
import logging
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger('infrastructure.orchestrator')


class ResiliencyOrchestrator:
    """
    Coordinates all resiliency components.
    - Initialize all components
    - Run health monitoring loop
    - Coordinate failover when needed
    - Manage state synchronization
    - Handle self-healing
    """

    def __init__(self):
        self._initialized = False
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self.failover_manager = None
        self.state_sync = None
        self.trading_state = None
        self.broker_failover = None
        self.mt5_pool = None
        self.power_protection = None
        self.internet_failover = None
        self.self_healing = None
        self.health_monitor = None
        self.alert_system = None

    def initialize(self):
        """Initialize all resiliency components."""
        if self._initialized:
            logger.warning("Orchestrator already initialized")
            return

        logger.info("Initializing Resiliency Orchestrator...")

        try:
            from .failover_manager import get_failover_manager
            self.failover_manager = get_failover_manager()
            logger.info("FailoverManager initialized")
        except Exception as e:
            logger.error("Failed to initialize FailoverManager: %s", e)

        try:
            from .state_sync import get_synchronizer
            self.state_sync = get_synchronizer()
            logger.info("StateSynchronizer initialized")
        except Exception as e:
            logger.error("Failed to initialize StateSynchronizer: %s", e)

        try:
            from .trading_state import get_state_persistence
            self.trading_state = get_state_persistence()
            logger.info("TradingStatePersistence initialized")
        except Exception as e:
            logger.error("Failed to initialize TradingStatePersistence: %s", e)

        try:
            from .broker_failover import get_broker_failover
            self.broker_failover = get_broker_failover()
            logger.info("BrokerFailover initialized")
        except Exception as e:
            logger.error("Failed to initialize BrokerFailover: %s", e)

        try:
            from .mt5_pool import get_pool
            self.mt5_pool = get_pool()
            logger.info("MT5ConnectionPool initialized")
        except Exception as e:
            logger.error("Failed to initialize MT5ConnectionPool: %s", e)

        try:
            from .power_protection import get_power_protection
            self.power_protection = get_power_protection()
            logger.info("PowerProtection initialized")
        except Exception as e:
            logger.error("Failed to initialize PowerProtection: %s", e)

        try:
            from .internet_failover import get_internet_failover
            self.internet_failover = get_internet_failover()
            logger.info("InternetFailover initialized")
        except Exception as e:
            logger.error("Failed to initialize InternetFailover: %s", e)

        try:
            from .self_healing import get_self_healing
            self.self_healing = get_self_healing()
            logger.info("SelfHealing initialized")
        except Exception as e:
            logger.error("Failed to initialize SelfHealing: %s", e)

        try:
            from .health_monitor import get_health_monitor
            self.health_monitor = get_health_monitor()
            logger.info("HealthMonitor initialized")
        except Exception as e:
            logger.error("Failed to initialize HealthMonitor: %s", e)

        try:
            from .alert_system import get_alert_system
            self.alert_system = get_alert_system()
            logger.info("AlertSystem initialized")
        except Exception as e:
            logger.error("Failed to initialize AlertSystem: %s", e)

        self._setup_callbacks()
        self._initialized = True
        logger.info("Resiliency Orchestrator initialized successfully")

    def _setup_callbacks(self):
        """Setup cross-component callbacks."""
        if self.failover_manager and self.alert_system:
            self.failover_manager.on('on_failover', self._on_node_failover)
            self.failover_manager.on('on_node_failure', self._on_node_failure)

        if self.broker_failover and self.alert_system:
            self.broker_failover.on('on_failover', self._on_broker_failover)

        if self.internet_failover and self.alert_system:
            self.internet_failover.on('on_failover', self._on_isp_failover)

        if self.health_monitor and self.alert_system:
            self.health_monitor.on('on_critical', self._on_health_critical)
            self.health_monitor.on('on_degradation', self._on_health_degradation)

        if self.power_protection and self.alert_system:
            self.power_protection.on('on_power_outage', self._on_power_outage)
            self.power_protection.on('on_critical_battery', self._on_critical_battery)

    def _on_node_failover(self, event):
        """Handle node failover event."""
        logger.warning("Orchestrator: Node failover detected: %s", event)
        if self.alert_system:
            self.alert_system.send_alert(
                level=__import__('infrastructure.alert_system', fromlist=['AlertLevel']).AlertLevel.WARNING,
                subject="Node Failover",
                message=f"Failover from {event.get('source', 'unknown')} to {event.get('target', 'unknown')}",
            )

    def _on_node_failure(self, node_id):
        """Handle node failure event."""
        logger.warning("Orchestrator: Node failure detected: %s", node_id)
        if self.alert_system:
            from .alert_system import AlertLevel
            self.alert_system.send_alert(
                level=AlertLevel.ERROR,
                subject="Node Failure",
                message=f"Node {node_id} has failed",
            )

    def _on_broker_failover(self, event):
        """Handle broker failover event."""
        logger.warning("Orchestrator: Broker failover detected")
        if self.alert_system:
            from .alert_system import AlertLevel
            self.alert_system.send_alert(
                level=AlertLevel.WARNING,
                subject="Broker Failover",
                message=f"Broker failover: {event.get('source_name', 'unknown')} -> {event.get('target_name', 'unknown')}",
            )

    def _on_isp_failover(self, event):
        """Handle ISP failover event."""
        logger.warning("Orchestrator: ISP failover detected")
        if self.alert_system:
            from .alert_system import AlertLevel
            self.alert_system.send_alert(
                level=AlertLevel.WARNING,
                subject="ISP Failover",
                message=f"ISP failover: {event.get('source_name', 'unknown')} -> {event.get('target_name', 'unknown')}",
            )

    def _on_health_critical(self, data):
        """Handle critical health event."""
        logger.critical("Orchestrator: Critical health event")
        if self.alert_system:
            from .alert_system import AlertLevel
            self.alert_system.send_alert(
                level=AlertLevel.CRITICAL,
                subject="System Health Critical",
                message=f"System health is critical: {data.get('new_level', 'unknown')}",
            )

    def _on_health_degradation(self, data):
        """Handle health degradation event."""
        logger.warning("Orchestrator: Health degradation detected")
        if self.alert_system:
            from .alert_system import AlertLevel
            self.alert_system.send_alert(
                level=AlertLevel.WARNING,
                subject="Health Degradation",
                message=f"System health degraded: {data.get('new_level', 'unknown')}",
            )

    def _on_power_outage(self, data):
        """Handle power outage event."""
        logger.critical("Orchestrator: Power outage detected")
        if self.alert_system:
            from .alert_system import AlertLevel
            self.alert_system.send_alert(
                level=AlertLevel.CRITICAL,
                subject="Power Outage",
                message=f"Power outage detected. Battery: {data.get('battery_level', 'unknown')}%",
            )

    def _on_critical_battery(self, data):
        """Handle critical battery event."""
        logger.critical("Orchestrator: Critical battery level")
        if self.alert_system:
            from .alert_system import AlertLevel
            self.alert_system.send_alert(
                level=AlertLevel.CRITICAL,
                subject="Critical Battery",
                message=f"Critical battery level: {data.get('battery_level', 'unknown')}%. System may shut down.",
            )

    def start(self):
        """Start all monitoring components."""
        if self._running:
            return

        logger.info("Starting Resiliency Orchestrator...")

        if self.failover_manager:
            self.failover_manager.start_monitoring()

        if self.health_monitor:
            self.health_monitor.start_monitoring()

        if self.power_protection:
            self.power_protection.start_monitoring()

        if self.internet_failover:
            self.internet_failover.start_monitoring()

        if self.broker_failover:
            self.broker_failover.start_monitoring()

        self._running = True
        self._monitor_thread = threading.Thread(target=self._orchestrator_loop, daemon=True)
        self._monitor_thread.start()

        logger.info("Resiliency Orchestrator started")

    def stop(self):
        """Stop all monitoring components."""
        logger.info("Stopping Resiliency Orchestrator...")
        self._running = False

        if self._monitor_thread:
            self._monitor_thread.join(timeout=10.0)

        if self.failover_manager:
            self.failover_manager.stop_monitoring()
        if self.health_monitor:
            self.health_monitor.stop_monitoring()
        if self.power_protection:
            self.power_protection.stop_monitoring()
        if self.internet_failover:
            self.internet_failover.stop_monitoring()
        if self.broker_failover:
            self.broker_failover.stop_monitoring()

        logger.info("Resiliency Orchestrator stopped")

    def _orchestrator_loop(self):
        """Main orchestrator loop for coordination."""
        while self._running:
            try:
                self._coordinate_failover()
                self._coordinate_state_sync()
                self._coordinate_self_healing()
            except Exception as e:
                logger.error("Orchestrator loop error: %s", e)

            time.sleep(30.0)

    def _coordinate_failover(self):
        """Coordinate failover decisions."""
        if not self.health_monitor:
            return

        status = self.health_monitor.get_status()
        if status.get('overall_level') in ('critical', 'unhealthy'):
            logger.warning("Orchestrator: Initiating coordinated failover due to health status")

            if self.failover_manager:
                self.failover_manager.trigger_failover()

            if self.broker_failover:
                self.broker_failover.trigger_failover()

    def _coordinate_state_sync(self):
        """Coordinate state synchronization."""
        if not self.state_sync:
            return

        try:
            positions = []
            account = {}
            orders = []

            if self.trading_state:
                positions = self.trading_state.load_positions() or []
                account = self.trading_state.load_account() or {}
                orders = self.trading_state.load_orders() or []

            self.state_sync.sync_positions(positions)
            self.state_sync.sync_account(account)
        except Exception as e:
            logger.debug("State sync coordination error: %s", e)

    def _coordinate_self_healing(self):
        """Coordinate self-healing actions."""
        if not self.self_healing:
            return

        try:
            status = self.self_healing.get_system_status()
            for name, cb in status.get('circuit_breakers', {}).items():
                if cb.get('state') == 'open':
                    logger.info("Orchestrator: Attempting recovery for %s", name)
                    self.self_healing.attempt_recovery(name)
        except Exception as e:
            logger.debug("Self-healing coordination error: %s", e)

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status from all components."""
        status = {
            'initialized': self._initialized,
            'running': self._running,
            'timestamp': datetime.utcnow().isoformat(),
            'components': {},
        }

        if self.failover_manager:
            status['components']['failover_manager'] = self.failover_manager.get_status()

        if self.state_sync:
            status['components']['state_sync'] = self.state_sync.get_sync_status()

        if self.trading_state:
            status['components']['trading_state'] = self.trading_state.get_persistence_status()

        if self.broker_failover:
            status['components']['broker_failover'] = self.broker_failover.get_status()

        if self.mt5_pool:
            status['components']['mt5_pool'] = self.mt5_pool.get_pool_status()

        if self.power_protection:
            status['components']['power_protection'] = self.power_protection.get_status()

        if self.internet_failover:
            status['components']['internet_failover'] = self.internet_failover.get_status()

        if self.self_healing:
            status['components']['self_healing'] = self.self_healing.get_system_status()

        if self.health_monitor:
            status['components']['health_monitor'] = self.health_monitor.get_status()

        if self.alert_system:
            status['components']['alert_system'] = self.alert_system.get_status()

        return status


_orchestrator: Optional[ResiliencyOrchestrator] = None


def get_resiliency_orchestrator() -> ResiliencyOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ResiliencyOrchestrator()
    return _orchestrator
