"""
V4 Self-Healing — Automatic service restart, circuit breaker recovery, MT5 reconnection.
"""
import gc
import logging
import os
import sys
import time
import threading
import psutil
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum
from collections import deque

logger = logging.getLogger('infrastructure.self_healing')


class CircuitState(Enum):
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.success_count = 0

    def record_success(self):
        self.failure_count = 0
        self.success_count += 1
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker %s: HALF_OPEN -> CLOSED", self.name)

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker %s: OPEN (failures=%d)", self.name, self.failure_count)

    def should_allow(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker %s: OPEN -> HALF_OPEN", self.name)
                return True
            return False
        else:
            return True

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
        }


class HealthMonitor:
    def __init__(self):
        self.health_checks: Dict[str, Callable] = {}
        self.results: Dict[str, Dict] = {}

    def register_check(self, name: str, check_fn: Callable):
        self.health_checks[name] = check_fn

    def run_checks(self) -> Dict[str, Dict]:
        for name, check_fn in self.health_checks.items():
            try:
                start = time.time()
                result = check_fn()
                elapsed = time.time() - start
                self.results[name] = {
                    'healthy': bool(result),
                    'latency_ms': round(elapsed * 1000, 2),
                    'checked_at': time.time(),
                }
            except Exception as e:
                self.results[name] = {
                    'healthy': False,
                    'error': str(e),
                    'checked_at': time.time(),
                }
        return self.results

    def is_healthy(self) -> bool:
        if not self.results:
            self.run_checks()
        return all(r.get('healthy', False) for r in self.results.values())


class WatchdogTimer:
    def __init__(self, name: str, timeout: float = 30.0, callback: Optional[Callable] = None):
        self.name = name
        self.timeout = timeout
        self.callback = callback
        self.last_reset = time.time()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while self._running:
            elapsed = time.time() - self.last_reset
            if elapsed > self.timeout:
                logger.warning("Watchdog %s triggered (elapsed: %.1fs)", self.name, elapsed)
                if self.callback:
                    try:
                        self.callback()
                    except Exception as e:
                        logger.error("Watchdog callback failed: %s", e)
                self.last_reset = time.time()
            time.sleep(1.0)

    def reset(self):
        self.last_reset = time.time()

    def stop(self):
        self._running = False


class ServiceRestartManager:
    """Manages automatic restart of crashed services."""

    def __init__(self):
        self._service_registry: Dict[str, Dict] = {}
        self._restart_history: deque = deque(maxlen=100)
        self._lock = threading.Lock()

    def register_service(self, name: str, start_fn: Callable,
                         stop_fn: Optional[Callable] = None,
                         health_fn: Optional[Callable] = None,
                         max_restarts: int = 5):
        """Register a service for restart management."""
        with self._lock:
            self._service_registry[name] = {
                'start_fn': start_fn,
                'stop_fn': stop_fn,
                'health_fn': health_fn,
                'max_restarts': max_restarts,
                'restart_count': 0,
                'last_restart': 0,
                'status': 'stopped',
            }
            logger.info("Service registered for restart: %s", name)

    def restart_service(self, name: str) -> bool:
        """Attempt to restart a service."""
        with self._lock:
            if name not in self._service_registry:
                logger.warning("Service not found: %s", name)
                return False

            service = self._service_registry[name]

            if service['restart_count'] >= service['max_restarts']:
                logger.error("Max restarts reached for service: %s", name)
                return False

        logger.info("Restarting service: %s", name)

        try:
            if service['stop_fn']:
                service['stop_fn']()
                time.sleep(1.0)

            service['start_fn']()
            service['restart_count'] += 1
            service['last_restart'] = time.time()
            service['status'] = 'running'

            self._restart_history.append({
                'service': name,
                'timestamp': time.time(),
                'success': True,
                'restart_number': service['restart_count'],
            })

            logger.info("Service %s restarted successfully (attempt %d)",
                        name, service['restart_count'])
            return True

        except Exception as e:
            logger.error("Failed to restart service %s: %s", name, e)
            service['status'] = 'failed'

            self._restart_history.append({
                'service': name,
                'timestamp': time.time(),
                'success': False,
                'error': str(e),
            })
            return False

    def check_service_health(self, name: str) -> bool:
        """Check if a service is healthy."""
        with self._lock:
            if name not in self._service_registry:
                return False
            service = self._service_registry[name]

        if service['health_fn']:
            try:
                return bool(service['health_fn']())
            except Exception:
                return False
        return service['status'] == 'running'


