"""
V5 Runtime Application Self-Protection (RASP) Engine.

Detects code tampering, runtime anomalies, debugger attachment,
memory injection, and environment manipulation.
"""
import hashlib
import importlib
import json
import logging
import os
import platform
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger('security.rasp')

BASE_DIR = Path(__file__).resolve().parent.parent
INTEGRITY_HASH_FILE = BASE_DIR / '.integrity_hashes.json'

# Files to monitor for integrity
_MONITORED_EXTENSIONS = {'.py'}
_SKIP_DIRS = {
    '__pycache__', '.git', 'node_modules', 'migrations',
    'htmlcov', '.pytest_cache', 'staticfiles', 'media', 'logs',
}


# ---------------------------------------------------------------------------
# Code Integrity Checker
# ---------------------------------------------------------------------------

class CodeIntegrityChecker:
    """Verifies code integrity by comparing SHA-256 hashes of source files."""

    def __init__(self):
        self._baseline: Dict[str, str] = {}
        self._load_baseline()

    def _load_baseline(self) -> None:
        if INTEGRITY_HASH_FILE.exists():
            try:
                with open(INTEGRITY_HASH_FILE, 'r') as f:
                    self._baseline = json.load(f)
                logger.info('Integrity baseline loaded: %d files', len(self._baseline))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning('Failed to load integrity baseline: %s', e)
                self._baseline = {}

    def _save_baseline(self) -> None:
        try:
            with open(INTEGRITY_HASH_FILE, 'w') as f:
                json.dump(self._baseline, f, indent=2)
            logger.info('Integrity baseline saved: %d files', len(self._baseline))
        except OSError as e:
            logger.error('Failed to save integrity baseline: %s', e)

    def compute_file_hash(self, filepath: str) -> Optional[str]:
        """Compute SHA-256 hex digest of a file."""
        path = Path(filepath)
        if not path.exists() or not path.is_file():
            return None
        sha = hashlib.sha256()
        try:
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha.update(chunk)
            return sha.hexdigest()
        except OSError:
            return None

    def _discover_files(self) -> Set[str]:
        """Recursively discover Python files under the backend directory."""
        files: Set[str] = set()
        backend_dir = BASE_DIR
        for root, dirs, filenames in os.walk(backend_dir):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for fn in filenames:
                if Path(fn).suffix in _MONITORED_EXTENSIONS:
                    full = os.path.join(root, fn)
                    files.add(os.path.relpath(full, BASE_DIR))
        return files

    def store_baseline(self) -> int:
        """Create a fresh hash baseline of all source files."""
        files = self._discover_files()
        baseline: Dict[str, str] = {}
        for rel in files:
            full = os.path.join(BASE_DIR, rel)
            h = self.compute_file_hash(full)
            if h:
                baseline[rel] = h
        self._baseline = baseline
        self._save_baseline()
        return len(baseline)

    def verify_all_files(self) -> Dict[str, bool]:
        """Compare current files against the stored baseline."""
        results: Dict[str, bool] = {}
        for rel, stored_hash in self._baseline.items():
            full = os.path.join(BASE_DIR, rel)
            current = self.compute_file_hash(full)
            if current is None:
                results[rel] = False  # file missing
            else:
                results[rel] = current == stored_hash
        return results

    def detect_changes(self) -> List[str]:
        """Return list of modified or missing files."""
        changed: List[str] = []
        for rel, stored_hash in self._baseline.items():
            full = os.path.join(BASE_DIR, rel)
            current = self.compute_file_hash(full)
            if current is None or current != stored_hash:
                changed.append(rel)

        # Detect newly added files not in baseline
        current_files = self._discover_files()
        for rel in current_files - set(self._baseline.keys()):
            changed.append(rel)

        return changed


# ---------------------------------------------------------------------------
# Runtime Monitor
# ---------------------------------------------------------------------------

