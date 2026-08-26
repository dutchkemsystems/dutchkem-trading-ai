"""Agent metering service — records executions and routes to billing."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import Agent, AgentExecution, AgentTask
from app.models.billing import ClientWallet
from app.services.billing import BillingService


class MeteringService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_execution(
        self,
        client_id: uuid.UUID,
        agent_slug: str,
        task_type: str,
        input_data: dict | None = None,
    ) -> AgentExecution:
        agent = await self.db.execute(
            select(Agent).where(Agent.slug == agent_slug, Agent.is_active == True)
        )
        agent = agent.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent '{agent_slug}' not found")

        task = await self.db.execute(
            select(AgentTask).where(
                AgentTask.agent_id == agent.id,
                AgentTask.task_type == task_type,
            )
        )
        task = task.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task '{task_type}' not found for agent '{agent_slug}'")

        wallet = await self.db.execute(
            select(ClientWallet).where(ClientWallet.client_id == client_id)
        )
        wallet = wallet.scalar_one_or_none()
        if not wallet:
            raise ValueError("Client wallet not found")

        execution = AgentExecution(
            task_id=task.id,
            client_id=client_id,
            wallet_id=wallet.id,
            credit_cost=task.credit_cost,
            input_data=input_data,
            status="pending",
        )
        self.db.add(execution)
        await self.db.flush()
        return execution

    async def complete_execution(
        self,
        execution_id: uuid.UUID,
        client_id: uuid.UUID,
        output_data: dict | None = None,
        result_summary: str | None = None,
    ) -> AgentExecution:
        execution = await self.db.get(AgentExecution, execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        execution.status = "completed"
        execution.output_data = output_data
        execution.result_summary = result_summary
        execution.completed_at = datetime.now(timezone.utc)

        billing = BillingService(self.db)
        await billing.charge_agent_execution(
            execution_id=execution.id,
            client_id=client_id,
            credit_cost=execution.credit_cost,
        )

        await self.db.flush()
        return execution

    async def fail_execution(
        self,
        execution_id: uuid.UUID,
        error_message: str,
    ) -> AgentExecution:
        execution = await self.db.get(AgentExecution, execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        execution.status = "failed"
        execution.error_message = error_message
        execution.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return execution

    async def get_client_executions(
        self,
        client_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentExecution]:
        result = await self.db.execute(
            select(AgentExecution)
            .where(AgentExecution.client_id == client_id)
            .order_by(AgentExecution.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
