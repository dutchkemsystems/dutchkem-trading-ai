"""
V4 Health Monitor — Continuous system health monitoring with alerting.
"""
import logging
import os
import time
import threading
import platform
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum
from collections import deque

logger = logging.getLogger('infrastructure.health_monitor')


class HealthLevel(Enum):
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'
    CRITICAL = 'critical'


class HealthCheck:
    """Represents a single health check."""

    def __init__(self, name: str, check_fn: Callable, interval: float = 30.0,
                 timeout: float = 10.0, critical: bool = False):
        self.name = name
        self.check_fn = check_fn
        self.interval = interval
        self.timeout = timeout
        self.critical = critical
        self.last_result: Optional[Dict] = None
        self.last_check = 0.0
        self.consecutive_failures = 0


class HealthMonitor:
    """
    Continuous health monitoring.
    - Monitor CPU, memory, disk, network
    - Monitor MT5 connection status
    - Monitor trading activity
    - Generate health reports
    - Trigger alerts on degradation
    """

    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        self.checks: Dict[str, HealthCheck] = {}
        self.results: Dict[str, Dict] = {}
        self.history: deque = deque(maxlen=1000)
        self.overall_level = HealthLevel.HEALTHY
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._callbacks: Dict[str, list] = {
            'on_degradation': [],
            'on_critical': [],
            'on_recovery': [],
        }

        self._register_default_checks()

    def _register_default_checks(self):
        """Register default system health checks."""
        self.register_check('cpu', self._check_cpu, interval=10.0, critical=False)
        self.register_check('memory', self._check_memory, interval=15.0, critical=False)
        self.register_check('disk', self._check_disk, interval=60.0, critical=False)
        self.register_check('network', self._check_network, interval=15.0, critical=True)
        self.register_check('mt5', self._check_mt5, interval=10.0, critical=True)
        self.register_check('redis', self._check_redis, interval=30.0, critical=False)
        self.register_check('database', self._check_database, interval=60.0, critical=True)

    def register_check(self, name: str, check_fn: Callable,
                       interval: float = 30.0, timeout: float = 10.0,
                       critical: bool = False):
        """Register a health check."""
        with self._lock:
            self.checks[name] = HealthCheck(
                name=name,
                check_fn=check_fn,
                interval=interval,
                timeout=timeout,
                critical=critical,
            )
            logger.info("Health check registered: %s (critical=%s)", name, critical)

    def run_check(self, name: str) -> Dict[str, Any]:
        """Run a specific health check."""
        with self._lock:
            if name not in self.checks:
                return {'name': name, 'healthy': False, 'error': 'Check not found'}

            check = self.checks[name]

        try:
            start = time.time()
            result = check.check_fn()
            elapsed = (time.time() - start) * 1000

            check_result = {
                'name': name,
                'healthy': bool(result.get('healthy', result)) if isinstance(result, dict) else bool(result),
                'latency_ms': round(elapsed, 2),
                'checked_at': time.time(),
                'critical': check.critical,
            }

            if isinstance(result, dict):
                check_result.update(result)

            if check_result['healthy']:
                check.consecutive_failures = 0
            else:
                check.consecutive_failures += 1
                check_result['consecutive_failures'] = check.consecutive_failures

            check.last_result = check_result
            check.last_check = time.time()

            with self._lock:
                self.results[name] = check_result

            return check_result

        except Exception as e:
            check.consecutive_failures += 1
            error_result = {
                'name': name,
                'healthy': False,
                'error': str(e),
                'checked_at': time.time(),
                'critical': check.critical,
                'consecutive_failures': check.consecutive_failures,
            }

            with self._lock:
                self.results[name] = error_result
                check.last_result = error_result

            return error_result

    def run_all_checks(self) -> Dict[str, Dict]:
        """Run all registered health checks."""
        check_names = list(self.checks.keys())
        for name in check_names:
            self.run_check(name)

        self._update_overall_level()
        return dict(self.results)

    def _update_overall_level(self):
        """Update the overall health level based on check results."""
        previous_level = self.overall_level

        if not self.results:
            self.overall_level = HealthLevel.HEALTHY
            return

        critical_failures = sum(
            1 for name, result in self.results.items()
            if not result.get('healthy', False) and result.get('critical', False)
        )

        all_failures = sum(
            1 for result in self.results.values()
            if not result.get('healthy', False)
        )

        total_checks = len(self.results)

        if critical_failures > 0:
            self.overall_level = HealthLevel.CRITICAL
        elif all_failures > total_checks * 0.5:
            self.overall_level = HealthLevel.UNHEALTHY
        elif all_failures > 0:
            self.overall_level = HealthLevel.DEGRADED
        else:
            self.overall_level = HealthLevel.HEALTHY

        if self.overall_level != previous_level:
            self._handle_level_change(previous_level, self.overall_level)

    def _handle_level_change(self, old_level: HealthLevel, new_level: HealthLevel):
        """Handle health level changes."""
        logger.warning("Health level changed: %s -> %s", old_level.value, new_level.value)

        event_data = {
            'previous_level': old_level.value,
            'new_level': new_level.value,
            'timestamp': time.time(),
            'results': dict(self.results),
        }

        if new_level in (HealthLevel.CRITICAL, HealthLevel.UNHEALTHY):
            self._fire_event('on_critical', event_data)
        elif new_level == HealthLevel.DEGRADED:
            self._fire_event('on_degradation', event_data)
        elif old_level in (HealthLevel.CRITICAL, HealthLevel.UNHEALTHY, HealthLevel.DEGRADED):
            self._fire_event('on_recovery', event_data)

    def _check_cpu(self) -> Dict:
        """Check CPU usage."""
        try:
            result = os.popen("wmic cpu get loadpercentage /value" if platform.system() == "Windows"
                            else "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'").read()
            if 'LoadPercentage' in result:
                load = float(result.split('LoadPercentage=')[1].strip())
            elif result.strip():
                load = float(result.strip())
            else:
                load = 0.0

            return {
                'healthy': load < 90,
                'cpu_percent': load,
                'level': 'critical' if load > 95 else 'warning' if load > 80 else 'normal',
            }
        except Exception:
            return {'healthy': True, 'cpu_percent': 0.0}

    def _check_memory(self) -> Dict:
        """Check memory usage."""
        try:
            if platform.system() == 'Windows':
                result = os.popen(
                    "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value"
                ).read()
                lines = result.strip().split('\n')
                free = total = 0
                for line in lines:
                    if 'FreePhysicalMemory' in line:
                        free = float(line.split('=')[1].strip()) / 1024 / 1024
                    elif 'TotalVisibleMemorySize' in line:
                        total = float(line.split('=')[1].strip()) / 1024 / 1024
                used = total - free
                percent = (used / total * 100) if total > 0 else 0
            else:
                with open('/proc/meminfo', 'r') as f:
                    lines = f.readlines()
                total = int(lines[0].split()[1]) / 1024 / 1024
                available = int(lines[2].split()[1]) / 1024 / 1024
                used = total - available
                percent = (used / total * 100) if total > 0 else 0

            return {
                'healthy': percent < 90,
                'memory_percent': round(percent, 1),
                'memory_used_gb': round(used, 2),
                'memory_total_gb': round(total, 2),
            }
        except Exception:
            return {'healthy': True, 'memory_percent': 0.0}

    def _check_disk(self) -> Dict:
        """Check disk usage."""
        try:
            if platform.system() == 'Windows':
                result = os.popen("wmic logicaldisk get size,freespace,caption /value").read()
                total = free = 0
                for line in result.split('\n'):
                    if 'FreeSpace' in line and line.split('=')[1].strip():
                        free = float(line.split('=')[1].strip()) / (1024**3)
                    elif 'Size' in line and line.split('=')[1].strip():
                        total = float(line.split('=')[1].strip()) / (1024**3)
                used = total - free
                percent = (used / total * 100) if total > 0 else 0
            else:
                stat = os.statvfs('/')
                total = (stat.f_blocks * stat.f_frsize) / (1024**3)
                free = (stat.f_bavail * stat.f_frsize) / (1024**3)
                used = total - free
                percent = (used / total * 100) if total > 0 else 0

            return {
                'healthy': percent < 90,
                'disk_percent': round(percent, 1),
                'disk_used_gb': round(used, 2),
                'disk_total_gb': round(total, 2),
            }
        except Exception:
            return {'healthy': True, 'disk_percent': 0.0}

    def _check_network(self) -> Dict:
        """Check network connectivity."""
        try:
            import socket
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(('8.8.8.8', 53))
            latency = (time.time() - start) * 1000
            sock.close()

            return {
                'healthy': latency < 200,
                'latency_ms': round(latency, 2),
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}

    def _check_mt5(self) -> Dict:
        """Check MT5 connection status."""
        try:
            from django.conf import settings
            mt5_host = getattr(settings, 'MT5_HOST', 'localhost')
            mt5_port = getattr(settings, 'MT5_PORT', 3000)

            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((mt5_host, mt5_port))
            sock.close()

            return {'healthy': True, 'host': mt5_host, 'port': mt5_port}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}

    def _check_redis(self) -> Dict:
        """Check Redis connectivity."""
        try:
            from django.core.cache import cache
            cache.set('_health_check', 'ok', 5)
            val = cache.get('_health_check')
            return {'healthy': val == 'ok'}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}

    def _check_database(self) -> Dict:
        """Check database connectivity."""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {'healthy': True}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}

    def on(self, event: str, callback: Callable):
        """Register a callback for health events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _fire_event(self, event: str, data: Any):
        """Fire callbacks for a health event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error("Health event callback error for %s: %s", event, e)

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive health report."""
        with self._lock:
            results = dict(self.results)

        report = {
            'timestamp': time.time(),
            'overall_level': self.overall_level.value,
            'total_checks': len(results),
            'healthy_checks': sum(1 for r in results.values() if r.get('healthy', False)),
            'unhealthy_checks': sum(1 for r in results.values() if not r.get('healthy', False)),
            'critical_checks': sum(
                1 for r in results.values()
                if not r.get('healthy', False) and r.get('critical', False)
            ),
            'checks': results,
            'history_count': len(self.history),
        }

        self.history.append(report)
        return report

    def start_monitoring(self):
        """Start the health monitoring thread."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Health monitoring started (interval: %.1fs)", self.check_interval)

    def stop_monitoring(self):
        """Stop the health monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Health monitoring stopped")

    def _monitor_loop(self):
        """Main health monitoring loop."""
        while self._running:
            try:
                self.run_all_checks()
                report = self.generate_report()

                if self.overall_level in (HealthLevel.CRITICAL, HealthLevel.UNHEALTHY):
                    logger.warning(
                        "System health degraded: %s (healthy=%d/%d)",
                        self.overall_level.value,
                        report['healthy_checks'],
                        report['total_checks']
                    )
            except Exception as e:
                logger.error("Health monitor error: %s", e)

            time.sleep(self.check_interval)

    def get_status(self) -> Dict[str, Any]:
        """Get current health monitoring status."""
        with self._lock:
            return {
                'overall_level': self.overall_level.value,
                'total_checks': len(self.checks),
                'results': dict(self.results),
                'monitoring': self._running,
                'history_size': len(self.history),
            }


_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor
