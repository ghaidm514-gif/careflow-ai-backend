"""Tests for health check endpoints."""


def test_health_live_endpoint(client):
    """GET /health/live returns 200."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_health_ready_endpoint(client):
    """GET /health/ready returns 200."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_trace_id_in_response(client):
    """X-Trace-ID is set in response headers."""
    response = client.get("/health/live")
    assert "X-Trace-ID" in response.headers
