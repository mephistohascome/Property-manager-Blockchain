"""Property registration and transfer workflows backed by the local ledger."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.blockchain.ledger import canonical_payload, compute_block_hash, verify_chain
from src.database.models import LedgerBlock, PropertyRecord, TransferRequest


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _next_block_index(session: Session) -> int:
    current_max = session.scalar(select(func.max(LedgerBlock.block_index)))
    return (int(current_max) if current_max is not None else -1) + 1


def _latest_hash(session: Session) -> str:
    latest = session.execute(select(LedgerBlock).order_by(LedgerBlock.block_index.desc()).limit(1)).scalar_one_or_none()
    return latest.block_hash if latest else "GENESIS"


def append_block(
    session: Session,
    property_record: PropertyRecord | None,
    transaction_type: str,
    actor: str,
    validator_node: str,
    payload: dict[str, object],
    consensus_status: str = "validated",
    created_at: datetime | None = None,
) -> LedgerBlock:
    timestamp = created_at or utcnow()
    block_index = _next_block_index(session)
    previous_hash = _latest_hash(session)
    payload_json = canonical_payload(payload)
    property_code = property_record.property_code if property_record else "system"
    block_hash = compute_block_hash(
        block_index,
        previous_hash,
        transaction_type,
        property_code,
        actor,
        payload_json,
        timestamp,
    )

    block = LedgerBlock(
        block_index=block_index,
        property_record=property_record,
        transaction_type=transaction_type,
        actor=actor,
        previous_hash=previous_hash,
        block_hash=block_hash,
        payload_json=payload_json,
        validator_node=validator_node,
        consensus_status=consensus_status,
        created_at=timestamp,
    )
    session.add(block)
    session.flush()
    return block


def register_property(
    session: Session,
    property_code: str,
    parcel_number: str,
    address: str,
    district: str,
    property_type: str,
    area_sqft: int,
    market_value: float,
    owner_name: str,
    owner_wallet: str,
    actor: str,
    validator_node: str,
) -> PropertyRecord:
    property_record = PropertyRecord(
        property_code=property_code,
        parcel_number=parcel_number,
        address=address,
        district=district,
        property_type=property_type,
        area_sqft=area_sqft,
        market_value=market_value,
        owner_name=owner_name,
        owner_wallet=owner_wallet,
        registration_status="registered",
    )
    session.add(property_record)
    session.flush()

    append_block(
        session=session,
        property_record=property_record,
        transaction_type="property_registration",
        actor=actor,
        validator_node=validator_node,
        payload={
            "property_code": property_code,
            "parcel_number": parcel_number,
            "owner_name": owner_name,
            "owner_wallet": owner_wallet,
            "registration_status": "registered",
        },
    )
    session.commit()
    return property_record


def score_transfer_risk(
    property_record: PropertyRecord,
    consideration_amount: float,
    buyer_wallet: str,
    submission_channel: str,
) -> int:
    score = 10
    if consideration_amount > property_record.market_value * 1.35:
        score += 30
    if consideration_amount < property_record.market_value * 0.45:
        score += 20
    if not buyer_wallet.startswith("0x") or len(buyer_wallet) < 12:
        score += 25
    if submission_channel in {"email_attachment", "walk_in_agent"}:
        score += 20
    return min(100, score)


def submit_transfer_request(
    session: Session,
    property_id: int,
    buyer_name: str,
    buyer_wallet: str,
    consideration_amount: float,
    document_hash: str,
    submission_channel: str,
    smart_contract_ref: str,
) -> TransferRequest:
    property_record = session.get(PropertyRecord, property_id)
    if property_record is None:
        raise ValueError("Property not found")

    fraud_score = score_transfer_risk(property_record, consideration_amount, buyer_wallet, submission_channel)
    transfer = TransferRequest(
        property_record=property_record,
        seller_name=property_record.owner_name,
        buyer_name=buyer_name,
        buyer_wallet=buyer_wallet,
        consideration_amount=consideration_amount,
        document_hash=document_hash,
        submission_channel=submission_channel,
        smart_contract_ref=smart_contract_ref,
        fraud_score=fraud_score,
        status="pending",
    )
    property_record.registration_status = "pending_transfer"
    session.add(transfer)
    append_block(
        session=session,
        property_record=property_record,
        transaction_type="transfer_requested",
        actor=property_record.owner_name,
        validator_node="validator-west-2",
        payload={
            "buyer_name": buyer_name,
            "buyer_wallet": buyer_wallet,
            "consideration_amount": consideration_amount,
            "document_hash": document_hash,
            "fraud_score": fraud_score,
        },
        consensus_status="pending_review",
    )
    session.commit()
    return transfer


def review_transfer_request(
    session: Session,
    transfer_id: int,
    new_status: str,
    actor: str,
    validator_node: str,
) -> TransferRequest:
    transfer = session.get(TransferRequest, transfer_id)
    if transfer is None:
        raise ValueError("Transfer request not found")

    property_record = transfer.property_record
    transfer.status = new_status

    if new_status == "approved":
        property_record.owner_name = transfer.buyer_name
        property_record.owner_wallet = transfer.buyer_wallet
        property_record.registration_status = "registered"
        property_record.last_transfer_at = utcnow()
    elif new_status == "rejected":
        property_record.registration_status = "registered"
    else:
        property_record.registration_status = "pending_transfer"

    append_block(
        session=session,
        property_record=property_record,
        transaction_type=f"transfer_{new_status}",
        actor=actor,
        validator_node=validator_node,
        payload={
            "transfer_id": transfer.id,
            "seller_name": transfer.seller_name,
            "buyer_name": transfer.buyer_name,
            "fraud_score": transfer.fraud_score,
            "status": new_status,
        },
        consensus_status="validated" if new_status != "pending" else "pending_review",
    )
    session.commit()
    return transfer


def load_chain(session: Session) -> list[LedgerBlock]:
    stmt = select(LedgerBlock).options(selectinload(LedgerBlock.property_record)).order_by(LedgerBlock.block_index.asc())
    return list(session.execute(stmt).scalars().all())


def verify_chain_health(session: Session) -> tuple[bool, list[str]]:
    blocks = load_chain(session)
    issues = verify_chain(blocks)
    return (len(issues) == 0, [issue.issue for issue in issues])
