from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


DEFAULT_DATABASE_URL = "postgresql+psycopg://whoowns:whoowns@localhost:5432/whoowns"


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def build_engine(url: str | None = None):
    return create_engine(url or database_url(), pool_pre_ping=True)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(bind=engine) -> None:
    Base.metadata.create_all(bind=bind)


def session_scope() -> Session:
    return SessionLocal()

