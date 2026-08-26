"""Pillar 0: Agentic Fuel Billing Engine.

Core business logic for credit management, metering, and invoicing.
All pillars route their billing through this service.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import ClientWallet, CreditTransaction, Invoice
from app.models.agents import AgentExecution


class BillingError(Exception):
    pass


class InsufficientCreditsError(BillingError):
    pass


class WalletNotFoundError(BillingError):
    pass


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_wallet(self, client_id: uuid.UUID) -> ClientWallet:
        result = await self.db.execute(
            select(ClientWallet).where(ClientWallet.client_id == client_id)
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise WalletNotFoundError(f"No wallet for client {client_id}")
        return wallet

    async def ensure_wallet(self, client_id: uuid.UUID) -> ClientWallet:
        try:
            return await self.get_wallet(client_id)
        except WalletNotFoundError:
            wallet = ClientWallet(client_id=client_id)
            self.db.add(wallet)
            await self.db.flush()
            return wallet

    async def check_balance(self, client_id: uuid.UUID, required_credits: float) -> bool:
        wallet = await self.get_wallet(client_id)
        return wallet.balance >= required_credits

    async def deduct_credits(
        self,
        client_id: uuid.UUID,
        amount: float,
        description: str,
        reference: str | None = None,
        idempotency_key: str | None = None,
        metadata: dict | None = None,
    ) -> CreditTransaction:
        if amount <= 0:
            raise BillingError("Deduction amount must be positive")

        wallet = await self.get_wallet(client_id)

        if wallet.balance < amount:
            raise InsufficientCreditsError(
                f"Insufficient credits: {wallet.balance} available, {amount} required"
            )

        wallet.balance -= amount
        wallet.total_spent += amount

        txn = CreditTransaction(
            wallet_id=wallet.id,
            type="debit",
            amount=amount,
            balance_after=wallet.balance,
            description=description,
            reference=reference,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )
        self.db.add(txn)
        await self.db.flush()
        return txn

    async def add_credits(
        self,
        client_id: uuid.UUID,
        amount: float,
        description: str,
        reference: str | None = None,
        metadata: dict | None = None,
    ) -> CreditTransaction:
        if amount <= 0:
            raise BillingError("Credit amount must be positive")

        wallet = await self.ensure_wallet(client_id)
        wallet.balance += amount
        wallet.total_earned += amount

        txn = CreditTransaction(
            wallet_id=wallet.id,
            type="credit",
            amount=amount,
            balance_after=wallet.balance,
            description=description,
            reference=reference,
            metadata=metadata,
        )
        self.db.add(txn)
        await self.db.flush()
        return txn

    async def refund_credits(
        self,
        client_id: uuid.UUID,
        amount: float,
        description: str,
        reference: str | None = None,
    ) -> CreditTransaction:
        if amount <= 0:
            raise BillingError("Refund amount must be positive")

        wallet = await self.get_wallet(client_id)
        wallet.balance += amount

        txn = CreditTransaction(
            wallet_id=wallet.id,
            type="refund",
            amount=amount,
            balance_after=wallet.balance,
            description=description,
            reference=reference,
        )
        self.db.add(txn)
        await self.db.flush()
        return txn

    async def charge_agent_execution(
        self,
        execution_id: uuid.UUID,
        client_id: uuid.UUID,
        credit_cost: float,
    ) -> CreditTransaction:
        """Charge credits for a completed agent task execution."""
        execution = await self.db.get(AgentExecution, execution_id)
        if not execution:
            raise BillingError(f"Execution {execution_id} not found")

        txn = await self.deduct_credits(
            client_id=client_id,
            amount=credit_cost,
            description=f"Agent task: {execution.task.task_name}",
            reference=str(execution_id),
            metadata={
                "execution_id": str(execution_id),
                "task_type": execution.task.task_type,
                "agent_slug": execution.task.agent.slug,
            },
        )

        execution.credits_charged = credit_cost
        execution.status = "completed"
        execution.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return txn

    async def generate_invoice(
        self,
        client_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> Invoice:
        """Generate an invoice for usage in a time period."""
        result = await self.db.execute(
            select(func.sum(CreditTransaction.amount)).where(
                CreditTransaction.type == "debit",
                CreditTransaction.wallet_id == ClientWallet.id,
                ClientWallet.client_id == client_id,
                CreditTransaction.created_at.between(period_start, period_end),
            )
        )
        total_credits = result.scalar() or 0.0

        wallet = await self.get_wallet(client_id)
        subtotal = total_credits * wallet.credit_rate_usd
        tax_amount = subtotal * 0.075  # 7.5% VAT (Nigeria)
        total = subtotal + tax_amount

        invoice_number = f"DK-{datetime.now(timezone.utc).strftime('%Y%m')}-{str(uuid.uuid4())[:8].upper()}"

        invoice = Invoice(
            client_id=client_id,
            invoice_number=invoice_number,
            status="pending" if total > 0 else "draft",
            subtotal_usd=subtotal,
            tax_rate=0.075,
            tax_amount=tax_amount,
            total_usd=total,
            credits_used=total_credits,
            line_items={
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "credit_rate_usd": wallet.credit_rate_usd,
            },
            due_at=datetime.now(timezone.utc).replace(day=min(28, datetime.now(timezone.utc).day + 30)),
        )
        self.db.add(invoice)
        await self.db.flush()
        return invoice

    async def get_balance(self, client_id: uuid.UUID) -> dict:
        wallet = await self.get_wallet(client_id)
        return {
            "balance": wallet.balance,
            "currency": wallet.currency,
            "credit_rate_usd": wallet.credit_rate_usd,
            "total_earned": wallet.total_earned,
            "total_spent": wallet.total_spent,
            "low_balance_threshold": wallet.low_balance_threshold,
            "auto_topup_enabled": wallet.auto_topup_enabled,
        }

    async def get_transaction_history(
        self, client_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[CreditTransaction]:
        wallet = await self.get_wallet(client_id)
        result = await self.db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.wallet_id == wallet.id)
            .order_by(CreditTransaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def check_low_balance(self, client_id: uuid.UUID) -> bool:
        wallet = await self.get_wallet(client_id)
        return wallet.balance <= wallet.auto_topup_trigger
