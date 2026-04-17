from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SQLITE_PATH = _PROJECT_ROOT / "data" / "compliance.db"


def get_database_url() -> str | None:
    """If set, raw URL string (postgresql+psycopg2://... or sqlite:///...)."""
    return os.getenv("DATABASE_URL") or None


def create_db_engine():
    raw = get_database_url()
    if raw:
        connect_args = {}
        if raw.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        return create_engine(raw, echo=False, connect_args=connect_args)

    _SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    url = URL.create("sqlite+pysqlite", database=str(_SQLITE_PATH))
    return create_engine(url, echo=False, connect_args={"check_same_thread": False})


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    from src.database.models import Base

    Base.metadata.create_all(bind=engine)
