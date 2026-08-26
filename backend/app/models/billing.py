"""Pillar 0: Agentic Fuel - Credit Ledger, Wallets, Invoices, Transactions."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ClientWallet(Base):
    """Each client has one wallet. Credits are pegged to $0.10 USD via FX rates."""

    __tablename__ = "client_wallets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), unique=True, nullable=False, index=True
    )
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    credit_rate_usd: Mapped[float] = mapped_column(Float, default=0.10)
    low_balance_threshold: Mapped[float] = mapped_column(Float, default=10.0)
    auto_topup_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_topup_amount: Mapped[float] = mapped_column(Float, default=100.0)
    auto_topup_trigger: Mapped[float] = mapped_column(Float, default=20.0)
    saved_payment_method_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    saved_payment_provider: Mapped[str | None] = mapped_column(
        Enum("paystack", "flutterwave", "stripe", name="payment_provider_enum"), nullable=True
    )
    total_earned: Mapped[float] = mapped_column(Float, default=0.0)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    client: Mapped["Client"] = relationship(back_populates="wallet")
    transactions: Mapped[list["CreditTransaction"]] = relationship(back_populates="wallet")

    __table_args__ = (Index("ix_wallet_balance", "balance"),)


class CreditTransaction(Base):
    """Immutable ledger of every credit movement. Double-entry bookkeeping."""

    __tablename__ = "credit_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client_wallets.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        Enum("debit", "credit", "refund", "adjustment", name="transaction_type"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    wallet: Mapped["ClientWallet"] = relationship(back_populates="transactions")

    __table_args__ = (
        Index("ix_credit_txn_wallet_created", "wallet_id", "created_at"),
        Index("ix_credit_txn_reference", "reference"),
    )


class Invoice(Base):
    """Generated invoices for billing cycles."""

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("draft", "pending", "paid", "overdue", "cancelled", name="invoice_status"),
        default="draft",
    )
    subtotal_usd: Mapped[float] = mapped_column(Float, nullable=False)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_usd: Mapped[float] = mapped_column(Float, nullable=False)
    credits_used: Mapped[float] = mapped_column(Float, nullable=False)
    payment_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    line_items: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped["Client"] = relationship(back_populates="invoices")

    __table_args__ = (Index("ix_invoice_client_status", "client_id", "status"),)
