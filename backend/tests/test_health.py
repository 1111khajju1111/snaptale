import pytest

@pytest.mark.asyncio
async def test_health_check_endpoint(client):
    """Ensure lightweight /health check works without calling expensive AI operations."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "snaptale-backend"
