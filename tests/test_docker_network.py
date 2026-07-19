import httpx
import pytest

pytestmark = pytest.mark.asyncio

async def test_orchestrator_ingress():
    """Verify that the FastAPI Orchestrator is running on port 8000 and accepting payloads."""
    async with httpx.AsyncClient() as client:
        payload = {
            "task_id": "test_docker_network_123",
            "intent": "network verification",
            "parameters": {}
        }
        res = await client.post("http://localhost:8000/api/v1/tasks/submit", json=payload)
        assert res.status_code == 202
