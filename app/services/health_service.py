from dataclasses import dataclass
from typing import Protocol

import httpx
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    healthy: bool
    detail: str


class HealthCheck(Protocol):
    async def check(self) -> DependencyStatus: ...


class OllamaHealthCheck:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    async def check(self) -> DependencyStatus:
        url = f"{self._settings.ollama_host.rstrip('/')}/api/tags"
        try:
            if self._client is not None:
                response = await self._client.get(url, timeout=3.0)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=3.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return DependencyStatus("ollama", False, f"unreachable: {exc.__class__.__name__}")

        installed = {model["name"] for model in response.json().get("models", [])}
        model = self._settings.ollama_model
        # Ollama tags without an explicit version resolve to ":latest".
        if model in installed or f"{model}:latest" in installed:
            return DependencyStatus("ollama", True, f"model '{model}' available")
        return DependencyStatus("ollama", False, f"model '{model}' not pulled (run: ollama pull {model})")


class DatabaseHealthCheck:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    async def check(self) -> DependencyStatus:
        try:
            # Sync driver call off the event loop so a slow database can't block other requests.
            await run_in_threadpool(self._ping)
        except SQLAlchemyError as exc:
            return DependencyStatus("database", False, f"unreachable: {exc.__class__.__name__}")
        return DependencyStatus("database", True, f"{self._engine.dialect.name} connection ok")

    def _ping(self) -> None:
        with self._engine.connect() as connection:
            connection.execute(text("SELECT 1"))


class HealthService:
    def __init__(self, checks: list[HealthCheck]) -> None:
        self._checks = checks

    async def run(self) -> list[DependencyStatus]:
        return [await check.check() for check in self._checks]
