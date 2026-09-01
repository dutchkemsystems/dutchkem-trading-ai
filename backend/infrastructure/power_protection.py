"""
V4 Power Protection — Monitor and respond to power events for graceful shutdown.
"""
import logging
import os
import signal
import subprocess
import time
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger('infrastructure.power_protection')


class PowerSource(Enum):
    AC_POWER = 'ac_power'
    UPS_BATTERY = 'ups_battery'
    UNKNOWN = 'unknown'


class PowerStatus(Enum):
    NORMAL = 'normal'
    LOW_BATTERY = 'low_battery'
    CRITICAL_BATTERY = 'critical_battery'
    POWER_OUTAGE = 'power_outage'


class PowerProtection:
    """
    Monitor and respond to power events.
    - Monitor UPS status and battery level
    - Handle power outage gracefully
    - Save state on low battery
    - Force shutdown on critical battery
    """

    def __init__(self, ups_host: str = 'localhost', ups_port: int = 3493,
                 low_battery_threshold: int = 50,
                 critical_battery_threshold: int = 20,
                 check_interval: float = 30.0):
        self.ups_host = ups_host
        self.ups_port = ups_port
        self.low_battery_threshold = low_battery_threshold
        self.critical_battery_threshold = critical_battery_threshold
        self.check_interval = check_interval

        self.status = PowerStatus.NORMAL
        self.power_source = PowerSource.UNKNOWN
        self.battery_level = 100
        self.battery_runtime = 0
        self.last_check = time.time()
        self.outage_start: Optional[float] = None
        self.is_shutting_down = False

        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._callbacks: Dict[str, list] = {
            'on_power_outage': [],
            'on_low_battery': [],
            'on_critical_battery': [],
            'on_power_restored': [],
            'on_shutdown': [],
        }
        self._lock = threading.Lock()

    def check_power_status(self) -> Dict[str, Any]:
        """Check current power status via system methods."""
        status_info = {
            'power_source': PowerSource.UNKNOWN.value,
            'battery_level': 100,
            'battery_runtime': 0,
            'status': PowerStatus.NORMAL.value,
            'check_time': time.time(),
        }

        try:
            battery_info = self._check_system_battery()
            if battery_info:
                status_info.update(battery_info)
        except Exception as e:
            logger.debug("Battery check via system failed: %s", e)

        try:
            ups_info = self._check_nut_ups()
            if ups_info:
                status_info.update(ups_info)
        except Exception as e:
            logger.debug("NUT UPS check failed: %s", e)

        with self._lock:
            self.battery_level = status_info['battery_level']
            self.battery_runtime = status_info['battery_runtime']
            self.power_source = PowerSource(status_info['power_source'])
            self.last_check = time.time()

            if self.battery_level <= self.critical_battery_threshold:
                self.status = PowerStatus.CRITICAL_BATTERY
            elif self.battery_level <= self.low_battery_threshold:
                self.status = PowerStatus.LOW_BATTERY
            elif self.power_source == PowerSource.UPS_BATTERY:
                self.status = PowerStatus.POWER_OUTAGE
            else:
                self.status = PowerStatus.NORMAL

            status_info['status'] = self.status.value

        return status_info

    def _check_system_battery(self) -> Optional[Dict]:
        """Check battery status via system commands."""
        try:
            if os.name == 'nt':
                result = subprocess.run(
                    ['WMIC', 'Path', 'Win32_Battery', 'get', 'EstimatedChargeRemaining,BatteryStatus'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            level = int(parts[0])
                            battery_status = int(parts[1]) if len(parts) > 1 else 2
                            source = PowerSource.AC_POWER if battery_status == 2 else PowerSource.UPS_BATTERY
                            return {
                                'power_source': source.value,
                                'battery_level': level,
                                'battery_runtime': 0,
                            }
            else:
                result = subprocess.run(
                    ['upower', '-i', '/org/freedesktop/UPower/DisplayDevice'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    level = 100
                    for line in result.stdout.split('\n'):
                        if 'percentage' in line:
                            level = int(line.split(':')[1].strip().replace('%', ''))
                        elif 'time-to-empty' in line:
                            runtime = float(line.split(':')[1].strip().split()[0])
                            return {
                                'power_source': PowerSource.UPS_BATTERY.value if level < 100 else PowerSource.AC_POWER.value,
                                'battery_level': level,
                                'battery_runtime': int(runtime),
                            }
                    return {
                        'power_source': PowerSource.AC_POWER.value,
                        'battery_level': level,
                        'battery_runtime': 0,
                    }
        except Exception:
            pass
        return None

    def _check_nut_ups(self) -> Optional[Dict]:
        """Check UPS status via NUT (Network UPS Tools)."""
        try:
            result = subprocess.run(
                ['upsc', f'{self.ups_host}:{self.ups_port}'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                info = {}
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()

                battery = int(info.get('battery.charge', 100))
                status = info.get('ups.status', 'OL')

                if 'OB' in status:
                    source = PowerSource.UPS_BATTERY
                else:
                    source = PowerSource.AC_POWER

                return {
                    'power_source': source.value,
                    'battery_level': battery,
                    'battery_runtime': int(info.get('battery.runtime', 0)),
                }
        except Exception:
            pass
        return None

    def handle_power_outage(self):
        """Handle a power outage event."""
        logger.warning("Power outage detected! Battery: %d%%", self.battery_level)

        with self._lock:
            if self.outage_start is None:
                self.outage_start = time.time()

        self._fire_event('on_power_outage', {
            'battery_level': self.battery_level,
            'battery_runtime': self.battery_runtime,
            'timestamp': time.time(),
        })

        self._log_power_event('power_outage', f"Battery at {self.battery_level}%")

    def handle_low_battery(self):
        """Handle low battery warning - save state."""
        logger.warning("Low battery detected! Level: %d%%", self.battery_level)

        self._save_emergency_state()
        self._fire_event('on_low_battery', {
            'battery_level': self.battery_level,
            'timestamp': time.time(),
        })

        self._log_power_event('low_battery', f"Battery at {self.battery_level}%")

    def handle_critical_battery(self):
        """Handle critical battery - prepare for forced shutdown."""
        logger.critical("CRITICAL battery! Level: %d%%. Preparing shutdown.", self.battery_level)

        self._save_emergency_state()
        self._fire_event('on_critical_battery', {
            'battery_level': self.battery_level,
            'timestamp': time.time(),
        })

        self._log_power_event('critical_battery', f"Battery at {self.battery_level}%, initiating shutdown")

        self.initiate_graceful_shutdown()

    def handle_power_restored(self):
        """Handle power restoration."""
        logger.info("Power restored. Battery charging: %d%%", self.battery_level)

        with self._lock:
            self.outage_start = None

        self._fire_event('on_power_restored', {
            'battery_level': self.battery_level,
            'timestamp': time.time(),
        })

        self._log_power_event('power_restored', f"Battery at {self.battery_level}%")

    def _save_emergency_state(self):
        """Save emergency state to disk."""
        try:
            from .trading_state import get_state_persistence
            persistence = get_state_persistence()

            persistence.save_positions(persistence.load_positions() or [])
            persistence.save_account(persistence.load_account() or {})
            persistence.save_orders(persistence.load_orders() or [])

            logger.info("Emergency state saved successfully")
        except Exception as e:
            logger.error("Failed to save emergency state: %s", e)

    def initiate_graceful_shutdown(self, delay: float = 10.0):
        """Initiate a graceful system shutdown."""
        if self.is_shutting_down:
            return

        self.is_shutting_down = True
        logger.critical("Initiating graceful shutdown in %.1f seconds", delay)

        self._fire_event('on_shutdown', {
            'delay': delay,
            'battery_level': self.battery_level,
            'timestamp': time.time(),
        })

        threading.Thread(
            target=self._shutdown_worker,
            args=(delay,),
            daemon=True
        ).start()

    def _shutdown_worker(self, delay: float):
        """Background worker to perform shutdown."""
        time.sleep(delay)

        try:
            self._save_emergency_state()
        except Exception as e:
            logger.error("Final state save failed: %s", e)

        logger.critical("Executing system shutdown")

        try:
            if os.name == 'nt':
                subprocess.run(['shutdown', '/s', '/t', '10', '/c', 'Power failure - Trading AI shutdown'],
                             timeout=5)
            else:
                subprocess.run(['shutdown', '-h', 'now'], timeout=5)
        except Exception as e:
            logger.error("Shutdown command failed: %s", e)

    def on(self, event: str, callback: Callable):
        """Register a callback for power events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _fire_event(self, event: str, data: Any):
        """Fire callbacks for a power event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error("Power event callback error for %s: %s", event, e)

    def _log_power_event(self, event_type: str, description: str):
        """Log power event to database."""
        try:
            from .models import FailoverEvent
            FailoverEvent.log(
                event_type='power_event',
                description=description,
                severity='WARNING' if 'critical' in event_type else 'INFO',
                metadata={
                    'event_type': event_type,
                    'battery_level': self.battery_level,
                    'power_source': self.power_source.value,
                }
            )
        except Exception as e:
            logger.error("Failed to log power event: %s", e)

    def start_monitoring(self):
        """Start the power monitoring thread."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Power monitoring started (interval: %.1fs)", self.check_interval)

    def stop_monitoring(self):
        """Stop the power monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Power monitoring stopped")

    def _monitor_loop(self):
        """Main power monitoring loop."""
        while self._running:
            try:
                status = self.check_power_status()

                if self.status == PowerStatus.CRITICAL_BATTERY:
                    self.handle_critical_battery()
                elif self.status == PowerStatus.LOW_BATTERY:
                    self.handle_low_battery()
                elif self.status == PowerStatus.POWER_OUTAGE:
                    self.handle_power_outage()
                elif self.outage_start is not None:
                    self.handle_power_restored()

            except Exception as e:
                logger.error("Power monitor error: %s", e)

            time.sleep(self.check_interval)

    def get_status(self) -> Dict[str, Any]:
        """Get current power protection status."""
        return {
            'status': self.status.value,
            'power_source': self.power_source.value,
            'battery_level': self.battery_level,
            'battery_runtime': self.battery_runtime,
            'outage_active': self.outage_start is not None,
            'outage_duration': (
                time.time() - self.outage_start if self.outage_start else 0
            ),
            'is_shutting_down': self.is_shutting_down,
            'last_check': self.last_check,
            'monitoring': self._running,
        }


_protection: Optional[PowerProtection] = None


def get_power_protection() -> PowerProtection:
    global _protection
    if _protection is None:
        _protection = PowerProtection()
    return _protection
