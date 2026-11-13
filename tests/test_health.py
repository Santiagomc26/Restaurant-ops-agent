import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_health_service
from app.core.config import Settings
from app.main import create_app
from app.services.health_service import DependencyStatus, HealthService, OllamaHealthCheck


class FakeCheck:
    def __init__(self, healthy: bool) -> None:
        self._healthy = healthy

    async def check(self) -> DependencyStatus:
        return DependencyStatus("fake", self._healthy, "stub")


def build_client(healthy: bool) -> TestClient:
    app = create_app(Settings(app_env="testing"))
    app.dependency_overrides[get_health_service] = lambda: HealthService([FakeCheck(healthy)])
    return TestClient(app)


def test_liveness_returns_app_metadata() -> None:
    response = build_client(healthy=True).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_is_ready_when_dependencies_are_healthy() -> None:
    response = build_client(healthy=True).get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_readiness_returns_503_when_a_dependency_fails() -> None:
    response = build_client(healthy=False).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def _ollama_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.anyio
async def test_ollama_check_detects_missing_model() -> None:
    client = _ollama_client(lambda request: httpx.Response(200, json={"models": [{"name": "llama3.1:8b"}]}))
    status = await OllamaHealthCheck(Settings(ollama_model="qwen3:14b"), client).check()

    assert status.healthy is False
    assert "ollama pull qwen3:14b" in status.detail


@pytest.mark.anyio
async def test_ollama_check_reports_unreachable_server() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    status = await OllamaHealthCheck(Settings(), _ollama_client(refuse)).check()

    assert status.healthy is False
    assert "unreachable" in status.detail


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
