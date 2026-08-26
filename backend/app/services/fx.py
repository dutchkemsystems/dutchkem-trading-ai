"""FX rate service — fetches real-time exchange rates for credit pegging."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.fx import FXRate, FXRateHistory


class FXService:
    """Manages the 1 Credit = $0.10 USD peg via live FX rates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_rate(self, from_currency: str, to_currency: str) -> float:
        result = await self.db.execute(
            select(FXRate).where(
                FXRate.base_currency == from_currency,
                FXRate.quote_currency == to_currency,
            )
        )
        rate = result.scalar_one_or_none()
        if rate:
            return rate.rate
        return await self.fetch_and_store_rate(from_currency, to_currency)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_rate(self, from_currency: str, to_currency: str) -> float:
        url = f"https://v6.exchangerate-api.com/v6/{settings.EXCHANGERATE_API_KEY}/latest/{from_currency}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data["conversion_rates"][to_currency]

    async def fetch_and_store_rate(self, from_currency: str, to_currency: str) -> float:
        rate = await self.fetch_rate(from_currency, to_currency)

        existing = await self.db.execute(
            select(FXRate).where(
                FXRate.base_currency == from_currency,
                FXRate.quote_currency == to_currency,
            )
        )
        fx_rate = existing.scalar_one_or_none()

        if fx_rate:
            fx_rate.rate = rate
        else:
            fx_rate = FXRate(
                base_currency=from_currency,
                quote_currency=to_currency,
                rate=rate,
                source="exchangerate-api",
            )
            self.db.add(fx_rate)

        history = FXRateHistory(
            base_currency=from_currency,
            quote_currency=to_currency,
            rate=rate,
            source="exchangerate-api",
        )
        self.db.add(history)
        await self.db.flush()
        return rate

    def calculate_credits_for_usd(self, usd_amount: float, credit_rate: float = 0.10) -> float:
        return round(usd_amount / credit_rate, 2)

    def calculate_usd_for_credits(self, credits: float, credit_rate: float = 0.10) -> float:
        return round(credits * credit_rate, 2)

    async def convert_local_to_credits(
        self, local_amount: float, from_currency: str, credit_rate: float = 0.10
    ) -> float:
        usd_rate = await self.get_rate(from_currency, "USD")
        usd_amount = local_amount * usd_rate
        return self.calculate_credits_for_usd(usd_amount, credit_rate)
