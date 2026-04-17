"""SQLAlchemy models for the blockchain-backed property registration demo."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class PropertyRecord(Base):
    __tablename__ = "property_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    parcel_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    address: Mapped[str] = mapped_column(String(512))
    district: Mapped[str] = mapped_column(String(128))
    property_type: Mapped[str] = mapped_column(String(64))
    area_sqft: Mapped[int] = mapped_column(Integer)
    market_value: Mapped[float] = mapped_column(Float)
    owner_name: Mapped[str] = mapped_column(String(256))
    owner_wallet: Mapped[str] = mapped_column(String(128))
    registration_status: Mapped[str] = mapped_column(String(32), default="registered")
    last_transfer_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    transfers: Mapped[list[TransferRequest]] = relationship(back_populates="property_record", cascade="all, delete-orphan")
    blocks: Mapped[list[LedgerBlock]] = relationship(back_populates="property_record", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(String(128), index=True)
    provider: Mapped[str] = mapped_column(String(16))  # aws | gcp
    asset_type: Mapped[str] = mapped_column(String(64))
    finding_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16))  # critical | high | medium | low
    title: Mapped[str] = mapped_column(String(512))
    detail: Mapped[str] = mapped_column(Text)
    iso_refs: Mapped[str] = mapped_column(String(512))  # comma-separated
    nist_refs: Mapped[str] = mapped_column(String(512))
    pci_refs: Mapped[str] = mapped_column(String(512))
    likelihood: Mapped[float] = mapped_column(Float)
    impact: Mapped[float] = mapped_column(Float)
    exposure: Mapped[float] = mapped_column(Float)
    data_sensitivity: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float, index=True)
    remediation: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open")  # open | accepted | remediated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    evidence: Mapped[list[EvidenceItem]] = relationship(back_populates="finding", cascade="all, delete-orphan")


class TransferRequest(Base):
    __tablename__ = "transfer_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("property_records.id", ondelete="CASCADE"), index=True)
    seller_name: Mapped[str] = mapped_column(String(256))
    buyer_name: Mapped[str] = mapped_column(String(256))
    buyer_wallet: Mapped[str] = mapped_column(String(128))
    consideration_amount: Mapped[float] = mapped_column(Float)
    document_hash: Mapped[str] = mapped_column(String(128))
    submission_channel: Mapped[str] = mapped_column(String(64), default="citizen_portal")
    smart_contract_ref: Mapped[str] = mapped_column(String(128))
    fraud_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    property_record: Mapped[PropertyRecord] = relationship(back_populates="transfers")


class LedgerBlock(Base):
    __tablename__ = "ledger_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    block_index: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("property_records.id", ondelete="CASCADE"), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(256))
    previous_hash: Mapped[str] = mapped_column(String(128), default="GENESIS")
    block_hash: Mapped[str] = mapped_column(String(128), unique=True)
    payload_json: Mapped[str] = mapped_column(Text)
    validator_node: Mapped[str] = mapped_column(String(128))
    consensus_status: Mapped[str] = mapped_column(String(32), default="validated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    property_record: Mapped[PropertyRecord | None] = relationship(back_populates="blocks")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(256))
    evidence_type: Mapped[str] = mapped_column(String(64))  # config_snapshot | screenshot | note
    content: Mapped[str] = mapped_column(Text)  # path, URL, or text blob reference
    owner: Mapped[str] = mapped_column(String(128), default="unassigned")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | collected | verified
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    finding: Mapped[Finding] = relationship(back_populates="evidence")


class VendorAssessment(Base):
    __tablename__ = "vendor_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_name: Mapped[str] = mapped_column(String(256))
    tier: Mapped[str] = mapped_column(String(32))  # T1 | T2 | T3
    data_sensitivity_score: Mapped[int] = mapped_column(Integer)
    access_breadth_score: Mapped[int] = mapped_column(Integer)
    assurance_score: Mapped[int] = mapped_column(Integer)
    composite_risk: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IncidentTicket(Base):
    __tablename__ = "incident_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(16))
    affected_system: Mapped[str] = mapped_column(String(256))
    containment_steps: Mapped[str] = mapped_column(Text)
    escalation_status: Mapped[str] = mapped_column(String(64), default="triage")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
