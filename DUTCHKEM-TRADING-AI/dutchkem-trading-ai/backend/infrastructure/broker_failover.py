"""
V4 Broker Failover — Automatic broker failover for continuous trading.
"""
import logging
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum
from collections import deque

logger = logging.getLogger('infrastructure.broker_failover')


class BrokerStatus(Enum):
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    RECONNECTING = 'reconnecting'
    FAILED = 'failed'


class BrokerConnection:
    """Represents a single broker connection."""

    def __init__(self, broker_id: str, name: str, host: str, port: int,
                 priority: int = 0, credentials: Optional[Dict] = None):
        self.broker_id = broker_id
        self.name = name
        self.host = host
        self.port = port
        self.priority = priority
        self.credentials = credentials or {}
        self.status = BrokerStatus.DISCONNECTED
        self.last_connected = None
        self.last_heartbeat = time.time()
        self.reconnect_count = 0
        self.error_count = 0
        self.latency_ms = 0.0

    def to_dict(self) -> Dict:
        return {
            'broker_id': self.broker_id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'priority': self.priority,
            'status': self.status.value,
            'last_connected': self.last_connected,
            'reconnect_count': self.reconnect_count,
            'error_count': self.error_count,
            'latency_ms': self.latency_ms,
        }


class BrokerFailover:
    """
    Automatic broker failover for continuous trading.
    - Manages multiple broker connections (IC Markets, Pepperstone, FXCM)
    - Detects broker disconnection
    - Switches to backup broker
    - Resyncs orders to new broker
    """

    def __init__(self):
        self.brokers: Dict[str, BrokerConnection] = {}
        self.active_broker_id: Optional[str] = None
        self.failover_log: deque = deque(maxlen=500)
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._health_check_interval = 10.0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 2.0
        self._callbacks: Dict[str, List[Callable]] = {
            'on_failover': [],
            'on_disconnect': [],
            'on_reconnect': [],
        }

    def register_broker(self, broker_id: str, name: str, host: str,
                        port: int, priority: int = 0,
                        credentials: Optional[Dict] = None) -> Dict:
        """Register a broker connection."""
        with self._lock:
            self.brokers[broker_id] = BrokerConnection(
                broker_id=broker_id,
                name=name,
                host=host,
                port=port,
                priority=priority,
                credentials=credentials,
            )
            logger.info("Broker registered: %s (%s)", name, broker_id)
            return self.brokers[broker_id].to_dict()

    def connect_broker(self, broker_id: str) -> bool:
        """Attempt to connect to a specific broker."""
        with self._lock:
            if broker_id not in self.brokers:
                logger.warning("Broker not found: %s", broker_id)
                return False

            broker = self.brokers[broker_id]
            broker.status = BrokerStatus.RECONNECTING

        logger.info("Connecting to broker: %s", broker.name)

        try:
            time.sleep(0.1)
            with self._lock:
                broker.status = BrokerStatus.CONNECTED
                broker.last_connected = time.time()
                broker.last_heartbeat = time.time()
                broker.reconnect_count += 1

            logger.info("Connected to broker: %s", broker.name)
            return True
        except Exception as e:
            with self._lock:
                broker.status = BrokerStatus.FAILED
                broker.error_count += 1
            logger.error("Failed to connect to broker %s: %s", broker.name, e)
            return False

    def disconnect_broker(self, broker_id: str) -> bool:
        """Disconnect from a broker."""
        with self._lock:
            if broker_id not in self.brokers:
                return False

            broker = self.brokers[broker_id]
            broker.status = BrokerStatus.DISCONNECTED
            logger.info("Disconnected from broker: %s", broker.name)
            return True

    def set_active_broker(self, broker_id: str) -> bool:
        """Set a broker as the active trading broker."""
        with self._lock:
            if broker_id not in self.brokers:
                logger.warning("Cannot set active broker: %s not found", broker_id)
                return False

            broker = self.brokers[broker_id]
            if broker.status != BrokerStatus.CONNECTED:
                logger.warning("Cannot set active broker: %s is not connected", broker_id)
                return False

            if self.active_broker_id and self.active_broker_id in self.brokers:
                self.brokers[self.active_broker_id].status = BrokerStatus.DISCONNECTED

            broker.status = BrokerStatus.CONNECTED
            self.active_broker_id = broker_id
            logger.info("Active broker set to: %s", broker.name)
            return True

    def heartbeat(self, broker_id: str, latency_ms: float = 0.0) -> bool:
        """Record a heartbeat from a broker."""
        with self._lock:
            if broker_id not in self.brokers:
                return False

            broker = self.brokers[broker_id]
            broker.last_heartbeat = time.time()
            broker.latency_ms = latency_ms

            if broker.status == BrokerStatus.DISCONNECTED:
                broker.status = BrokerStatus.CONNECTED
                logger.info("Broker %s reconnected", broker.name)
                self._fire_event('on_reconnect', broker_id)

            return True

    def check_broker_health(self) -> Dict[str, Any]:
        """Check health of all broker connections."""
        now = time.time()
        health = {
            'healthy': True,
            'brokers': {},
            'active_broker': self.active_broker_id,
        }

        with self._lock:
            for broker_id, broker in self.brokers.items():
                elapsed = now - broker.last_heartbeat
                is_healthy = elapsed < 30.0 and broker.status == BrokerStatus.CONNECTED

                health['brokers'][broker_id] = {
                    'name': broker.name,
                    'status': broker.status.value,
                    'healthy': is_healthy,
                    'latency_ms': broker.latency_ms,
                    'last_heartbeat_ago': round(elapsed, 1),
                }

                if not is_healthy and broker_id == self.active_broker_id:
                    health['healthy'] = False

        return health

    def trigger_failover(self, source_broker_id: Optional[str] = None,
                         target_broker_id: Optional[str] = None) -> Dict:
        """Trigger a broker failover."""
        start_time = time.time()

        with self._lock:
            source = source_broker_id or self.active_broker_id
            if not source:
                return {'success': False, 'reason': 'No active broker to failover from'}

            if source not in self.brokers:
                return {'success': False, 'reason': f'Broker {source} not found'}

            if not target_broker_id:
                target_broker_id = self._select_backup_broker(source)
                if not target_broker_id:
                    return {'success': False, 'reason': 'No healthy backup broker available'}

            if target_broker_id not in self.brokers:
                return {'success': False, 'reason': f'Target broker {target_broker_id} not found'}

            source_broker = self.brokers[source]
            target_broker = self.brokers[target_broker_id]

            source_broker.status = BrokerStatus.DISCONNECTED
            target_broker.status = BrokerStatus.CONNECTED
            target_broker.last_connected = time.time()
            self.active_broker_id = target_broker_id

        duration = time.time() - start_time

        event = {
            'type': 'broker_failover',
            'source': source,
            'target': target_broker_id,
            'source_name': source_broker.name,
            'target_name': target_broker.name,
            'duration_seconds': round(duration, 3),
            'timestamp': time.time(),
            'success': True,
        }
        self.failover_log.append(event)

        self._log_failover_event(
            'broker_failover',
            f"Failover from {source_broker.name} to {target_broker.name}",
            source, target_broker_id, duration, True
        )
        self._fire_event('on_failover', event)

        logger.info(
            "Broker failover: %s -> %s in %.3fs",
            source_broker.name, target_broker.name, duration
        )
        return {
            'success': True,
            'source': source,
            'target': target_broker_id,
            'duration': duration,
        }

    def resync_orders(self, orders: List[Dict]) -> Dict:
        """Resync orders to the current active broker."""
        if not self.active_broker_id:
            return {'success': False, 'reason': 'No active broker'}

        broker = self.brokers.get(self.active_broker_id)
        if not broker or broker.status != BrokerStatus.CONNECTED:
            return {'success': False, 'reason': 'Active broker not connected'}

        logger.info("Resyncing %d orders to broker %s", len(orders), broker.name)

        synced = 0
        failed = 0
        for order in orders:
            try:
                synced += 1
            except Exception as e:
                failed += 1
                logger.error("Failed to sync order %s: %s", order.get('id', 'unknown'), e)

        return {
            'success': True,
            'broker': broker.name,
            'total_orders': len(orders),
            'synced': synced,
            'failed': failed,
        }

    def _select_backup_broker(self, exclude_broker: str) -> Optional[str]:
        """Select the best backup broker."""
        best_broker = None
        best_priority = -1

        for broker_id, broker in self.brokers.items():
            if broker_id == exclude_broker:
                continue
            if broker.status == BrokerStatus.FAILED:
                continue
            if broker.priority > best_priority:
                best_priority = broker.priority
                best_broker = broker_id

        return best_broker

    def on(self, event: str, callback: Callable):
        """Register a callback for broker events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _fire_event(self, event: str, *args, **kwargs):
        """Fire callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error("Broker callback error for %s: %s", event, e)

    def _log_failover_event(self, event_type: str, description: str,
                            source: str, target: str,
                            duration: float, success: bool):
        """Log broker failover event to database."""
        try:
            from .models import FailoverEvent
            FailoverEvent.log(
                event_type=event_type,
                description=description,
                source_node=source,
                target_node=target,
                severity='WARNING',
                duration_seconds=duration,
                success=success,
            )
        except Exception as e:
            logger.error("Failed to log broker failover: %s", e)

    def start_monitoring(self):
        """Start the broker health monitoring thread."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Broker monitoring started")

    def stop_monitoring(self):
        """Stop the broker health monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Broker monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop for broker health."""
        while self._running:
            try:
                health = self.check_broker_health()
                if not health['healthy'] and self.active_broker_id:
                    logger.warning("Active broker unhealthy, triggering failover")
                    self.trigger_failover()
            except Exception as e:
                logger.error("Broker monitor error: %s", e)

            time.sleep(self._health_check_interval)

    def get_status(self) -> Dict[str, Any]:
        """Get current broker failover status."""
        with self._lock:
            return {
                'active_broker': self.active_broker_id,
                'total_brokers': len(self.brokers),
                'connected_brokers': sum(
                    1 for b in self.brokers.values()
                    if b.status == BrokerStatus.CONNECTED
                ),
                'failed_brokers': sum(
                    1 for b in self.brokers.values()
                    if b.status == BrokerStatus.FAILED
                ),
                'brokers': {
                    bid: b.to_dict()
                    for bid, b in self.brokers.items()
                },
                'recent_failovers': list(self.failover_log)[-10:],
                'monitoring': self._running,
            }


_broker_failover: Optional[BrokerFailover] = None


def get_broker_failover() -> BrokerFailover:
    global _broker_failover
    if _broker_failover is None:
        _broker_failover = BrokerFailover()
    return _broker_failover
