from fastapi import APIRouter, Response, status

from app.api.dependencies import HealthServiceDep, SettingsDep
from app.api.schemas.health import DependencyStatusDTO, LivenessResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=LivenessResponse)
async def liveness(settings: SettingsDep) -> LivenessResponse:
    return LivenessResponse(
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env.value,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "One or more dependencies are unavailable"}},
)
async def readiness(health_service: HealthServiceDep, response: Response) -> ReadinessResponse:
    results = await health_service.run()
    all_healthy = all(result.healthy for result in results)
    # 503 lets an orchestrator or uptime monitor stop routing traffic
    # while a dependency (e.g. Ollama) is down, without killing the process.
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if all_healthy else "degraded",
        dependencies=[DependencyStatusDTO(**vars(result)) for result in results],
    )
