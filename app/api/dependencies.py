from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import get_engine, get_session_factory
from app.repositories.interfaces import UnitOfWork
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.services.health_service import DatabaseHealthCheck, HealthService, OllamaHealthCheck

SettingsDep = Annotated[Settings, Depends(get_settings)]
EngineDep = Annotated[Engine, Depends(get_engine)]
SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]


def get_health_service(settings: SettingsDep, engine: EngineDep) -> HealthService:
    return HealthService(checks=[DatabaseHealthCheck(engine), OllamaHealthCheck(settings)])


def get_unit_of_work(session_factory: SessionFactoryDep) -> UnitOfWork:
    # Services receive the UnitOfWork abstraction; swapping to an in-memory
    # fake in tests or another ORM later doesn't touch business logic.
    return SqlAlchemyUnitOfWork(session_factory)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]
