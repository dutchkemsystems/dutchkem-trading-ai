import logging
import time
from functools import wraps

from django.conf import settings
from django.http import HttpRequest

logger = logging.getLogger("monitoring")


class MetricsCollector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._counters = {}
            cls._instance._histograms = {}
            cls._instance._gauges = {}
        return cls._instance

    def inc_counter(self, name: str, labels: dict | None = None, value: float = 1):
        key = self._make_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: dict | None = None):
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def observe_histogram(self, name: str, value: float, labels: dict | None = None):
        key = self._make_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    def _make_key(self, name: str, labels: dict | None) -> str:
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name

    def export_prometheus(self) -> str:
        lines = []
        for key, value in self._counters.items():
            lines.append(f"# TYPE {key.split('{')[0]} counter")
            lines.append(f"{key} {value}")
        for key, value in self._gauges.items():
            lines.append(f"# TYPE {key.split('{')[0]} gauge")
            lines.append(f"{key} {value}")
        for key, values in self._histograms.items():
            base = key.split("{")[0]
            lines.append(f"# TYPE {base} histogram")
            lines.append(f"{key}_sum {sum(values)}")
            lines.append(f"{key}_count {len(values)}")
            lines.append(f"{key}_bucket{{le=\"+Inf\"}} {len(values)}")
        return "\n".join(lines)


metrics = MetricsCollector()


class PrometheusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        start = time.time()
        response = self.get_response(request)
        duration = time.time() - start

        path = request.path
        method = request.method
        status = response.status_code

        metrics.inc_counter("http_requests_total", {"method": method, "path": path, "status": str(status)})
        metrics.observe_histogram("http_request_duration_seconds", duration, {"method": method, "path": path})
        metrics.set_gauge("http_requests_in_progress", 0, {"path": path})

        if status >= 500:
            logger.warning("HTTP %s %s returned %d in %.3fs", method, path, status, duration)
        elif status >= 400:
            logger.info("HTTP %s %s returned %d in %.3fs", method, path, status, duration)

        return response


def track_trading_metric(metric_name: str, labels: dict | None = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                metrics.inc_counter(f"trading_{metric_name}_total", labels)
                return result
            except Exception as exc:
                metrics.inc_counter(f"trading_{metric_name}_errors_total", labels)
                raise
            finally:
                duration = time.time() - start
                metrics.observe_histogram(f"trading_{metric_name}_duration_seconds", duration, labels)
        return wrapper
    return decorator