class ConnectionReconnectManager:
    """Manages automatic reconnection of failed connections."""

    def __init__(self):
        self._connections: Dict[str, Dict] = {}
        self._reconnect_history: deque = deque(maxlen=100)
        self._lock = threading.Lock()

    def register_connection(self, name: str, connect_fn: Callable,
                            disconnect_fn: Optional[Callable] = None,
                            health_fn: Optional[Callable] = None,
                            max_retries: int = 10,
                            retry_delay: float = 2.0):
        """Register a connection for automatic reconnection."""
        with self._lock:
            self._connections[name] = {
                'connect_fn': connect_fn,
                'disconnect_fn': disconnect_fn,
                'health_fn': health_fn,
                'max_retries': max_retries,
                'retry_delay': retry_delay,
                'retry_count': 0,
                'status': 'disconnected',
                'last_connected': 0,
            }
            logger.info("Connection registered for reconnect: %s", name)

    def reconnect(self, name: str) -> bool:
        """Attempt to reconnect a failed connection."""
        with self._lock:
            if name not in self._connections:
                logger.warning("Connection not found: %s", name)
                return False

            conn = self._connections[name]

        for attempt in range(conn['max_retries']):
            try:
                logger.info("Reconnecting %s (attempt %d/%d)",
                            name, attempt + 1, conn['max_retries'])

                if conn['disconnect_fn']:
                    try:
                        conn['disconnect_fn']()
                    except Exception:
                        pass

                conn['connect_fn']()
                conn['retry_count'] = 0
                conn['status'] = 'connected'
                conn['last_connected'] = time.time()

                self._reconnect_history.append({
                    'connection': name,
                    'timestamp': time.time(),
                    'attempt': attempt + 1,
                    'success': True,
                })

                logger.info("Reconnected %s after %d attempts", name, attempt + 1)
                return True

            except Exception as e:
                logger.warning("Reconnect attempt %d failed for %s: %s",
                              attempt + 1, name, e)
                time.sleep(conn['retry_delay'])

        conn['status'] = 'failed'
        conn['retry_count'] = conn['max_retries']

        self._reconnect_history.append({
            'connection': name,
            'timestamp': time.time(),
            'attempt': conn['max_retries'],
            'success': False,
        })

        logger.error("Failed to reconnect %s after %d attempts",
                     name, conn['max_retries'])
        return False

    def check_health(self, name: str) -> bool:
        """Check if a connection is healthy."""
        with self._lock:
            if name not in self._connections:
                return False
            conn = self._connections[name]

        if conn['health_fn']:
            try:
                return bool(conn['health_fn']())
            except Exception:
                return False
        return conn['status'] == 'connected'


