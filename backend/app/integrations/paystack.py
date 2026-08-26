"""Paystack integration for Nigerian Naira payments."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class PaystackClient:
    BASE_URL = "https://api.paystack.co"

    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def initialize_transaction(
        self, email: str, amount_kobo: int, reference: str, metadata: dict | None = None
    ) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/transaction/initialize",
                headers=self.headers,
                json={
                    "email": email,
                    "amount": amount_kobo,
                    "reference": reference,
                    "currency": "NGN",
                    "metadata": metadata or {},
                },
            )
            response.raise_for_status()
            return response.json()["data"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def verify_transaction(self, reference: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/transaction/verify/{reference}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()["data"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def create_customer(self, email: str, first_name: str, last_name: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/customer",
                headers=self.headers,
                json={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                },
            )
            response.raise_for_status()
            return response.json()["data"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def create_charge(self, email: str, amount_kobo: int, reference: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/charge",
                headers=self.headers,
                json={
                    "email": email,
                    "amount": amount_kobo,
                    "reference": reference,
                },
            )
            response.raise_for_status()
            return response.json()["data"]
