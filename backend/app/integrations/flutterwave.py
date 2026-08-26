"""Flutterwave integration for Nigerian/Ghanaian mobile money payments."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class FlutterwaveClient:
    BASE_URL = "https://api.flutterwave.com/v3"

    def __init__(self):
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def initialize_payment(
        self,
        amount: float,
        currency: str,
        email: str,
        tx_ref: str,
        redirect_url: str | None = None,
    ) -> dict:
        payload = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": currency,
            "customer": {"email": email},
            "payment_options": "card,mobilemoney,ussd,banktransfer",
        }
        if redirect_url:
            payload["redirect_url"] = redirect_url

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/payments",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()["data"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def verify_transaction(self, transaction_id: int) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/transactions/{transaction_id}/verify",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()["data"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def create_subaccount(
        self, account_bank: str, account_number: str, business_name: str, country: str = "NG"
    ) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/subaccounts",
                headers=self.headers,
                json={
                    "account_bank": account_bank,
                    "account_number": account_number,
                    "business_name": business_name,
                    "country": country,
                    "split_type": "percentage",
                    "split_value": "0",
                },
            )
            response.raise_for_status()
            return response.json()["data"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def transfer(self, account_bank: str, account_number: str, amount: float, currency: str, reference: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/transfers",
                headers=self.headers,
                json={
                    "account_bank": account_bank,
                    "account_number": account_number,
                    "amount": amount,
                    "currency": currency,
                    "reference": reference,
                    "debit_subaccount": True,
                },
            )
            response.raise_for_status()
            return response.json()["data"]
