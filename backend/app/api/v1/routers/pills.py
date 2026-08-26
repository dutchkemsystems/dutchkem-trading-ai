"""Pillar-specific API routes: Afro-Pay, Sentinel, Agent Cloud, NetraID, TrustNode."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.models.pillars import (
    AfroPayTransaction,
    SentinelAlert,
    AgentCloudDeployment,
    NetraIDVerification,
    TrustNodeRequest,
)

# ─── Pillar 1: Afro-Pay ────────────────────────────────────────────────
afropay_router = APIRouter(prefix="/afropay", tags=["afro-pay"])


class RemittanceRequest(BaseModel):
    receiver_country: str
    amount: float
    currency: str = "NGN"
    receiver_name: str
    receiver_phone: str
    stablecoin_type: str | None = None


class RemittanceResponse(BaseModel):
    transaction_id: str
    settlement_fee: float
    total_debit: float
    status: str


@afropay_router.post("/send", response_model=RemittanceResponse)
async def send_remittance(client: CurrentUser, db: DbSession, req: RemittanceRequest):
    settlement_fee_pct = 0.005
    settlement_fee = req.amount * settlement_fee_pct
    total_debit = req.amount + settlement_fee

    txn = AfroPayTransaction(
        client_id=client.id,
        sender_country=client.country,
        receiver_country=req.receiver_country,
        amount=req.amount,
        currency=req.currency,
        settlement_fee_pct=settlement_fee_pct,
        settlement_fee_amount=settlement_fee,
        stablecoin_type=req.stablecoin_type,
        status="initiated",
    )
    db.add(txn)
    await db.flush()

    return RemittanceResponse(
        transaction_id=str(txn.id),
        settlement_fee=settlement_fee,
        total_debit=total_debit,
        status="initiated",
    )


@afropay_router.get("/transactions")
async def get_afropay_transactions(
    client: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    result = await db.execute(
        select(AfroPayTransaction)
        .where(AfroPayTransaction.client_id == client.id)
        .order_by(AfroPayTransaction.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ─── Pillar 2: Sentinel Africa ──────────────────────────────────────────
sentinel_router = APIRouter(prefix="/sentinel", tags=["sentinel-africa"])


class ThreatAlertResponse(BaseModel):
    id: str
    severity: str
    title: str
    status: str
    credits_charged: float


class ThreatScanRequest(BaseModel):
    target: str
    scan_type: str = "full"


@sentinel_router.post("/scan")
async def initiate_scan(client: CurrentUser, db: DbSession, req: ThreatScanRequest):
    alert = SentinelAlert(
        client_id=client.id,
        agent_type="recon",
        severity="medium",
        title=f"Scan initiated: {req.target}",
        status="open",
    )
    db.add(alert)
    await db.flush()

    return {
        "scan_id": str(alert.id),
        "target": req.target,
        "status": "initiated",
        "message": "Threat scan initiated. Results will be available shortly.",
    }


@sentinel_router.get("/alerts", response_model=list[ThreatAlertResponse])
async def get_alerts(
    client: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    result = await db.execute(
        select(SentinelAlert)
        .where(SentinelAlert.client_id == client.id)
        .order_by(SentinelAlert.created_at.desc())
        .limit(limit)
    )
    alerts = result.scalars().all()
    return [
        ThreatAlertResponse(
            id=str(a.id),
            severity=a.severity,
            title=a.title,
            status=a.status,
            credits_charged=a.credits_charged,
        )
        for a in alerts
    ]


# ─── Pillar 3: African Agent Cloud ──────────────────────────────────────
agent_cloud_router = APIRouter(prefix="/agent-cloud", tags=["agent-cloud"])


class DeployRequest(BaseModel):
    agent_type: str
    name: str
    region: str = "NG"
    language: str = "en"
    config: dict | None = None


@agent_cloud_router.post("/deploy")
async def deploy_agent(client: CurrentUser, db: DbSession, req: DeployRequest):
    credit_costs = {
        "sales": 1.50,
        "kyc": 2.00,
        "hr": 1.50,
        "ecommerce": 1.50,
        "loan_recovery": 1.50,
    }

    deployment = AgentCloudDeployment(
        client_id=client.id,
        agent_type=req.agent_type,
        name=req.name,
        region=req.region,
        language=req.language,
        status="provisioning",
        credits_per_run=credit_costs.get(req.agent_type, 1.50),
        config=req.config,
    )
    db.add(deployment)
    await db.flush()

    return {
        "deployment_id": str(deployment.id),
        "agent_type": req.agent_type,
        "status": "provisioning",
        "credits_per_run": deployment.credits_per_run,
    }


@agent_cloud_router.get("/deployments")
async def list_deployments(client: CurrentUser, db: DbSession):
    result = await db.execute(
        select(AgentCloudDeployment)
        .where(AgentCloudDeployment.client_id == client.id)
        .order_by(AgentCloudDeployment.created_at.desc())
    )
    return result.scalars().all()


# ─── Pillar 4: NetraID ──────────────────────────────────────────────────
netraid_router = APIRouter(prefix="/netra-id", tags=["netra-id"])


class VerifyRequest(BaseModel):
    verification_type: str
    subject_id: str
    compliance_regime: str = "NDPA"
    document_data: dict | None = None


class VerificationResponse(BaseModel):
    verification_id: str
    status: str
    credits_charged: float


@netraid_router.post("/verify", response_model=VerificationResponse)
async def verify_identity(client: CurrentUser, db: DbSession, req: VerifyRequest):
    verification = NetraIDVerification(
        client_id=client.id,
        verification_type=req.verification_type,
        subject_id=req.subject_id,
        compliance_regime=req.compliance_regime,
        status="pending",
        verification_data=req.document_data,
    )
    db.add(verification)
    await db.flush()

    credit_costs = {
        "biometric": 2.00,
        "liveness": 2.00,
        "document": 1.50,
        "blockchain_token": 3.00,
    }
    cost = credit_costs.get(req.verification_type, 2.00)

    return VerificationResponse(
        verification_id=str(verification.id),
        status="pending",
        credits_charged=cost,
    )


@netraid_router.get("/verifications")
async def get_verifications(
    client: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    result = await db.execute(
        select(NetraIDVerification)
        .where(NetraIDVerification.client_id == client.id)
        .order_by(NetraIDVerification.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ─── Pillar 5: TrustNode ────────────────────────────────────────────────
trustnode_router = APIRouter(prefix="/trust-node", tags=["trust-node"])


class AIRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: int = 1000
    temperature: float = 0.7


class AIResponse(BaseModel):
    request_id: str
    routed_to_model: str
    provider: str
    response_text: str
    tokens_used: int
    cost_usd: float


@trustnode_router.post("/generate", response_model=AIResponse)
async def generate(client: CurrentUser, db: DbSession, req: AIRequest):
    model_routing = {
        "gpt-4": {"provider": "openai", "cost_per_1k": 0.03},
        "gpt-3.5-turbo": {"provider": "openai", "cost_per_1k": 0.002},
        "claude-3-sonnet": {"provider": "anthropic", "cost_per_1k": 0.015},
        "llama-3-70b": {"provider": "together", "cost_per_1k": 0.002},
        "mistral-large": {"provider": "mistral", "cost_per_1k": 0.008},
    }

    routing = model_routing.get(req.model, {"provider": "openai", "cost_per_1k": 0.015})

    import random
    simulated_tokens = random.randint(50, req.max_tokens)
    cost = (simulated_tokens / 1000) * routing["cost_per_1k"]

    request_log = TrustNodeRequest(
        client_id=client.id,
        requested_model=req.model,
        routed_to_model=req.model,
        provider=routing["provider"],
        tokens_input=len(req.prompt.split()),
        tokens_output=simulated_tokens,
        cost_usd=cost,
        status="success",
        request_data={"prompt": req.prompt[:200]},
    )
    db.add(request_log)
    await db.flush()

    return AIResponse(
        request_id=str(request_log.id),
        routed_to_model=req.model,
        provider=routing["provider"],
        response_text="TrustNode routing simulated. Connect to real models for production.",
        tokens_used=simulated_tokens,
        cost_usd=cost,
    )


@trustnode_router.get("/models")
async def list_models():
    return {
        "models": [
            {"id": "gpt-4", "provider": "openai", "cost_per_1k_tokens": 0.03},
            {"id": "gpt-3.5-turbo", "provider": "openai", "cost_per_1k_tokens": 0.002},
            {"id": "claude-3-sonnet", "provider": "anthropic", "cost_per_1k_tokens": 0.015},
            {"id": "llama-3-70b", "provider": "together", "cost_per_1k_tokens": 0.002},
            {"id": "mistral-large", "provider": "mistral", "cost_per_1k_tokens": 0.008},
        ]
    }