class RuntimeMonitor:
    """Monitors for suspicious runtime behaviour."""

    def __init__(self):
        self._initial_env = dict(os.environ)
        self._processes_at_start = self._get_pids()
        self._monitoring = False
        self._thread: Optional[threading.Thread] = None
        self._anomalies: List[Dict[str, Any]] = []

    def _get_pids(self) -> Set[int]:
        try:
            pids_path = '/proc' if platform.system() == 'Linux' else None
            if pids_path and os.path.isdir(pids_path):
                return {int(d) for d in os.listdir(pids_path) if d.isdigit()}
        except (OSError, ValueError):
            pass
        return set()

    def monitor_suspicious_calls(self) -> List[str]:
        """Check for suspicious system calls (Linux /proc-based)."""
        suspicious: List[str] = []
        if platform.system() != 'Linux':
            return suspicious

        proc_dir = Path('/proc/self')
        try:
            status = (proc_dir / 'status').read_text()
            for line in status.splitlines():
                if line.startswith('TracerPid:'):
                    val = line.split(':')[1].strip()
                    if val != '0':
                        suspicious.append(f'TracerPid detected: {val}')
        except OSError:
            pass

        return suspicious

    def detect_debugger(self) -> bool:
        """Detect if a debugger is attached to the current process."""
        # Check for common debug environment variables
        debug_envs = ['PYDEVD', 'PYCHARM_DEBUG', 'PYTHONBREAKPOINT', 'REMOTE_DEBUG']
        for env in debug_envs:
            if env in os.environ:
                return True

        # Linux: check TracerPid
        if platform.system() == 'Linux':
            try:
                status = Path('/proc/self/status').read_text()
                for line in status.splitlines():
                    if line.startswith('TracerPid:'):
                        val = line.split(':')[1].strip()
                        if val != '0':
                            return True
            except OSError:
                pass

        return False

    def detect_memory_modification(self) -> List[str]:
        """Heuristic checks for memory-level tampering."""
        warnings: List[str] = []

        # Verify critical module code objects haven't been replaced
        critical_modules = ['security.siem', 'security.rasp', 'security.credential_manager']
        for mod_name in critical_modules:
            mod = sys.modules.get(mod_name)
            if mod is None:
                continue
            mod_file = getattr(mod, '__file__', None)
            if mod_file and os.path.exists(mod_file):
                # Compare module's cached source hash vs on-disk hash
                try:
                    from .encryption import get_encryption
                    enc = get_encryption()
                    with open(mod_file, 'rb') as f:
                        source = f.read()
                    current_hash = hashlib.sha256(source).hexdigest()
                    # If we have a stored hash, verify
                    stored = self._baseline_hashes.get(mod_name)
                    if stored and stored != current_hash:
                        warnings.append(f'Module {mod_name} source modified in memory check')
                except Exception:
                    pass

        return warnings

    def monitor_env_changes(self) -> List[str]:
        """Detect environment variable changes since startup."""
        changes: List[str] = []
        current = dict(os.environ)
        for key, value in current.items():
            if key not in self._initial_env:
                changes.append(f'New env var added: {key}')
            elif self._initial_env[key] != value:
                changes.append(f'Env var changed: {key}')

        removed = set(self._initial_env.keys()) - set(current.keys())
        for key in removed:
            changes.append(f'Env var removed: {key}')

        return changes

    def detect_process_injection(self) -> bool:
        """Check for indicators of process injection (Linux)."""
        if platform.system() != 'Linux':
            return False

        try:
            maps_path = Path('/proc/self/maps')
            if not maps_path.exists():
                return False
            maps_content = maps_path.read_text()
            # Look for suspicious RWX (read-write-execute) memory regions
            rwx_count = maps_content.count('rwxp')
            if rwx_count > 10:
                logger.warning('High number of RWX memory regions: %d', rwx_count)
                return True
        except OSError:
            pass

        return False

    @property
    def _baseline_hashes(self) -> Dict[str, str]:
        if INTEGRITY_HASH_FILE.exists():
            try:
                with open(INTEGRITY_HASH_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def start_continuous_monitoring(self, interval: int = 60) -> None:
        """Start background monitoring thread."""
        if self._monitoring:
            return
        self._monitoring = True

        def _monitor_loop():
            while self._monitoring:
                try:
                    env_changes = self.monitor_env_changes()
                    for c in env_changes:
                        logger.warning('ENV change: %s', c)
                        self._anomalies.append({'type': 'env_change', 'detail': c})

                    if self.detect_debugger():
                        logger.critical('Debugger detected!')
                        self._anomalies.append({'type': 'debugger_detected', 'detail': 'Debugger attached'})

                    if self.detect_process_injection():
                        logger.critical('Possible process injection detected!')
                        self._anomalies.append({'type': 'process_injection', 'detail': 'RWX regions exceeded threshold'})

                    memory_warns = self.detect_memory_modification()
                    for w in memory_warns:
                        logger.critical(w)
                        self._anomalies.append({'type': 'memory_modification', 'detail': w})
                except Exception as e:
                    logger.error('Runtime monitor error: %s', e)

                time.sleep(interval)

        self._thread = threading.Thread(target=_monitor_loop, daemon=True, name='rasp-monitor')
        self._thread.start()

    def stop_continuous_monitoring(self) -> None:
        self._monitoring = False

    def get_anomalies(self) -> List[Dict[str, Any]]:
        return list(self._anomalies)


# ---------------------------------------------------------------------------
# Tamper Detector
# ---------------------------------------------------------------------------

class TamperDetector:
    """Checks integrity of critical Django configuration components."""

    def check_settings_integrity(self) -> Dict[str, Any]:
        """Verify Django settings module hasn't been unexpectedly modified."""
        from config import settings
        settings_file = Path(settings.__file__)
        baseline_file = INTEGRITY_HASH_FILE

        result = {'status': 'ok', 'file': str(settings_file), 'modified': False}
        if not settings_file.exists():
            result['status'] = 'missing'
            return result

        current_hash = hashlib.sha256(settings_file.read_bytes()).hexdigest()
        if baseline_file.exists():
            try:
                baseline = json.loads(baseline_file.read_text())
                stored = baseline.get('config/settings.py')
                if stored and stored != current_hash:
                    result['status'] = 'tampered'
                    result['modified'] = True
            except (json.JSONDecodeError, OSError):
                pass

        return result

    def check_middleware_integrity(self) -> Dict[str, Any]:
        """Verify the middleware chain matches expected configuration."""
        from config import settings
        expected_middleware = [
            'corsheaders.middleware.CorsMiddleware',
            'django.middleware.security.SecurityMiddleware',
            'whitenoise.middleware.WhiteNoiseMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django_otp.middleware.OTPMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
            'django_ratelimit.middleware.RatelimitMiddleware',
            'config.middleware.RequestTimingMiddleware',
        ]

        actual = getattr(settings, 'MIDDLEWARE', [])
        missing = set(expected_middleware) - set(actual)
        extra = set(actual) - set(expected_middleware)

        return {
            'status': 'ok' if not missing and not extra else 'tampered',
            'missing': list(missing),
            'extra': list(extra),
            'count_match': len(expected_middleware) == len(actual),
        }

    def check_url_integrity(self) -> Dict[str, Any]:
        """Verify URL configuration hasn't been modified."""
        from config import settings
        url_conf_module = importlib.import_module(settings.ROOT_URLCONF)

        patterns = []
        if hasattr(url_conf_module, 'urlpatterns'):
            for p in url_conf_module.urlpatterns:
                patterns.append(str(p.pattern))

        baseline_file = INTEGRITY_HASH_FILE
        result = {'status': 'ok', 'pattern_count': len(patterns), 'modified': False}

        if baseline_file.exists():
            try:
                baseline = json.loads(baseline_file.read_text())
                stored_count = baseline.get('__url_pattern_count__')
                if stored_count is not None and stored_count != len(patterns):
                    result['status'] = 'tampered'
                    result['modified'] = True
                    result['expected_count'] = stored_count
            except (json.JSONDecodeError, OSError):
                pass

        return result

    def check_model_integrity(self) -> Dict[str, Any]:
        """Verify critical model definitions are intact."""
        from django.apps import apps

        critical_models = ['security.SecurityEvent', 'security.CredentialVault', 'security.EncryptionKey']
        status = {'status': 'ok', 'models': {}}

        for model_label in critical_models:
            app_label, model_name = model_label.split('.')
            try:
                model = apps.get_model(app_label, model_name)
                fields = [f.name for f in model._meta.get_fields()]
                status['models'][model_label] = {
                    'status': 'ok',
                    'field_count': len(fields),
                }
            except LookupError:
                status['models'][model_label] = {'status': 'missing'}
                status['status'] = 'tampered'

        return status

    def full_check(self) -> Dict[str, Any]:
        """Run all tamper checks and return combined report."""
        return {
            'settings': self.check_settings_integrity(),
            'middleware': self.check_middleware_integrity(),
            'urls': self.check_url_integrity(),
            'models': self.check_model_integrity(),
        }


# ---------------------------------------------------------------------------
# Anti-Debug
# ---------------------------------------------------------------------------

class AntiDebug:
    """Detects and optionally terminates on debugger attachment."""

    DEBUGGER_PATTERNS = [
        'pdb', 'ipdb', 'pydevd', 'debugpy',
        'pyrasite', 'pyringe', 'pyattach',
    ]

    def __init__(self, terminate_on_detection: bool = False):
        self.terminate_on_detection = terminate_on_detection
        self._detected: List[str] = []

    def check_debugger_modules(self) -> List[str]:
        """Check if any debugger modules are loaded."""
        loaded = []
        for name in sys.modules:
            for pattern in self.DEBUGGER_PATTERNS:
                if pattern in name.lower():
                    loaded.append(name)
        self._detected.extend(loaded)
        return loaded

    def check_trace_attach(self) -> bool:
        """Check for trace attachment via sys.settrace."""
        return sys.gettrace() is not None

    def check_debugpy_socket(self) -> bool:
        """Check for debugpy listening sockets."""
        try:
            import socket
            for conn in socket.socket._imonkey if hasattr(socket.socket, '_imonkey') else []:
                pass
        except Exception:
            pass

        # Check for common debug port
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('127.0.0.1', 5678))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        return False

    def scan(self) -> Dict[str, Any]:
        """Run all anti-debug checks."""
        modules = self.check_debugger_modules()
        trace = self.check_trace_attach()
        socket_detected = self.check_debugpy_socket()

        detected = bool(modules or trace or socket_detected)
        result = {
            'debugger_detected': detected,
            'modules': modules,
            'trace_active': trace,
            'debug_socket': socket_detected,
        }

        if detected and self.terminate_on_detection:
            logger.critical('Debugger detected — terminating process')
            self._detected.extend(modules)
            os._exit(1)

        return result

    def get_detections(self) -> List[str]:
        return list(set(self._detected))


