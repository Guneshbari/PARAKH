"""Tests for database configuration, engine creation, and session dependencies."""
import inspect
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import Engine, text
from sqlalchemy.orm import DeclarativeBase, Session
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.schemas.common import DatabaseHealthResponse


def can_connect_to_postgres() -> bool:
    """Helper to detect if PostgreSQL is active and reachable locally."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


class TestDatabaseFoundationUnit(unittest.TestCase):
    """Unit tests for database infrastructure and configuration."""

    def test_database_config_loaded(self) -> None:
        """Verify DATABASE_URL loads correctly from settings."""
        self.assertIsNotNone(settings.DATABASE_URL)
        self.assertTrue(len(settings.DATABASE_URL) > 0)
        self.assertTrue(
            settings.DATABASE_URL.startswith("postgresql"),
            "DATABASE_URL should use postgresql protocol",
        )

    def test_sqlalchemy_engine_created(self) -> None:
        """Verify SQLAlchemy engine is properly initialized with psycopg driver."""
        self.assertIsInstance(engine, Engine)
        self.assertEqual(engine.dialect.name, "postgresql")
        self.assertEqual(engine.dialect.driver, "psycopg")

    def test_declarative_base_defined(self) -> None:
        """Verify DeclarativeBase model is configured."""
        self.assertTrue(issubclass(Base, DeclarativeBase))
        self.assertIsNotNone(Base.metadata)

    def test_get_db_session_dependency_structure(self) -> None:
        """Verify get_db dependency yields a Session and calls close on termination."""
        self.assertTrue(inspect.isgeneratorfunction(get_db))

        # 1. Test real generator yields an actual Session instance
        real_gen = get_db()
        real_session = next(real_gen)
        self.assertIsInstance(real_session, Session)
        try:
            next(real_gen)
        except StopIteration:
            pass

        # 2. Verify close() invocation is guaranteed upon generator completion
        with patch("app.core.database.SessionLocal") as mock_sessionmaker:
            mock_session = MagicMock(spec=Session)
            mock_sessionmaker.return_value = mock_session

            gen = get_db()
            session = next(gen)
            self.assertEqual(session, mock_session)
            mock_session.close.assert_not_called()

            try:
                next(gen)
            except StopIteration:
                pass

            mock_session.close.assert_called_once()

    def test_database_health_schema(self) -> None:
        """Verify DatabaseHealthResponse schema fields and validation."""
        data = DatabaseHealthResponse(status="healthy", database="connected")
        self.assertEqual(data.status, "healthy")
        self.assertEqual(data.database, "connected")

        unhealthy = DatabaseHealthResponse(status="unhealthy", database="disconnected")
        self.assertEqual(unhealthy.status, "unhealthy")
        self.assertEqual(unhealthy.database, "disconnected")


class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for live PostgreSQL connectivity."""

    @unittest.skipUnless(
        can_connect_to_postgres(),
        "PostgreSQL is not reachable locally. Set up PostgreSQL and configure DATABASE_URL in .env to run live integration tests.",
    )
    def test_live_postgres_select_1(self) -> None:
        """Verify live database connectivity by executing SELECT 1 query."""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
