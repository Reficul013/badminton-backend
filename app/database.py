# app/database.py
from __future__ import annotations
import os
from sqlmodel import SQLModel, create_engine, Session

# --- read env ----------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var is required")

# Neon gives: postgresql://...
# SQLAlchemy + psycopg = postgresql+psycopg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Always require TLS on Neon
if "sslmode=" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

# --- engine ------------------------------
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # auto-reconnect
    pool_size=5,
    max_overflow=10,
)

def get_session() -> Session:
    return Session(engine)

def init_db() -> None:
    # Creates tables that don't exist; does not drop/alter
    SQLModel.metadata.create_all(engine)
