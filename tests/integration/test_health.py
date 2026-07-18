"""Tests for health check endpoints and trace ID middleware."""


def test_health_live_returns_200(client):
    """GET /health/live returns 200 with alive status."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_health_ready_returns_200(client):
    """GET /health/ready returns 200 with test dependencies."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_trace_id_header_is_set(client):
    """Every response carries an X-Trace-ID header."""
    response = client.get("/health/live")
    assert "X-Trace-ID" in response.headers
    assert response.headers["X-Trace-ID"]


def test_custom_trace_id_is_propagated(client):
    """A client-supplied X-Trace-ID is echoed back."""
    custom = "custom-trace-id-12345"
    response = client.get("/health/live", headers={"X-Trace-ID": custom})
    assert response.headers["X-Trace-ID"] == custom


def test_unknown_route_returns_404(client):
    """Unknown routes return 404."""
    response = client.get("/does-not-exist")
    assert response.status_code == 404
