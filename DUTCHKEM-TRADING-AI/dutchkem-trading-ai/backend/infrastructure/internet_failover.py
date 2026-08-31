"""
V4 Internet Failover — Automatic ISP failover for continuous connectivity.
"""
import logging
import time
import subprocess
import threading
import socket
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum
from collections import deque

logger = logging.getLogger('infrastructure.internet_failover')


class ISPStatus(Enum):
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    DEGRADED = 'degraded'
    UNKNOWN = 'unknown'


class ConnectionType(Enum):
    WIRED = 'wired'
    CELLULAR = 'cellular'
    WIFI = 'wifi'
    VPN = 'vpn'
    UNKNOWN = 'unknown'


class ISPConnection:
    """Represents a single ISP connection."""

    def __init__(self, isp_id: str, name: str, connection_type: ConnectionType,
                 priority: int = 0, test_host: str = '8.8.8.8',
                 test_port: int = 53, bandwidth_limit_mbps: float = 0.0):
        self.isp_id = isp_id
        self.name = name
        self.connection_type = connection_type
        self.priority = priority
        self.test_host = test_host
        self.test_port = test_port
        self.bandwidth_limit_mbps = bandwidth_limit_mbps

        self.status = ISPStatus.UNKNOWN
        self.latency_ms = 0.0
        self.packet_loss = 0.0
        self.bandwidth_mbps = 0.0
        self.last_check = time.time()
        self.consecutive_failures = 0
        self.total_failures = 0

    def to_dict(self) -> Dict:
        return {
            'isp_id': self.isp_id,
            'name': self.name,
            'connection_type': self.connection_type.value,
            'priority': self.priority,
            'status': self.status.value,
            'latency_ms': self.latency_ms,
            'packet_loss': self.packet_loss,
            'bandwidth_mbps': self.bandwidth_mbps,
            'consecutive_failures': self.consecutive_failures,
            'total_failures': self.total_failures,
            'last_check': self.last_check,
        }


