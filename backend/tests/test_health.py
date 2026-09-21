"""Health and root endpoint tests using FastAPI TestClient."""
import unittest
from fastapi.testclient import TestClient
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


if __name__ == "__main__":
    unittest.main()
