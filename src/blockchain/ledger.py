"""Helpers for building and validating a lightweight tamper-evident ledger."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone


def canonical_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def normalized_timestamp(created_at: datetime) -> datetime:
    return created_at.astimezone(timezone.utc) if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)


def compute_block_hash(
    block_index: int,
    previous_hash: str,
    transaction_type: str,
    property_code: str,
    actor: str,
    payload_json: str,
    created_at: datetime,
) -> str:
    material = "|".join(
        [
            str(block_index),
            previous_hash,
            transaction_type,
            property_code,
            actor,
            payload_json,
            normalized_timestamp(created_at).isoformat(),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChainIssue:
    block_index: int
    issue: str


def verify_chain(blocks: list[object]) -> list[ChainIssue]:
    issues: list[ChainIssue] = []
    expected_previous = "GENESIS"

    for expected_index, block in enumerate(blocks):
        property_code = getattr(getattr(block, "property_record", None), "property_code", "system")
        recalculated_hash = compute_block_hash(
            getattr(block, "block_index"),
            getattr(block, "previous_hash"),
            getattr(block, "transaction_type"),
            property_code,
            getattr(block, "actor"),
            getattr(block, "payload_json"),
            getattr(block, "created_at"),
        )

        if getattr(block, "block_index") != expected_index:
            issues.append(ChainIssue(block_index=getattr(block, "block_index"), issue="Block index sequence gap detected"))
        if getattr(block, "previous_hash") != expected_previous:
            issues.append(ChainIssue(block_index=getattr(block, "block_index"), issue="Previous hash mismatch"))
        if getattr(block, "block_hash") != recalculated_hash:
            issues.append(ChainIssue(block_index=getattr(block, "block_index"), issue="Block payload hash mismatch"))

        expected_previous = getattr(block, "block_hash")

    return issues
