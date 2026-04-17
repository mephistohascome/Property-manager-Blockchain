from __future__ import annotations

import paths  # noqa: F401

import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from src.database.models import EvidenceItem, Finding
from src.database.session import SessionLocal, init_db

st.set_page_config(page_title="Audit Evidence Vault", layout="wide")
init_db()

st.header("Audit Evidence Vault")
st.markdown(
    "Attach notarization reports, validator logs, screenshots, and investigator notes to security findings for audit-ready traceability."
)

with SessionLocal() as db:
    findings = db.execute(select(Finding).order_by(Finding.risk_score.desc())).scalars().all()

if not findings:
    st.warning("No findings are available yet.")
else:
    with st.form("evidence_form"):
        finding_id = st.selectbox(
            "Finding",
            options=[finding.id for finding in findings],
            format_func=lambda fid: next(finding.title for finding in findings if finding.id == fid),
        )
        title = st.text_input("Evidence title", value="Multisig validator log review")
        evidence_type = st.selectbox("Evidence type", ["config_snapshot", "screenshot", "note"])
        content = st.text_area("Content", value="ipfs://audit-pack/validator-west-2/log-review.json")
        owner = st.text_input("Owner", value="soc@propertychain.local")
        status = st.selectbox("Evidence status", ["pending", "collected", "verified"])
        add = st.form_submit_button("Attach evidence")

    if add:
        with SessionLocal() as db:
            db.add(
                EvidenceItem(
                    finding_id=int(finding_id),
                    title=title.strip(),
                    evidence_type=evidence_type,
                    content=content.strip(),
                    owner=owner.strip(),
                    status=status,
                )
            )
            db.commit()
        st.success("Evidence added.")

with SessionLocal() as db:
    evidence_rows = db.execute(select(EvidenceItem).order_by(EvidenceItem.created_at.desc()).limit(50)).scalars().all()
    finding_titles = {finding.id: finding.title for finding in db.execute(select(Finding)).scalars().all()}
    status_counts = {
        status: count for status, count in db.execute(select(EvidenceItem.status, func.count()).group_by(EvidenceItem.status)).all()
    }

e1, e2, e3 = st.columns(3)
e1.metric("Pending", status_counts.get("pending", 0))
e2.metric("Collected", status_counts.get("collected", 0))
e3.metric("Verified", status_counts.get("verified", 0))

st.subheader("Evidence index")
if evidence_rows:
    evidence_df = pd.DataFrame(
        [
            {
                "Title": row.title,
                "Finding": finding_titles.get(row.finding_id, str(row.finding_id)),
                "Type": row.evidence_type,
                "Status": row.status,
                "Owner": row.owner,
                "Created": row.created_at.strftime("%Y-%m-%d %H:%M"),
                "Content": row.content,
            }
            for row in evidence_rows
        ]
    )
    st.dataframe(evidence_df, use_container_width=True, hide_index=True)
else:
    st.caption("No evidence items stored.")