# ---------------------------------------------------------------------------
# RASP Engine (Singleton)
# ---------------------------------------------------------------------------

class RASPEngine:
    """Central RASP engine — integrity, runtime monitoring, tamper detection."""

    _instance: Optional['RASPEngine'] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialised = False
            return cls._instance

    def __init__(self):
        if self._initialised:
            return
        self._initialised = True

        self.integrity_checker = CodeIntegrityChecker()
        self.runtime_monitor = RuntimeMonitor()
        self.tamper_detector = TamperDetector()
        self.anti_debug = AntiDebug()

        self._protection_state = {
            'integrity_verified': False,
            'runtime_monitoring': False,
            'tamper_checks_passed': False,
            'anti_debug_active': False,
        }

        logger.info('RASP engine initialised')

    def verify_integrity(self) -> bool:
        """Verify code integrity against stored baseline."""
        results = self.integrity_checker.verify_all_files()
        modified = [f for f, ok in results.items() if not ok]

        if modified:
            logger.critical('Integrity violations detected: %s', modified)
            self._protection_state['integrity_verified'] = False
        else:
            self._protection_state['integrity_verified'] = True

        return len(modified) == 0

    def monitor_runtime(self) -> List[str]:
        """Run runtime anomaly checks."""
        anomalies: List[str] = []

        suspicious = self.runtime_monitor.monitor_suspicious_calls()
        anomalies.extend(suspicious)

        env_changes = self.runtime_monitor.monitor_env_changes()
        anomalies.extend(env_changes)

        if self.runtime_monitor.detect_debugger():
            anomalies.append('Debugger detected during runtime check')

        if self.runtime_monitor.detect_process_injection():
            anomalies.append('Process injection indicators found')

        memory_warns = self.runtime_monitor.detect_memory_modification()
        anomalies.extend(memory_warns)

        self._protection_state['runtime_monitoring'] = len(anomalies) == 0
        return anomalies

    def protect_memory(self) -> Dict[str, Any]:
        """Check for memory-level attacks."""
        return {
            'memory_modifications': self.runtime_monitor.detect_memory_modification(),
            'process_injection': self.runtime_monitor.detect_process_injection(),
            'debugger_attached': self.runtime_monitor.detect_debugger(),
        }

    def detect_tampering(self) -> Dict[str, Any]:
        """Run full tamper detection suite."""
        results = self.tamper_detector.full_check()
        all_ok = all(
            v.get('status') == 'ok'
            for v in results.values()
            if isinstance(v, dict)
        )
        self._protection_state['tamper_checks_passed'] = all_ok
        return results

    def get_protection_status(self) -> Dict[str, Any]:
        """Return current protection state."""
        return {
            **self._protection_state,
            'anti_debug_active': self.anti_debug.check_debugger_modules() or self.anti_debug.check_trace_attach(),
            'integrity_baseline_files': len(self.integrity_checker._baseline),
        }

    def full_scan(self) -> Dict[str, Any]:
        """Run a complete RASP scan combining all checks."""
        integrity = self.verify_integrity()
        tamper = self.detect_tampering()
        runtime = self.monitor_runtime()
        memory = self.protect_memory()
        status = self.get_protection_status()

        return {
            'integrity_ok': integrity,
            'tamper': tamper,
            'runtime_anomalies': runtime,
            'memory': memory,
            'status': status,
        }


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_rasp_instance: Optional[RASPEngine] = None


def get_rasp() -> RASPEngine:
    global _rasp_instance
    if _rasp_instance is None:
        _rasp_instance = RASPEngine()
    return _rasp_instance
