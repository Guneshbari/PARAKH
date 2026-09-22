"""Database connection engine, session management, and dependencies."""
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings
from app.models.base import Base

# Create SQLAlchemy engine using configured DATABASE_URL
# pool_pre_ping=True tests connections for liveness before checking them out
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# Session factory for generating independent database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing a database session per request.

    Yields:
        Session: Active SQLAlchemy session.

    Ensures the session is closed reliably upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["engine", "SessionLocal", "Base", "get_db"]