class MemoryLeakDetector:
    """Detects and helps clear memory leaks."""

    def __init__(self, threshold_percent: float = 85.0):
        self.threshold_percent = threshold_percent
        self._snapshots: deque = deque(maxlen=50)

    def take_snapshot(self) -> Dict[str, Any]:
        """Take a memory usage snapshot."""
        try:
            process = psutil.Process()
            mem_info = process.memory_info()
            mem_percent = process.memory_percent()

            snapshot = {
                'timestamp': time.time(),
                'rss_mb': mem_info.rss / (1024 * 1024),
                'vms_mb': mem_info.vms / (1024 * 1024),
                'percent': mem_percent,
                'objects_count': len(gc.get_objects()),
            }

            self._snapshots.append(snapshot)
            return snapshot
        except Exception as e:
            logger.error("Memory snapshot failed: %s", e)
            return {'error': str(e)}

    def detect_leak(self) -> Dict[str, Any]:
        """Detect potential memory leaks by comparing snapshots."""
        if len(self._snapshots) < 2:
            return {'leak_detected': False, 'reason': 'Insufficient data'}

        recent = self._snapshots[-1]
        old = self._snapshots[0]

        growth = recent.get('percent', 0) - old.get('percent', 0)
        object_growth = recent.get('objects_count', 0) - old.get('objects_count', 0)

        leak_detected = growth > 10 or object_growth > 100000

        return {
            'leak_detected': leak_detected,
            'memory_growth_percent': round(growth, 2),
            'object_growth': object_growth,
            'current_percent': recent.get('percent', 0),
            'snapshots_analyzed': len(self._snapshots),
        }

    def clear_memory(self) -> Dict[str, Any]:
        """Attempt to clear memory leaks."""
        before = self.take_snapshot()

        gc.collect()

        collected = gc.collect()

        after = self.take_snapshot()

        return {
            'objects_collected': collected,
            'memory_before_mb': before.get('rss_mb', 0),
            'memory_after_mb': after.get('rss_mb', 0),
            'freed_mb': round(before.get('rss_mb', 0) - after.get('rss_mb', 0), 2),
        }


class CorruptedStateManager:
    """Detects and rebuilds corrupted state."""

    def __init__(self):
        self._state_backups: Dict[str, Dict] = {}
        self._corruption_log: deque = deque(maxlen=100)

    def backup_state(self, key: str, state: Dict):
        """Create a backup of valid state."""
        import hashlib
        import json
        state_json = json.dumps(state, sort_keys=True, default=str)
        state_hash = hashlib.md5(state_json.encode()).hexdigest()

        self._state_backups[key] = {
            'state': state.copy(),
            'hash': state_hash,
            'timestamp': time.time(),
        }

    def verify_state(self, key: str, state: Dict) -> Dict[str, Any]:
        """Verify if state is corrupted."""
        import hashlib
        import json
        try:
            state_json = json.dumps(state, sort_keys=True, default=str)
            current_hash = hashlib.md5(state_json.encode()).hexdigest()

            if key in self._state_backups:
                expected_hash = self._state_backups[key]['hash']
                is_valid = current_hash == expected_hash
            else:
                is_valid = True

            return {
                'key': key,
                'valid': is_valid,
                'current_hash': current_hash,
                'has_backup': key in self._state_backups,
            }
        except Exception as e:
            return {
                'key': key,
                'valid': False,
                'error': str(e),
            }

    def rebuild_state(self, key: str) -> Optional[Dict]:
        """Rebuild corrupted state from backup."""
        if key not in self._state_backups:
            logger.error("No backup available for state: %s", key)
            return None

        backup = self._state_backups[key]
        logger.info("Rebuilding state %s from backup (age: %.1fs)",
                     key, time.time() - backup['timestamp'])

        self._corruption_log.append({
            'key': key,
            'action': 'rebuilt',
            'timestamp': time.time(),
            'backup_age': time.time() - backup['timestamp'],
        })

        return backup['state'].copy()


