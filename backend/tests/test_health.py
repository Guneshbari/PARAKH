"""Tests for health, root, status, and database health endpoints using FastAPI TestClient."""
import unittest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app


class TestAPIEndpoints(unittest.TestCase):
    """Test suite for core API endpoints."""

    def setUp(self) -> None:
        """Initialize FastAPI TestClient."""
        self.client = TestClient(app)

    def test_root_endpoint(self) -> None:
        """Verify GET / returns expected message and 200 OK."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "PARAKH API is running"})

    def test_health_endpoint(self) -> None:
        """Verify GET /health returns status healthy and 200 OK."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_api_v1_status_endpoint(self) -> None:
        """Verify GET /api/v1/status returns service status, name, version, and 200 OK."""
        status_url = f"{settings.API_V1_PREFIX}/status"
        response = self.client.get(status_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data,
            {
                "status": "ok",
                "service": "PARAKH API",
                "version": "0.1.0",
            },
        )
        self.assertIn("status", data)
        self.assertIn("service", data)
        self.assertIn("version", data)

    def test_api_v1_database_health_endpoint(self) -> None:
        """Verify GET /api/v1/database/health returns structured status without leaking credentials."""
        db_health_url = f"{settings.API_V1_PREFIX}/database/health"
        response = self.client.get(db_health_url)
        # Expected status: 200 if database is reachable, 503 if unavailable
        self.assertIn(response.status_code, [200, 503])
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("database", data)

        if response.status_code == 200:
            self.assertEqual(data, {"status": "healthy", "database": "connected"})
        else:
            self.assertEqual(data, {"status": "unhealthy", "database": "disconnected"})

        # Strict security validation: Ensure zero credential or stack trace exposure
        response_text = response.text.lower()
        self.assertNotIn("password", response_text)
        self.assertNotIn("traceback", response_text)
        self.assertNotIn("connection refused", response_text)


if __name__ == "__main__":
    unittest.main()
