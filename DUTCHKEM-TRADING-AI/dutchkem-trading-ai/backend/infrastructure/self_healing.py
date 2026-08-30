"""
V4 Self-Healing — Automatic service restart, circuit breaker recovery, MT5 reconnection.
"""
import logging
import time
import threading
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


class SelfHealingSystem:
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.health_monitor = HealthMonitor()
        self.watchdog_timers: Dict[str, WatchdogTimer] = {}
        self.recovery_log: deque = deque(maxlen=100)
        self._lock = threading.Lock()
    
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
    
    def get_system_status(self) -> Dict[str, Any]:
        return {
            'circuit_breakers': {name: cb.to_dict() for name, cb in self.circuit_breakers.items()},
            'healthy': self.is_system_healthy(),
            'watchdog_timers': list(self.watchdog_timers.keys()),
            'recovery_count': len(self.recovery_log),
        }


_self_healing: Optional[SelfHealingSystem] = None

def get_self_healing() -> SelfHealingSystem:
    global _self_healing
    if _self_healing is None:
        _self_healing = SelfHealingSystem()
    return _self_healing