class InternetFailover:
    """
    Automatic ISP failover for continuous connectivity.
    - Monitor multiple ISP connections
    - Detect connectivity loss
    - Switch to backup ISP (wired, cellular)
    - Data compression during poor connectivity
    """

    def __init__(self, check_interval: float = 15.0,
                 failure_threshold: int = 3,
                 latency_threshold_ms: float = 500.0,
                 packet_loss_threshold: float = 10.0):
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.packet_loss_threshold = packet_loss_threshold

        self.connections: Dict[str, ISPConnection] = {}
        self.active_isp_id: Optional[str] = None
        self.failover_log: deque = deque(maxlen=500)
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._compression_enabled = False
        self._callbacks: Dict[str, list] = {
            'on_failover': [],
            'on_disconnect': [],
            'on_reconnect': [],
            'on_degraded': [],
        }

    def register_isp(self, isp_id: str, name: str,
                     connection_type: ConnectionType = ConnectionType.WIRED,
                     priority: int = 0, test_host: str = '8.8.8.8',
                     test_port: int = 53,
                     bandwidth_limit_mbps: float = 0.0) -> Dict:
        """Register an ISP connection for monitoring."""
        with self._lock:
            self.connections[isp_id] = ISPConnection(
                isp_id=isp_id,
                name=name,
                connection_type=connection_type,
                priority=priority,
                test_host=test_host,
                test_port=test_port,
                bandwidth_limit_mbps=bandwidth_limit_mbps,
            )
            logger.info("ISP registered: %s (%s)", name, connection_type.value)
            return self.connections[isp_id].to_dict()

    def set_active_isp(self, isp_id: str) -> bool:
        """Set an ISP as the active connection."""
        with self._lock:
            if isp_id not in self.connections:
                logger.warning("Cannot set active ISP: %s not found", isp_id)
                return False

            self.active_isp_id = isp_id
            self.connections[isp_id].status = ISPStatus.CONNECTED
            logger.info("Active ISP set to: %s", self.connections[isp_id].name)
            return True

    def test_connectivity(self, isp_id: str) -> Dict[str, Any]:
        """Test connectivity for a specific ISP connection."""
        with self._lock:
            if isp_id not in self.connections:
                return {'success': False, 'reason': 'ISP not found'}

            conn = self.connections[isp_id]

        result = {
            'isp_id': isp_id,
            'name': conn.name,
            'success': False,
            'latency_ms': 0.0,
            'packet_loss': 0.0,
        }

        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((conn.test_host, conn.test_port))
            latency = (time.time() - start) * 1000
            sock.close()

            result['success'] = True
            result['latency_ms'] = round(latency, 2)

            with self._lock:
                conn.latency_ms = latency
                conn.last_check = time.time()
                conn.consecutive_failures = 0

                if latency > self.latency_threshold_ms:
                    conn.status = ISPStatus.DEGRADED
                else:
                    conn.status = ISPStatus.CONNECTED

                result['status'] = conn.status.value

        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            with self._lock:
                conn.consecutive_failures += 1
                conn.total_failures += 1
                conn.last_check = time.time()

                if conn.consecutive_failures >= self.failure_threshold:
                    conn.status = ISPStatus.DISCONNECTED
                else:
                    conn.status = ISPStatus.DEGRADED

                result['status'] = conn.status.value
                result['error'] = str(e)

        return result

    def test_all_connections(self) -> Dict[str, Any]:
        """Test connectivity for all registered ISP connections."""
        results = {}
        with self._lock:
            isp_ids = list(self.connections.keys())

        for isp_id in isp_ids:
            results[isp_id] = self.test_connectivity(isp_id)

        healthy = any(r['success'] for r in results.values())
        return {
            'healthy': healthy,
            'active_isp': self.active_isp_id,
            'connections': results,
        }

    def trigger_failover(self, source_isp_id: Optional[str] = None,
                         target_isp_id: Optional[str] = None) -> Dict:
        """Trigger an ISP failover."""
        start_time = time.time()

        with self._lock:
            source = source_isp_id or self.active_isp_id
            if not source:
                return {'success': False, 'reason': 'No active ISP to failover from'}

            if source not in self.connections:
                return {'success': False, 'reason': f'ISP {source} not found'}

            if not target_isp_id:
                target_isp_id = self._select_backup_isp(source)
                if not target_isp_id:
                    return {'success': False, 'reason': 'No healthy backup ISP available'}

            if target_isp_id not in self.connections:
                return {'success': False, 'reason': f'Target ISP {target_isp_id} not found'}

            source_conn = self.connections[source]
            target_conn = self.connections[target_isp_id]

            source_conn.status = ISPStatus.DISCONNECTED
            target_conn.status = ISPStatus.CONNECTED
            self.active_isp_id = target_isp_id

        duration = time.time() - start_time

        event = {
            'type': 'isp_failover',
            'source': source,
            'target': target_isp_id,
            'source_name': source_conn.name,
            'target_name': target_conn.name,
            'duration_seconds': round(duration, 3),
            'timestamp': time.time(),
            'success': True,
        }
        self.failover_log.append(event)

        self._log_failover_event(
            'isp_failover',
            f"Failover from {source_conn.name} to {target_conn.name}",
            source, target_isp_id, duration, True
        )
        self._fire_event('on_failover', event)

        logger.info(
            "ISP failover: %s -> %s in %.3fs",
            source_conn.name, target_conn.name, duration
        )
        return {
            'success': True,
            'source': source,
            'target': target_isp_id,
            'duration': duration,
        }

    def enable_compression(self):
        """Enable data compression for poor connectivity."""
        self._compression_enabled = True
        logger.info("Data compression enabled for poor connectivity")

    def disable_compression(self):
        """Disable data compression."""
        self._compression_enabled = False
        logger.info("Data compression disabled")

    def is_compression_active(self) -> bool:
        """Check if compression should be active based on current conditions."""
        if self.active_isp_id and self.active_isp_id in self.connections:
            conn = self.connections[self.active_isp_id]
            if conn.status == ISPStatus.DEGRADED or conn.latency_ms > self.latency_threshold_ms:
                return True
        return self._compression_enabled

    def _select_backup_isp(self, exclude_isp: str) -> Optional[str]:
        """Select the best backup ISP."""
        best_isp = None
        best_priority = -1

        for isp_id, conn in self.connections.items():
            if isp_id == exclude_isp:
                continue
            if conn.status == ISPStatus.DISCONNECTED:
                continue
            if conn.priority > best_priority:
                best_priority = conn.priority
                best_isp = isp_id

        return best_isp

    def on(self, event: str, callback: Callable):
        """Register a callback for ISP events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _fire_event(self, event: str, *args, **kwargs):
        """Fire callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error("ISP callback error for %s: %s", event, e)

    def _log_failover_event(self, event_type: str, description: str,
                            source: str, target: str,
                            duration: float, success: bool):
        """Log ISP failover event to database."""
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
            logger.error("Failed to log ISP failover: %s", e)

    def start_monitoring(self):
        """Start the ISP monitoring thread."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("ISP monitoring started (interval: %.1fs)", self.check_interval)

    def stop_monitoring(self):
        """Stop the ISP monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("ISP monitoring stopped")

    def _monitor_loop(self):
        """Main ISP monitoring loop."""
        while self._running:
            try:
                results = self.test_all_connections()

                if not results['healthy'] and self.active_isp_id:
                    logger.warning("Active ISP unhealthy, triggering failover")
                    self.trigger_failover()

                for isp_id, result in results.get('connections', {}).items():
                    if result.get('status') == 'degraded' and isp_id == self.active_isp_id:
                        self._fire_event('on_degraded', isp_id)

            except Exception as e:
                logger.error("ISP monitor error: %s", e)

            time.sleep(self.check_interval)

    def get_status(self) -> Dict[str, Any]:
        """Get current internet failover status."""
        with self._lock:
            return {
                'active_isp': self.active_isp_id,
                'total_connections': len(self.connections),
                'connected': sum(
                    1 for c in self.connections.values()
                    if c.status == ISPStatus.CONNECTED
                ),
                'degraded': sum(
                    1 for c in self.connections.values()
                    if c.status == ISPStatus.DEGRADED
                ),
                'disconnected': sum(
                    1 for c in self.connections.values()
                    if c.status == ISPStatus.DISCONNECTED
                ),
                'compression_active': self.is_compression_active(),
                'connections': {
                    cid: c.to_dict()
                    for cid, c in self.connections.items()
                },
                'recent_failovers': list(self.failover_log)[-10:],
                'monitoring': self._running,
            }


_internet_failover: Optional[InternetFailover] = None


def get_internet_failover() -> InternetFailover:
    global _internet_failover
    if _internet_failover is None:
        _internet_failover = InternetFailover()
    return _internet_failover
