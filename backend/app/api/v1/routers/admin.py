"""Admin dashboard API for Dutchkem Ventures monitoring."""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, DbSession
from app.models.clients import Client
from app.models.billing import ClientWallet, CreditTransaction
from app.models.agents import AgentExecution
from app.models.pillars import (
    AfroPayTransaction,
    SentinelAlert,
    AgentCloudDeployment,
    NetraIDVerification,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class GrossMarginResponse(BaseModel):
    total_revenue_usd: float
    total_cost_usd: float
    gross_margin_pct: float
    total_credits_consumed: float
    active_clients: int
    total_wallet_balance: float


class PillarBreakdown(BaseModel):
    pillar: str
    transactions: int
    revenue_usd: float
    credits_charged: float


class ClientMetrics(BaseModel):
    client_id: str
    client_name: str
    email: str
    credits_spent: float
    revenue_usd: float
    balance: float


@router.get("/dashboard", response_model=GrossMarginResponse)
async def get_dashboard(
    admin: Client = Depends(get_current_admin),
    db: DbSession = Depends(lambda: None),
):
    from app.core.database import get_db

    async for session in get_db():
        revenue_result = await session.execute(
            select(func.sum(CreditTransaction.amount)).where(
                CreditTransaction.type == "debit"
            )
        )
        total_credits_consumed = revenue_result.scalar() or 0.0
        total_revenue = total_credits_consumed * 0.10
        total_cost = total_revenue * 0.35  # 35% COGS estimate

        clients_result = await session.execute(
            select(func.count(Client.id)).where(Client.is_active == True)
        )
        active_clients = clients_result.scalar() or 0

        balance_result = await session.execute(
            select(func.sum(ClientWallet.balance))
        )
        total_balance = balance_result.scalar() or 0.0

        return GrossMarginResponse(
            total_revenue_usd=total_revenue,
            total_cost_usd=total_cost,
            gross_margin_pct=round((total_revenue - total_cost) / total_revenue * 100, 2) if total_revenue > 0 else 0,
            total_credits_consumed=total_credits_consumed,
            active_clients=active_clients,
            total_wallet_balance=total_balance,
        )


@router.get("/pillar-breakdown", response_model=list[PillarBreakdown])
async def get_pillar_breakdown(
    admin: Client = Depends(get_current_admin),
):
    from app.core.database import get_db

    async for session in get_db():
        pillars_data = []

        afropay = await session.execute(
            select(func.count(AfroPayTransaction.id), func.sum(AfroPayTransaction.amount))
        )
        row = afropay.one()
        pillars_data.append(PillarBreakdown(
            pillar="Afro-Pay",
            transactions=row[0] or 0,
            revenue_usd=(row[1] or 0) * 0.005,
            credits_charged=0,
        ))

        sentinel = await session.execute(
            select(func.count(SentinelAlert.id), func.sum(SentinelAlert.credits_charged))
        )
        row = sentinel.one()
        pillars_data.append(PillarBreakdown(
            pillar="Sentinel Africa",
            transactions=row[0] or 0,
            revenue_usd=(row[1] or 0) * 0.10,
            credits_charged=row[1] or 0,
        ))

        agent_cloud = await session.execute(
            select(func.count(AgentCloudDeployment.id), func.sum(AgentCloudDeployment.total_credits))
        )
        row = agent_cloud.one()
        pillars_data.append(PillarBreakdown(
            pillar="African Agent Cloud",
            transactions=row[0] or 0,
            revenue_usd=(row[1] or 0) * 0.10,
            credits_charged=row[1] or 0,
        ))

        netra = await session.execute(
            select(func.count(NetraIDVerification.id), func.sum(NetraIDVerification.credits_charged))
        )
        row = netra.one()
        pillars_data.append(PillarBreakdown(
            pillar="NetraID",
            transactions=row[0] or 0,
            revenue_usd=(row[1] or 0) * 0.10,
            credits_charged=row[1] or 0,
        ))

        return pillars_data


@router.get("/clients", response_model=list[ClientMetrics])
async def get_client_metrics(
    admin: Client = Depends(get_current_admin),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    from app.core.database import get_db

    async for session in get_db():
        result = await session.execute(
            select(Client).where(Client.is_active == True).limit(limit)
        )
        clients = result.scalars().all()

        metrics = []
        for client in clients:
            wallet = await session.execute(
                select(ClientWallet).where(ClientWallet.client_id == client.id)
            )
            wallet = wallet.scalar_one_or_none()

            spend = await session.execute(
                select(func.sum(CreditTransaction.amount)).where(
                    CreditTransaction.wallet_id == wallet.id if wallet else False,
                    CreditTransaction.type == "debit",
                )
            )
            credits_spent = spend.scalar() or 0.0

            metrics.append(ClientMetrics(
                client_id=str(client.id),
                client_name=client.name,
                email=client.email,
                credits_spent=credits_spent,
                revenue_usd=credits_spent * 0.10,
                balance=wallet.balance if wallet else 0,
            ))

        return metrics
