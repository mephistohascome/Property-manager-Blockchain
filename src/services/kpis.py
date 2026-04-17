"""Aggregate KPIs for the property registration and blockchain demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.blockchain.ledger import verify_chain
from src.database.models import EvidenceItem, Finding, IncidentTicket, LedgerBlock, PropertyRecord, TransferRequest


@dataclass
class KpiSnapshot:
    total_properties: int
    registered_titles: int
    pending_transfers: int
    open_critical: int
    open_high: int
    mean_risk_score: float
    chain_integrity_score: float
    compliance_posture_score: float
    total_open: int


@dataclass
class OpsSnapshot:
    total_properties: int
    total_blocks: int
    total_evidence_items: int
    verified_evidence_items: int
    disputed_properties: int
    open_incidents: int


def compute_kpis(session: Session) -> KpiSnapshot:
    stmt = select(Finding).where(Finding.status == "open")
    open_rows: Sequence[Finding] = session.execute(stmt).scalars().all()
    total_properties = int(session.scalar(select(func.count()).select_from(PropertyRecord)) or 0)
    registered_titles = int(
        session.scalar(
            select(func.count())
            .select_from(PropertyRecord)
            .where(PropertyRecord.registration_status == "registered")
        )
        or 0
    )
    pending_transfers = int(
        session.scalar(
            select(func.count())
            .select_from(TransferRequest)
            .where(TransferRequest.status == "pending")
        )
        or 0
    )

    crit = sum(1 for f in open_rows if f.severity == "critical")
    high = sum(1 for f in open_rows if f.severity == "high")
    mean_risk = float(sum(f.risk_score for f in open_rows) / len(open_rows)) if open_rows else 0.0

    blocks = session.execute(
        select(LedgerBlock).options(selectinload(LedgerBlock.property_record)).order_by(LedgerBlock.block_index.asc())
    ).scalars().all()
    issues = verify_chain(list(blocks))
    chain_integrity = 100.0 if not blocks else max(0.0, 100 - len(issues) * 25)
    posture = max(0.0, min(100.0, chain_integrity - mean_risk * 0.55 + registered_titles * 2 - pending_transfers * 3))

    return KpiSnapshot(
        total_properties=total_properties,
        registered_titles=registered_titles,
        pending_transfers=pending_transfers,
        open_critical=crit,
        open_high=high,
        mean_risk_score=round(mean_risk, 2),
        chain_integrity_score=round(chain_integrity, 1),
        compliance_posture_score=round(posture, 1),
        total_open=len(open_rows),
    )


def property_status_distribution(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(PropertyRecord.registration_status, func.count()).group_by(PropertyRecord.registration_status)
    ).all()
    return {status: int(count) for status, count in rows}


def severity_distribution(session: Session, status: str = "open") -> dict[str, int]:
    stmt = select(Finding.severity, func.count()).group_by(Finding.severity)
    if status != "all":
        stmt = stmt.where(Finding.status == status)
    rows = session.execute(stmt).all()
    order = ["critical", "high", "medium", "low"]
    data = {severity: int(count) for severity, count in rows}
    return {severity: data[severity] for severity in order if severity in data}


def provider_risk_summary(session: Session) -> list[dict[str, float | str | int]]:
    stmt = (
        select(Finding.provider, func.count(), func.avg(Finding.risk_score))
        .where(Finding.status == "open")
        .group_by(Finding.provider)
        .order_by(func.avg(Finding.risk_score).desc())
    )
    rows = session.execute(stmt).all()
    return [
        {
            "provider": provider.upper(),
            "open_findings": int(count),
            "mean_risk": round(float(mean_risk or 0.0), 2),
        }
        for provider, count, mean_risk in rows
    ]


def top_open_findings(session: Session, limit: int = 5) -> list[Finding]:
    stmt = (
        select(Finding)
        .where(Finding.status == "open")
        .order_by(Finding.risk_score.desc(), Finding.id.asc())
        .limit(limit)
    )
    return session.execute(stmt).scalars().all()


def framework_coverage_summary(session: Session) -> list[dict[str, int | str]]:
    total = session.scalar(select(func.count()).select_from(Finding)) or 0
    if total == 0:
        return []

    def _covered(column) -> int:
        return int(session.scalar(select(func.count()).select_from(Finding).where(column != "")) or 0)

    iso_count = _covered(Finding.iso_refs)
    nist_count = _covered(Finding.nist_refs)
    pci_count = _covered(Finding.pci_refs)

    return [
        {"framework": "ISO 27001", "mapped_findings": iso_count, "coverage_pct": round(iso_count / total * 100)},
        {"framework": "NIST CSF", "mapped_findings": nist_count, "coverage_pct": round(nist_count / total * 100)},
        {"framework": "PCI DSS / evidentiary controls", "mapped_findings": pci_count, "coverage_pct": round(pci_count / total * 100)},
    ]


def ops_snapshot(session: Session) -> OpsSnapshot:
    total_properties = int(session.scalar(select(func.count()).select_from(PropertyRecord)) or 0)
    total_blocks = int(session.scalar(select(func.count()).select_from(LedgerBlock)) or 0)
    total_evidence_items = int(session.scalar(select(func.count()).select_from(EvidenceItem)) or 0)
    verified_evidence_items = int(
        session.scalar(
            select(func.count()).select_from(EvidenceItem).where(EvidenceItem.status == "verified")
        )
        or 0
    )
    disputed_properties = int(
        session.scalar(
            select(func.count())
            .select_from(PropertyRecord)
            .where(PropertyRecord.registration_status == "disputed")
        )
        or 0
    )
    open_incidents = int(
        session.scalar(
            select(func.count())
            .select_from(IncidentTicket)
            .where(IncidentTicket.escalation_status != "resolved")
        )
        or 0
    )
    return OpsSnapshot(
        total_properties=total_properties,
        total_blocks=total_blocks,
        total_evidence_items=total_evidence_items,
        verified_evidence_items=verified_evidence_items,
        disputed_properties=disputed_properties,
        open_incidents=open_incidents,
    )
