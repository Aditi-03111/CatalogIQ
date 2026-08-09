from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_live():
    """
    Verifies that the /health/live endpoint is accessible and returns the expected status.
    """
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "CatalogIQ Backend is live"}

def test_health_ready():
    """
    Verifies that the /health/ready endpoint successfully tests backend dependencies
    and reports their connectivity status gracefully.
    """
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]
    
    services = data.get("services", {})
    assert "postgresql" in services
    assert "redis" in services
    assert "qdrant" in services
