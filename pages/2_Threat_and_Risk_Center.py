from __future__ import annotations

import paths  # noqa: F401

import pandas as pd
import streamlit as st
from sqlalchemy import select

from src.database.models import Finding
from src.database.session import SessionLocal, init_db
from src.services.kpis import (
    compute_kpis,
    framework_coverage_summary,
    property_status_distribution,
    provider_risk_summary,
    severity_distribution,
    top_open_findings,
)

st.set_page_config(page_title="Threat & Risk Center", layout="wide")
init_db()

st.header("Threat & Risk Center")
st.markdown("Review fraud, blockchain, identity, and backup weaknesses mapped to recognizable security controls.")

with SessionLocal() as db:
    rows = db.execute(select(Finding).order_by(Finding.risk_score.desc())).scalars().all()
    kpis = compute_kpis(db)
    status_dist = property_status_distribution(db)
    severity = severity_distribution(db)
    component_risk = provider_risk_summary(db)
    framework_summary = framework_coverage_summary(db)
    top_findings = top_open_findings(db, limit=7)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Open findings", kpis.total_open)
c2.metric("High", kpis.open_high)
c3.metric("Critical", kpis.open_critical)
c4.metric("Mean risk", kpis.mean_risk_score)

f1, f2, f3, f4 = st.columns(4)
severities = sorted({finding.severity for finding in rows}) or ["critical", "high", "medium", "low"]
providers = sorted({finding.provider for finding in rows})
statuses = sorted({finding.status for finding in rows})
selected_severities = f1.multiselect("Severity", severities, default=severities)
selected_components = f2.multiselect("Component", providers, default=providers)
selected_statuses = f3.multiselect("Status", statuses, default=statuses)
search = f4.text_input("Search asset/title", value="").strip().lower()

filtered = [
    finding
    for finding in rows
    if finding.severity in selected_severities
    and finding.provider in selected_components
    and finding.status in selected_statuses
    and (not search or search in finding.title.lower() or search in finding.asset_id.lower())
]

if filtered:
    findings_df = pd.DataFrame(
        [
            {
                "Risk": finding.risk_score,
                "Severity": finding.severity,
                "Component": finding.provider,
                "Asset": finding.asset_id,
                "Finding type": finding.finding_type,
                "Title": finding.title,
                "ISO": finding.iso_refs,
                "NIST": finding.nist_refs,
                "Control set": finding.pci_refs,
                "Status": finding.status,
            }
            for finding in filtered
        ]
    )
    st.dataframe(findings_df, use_container_width=True, hide_index=True)
else:
    st.caption("No findings match the active filters.")

left, right = st.columns(2)

with left:
    st.subheader("Property status distribution")
    if status_dist:
        status_df = pd.DataFrame({"status": list(status_dist.keys()), "count": list(status_dist.values())}).set_index("status")
        st.bar_chart(status_df, use_container_width=True)
    else:
        st.caption("No property statuses available.")

with right:
    st.subheader("Open findings by severity")
    if severity:
        severity_df = pd.DataFrame({"severity": list(severity.keys()), "count": list(severity.values())}).set_index("severity")
        st.bar_chart(severity_df, use_container_width=True)
    else:
        st.caption("No severity distribution available.")

bottom_left, bottom_right = st.columns(2)

with bottom_left:
    st.subheader("Component risk summary")
    if component_risk:
        component_df = pd.DataFrame(component_risk).set_index("provider")
        st.bar_chart(component_df[["open_findings", "mean_risk"]], use_container_width=True)
    else:
        st.caption("No component risk data.")

with bottom_right:
    st.subheader("Control coverage")
    if framework_summary:
        st.dataframe(pd.DataFrame(framework_summary), use_container_width=True, hide_index=True)
    else:
        st.caption("No framework coverage to show.")

st.subheader("Top open findings")
if top_findings:
    top_df = pd.DataFrame(
        [
            {
                "Risk": finding.risk_score,
                "Severity": finding.severity,
                "Component": finding.provider,
                "Title": finding.title,
                "Remediation": finding.remediation,
            }
            for finding in top_findings
        ]
    )
    st.dataframe(top_df, use_container_width=True, hide_index=True)
else:
    st.caption("No open findings.")
