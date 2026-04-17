from __future__ import annotations

import paths  # noqa: F401

import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from src.database.models import IncidentTicket
from src.database.session import SessionLocal, init_db

st.set_page_config(page_title="Incident Readiness", layout="wide")
init_db()

st.header("Incident Readiness")
st.markdown(
    "Capture blockchain-registry incidents such as title fraud, wallet compromise, validator drift, and evidence-vault outages."
)

PLAYBOOK_HINTS = {
    "title_fraud_claim": "Freeze title state, preserve transfer digests, and require registrar plus legal review before any ownership change.",
    "wallet_compromise_suspected": "Rotate registrar keys, disable signing wallets, and inspect recent on-chain approvals for abuse.",
    "validator_consensus_failure": "Isolate the validator node, compare peer block histories, and rerun chain-integrity validation.",
    "document_vault_breach": "Preserve access logs, revoke vault access, and verify off-chain evidence copies for tampering.",
    "api_override_abuse": "Disable maintenance endpoints and compare database title state with the canonical ledger.",
}

with st.form("ir_form"):
    event_type = st.selectbox("Event type", list(PLAYBOOK_HINTS.keys()))
    severity = st.selectbox("Severity", ["sev1", "sev2", "sev3", "sev4"])
    affected_system = st.text_input("Affected system", value="validator-west-2")
    containment = st.text_area(
        "Containment steps",
        value="Disable signing permissions, preserve node logs, and require manual title freeze for impacted parcels.",
    )
    escalation = st.selectbox("Escalation status", ["triage", "war_room", "legal_notified", "resolved"])
    create_ticket = st.form_submit_button("Open incident ticket")

st.info(PLAYBOOK_HINTS[event_type])

if create_ticket:
    with SessionLocal() as db:
        db.add(
            IncidentTicket(
                event_type=event_type,
                severity=severity,
                affected_system=affected_system.strip(),
                containment_steps=containment.strip(),
                escalation_status=escalation,
            )
        )
        db.commit()
    st.success("Incident stored.")

with SessionLocal() as db:
    rows = db.execute(select(IncidentTicket).order_by(IncidentTicket.created_at.desc()).limit(20)).scalars().all()
    severity_counts = {
        sev: count for sev, count in db.execute(select(IncidentTicket.severity, func.count()).group_by(IncidentTicket.severity)).all()
    }

s1, s2, s3, s4 = st.columns(4)
s1.metric("SEV1", severity_counts.get("sev1", 0))
s2.metric("SEV2", severity_counts.get("sev2", 0))
s3.metric("SEV3", severity_counts.get("sev3", 0))
s4.metric("SEV4", severity_counts.get("sev4", 0))

st.subheader("Recent incidents")
if rows:
    table = pd.DataFrame(
        [
            {
                "Opened": row.created_at.strftime("%Y-%m-%d %H:%M"),
                "Event": row.event_type,
                "Severity": row.severity,
                "Affected system": row.affected_system,
                "Escalation": row.escalation_status,
                "Containment": row.containment_steps,
            }
            for row in rows
        ]
    )
    st.dataframe(table, use_container_width=True, hide_index=True)
else:
    st.caption("No incident tickets recorded.")
