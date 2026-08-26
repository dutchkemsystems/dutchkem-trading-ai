"""Pillar-specific models for Afro-Pay, Sentinel, Agent Cloud, NetraID, TrustNode."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AfroPayTransaction(Base):
    """Pillar 1: Remittance and fintech transactions."""

    __tablename__ = "afropay_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    sender_country: Mapped[str] = mapped_column(String(3), nullable=False)
    receiver_country: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    settlement_fee_pct: Mapped[float] = mapped_column(Float, default=0.005)
    settlement_fee_amount: Mapped[float] = mapped_column(Float, default=0.0)
    stablecoin_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("initiated", "pending", "completed", "failed", "reversed", name="afropay_status"),
        default="initiated",
    )
    credits_charged: Mapped[float] = mapped_column(Float, default=0.0)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_afropay_client_created", "client_id", "created_at"),
    )


class SentinelAgent(Base):
    """Pillar 2: SOC agent registry."""

    __tablename__ = "sentinel_agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type: Mapped[str] = mapped_column(
        Enum("recon", "simulation", "response", "log", "deepfake", "phishing", name="sentinel_agent_type"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    cost_per_neutralization: Mapped[float] = mapped_column(Float, default=500.0)


class SentinelAlert(Base):
    """Pillar 2: Threat alerts and neutralizations."""

    __tablename__ = "sentinel_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical", name="alert_severity"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("open", "investigating", "neutralized", "false_positive", name="alert_status"),
        default="open",
    )
    credits_charged: Mapped[float] = mapped_column(Float, default=0.0)
    threat_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    neutralized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentCloudDeployment(Base):
    """Pillar 3: Deployed AI agent instances."""

    __tablename__ = "agent_cloud_deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    agent_type: Mapped[str] = mapped_column(
        Enum("sales", "kyc", "hr", "ecommerce", "loan_recovery", name="cloud_agent_type"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(10), nullable=False, default="NG")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    status: Mapped[str] = mapped_column(
        Enum("provisioning", "active", "paused", "terminated", name="deployment_status"),
        default="provisioning",
    )
    credits_per_run: Mapped[float] = mapped_column(Float, nullable=False)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    total_credits: Mapped[float] = mapped_column(Float, default=0.0)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class NetraIDVerification(Base):
    """Pillar 4: Digital identity verification records."""

    __tablename__ = "netra_id_verifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    verification_type: Mapped[str] = mapped_column(
        Enum("biometric", "liveness", "document", "blockchain_token", name="verification_type"),
        nullable=False,
    )
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "verified", "rejected", "expired", name="verification_status"),
        default="pending",
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_regime: Mapped[str] = mapped_column(String(50), nullable=False, default="NDPA")
    blockchain_token_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credits_charged: Mapped[float] = mapped_column(Float, default=0.0)
    verification_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrustNodeRequest(Base):
    """Pillar 5: AI model abstraction layer requests."""

    __tablename__ = "trustnode_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    requested_model: Mapped[str] = mapped_column(String(100), nullable=False)
    routed_to_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("success", "fallback", "failed", name="trustnode_status"), default="success"
    )
    request_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
