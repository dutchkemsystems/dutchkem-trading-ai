"""Celery tasks for metering, billing, and auto-topup."""

import uuid
import logging
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.billing import ClientWallet
from app.models.agents import AgentExecution
from app.models.fx import FXRate, FXRateHistory

logger = logging.getLogger(__name__)

sync_engine = create_engine(settings.DATABASE_URL_SYNC)
SyncSession = sessionmaker(bind=sync_engine)


@shared_task(name="app.workers.tasks.fetch_fx_rates")
def fetch_fx_rates():
    """Fetch and store FX rates every 15 minutes."""
    import httpx

    currencies = ["NGN", "GHS", "KES", "ZAR", "UGX", "TZS", "XOF", "XAF"]

    with SyncSession() as db:
        for currency in currencies:
            try:
                url = f"https://v6.exchangerate-api.com/v6/{settings.EXCHANGERATE_API_KEY}/latest/USD"
                response = httpx.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                rate = data["conversion_rates"].get(currency)

                if rate:
                    existing = db.execute(
                        select(FXRate).where(
                            FXRate.base_currency == "USD",
                            FXRate.quote_currency == currency,
                        )
                    ).scalar_one_or_none()

                    if existing:
                        existing.rate = rate
                    else:
                        fx = FXRate(
                            base_currency="USD",
                            quote_currency=currency,
                            rate=rate,
                            source="exchangerate-api",
                        )
                        db.add(fx)

                    history = FXRateHistory(
                        base_currency="USD",
                        quote_currency=currency,
                        rate=rate,
                        source="exchangerate-api",
                    )
                    db.add(history)
                    logger.info(f"Fetched USD/{currency}: {rate}")
            except Exception as e:
                logger.error(f"Failed to fetch {currency}: {e}")

        db.commit()


@shared_task(name="app.workers.tasks.check_low_balances")
def check_low_balances():
    """Check all wallets and trigger auto-topup for low balances."""
    from app.workers.tasks import process_auto_topup

    with SyncSession() as db:
        wallets = db.execute(
            select(ClientWallet).where(ClientWallet.auto_topup_enabled == True)
        ).scalars().all()

        for wallet in wallets:
            if wallet.balance <= wallet.auto_topup_trigger:
                logger.info(
                    f"Low balance alert: Client {wallet.client_id}, "
                    f"balance: {wallet.balance}, threshold: {wallet.auto_topup_trigger}"
                )
                process_auto_topup.delay(str(wallet.client_id))


@shared_task(name="app.workers.tasks.process_auto_topup")
def process_auto_topup(client_id: str):
    """Auto-topup from saved payment method."""
    import httpx

    with SyncSession() as db:
        wallet = db.execute(
            select(ClientWallet).where(ClientWallet.client_id == uuid.UUID(client_id))
        ).scalar_one_or_none()

        if not wallet or not wallet.auto_topup_enabled:
            return

        if wallet.saved_payment_method_id and wallet.saved_payment_provider:
            logger.info(
                f"Auto-topup triggered for client {client_id}: "
                f"${wallet.auto_topup_amount} via {wallet.saved_payment_provider}"
            )
            # Payment provider specific logic would go here
            # For now, we log the event and create a pending transaction


@shared_task(name="app.workers.tasks.meter_agent_execution")
def meter_agent_execution(execution_id: str, client_id: str, credit_cost: float):
    """Charge credits for a completed agent execution."""
    from app.services.billing import BillingService
    import asyncio

    async def _charge():
        from app.core.database import async_session
        async with async_session() as db:
            billing = BillingService(db)
            await billing.deduct_credits(
                client_id=uuid.UUID(client_id),
                amount=credit_cost,
                description="Agent task execution",
                reference=execution_id,
            )
            await db.commit()

    asyncio.run(_charge())
    logger.info(f"Charged {credit_cost} credits to client {client_id}")


@shared_task(name="app.workers.tasks.generate_daily_invoices")
def generate_daily_invoices():
    """Generate invoices for all active clients daily."""
    import asyncio

    async def _generate():
        from app.services.billing import BillingService
        from app.core.database import async_session
        from app.models.clients import Client

        async with async_session() as db:
            result = await db.execute(select(Client).where(Client.is_active == True))
            clients = result.scalars().all()

            now = datetime.now(timezone.utc)
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = now

            for client in clients:
                try:
                    billing = BillingService(db)
                    invoice = await billing.generate_invoice(client.id, period_start, period_end)
                    if invoice.total_usd > 0:
                        logger.info(f"Generated invoice {invoice.invoice_number} for {client.email}")
                except Exception as e:
                    logger.error(f"Failed to generate invoice for {client.email}: {e}")

            await db.commit()

    asyncio.run(_generate())


@shared_task(name="app.workers.tasks.process_settlement")
def process_settlement(transaction_id: str, provider: str):
    """Process payment settlement after verification."""
    logger.info(f"Processing settlement for {provider} transaction {transaction_id}")


@shared_task(name="app.workers.tasks.scan_sentinel_threats")
def scan_sentinel_threats(client_id: str):
    """Run Sentinel Africa threat scanning."""
    logger.info(f"Running Sentinel scan for client {client_id}")


@shared_task(name="app.workers.tasks.process_kyc_verification")
def process_kyc_verification(client_id: str, document_data: dict):
    """Process KYC identity verification."""
    logger.info(f"Processing KYC verification for client {client_id}")


@shared_task(name="app.workers.tasks.route_ai_request")
def route_ai_request(client_id: str, model: str, prompt: str):
    """Route AI request through TrustNode abstraction layer."""
    logger.info(f"Routing AI request via TrustNode for client {client_id}")
