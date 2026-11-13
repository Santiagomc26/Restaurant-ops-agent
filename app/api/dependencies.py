from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.health_service import HealthService, OllamaHealthCheck

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_health_service(settings: SettingsDep) -> HealthService:
    # Composition root for health checks: the database check joins this list in Step 2.
    return HealthService(checks=[OllamaHealthCheck(settings)])


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
