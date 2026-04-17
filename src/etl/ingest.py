"""Seed a blockchain-backed property registration demo dataset."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete

from src.controls.mapping import map_finding, refs_as_csv
from src.database.models import EvidenceItem, Finding, IncidentTicket, LedgerBlock, PropertyRecord, TransferRequest
from src.risk.scoring import compute_risk, severity_from_risk
from src.services.property_registry import append_block


def _data_class_to_sensitivity(label: str) -> float:
    return {
        "title_deed": 0.95,
        "citizen_pii": 0.85,
        "payment_record": 0.75,
        "internal": 0.45,
        "public": 0.2,
    }.get(label, 0.5)


def load_seed(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def default_sample_path() -> Path:
    return Path(__file__).resolve().parents[2] / "samples" / "property_registry_seed.json"


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _seed_properties(session, data: dict[str, Any]) -> dict[str, PropertyRecord]:
    properties: dict[str, PropertyRecord] = {}
    for item in data.get("properties", []):
        record = PropertyRecord(
            property_code=item["property_code"],
            parcel_number=item["parcel_number"],
            address=item["address"],
            district=item["district"],
            property_type=item["property_type"],
            area_sqft=item["area_sqft"],
            market_value=item["market_value"],
            owner_name=item["owner_name"],
            owner_wallet=item["owner_wallet"],
            registration_status=item["registration_status"],
            last_transfer_at=_parse_timestamp(item["last_transfer_at"]),
            created_at=_parse_timestamp(item["created_at"]),
        )
        session.add(record)
        session.flush()
        properties[record.property_code] = record
    return properties


def _seed_ledger(session, data: dict[str, Any], properties: dict[str, PropertyRecord]) -> None:
    for item in data.get("ledger_blocks", []):
        property_record = properties.get(item["property_code"]) if item.get("property_code") else None
        append_block(
            session=session,
            property_record=property_record,
            transaction_type=item["transaction_type"],
            actor=item["actor"],
            validator_node=item["validator_node"],
            payload=item["payload"],
            consensus_status=item["consensus_status"],
            created_at=_parse_timestamp(item["created_at"]),
        )


def _seed_transfers(session, data: dict[str, Any], properties: dict[str, PropertyRecord]) -> None:
    for item in data.get("transfer_requests", []):
        record = properties[item["property_code"]]
        session.add(
            TransferRequest(
                property_record=record,
                seller_name=item["seller_name"],
                buyer_name=item["buyer_name"],
                buyer_wallet=item["buyer_wallet"],
                consideration_amount=item["consideration_amount"],
                document_hash=item["document_hash"],
                submission_channel=item["submission_channel"],
                smart_contract_ref=item["smart_contract_ref"],
                fraud_score=item["fraud_score"],
                status=item["status"],
                created_at=_parse_timestamp(item["created_at"]),
            )
        )


def _seed_findings(session, data: dict[str, Any]) -> int:
    count = 0
    for raw in data.get("security_findings", []):
        cm = map_finding(raw["finding_type"])
        iso, nist, pci = refs_as_csv(cm)
        score = compute_risk(
            raw["likelihood"],
            raw["impact"],
            raw["exposure"],
            _data_class_to_sensitivity(raw["data_classification"]),
        )
        session.add(
            Finding(
                asset_id=raw["asset_id"],
                provider=raw["provider"],
                asset_type=raw["asset_type"],
                finding_type=raw["finding_type"],
                severity=severity_from_risk(score),
                title=raw["title"],
                detail=raw["detail"],
                iso_refs=iso,
                nist_refs=nist,
                pci_refs=pci,
                likelihood=raw["likelihood"],
                impact=raw["impact"],
                exposure=raw["exposure"],
                data_sensitivity=_data_class_to_sensitivity(raw["data_classification"]),
                risk_score=score,
                remediation=cm.default_remediation,
                status=raw.get("status", "open"),
                created_at=_parse_timestamp(raw["created_at"]),
            )
        )
        count += 1
    return count


def _seed_evidence(session, data: dict[str, Any]) -> None:
    title_to_id = {finding.title: finding.id for finding in session.query(Finding).all()}
    for item in data.get("evidence_items", []):
        finding_id = title_to_id.get(item["finding_title"])
        if finding_id is None:
            continue
        session.add(
            EvidenceItem(
                finding_id=finding_id,
                title=item["title"],
                evidence_type=item["evidence_type"],
                content=item["content"],
                owner=item["owner"],
                status=item["status"],
                created_at=_parse_timestamp(item["created_at"]),
            )
        )


def _seed_incidents(session, data: dict[str, Any]) -> None:
    for item in data.get("incident_tickets", []):
        session.add(
            IncidentTicket(
                event_type=item["event_type"],
                severity=item["severity"],
                affected_system=item["affected_system"],
                containment_steps=item["containment_steps"],
                escalation_status=item["escalation_status"],
                created_at=_parse_timestamp(item["created_at"]),
            )
        )


def ingest_sample(session, clear_existing: bool = True) -> int:
    """Load demo property-registry data into the database."""
    if clear_existing:
        session.execute(delete(EvidenceItem))
        session.execute(delete(IncidentTicket))
        session.execute(delete(TransferRequest))
        session.execute(delete(LedgerBlock))
        session.execute(delete(PropertyRecord))
        session.execute(delete(Finding))
        session.commit()

    data = load_seed(default_sample_path())
    properties = _seed_properties(session, data)
    _seed_ledger(session, data, properties)
    _seed_transfers(session, data, properties)
    finding_count = _seed_findings(session, data)
    session.flush()
    _seed_evidence(session, data)
    _seed_incidents(session, data)

    session.commit()
    return finding_count
