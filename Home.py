"""PropertyChain Shield — blockchain property registration Infosec dashboard."""

from __future__ import annotations

import paths  # noqa: F401

import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from src.database.models import LedgerBlock, PropertyRecord
from src.database.session import SessionLocal, init_db
from src.etl.ingest import ingest_sample
from src.services.kpis import (
    compute_kpis,
    framework_coverage_summary,
    ops_snapshot,
    property_status_distribution,
    provider_risk_summary,
    top_open_findings,
)

st.set_page_config(
    page_title="PropertyChain Shield",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

with SessionLocal() as db:
    property_count = db.scalar(select(func.count()).select_from(PropertyRecord)) or 0

st.sidebar.title("Demo Data")
st.sidebar.caption("Blockchain property registration + Infosec monitoring demo backed by SQLite or PostgreSQL.")

if st.sidebar.button("Reset property-chain demo", use_container_width=True):
    with SessionLocal() as db:
        count = ingest_sample(db, clear_existing=True)
    st.sidebar.success(f"Reloaded demo with {count} security findings.")
    st.rerun()

if property_count == 0:
    with SessionLocal() as db:
        ingest_sample(db, clear_existing=True)
    st.rerun()

with SessionLocal() as db:
    kpis = compute_kpis(db)
    ops = ops_snapshot(db)
    property_status = property_status_distribution(db)
    component_risk = provider_risk_summary(db)
    framework_summary = framework_coverage_summary(db)
    top_findings = top_open_findings(db, limit=5)
    recent_blocks = db.execute(select(LedgerBlock).order_by(LedgerBlock.block_index.desc()).limit(5)).scalars().all()

st.title("Property Registration Management System Using Blockchain")
st.markdown(
    """
This project models a **tamper-evident land/property registry** where title operations are written to a local blockchain-style
ledger, while the security team monitors **fraud signals, privileged override paths, wallet hygiene, incident response, and audit evidence**.
It is designed as an **Infosec portfolio project** rather than a production land-record platform.
"""
)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Properties tracked", kpis.total_properties)
c2.metric("Registered titles", kpis.registered_titles)
c3.metric("Pending transfers", kpis.pending_transfers)
c4.metric("Open high / critical", f"{kpis.open_high} / {kpis.open_critical}")
c5.metric("Chain integrity", f"{kpis.chain_integrity_score}%")
c6.metric("Security posture", f"{kpis.compliance_posture_score}%")

st.info(
    "Use the sidebar pages to register properties, inspect the ledger, submit transfers, review findings, respond to incidents, and maintain audit evidence."
)

left, right = st.columns((1.3, 1))

with left:
    st.subheader("Highest-priority security issues")
    if top_findings:
        top_df = pd.DataFrame(
            [
                {
                    "Risk": finding.risk_score,
                    "Severity": finding.severity,
                    "Component": finding.provider,
                    "Asset": finding.asset_id,
                    "Title": finding.title,
                }
                for finding in top_findings
            ]
        )
        st.dataframe(top_df, use_container_width=True, hide_index=True)
    else:
        st.caption("No open findings.")

with right:
    st.subheader("Operations snapshot")
    o1, o2 = st.columns(2)
    o1.metric("Ledger blocks", ops.total_blocks)
    o2.metric("Disputed titles", ops.disputed_properties)
    o3, o4 = st.columns(2)
    o3.metric("Evidence items", ops.total_evidence_items)
    o4.metric("Open incidents", ops.open_incidents)

chart_left, chart_right = st.columns(2)

with chart_left:
    st.subheader("Property status")
    if property_status:
        status_df = pd.DataFrame({"status": list(property_status.keys()), "count": list(property_status.values())}).set_index(
            "status"
        )
        st.bar_chart(status_df, use_container_width=True)
    else:
        st.caption("No property records loaded.")

with chart_right:
    st.subheader("Risk by component")
    if component_risk:
        component_df = pd.DataFrame(component_risk).set_index("provider")
        st.bar_chart(component_df[["open_findings", "mean_risk"]], use_container_width=True)
    else:
        st.caption("No risk telemetry available.")

lower_left, lower_right = st.columns(2)

with lower_left:
    st.subheader("Recent ledger activity")
    if recent_blocks:
        block_df = pd.DataFrame(
            [
                {
                    "Index": block.block_index,
                    "Type": block.transaction_type,
                    "Validator": block.validator_node,
                    "Consensus": block.consensus_status,
                    "Hash": f"{block.block_hash[:16]}...",
                }
                for block in recent_blocks
            ]
        )
        st.dataframe(block_df, use_container_width=True, hide_index=True)
    else:
        st.caption("No blocks found.")

with lower_right:
    st.subheader("Control mapping coverage")
    if framework_summary:
        st.dataframe(pd.DataFrame(framework_summary), use_container_width=True, hide_index=True)
    else:
        st.caption("No findings available yet.")
