import gzip
import io
import logging
import time
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("middleware")


class RequestTimingMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.time()
        response = self.get_response(request)
        duration = time.time() - start

        response["X-Request-Duration"] = f"{duration:.4f}s"
        response["X-Request-Path"] = request.path

        if duration > 1.0:
            logger.warning("Slow request: %s %s took %.3fs", request.method, request.path, duration)

        return response


class ResponseCompressionMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        accept_encoding = request.META.get("HTTP_ACCEPT_ENCODING", "")
        content_type = response.get("Content-Type", "")

        if "gzip" in accept_encoding and self._should_compress(content_type, response):
            compressed = gzip.compress(response.content)
            if len(compressed) < len(response.content):
                response.content = compressed
                response["Content-Encoding"] = "gzip"
                response["Content-Length"] = len(compressed)

        return response

    def _should_compress(self, content_type: str, response: HttpResponse) -> bool:
        compressible = ["text/", "application/json", "application/javascript", "application/xml"]
        if not any(ct in content_type for ct in compressible):
            return False
        if response.get("Content-Encoding"):
            return False
        if len(response.content) < 500:
            return False
        return True


class RateLimitMiddleware:
    _requests = {}

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not settings.DEBUG:
            client_ip = self._get_client_ip(request)
            now = time.time()
            window = 60

            if client_ip not in self._requests:
                self._requests[client_ip] = []

            self._requests[client_ip] = [
                t for t in self._requests[client_ip] if now - t < window
            ]

            max_requests = 1000 if request.user.is_authenticated else 100
            if len(self._requests[client_ip]) >= max_requests:
                return HttpResponse(
                    '{"error": "Rate limit exceeded"}',
                    status=429,
                    content_type="application/json",
                )

            self._requests[client_ip].append(now)

        return self.get_response(request)

    def _get_client_ip(self, request: HttpRequest) -> str:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
