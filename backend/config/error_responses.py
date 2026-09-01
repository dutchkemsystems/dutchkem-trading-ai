"""
Standardized API Error Response Utilities

All API endpoints should use these helpers to ensure consistent
error response formatting across the entire application.

Standard Format:
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable description",
        "details": { ... },          # optional field-level info
        "request_id": "abc-123",     # optional trace ID
    },
    "status": "error"
}
"""

import uuid
from typing import Any, Dict, List, Optional

from rest_framework.response import Response
from rest_framework import status


def _error_response(
    code: str,
    message: str,
    http_status: int,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Response:
    """Build a standardized error Response."""
    body: Dict[str, Any] = {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        body["error"]["details"] = details
    if request_id:
        body["error"]["request_id"] = request_id
    else:
        body["error"]["request_id"] = str(uuid.uuid4())[:8]
    return Response(body, status=http_status)


# ─── Convenience helpers ──────────────────────────────────────────────────

def bad_request(message: str, details: Optional[Dict] = None) -> Response:
    """400 Bad Request"""
    return _error_response("BAD_REQUEST", message, status.HTTP_400_BAD_REQUEST, details)


def unauthorized(message: str = "Authentication required") -> Response:
    """401 Unauthorized"""
    return _error_response("UNAUTHORIZED", message, status.HTTP_401_UNAUTHORIZED)


def forbidden(message: str = "Permission denied") -> Response:
    """403 Forbidden"""
    return _error_response("FORBIDDEN", message, status.HTTP_403_FORBIDDEN)


def not_found(message: str = "Resource not found") -> Response:
    """404 Not Found"""
    return _error_response("NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


def conflict(message: str, details: Optional[Dict] = None) -> Response:
    """409 Conflict"""
    return _error_response("CONFLICT", message, status.HTTP_409_CONFLICT, details)


def validation_error(message: str, field_errors: Optional[Dict[str, List[str]]] = None) -> Response:
    """422 Validation Error"""
    return _error_response("VALIDATION_ERROR", message, status.HTTP_422_UNPROCESSABLE_ENTITY, field_errors)


def rate_limited(message: str = "Rate limit exceeded. Please try again later.") -> Response:
    """429 Too Many Requests"""
    return _error_response("RATE_LIMITED", message, status.HTTP_429_TOO_MANY_REQUESTS)


def server_error(message: str = "An unexpected error occurred") -> Response:
    """500 Internal Server Error"""
    return _error_response("SERVER_ERROR", message, status.HTTP_500_INTERNAL_SERVER_ERROR)


def service_unavailable(message: str = "Service temporarily unavailable") -> Response:
    """503 Service Unavailable"""
    return _error_response("SERVICE_UNAVAILABLE", message, status.HTTP_503_SERVICE_UNAVAILABLE)


# ─── Trading-specific errors ──────────────────────────────────────────────

def insufficient_margin(required: float, available: float) -> Response:
    return bad_request(
        f"Insufficient margin. Required: {required:.2f}, Available: {available:.2f}",
        {"required": required, "available": available},
    )


def max_positions_reached(current: int, maximum: int) -> Response:
    return conflict(
        f"Maximum open positions ({maximum}) reached. Current: {current}",
        {"current": current, "maximum": maximum},
    )


def symbol_not_found(symbol: str) -> Response:
    return not_found(f"Trading symbol '{symbol}' not found")


def trade_not_found(trade_id: str) -> Response:
    return not_found(f"Trade '{trade_id}' not found")


def broker_error(details: str) -> Response:
    return _error_response("BROKER_ERROR", f"Broker returned an error: {details}", status.HTTP_502_BAD_GATEWAY)


def risk_limit_exceeded(limit_type: str, value: float, threshold: float) -> Response:
    return conflict(
        f"Risk limit exceeded: {limit_type} = {value:.4f} (threshold: {threshold:.4f})",
        {"limit_type": limit_type, "value": value, "threshold": threshold},
    )
