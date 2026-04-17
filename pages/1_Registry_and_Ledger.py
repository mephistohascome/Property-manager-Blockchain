from __future__ import annotations

import paths  # noqa: F401

import pandas as pd
import streamlit as st
from sqlalchemy import select

from src.database.models import LedgerBlock, PropertyRecord
from src.database.session import SessionLocal, init_db
from src.services.property_registry import load_chain, register_property, verify_chain_health

st.set_page_config(page_title="Registry & Ledger", layout="wide")
init_db()

st.header("Property Registry & Blockchain Ledger")
st.markdown(
    "Register properties, inspect title records, and verify that the blockchain-style ledger remains tamper-evident."
)

with st.form("property_form"):
    c1, c2 = st.columns(2)
    property_code = c1.text_input("Property code", value="PR-HYD-031")
    parcel_number = c2.text_input("Parcel number", value="TS-41-778-1201")
    c3, c4 = st.columns(2)
    owner_name = c3.text_input("Owner name", value="Saanvi Developers")
    owner_wallet = c4.text_input("Owner wallet", value="0xd53c76f2109ab441")
    address = st.text_input("Address", value="7 Banjara Hills, Hyderabad")
    c5, c6, c7, c8 = st.columns(4)
    district = c5.text_input("District", value="Hyderabad")
    property_type = c6.selectbox("Property type", ["Residential", "Commercial", "Industrial", "Agricultural"])
    area_sqft = c7.number_input("Area (sq ft)", min_value=100, value=3600, step=100)
    market_value = c8.number_input("Market value", min_value=100000.0, value=21800000.0, step=100000.0)
    create = st.form_submit_button("Register property on ledger")

if create:
    with SessionLocal() as db:
        try:
            register_property(
                session=db,
                property_code=property_code.strip(),
                parcel_number=parcel_number.strip(),
                address=address.strip(),
                district=district.strip(),
                property_type=property_type,
                area_sqft=int(area_sqft),
                market_value=float(market_value),
                owner_name=owner_name.strip(),
                owner_wallet=owner_wallet.strip(),
                actor="Registrar Control Room",
                validator_node="validator-hyd-1",
            )
            st.success("Property registered and committed to the ledger.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Registration failed: {exc}")

with SessionLocal() as db:
    properties = db.execute(select(PropertyRecord).order_by(PropertyRecord.created_at.desc())).scalars().all()
    blocks = db.execute(select(LedgerBlock).order_by(LedgerBlock.block_index.desc())).scalars().all()
    chain_ok, chain_issues = verify_chain_health(db)
    chain = load_chain(db)

summary_left, summary_right = st.columns((1.2, 1))

with summary_left:
    st.subheader("Property records")
    if properties:
        property_df = pd.DataFrame(
            [
                {
                    "Code": record.property_code,
                    "Parcel": record.parcel_number,
                    "Owner": record.owner_name,
                    "District": record.district,
                    "Type": record.property_type,
                    "Status": record.registration_status,
                    "Market value": record.market_value,
                }
                for record in properties
            ]
        )
        st.dataframe(property_df, use_container_width=True, hide_index=True)
    else:
        st.caption("No properties registered yet.")

with summary_right:
    st.subheader("Chain verification")
    st.metric("Ledger status", "Healthy" if chain_ok else "Attention needed")
    st.metric("Blocks committed", len(chain))
    if chain_issues:
        for issue in chain_issues:
            st.warning(issue)
    else:
        st.success("Each block hash and previous-hash link verified successfully.")

st.subheader("Ledger explorer")
if blocks:
    block_df = pd.DataFrame(
        [
            {
                "Index": block.block_index,
                "Transaction": block.transaction_type,
                "Actor": block.actor,
                "Validator": block.validator_node,
                "Consensus": block.consensus_status,
                "Previous": f"{block.previous_hash[:14]}...",
                "Hash": f"{block.block_hash[:14]}...",
            }
            for block in blocks
        ]
    )
    st.dataframe(block_df, use_container_width=True, hide_index=True)
else:
    st.caption("No ledger blocks to display.")
