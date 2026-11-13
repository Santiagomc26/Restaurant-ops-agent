from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    version: str
    environment: str


class DependencyStatusDTO(BaseModel):
    name: str
    healthy: bool
    detail: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded"]
    dependencies: list[DependencyStatusDTO]
