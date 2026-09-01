import hashlib
import hmac
import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger("payments")


class KorapayGateway:
    BASE_URL = os.environ.get("KORA_BASE_URL", "https://api.korapay.com/merchant/api/v1")

    def __init__(self):
        self.secret_key = os.environ.get("KORA_SECRET_KEY", "")
        self.public_key = os.environ.get("KORA_PUBLIC_KEY", "")
        self.encryption_key = os.environ.get("KORA_ENCRYPTION_KEY", "")
        self.webhook_secret = os.environ.get("KORA_WEBHOOK_SECRET", "")
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 1.0

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def _request_with_retry(self, method, url, **kwargs):
        last_exc = None
        for attempt in range(self.max_retries):
            try:
                resp = requests.request(method, url, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning(
                    "Korapay %s attempt %d/%d failed: %s",
                    method, attempt + 1, self.max_retries, exc,
                )
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(self.retry_delay * (attempt + 1))
        raise last_exc

    def initialize_transaction(
        self,
        amount: float,
        currency: str,
        reference: str,
        customer_email: str,
        customer_name: str = "",
        description: str = "",
        metadata: dict[str, Any] | None = None,
        channels: list[str] | None = None,
        redirect_url: str = "",
    ) -> dict[str, Any]:
        supported_currencies = ["NGN", "GHS", "KES", "ZAR"]
        if currency not in supported_currencies:
            return {"status": False, "message": f"Unsupported currency: {currency}. Use one of {supported_currencies}"}

        payload = {
            "amount": str(amount),
            "currency": currency,
            "reference": reference,
            "customer": {
                "email": customer_email,
                "name": customer_name,
            },
            "description": description or f"Deposit {amount} {currency}",
            "metadata": metadata or {},
            "payment_methods": channels or ["card", "bank_transfer", "ussd", "mobile_money"],
        }
        if redirect_url:
            payload["redirect_url"] = redirect_url

        try:
            data = self._request_with_retry(
                "POST",
                f"{self.BASE_URL}/payments/initialize",
                json=payload,
                headers=self._headers(),
            )
            logger.info("Korapay init success: ref=%s status=%s", reference, data.get("status"))
            return data
        except requests.RequestException as exc:
            logger.error("Korapay init failed: ref=%s err=%s", reference, exc)
            return {"status": False, "message": str(exc)}

    def verify_transaction(self, reference: str) -> dict[str, Any]:
        try:
            data = self._request_with_retry(
                "GET",
                f"{self.BASE_URL}/payments/{reference}",
                headers=self._headers(),
            )
            logger.info("Korapay verify: ref=%s status=%s", reference, data.get("status"))
            return data
        except requests.RequestException as exc:
            logger.error("Korapay verify failed: ref=%s err=%s", reference, exc)
            return {"status": False, "message": str(exc)}

    def verify_webhook_signature(self, payload_body: bytes, signature: str) -> bool:
        secret = self.webhook_secret or self.secret_key
        if not secret:
            logger.warning("KORA_WEBHOOK_SECRET not set, rejecting webhook (no secret configured)")
            return False
        expected = hmac.new(
            secret.encode(), payload_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_webhook_event(self, body: dict[str, Any]) -> dict[str, Any]:
        event_type = body.get("event", "")
        data = body.get("data", {})
        return {
            "event_type": event_type,
            "reference": data.get("reference", ""),
            "status": data.get("status", ""),
            "amount": float(data.get("amount", 0)),
            "currency": data.get("currency", ""),
            "metadata": data.get("metadata", {}),
            "channel": data.get("channel", ""),
            "paid_at": data.get("paid_at"),
        }