class SelfHealingSystem:
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.health_monitor = HealthMonitor()
        self.watchdog_timers: Dict[str, WatchdogTimer] = {}
        self.recovery_log: deque = deque(maxlen=100)
        self._lock = threading.Lock()

        self.restart_manager = ServiceRestartManager()
        self.reconnect_manager = ConnectionReconnectManager()
        self.memory_detector = MemoryLeakDetector()
        self.state_manager = CorruptedStateManager()

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        with self._lock:
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = CircuitBreaker(name)
            return self.circuit_breakers[name]

    def can_execute(self, service_name: str) -> bool:
        cb = self.get_circuit_breaker(service_name)
        return cb.should_allow()

    def record_service_result(self, service_name: str, success: bool):
        cb = self.get_circuit_breaker(service_name)
        if success:
            cb.record_success()
        else:
            cb.record_failure()

    def register_health_check(self, name: str, check_fn: Callable):
        self.health_monitor.register_check(name, check_fn)

    def run_health_checks(self) -> Dict[str, Dict]:
        return self.health_monitor.run_checks()

    def is_system_healthy(self) -> bool:
        return self.health_monitor.is_healthy()

    def add_watchdog(self, name: str, timeout: float = 30.0, callback: Optional[Callable] = None):
        watchdog = WatchdogTimer(name, timeout, callback)
        self.watchdog_timers[name] = watchdog
        watchdog.start()

    def reset_watchdog(self, name: str):
        if name in self.watchdog_timers:
            self.watchdog_timers[name].reset()

    def attempt_recovery(self, service_name: str) -> bool:
        """Attempt recovery for a service."""
        logger.info("Attempting recovery for %s", service_name)
        self.recovery_log.append({
            'service': service_name,
            'timestamp': time.time(),
            'action': 'recovery_attempt',
        })

        cb = self.get_circuit_breaker(service_name)
        if cb.state == CircuitState.OPEN:
            cb.state = CircuitState.HALF_OPEN
            return True
        return False

    def restart_crashed_service(self, service_name: str) -> bool:
        """Restart a crashed service."""
        logger.info("Restarting crashed service: %s", service_name)
        success = self.restart_manager.restart_service(service_name)

        self.recovery_log.append({
            'service': service_name,
            'timestamp': time.time(),
            'action': 'restart',
            'success': success,
        })

        return success

    def reconnect_failed_connection(self, connection_name: str) -> bool:
        """Reconnect a failed connection."""
        logger.info("Reconnecting failed connection: %s", connection_name)
        success = self.reconnect_manager.reconnect(connection_name)

        self.recovery_log.append({
            'service': connection_name,
            'timestamp': time.time(),
            'action': 'reconnect',
            'success': success,
        })

        return success

    def clear_memory_leaks(self) -> Dict[str, Any]:
        """Clear memory leaks."""
        logger.info("Clearing memory leaks")
        result = self.memory_detector.clear_memory()

        self.recovery_log.append({
            'service': 'memory',
            'timestamp': time.time(),
            'action': 'memory_cleanup',
            'result': result,
        })

        return result

    def rebuild_corrupted_state(self, state_key: str) -> Optional[Dict]:
        """Rebuild corrupted state from backup."""
        logger.info("Rebuilding corrupted state: %s", state_key)
        state = self.state_manager.rebuild_state(state_key)

        self.recovery_log.append({
            'service': state_key,
            'timestamp': time.time(),
            'action': 'state_rebuild',
            'success': state is not None,
        })

        return state

    def get_system_status(self) -> Dict[str, Any]:
        return {
            'circuit_breakers': {name: cb.to_dict() for name, cb in self.circuit_breakers.items()},
            'healthy': self.is_system_healthy(),
            'watchdog_timers': list(self.watchdog_timers.keys()),
            'recovery_count': len(self.recovery_log),
            'restart_manager': {
                'registered_services': len(self.restart_manager._service_registry),
            },
            'reconnect_manager': {
                'registered_connections': len(self.reconnect_manager._connections),
            },
            'memory_status': self.memory_detector.take_snapshot(),
            'recent_recovery': list(self.recovery_log)[-10:],
        }


_self_healing: Optional[SelfHealingSystem] = None


def get_self_healing() -> SelfHealingSystem:
    global _self_healing
    if _self_healing is None:
        _self_healing = SelfHealingSystem()
    return _self_healing
