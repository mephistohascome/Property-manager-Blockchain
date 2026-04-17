from __future__ import annotations

import paths  # noqa: F401

import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database.models import PropertyRecord, TransferRequest
from src.database.session import SessionLocal, init_db
from src.services.property_registry import review_transfer_request, submit_transfer_request

st.set_page_config(page_title="Transfer Validation Lab", layout="wide")
init_db()

st.header("Transfer Validation Lab")
st.markdown(
    "Model ownership-transfer requests, compute fraud scores, and decide whether a title move should be approved, rejected, or held."
)

with SessionLocal() as db:
    properties = db.execute(select(PropertyRecord).order_by(PropertyRecord.property_code.asc())).scalars().all()

if not properties:
    st.warning("No properties available. Register a property from the Registry page first.")
else:
    with st.form("transfer_form"):
        property_id = st.selectbox(
            "Property",
            options=[record.id for record in properties],
            format_func=lambda pid: next(
                f"{record.property_code} | {record.owner_name} | {record.registration_status}"
                for record in properties
                if record.id == pid
            ),
        )
        c1, c2 = st.columns(2)
        buyer_name = c1.text_input("Buyer name", value="Aurora Estates")
        buyer_wallet = c2.text_input("Buyer wallet", value="0xe44bc712d05aa771")
        c3, c4, c5 = st.columns(3)
        consideration_amount = c3.number_input("Consideration amount", min_value=100000.0, value=25500000.0, step=100000.0)
        submission_channel = c4.selectbox("Submission channel", ["citizen_portal", "bank_api", "email_attachment", "walk_in_agent"])
        smart_contract_ref = c5.text_input("Smart contract ref", value="SC-HYD-031-TX-01")
        document_hash = st.text_input("Document hash", value="sha256:4a13bc91d0efa219")
        submit = st.form_submit_button("Submit transfer request")

    if submit:
        with SessionLocal() as db:
            try:
                transfer = submit_transfer_request(
                    session=db,
                    property_id=int(property_id),
                    buyer_name=buyer_name.strip(),
                    buyer_wallet=buyer_wallet.strip(),
                    consideration_amount=float(consideration_amount),
                    document_hash=document_hash.strip(),
                    submission_channel=submission_channel,
                    smart_contract_ref=smart_contract_ref.strip(),
                )
                st.success(f"Transfer queued with fraud score {transfer.fraud_score}.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Unable to submit transfer: {exc}")

with SessionLocal() as db:
    requests = db.execute(
        select(TransferRequest)
        .options(selectinload(TransferRequest.property_record))
        .order_by(TransferRequest.created_at.desc())
    ).scalars().all()

st.subheader("Transfer queue")
if requests:
    request_df = pd.DataFrame(
        [
            {
                "ID": req.id,
                "Property": req.property_record.property_code,
                "Seller": req.seller_name,
                "Buyer": req.buyer_name,
                "Amount": req.consideration_amount,
                "Fraud score": req.fraud_score,
                "Channel": req.submission_channel,
                "Status": req.status,
            }
            for req in requests
        ]
    )
    st.dataframe(request_df, use_container_width=True, hide_index=True)
else:
    st.caption("No transfer requests submitted.")

pending_requests = [request for request in requests if request.status == "pending"]

if pending_requests:
    st.subheader("Review a pending transfer")
    selected_id = st.selectbox(
        "Pending request",
        options=[request.id for request in pending_requests],
        format_func=lambda rid: next(
            f"#{request.id} | {request.property_record.property_code} | fraud {request.fraud_score}"
            for request in pending_requests
            if request.id == rid
        ),
    )
    decision = st.radio("Decision", ["approved", "rejected", "pending"], horizontal=True)
    if st.button("Commit review decision", use_container_width=True):
        with SessionLocal() as db:
            review_transfer_request(
                session=db,
                transfer_id=int(selected_id),
                new_status=decision,
                actor="Fraud Review Board",
                validator_node="validator-review-1",
            )
        st.success(f"Transfer {selected_id} marked as {decision}.")
        st.rerun()
else:
    st.caption("No pending transfers to review.")
