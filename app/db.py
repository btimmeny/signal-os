"""Database engine and session management."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


_raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql://signalos:signalos@localhost:5432/signal_os",
)
# Use psycopg (v3) driver — rewrite postgresql:// to postgresql+psycopg://
# Leave sqlite:// URLs untouched (used in tests)
if _raw_url.startswith("postgresql://"):
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    DATABASE_URL = _raw_url


engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
