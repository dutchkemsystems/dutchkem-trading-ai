"""Pillar 0: Billing & Metering API routes."""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.services.billing import BillingService, InsufficientCreditsError

router = APIRouter(prefix="/billing", tags=["billing"])


class CreditBalanceResponse(BaseModel):
    balance: float
    currency: str
    credit_rate_usd: float
    total_earned: float
    total_spent: float
    low_balance_threshold: float
    auto_topup_enabled: bool


class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: float
    balance_after: float
    description: str
    reference: str | None
    created_at: str


class DeductRequest(BaseModel):
    amount: float
    description: str
    reference: str | None = None
    idempotency_key: str | None = None


class TopUpRequest(BaseModel):
    amount_usd: float
    provider: str = "stripe"


class AutoTopUpRequest(BaseModel):
    enabled: bool
    amount: float = 100.0
    trigger_at: float = 20.0


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    status: str
    subtotal_usd: float
    tax_rate: float
    tax_amount: float
    total_usd: float
    credits_used: float
    issued_at: str
    due_at: str | None


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_balance(
    client: CurrentUser,
    db: DbSession,
):
    billing = BillingService(db)
    data = await billing.get_balance(client.id)
    return CreditBalanceResponse(**data)


@router.post("/deduct")
async def deduct_credits(
    client: CurrentUser,
    db: DbSession,
    req: DeductRequest,
):
    billing = BillingService(db)
    try:
        txn = await billing.deduct_credits(
            client_id=client.id,
            amount=req.amount,
            description=req.description,
            reference=req.reference,
            idempotency_key=req.idempotency_key,
        )
        return {
            "message": "Credits deducted",
            "transaction_id": str(txn.id),
            "balance_after": txn.balance_after,
        }
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))


@router.post("/topup")
async def top_up_credits(
    client: CurrentUser,
    db: DbSession,
    req: TopUpRequest,
):
    billing = BillingService(db)
    credits = billing.calculate_credits_for_usd(req.amount_usd)
    return {
        "message": "Top-up initiated",
        "provider": req.provider,
        "amount_usd": req.amount_usd,
        "credits_to_receive": credits,
        "redirect_url": f"/api/v1/billing/checkout/{req.provider}",
    }


@router.put("/auto-topup")
async def configure_auto_topup(
    client: CurrentUser,
    db: DbSession,
    req: AutoTopUpRequest,
):
    from sqlalchemy import select
    from app.models.billing import ClientWallet

    result = await db.execute(
        select(ClientWallet).where(ClientWallet.client_id == client.id)
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet.auto_topup_enabled = req.enabled
    wallet.auto_topup_amount = req.amount
    wallet.auto_topup_trigger = req.trigger_at
    await db.flush()

    return {"message": "Auto-topup configured", "enabled": req.enabled}


@router.get("/transactions", response_model=list[TransactionResponse])
async def get_transactions(
    client: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    billing = BillingService(db)
    txns = await billing.get_transaction_history(client.id, limit, offset)
    return [
        TransactionResponse(
            id=str(t.id),
            type=t.type,
            amount=t.amount,
            balance_after=t.balance_after,
            description=t.description,
            reference=t.reference,
            created_at=t.created_at.isoformat(),
        )
        for t in txns
    ]


@router.post("/invoices/generate")
async def generate_invoice(
    client: CurrentUser,
    db: DbSession,
):
    billing = BillingService(db)
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    invoice = await billing.generate_invoice(client.id, period_start, now)
    return {
        "invoice_number": invoice.invoice_number,
        "total_usd": invoice.total_usd,
        "credits_used": invoice.credits_used,
    }
