"""Agent metering API — records task executions and charges credits."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.models.agents import Agent, AgentExecution, AgentTask
from app.models.billing import ClientWallet
from app.services.billing import BillingService, InsufficientCreditsError

router = APIRouter(prefix="/metering", tags=["metering"])


class TaskExecutionRequest(BaseModel):
    agent_slug: str
    task_type: str
    input_data: dict | None = None
    idempotency_key: str | None = None


class ExecutionResponse(BaseModel):
    execution_id: str
    status: str
    credits_charged: float
    balance_after: float


class AgentInfo(BaseModel):
    id: str
    name: str
    slug: str
    pillar: str
    credit_cost_per_task: float


class UsageStats(BaseModel):
    total_executions: int
    total_credits_charged: float
    executions_by_agent: dict
    executions_today: int


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents(db: DbSession):
    result = await db.execute(select(Agent).where(Agent.is_active == True))
    agents = result.scalars().all()
    return [
        AgentInfo(
            id=str(a.id),
            name=a.name,
            slug=a.slug,
            pillar=a.pillar,
            credit_cost_per_task=a.credit_cost_per_task,
        )
        for a in agents
    ]


@router.post("/execute", response_model=ExecutionResponse)
async def execute_task(
    client: CurrentUser,
    db: DbSession,
    req: TaskExecutionRequest,
):
    agent_result = await db.execute(
        select(Agent).where(Agent.slug == req.agent_slug, Agent.is_active == True)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    task_result = await db.execute(
        select(AgentTask).where(
            AgentTask.agent_id == agent.id,
            AgentTask.task_type == req.task_type,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task type '{req.task_type}' not found")

    wallet_result = await db.execute(
        select(ClientWallet).where(ClientWallet.client_id == client.id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if wallet.balance < task.credit_cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits: {wallet.balance} available, {task.credit_cost} required",
        )

    execution = AgentExecution(
        task_id=task.id,
        client_id=client.id,
        wallet_id=wallet.id,
        credit_cost=task.credit_cost,
        input_data=req.input_data,
        status="pending",
    )
    db.add(execution)
    await db.flush()

    billing = BillingService(db)
    try:
        txn = await billing.charge_agent_execution(
            execution_id=execution.id,
            client_id=client.id,
            credit_cost=task.credit_cost,
        )
        return ExecutionResponse(
            execution_id=str(execution.id),
            status="completed",
            credits_charged=task.credit_cost,
            balance_after=txn.balance_after,
        )
    except InsufficientCreditsError as e:
        execution.status = "failed"
        execution.error_message = str(e)
        await db.flush()
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    client: CurrentUser,
    db: DbSession,
):
    from sqlalchemy.orm import selectinload
    from datetime import datetime, timezone

    result = await db.execute(
        select(AgentExecution)
        .where(AgentExecution.client_id == client.id)
        .options(selectinload(AgentExecution.task).selectinload("agent"))
    )
    executions = result.scalars().all()

    total_credits = sum(e.credits_charged for e in executions)
    by_agent: dict[str, int] = {}
    today_count = 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    for e in executions:
        agent_slug = e.task.agent.slug if e.task and e.task.agent else "unknown"
        by_agent[agent_slug] = by_agent.get(agent_slug, 0) + 1
        if e.started_at and e.started_at >= today_start:
            today_count += 1

    return UsageStats(
        total_executions=len(executions),
        total_credits_charged=total_credits,
        executions_by_agent=by_agent,
        executions_today=today_count,
    )
