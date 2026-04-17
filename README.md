# Property Registration Management System Using Blockchain

Python + **Streamlit** + **SQLAlchemy** + **SQLite/PostgreSQL** demo of a **blockchain-backed property registry** built as an **Infosec project**.

The app simulates:

- property/title registration records
- a tamper-evident ledger with chained block hashes
- ownership transfer requests with fraud scoring
- security findings mapped to **ISO 27001**, **NIST CSF**, and evidentiary control references
- incident handling and audit-evidence workflows

## Quick start

```bash
cd cloud-compliance-risk-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run Home.py
```

Open the Streamlit app and use the sidebar pages:

- `Registry and Ledger`
- `Threat and Risk Center`
- `Transfer Validation Lab`
- `Incident Readiness`
- `Audit Evidence Vault`

The app auto-seeds a demo dataset from [`samples/property_registry_seed.json`](/Users/ravikoundilya/projects/cloud-compliance-risk-dashboard/samples/property_registry_seed.json).

## Project idea

This project is intentionally framed as a **cybersecurity portfolio/demo system**:

- the ledger shows how blockchain concepts support tamper evidence
- transfer workflows surface fraud and abuse cases
- findings highlight admin override risk, missing multisig, wallet hygiene, and backup gaps
- the incident and evidence pages make the system feel like an end-to-end Infosec case study instead of just a CRUD app

## Main paths

| Path | Role |
|------|------|
| `Home.py` | Executive overview dashboard |
| `src/database/models.py` | ORM schema for properties, transfers, blocks, findings, evidence, incidents |
| `src/services/property_registry.py` | Register property, submit/review transfer, append ledger block |
| `src/blockchain/ledger.py` | Block hashing and chain verification |
| `src/etl/ingest.py` | Demo data seeding |
| `pages/` | Streamlit multipage UI |

## Optional PostgreSQL

```bash
docker compose up -d
cp .env.example .env
# set DATABASE_URL if you want PostgreSQL instead of SQLite
streamlit run Home.py
```
