"""Initial schema — all tables

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    client_tier = postgresql.ENUM("free", "starter", "growth", "enterprise", name="client_tier", create_type=False)
    transaction_type = postgresql.ENUM("debit", "credit", "refund", "adjustment", name="transaction_type", create_type=False)
    invoice_status = postgresql.ENUM("draft", "pending", "paid", "overdue", "cancelled", name="invoice_status", create_type=False)

    client_tier.create(op.get_bind(), checkfirst=True)
    transaction_type.create(op.get_bind(), checkfirst=True)
    invoice_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("country", sa.String(3), nullable=False, server_default="NG"),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("tier", sa.Enum("free", "starter", "growth", "enterprise", name="client_tier"), server_default="free"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "client_wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), unique=True, nullable=False, index=True),
        sa.Column("balance", sa.Float(), server_default="0.0"),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("credit_rate_usd", sa.Float(), server_default="0.10"),
        sa.Column("low_balance_threshold", sa.Float(), server_default="10.0"),
        sa.Column("auto_topup_enabled", sa.Boolean(), server_default="false"),
        sa.Column("auto_topup_amount", sa.Float(), server_default="100.0"),
        sa.Column("auto_topup_trigger", sa.Float(), server_default="20.0"),
        sa.Column("saved_payment_method_id", sa.String(255), nullable=True),
        sa.Column("saved_payment_provider", sa.String(50), nullable=True),
        sa.Column("total_earned", sa.Float(), server_default="0.0"),
        sa.Column("total_spent", sa.Float(), server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "credit_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_wallets.id"), nullable=False, index=True),
        sa.Column("type", sa.Enum("debit", "credit", "refund", "adjustment", name="transaction_type"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("balance_after", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reference", sa.String(255), nullable=True, index=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_credit_txn_wallet_created", "credit_transactions", ["wallet_id", "created_at"])

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("invoice_number", sa.String(50), unique=True, nullable=False),
        sa.Column("status", sa.Enum("draft", "pending", "paid", "overdue", "cancelled", name="invoice_status"), server_default="draft"),
        sa.Column("subtotal_usd", sa.Float(), nullable=False),
        sa.Column("tax_rate", sa.Float(), server_default="0.0"),
        sa.Column("tax_amount", sa.Float(), server_default="0.0"),
        sa.Column("total_usd", sa.Float(), nullable=False),
        sa.Column("credits_used", sa.Float(), nullable=False),
        sa.Column("payment_provider", sa.String(50), nullable=True),
        sa.Column("payment_reference", sa.String(255), nullable=True),
        sa.Column("line_items", postgresql.JSONB(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "fx_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("quote_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("base_currency", "quote_currency", name="uq_fx_rate_pair"),
    )

    op.create_table(
        "fx_rate_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("quote_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("pillar", sa.Enum("afro_pay", "sentinel", "agent_cloud", "netra_id", "trust_node", "billing", name="agent_pillar"), nullable=False),
        sa.Column("credit_cost_per_task", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agent_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False, index=True),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("task_name", sa.String(255), nullable=False),
        sa.Column("credit_cost", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("agent_id", "task_type", name="uq_agent_task_type"),
    )

    op.create_table(
        "agent_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id"), nullable=False, index=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_wallets.id"), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "completed", "failed", name="execution_status"), server_default="pending"),
        sa.Column("credit_cost", sa.Float(), nullable=False),
        sa.Column("credits_charged", sa.Float(), server_default="0.0"),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("input_data", postgresql.JSONB(), nullable=True),
        sa.Column("output_data", postgresql.JSONB(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_execution_client_started", "agent_executions", ["client_id", "started_at"])

    op.create_table(
        "payment_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("provider", sa.Enum("paystack", "flutterwave", "stripe", name="provider_enum"), nullable=False),
        sa.Column("provider_customer_id", sa.String(255), nullable=False),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "payment_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("provider", sa.Enum("paystack", "flutterwave", "stripe", name="payment_txn_provider"), nullable=False),
        sa.Column("provider_txn_id", sa.String(255), nullable=True, index=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.Enum("pending", "success", "failed", "refunded", name="payment_status"), server_default="pending"),
        sa.Column("credits_purchased", sa.Float(), server_default="0.0"),
        sa.Column("exchange_rate_used", sa.Float(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "afropay_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("sender_country", sa.String(3), nullable=False),
        sa.Column("receiver_country", sa.String(3), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("settlement_fee_pct", sa.Float(), server_default="0.005"),
        sa.Column("settlement_fee_amount", sa.Float(), server_default="0.0"),
        sa.Column("stablecoin_type", sa.String(10), nullable=True),
        sa.Column("tx_hash", sa.String(255), nullable=True),
        sa.Column("status", sa.Enum("initiated", "pending", "completed", "failed", "reversed", name="afropay_status"), server_default="initiated"),
        sa.Column("credits_charged", sa.Float(), server_default="0.0"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "sentinel_agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_type", sa.Enum("recon", "simulation", "response", "log", "deepfake", "phishing", name="sentinel_agent_type"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("cost_per_neutralization", sa.Float(), server_default="500.0"),
    )

    op.create_table(
        "sentinel_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.Enum("low", "medium", "high", "critical", name="alert_severity"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("open", "investigating", "neutralized", "false_positive", name="alert_status"), server_default="open"),
        sa.Column("credits_charged", sa.Float(), server_default="0.0"),
        sa.Column("threat_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("neutralized_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "agent_cloud_deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("agent_type", sa.Enum("sales", "kyc", "hr", "ecommerce", "loan_recovery", name="cloud_agent_type"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("region", sa.String(10), nullable=False, server_default="NG"),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("status", sa.Enum("provisioning", "active", "paused", "terminated", name="deployment_status"), server_default="provisioning"),
        sa.Column("credits_per_run", sa.Float(), nullable=False),
        sa.Column("total_runs", sa.Integer(), server_default="0"),
        sa.Column("total_credits", sa.Float(), server_default="0.0"),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "netra_id_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("verification_type", sa.Enum("biometric", "liveness", "document", "blockchain_token", name="verification_type"), nullable=False),
        sa.Column("subject_id", sa.String(255), nullable=False, index=True),
        sa.Column("status", sa.Enum("pending", "verified", "rejected", "expired", name="verification_status"), server_default="pending"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("compliance_regime", sa.String(50), nullable=False, server_default="NDPA"),
        sa.Column("blockchain_token_id", sa.String(255), nullable=True),
        sa.Column("credits_charged", sa.Float(), server_default="0.0"),
        sa.Column("verification_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "trustnode_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("requested_model", sa.String(100), nullable=False),
        sa.Column("routed_to_model", sa.String(100), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("tokens_input", sa.Integer(), server_default="0"),
        sa.Column("tokens_output", sa.Integer(), server_default="0"),
        sa.Column("cost_usd", sa.Float(), server_default="0.0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("success", "fallback", "failed", name="trustnode_status"), server_default="success"),
        sa.Column("request_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "client_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("key_hash", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("client_api_keys")
    op.drop_table("trustnode_requests")
    op.drop_table("netra_id_verifications")
    op.drop_table("agent_cloud_deployments")
    op.drop_table("sentinel_alerts")
    op.drop_table("sentinel_agents")
    op.drop_table("afropay_transactions")
    op.drop_table("payment_transactions")
    op.drop_table("payment_providers")
    op.drop_table("agent_executions")
    op.drop_table("agent_tasks")
    op.drop_table("agents")
    op.drop_table("fx_rate_history")
    op.drop_table("fx_rates")
    op.drop_table("invoices")
    op.drop_table("credit_transactions")
    op.drop_table("client_wallets")
    op.drop_table("clients")

    for enum_name in [
        "trustnode_status", "verification_status", "verification_type",
        "deployment_status", "cloud_agent_type", "alert_status",
        "alert_severity", "sentinel_agent_type", "afropay_status",
        "payment_status", "payment_txn_provider", "provider_enum",
        "execution_status", "agent_pillar", "invoice_status",
        "transaction_type", "client_tier",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
