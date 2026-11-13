import logging

from fastapi import FastAPI

from app.api.routes import health
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    # App factory: tests and scripts can build isolated instances with custom settings.
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Agente de operaciones para restaurantes: pedidos por WhatsApp, "
            "inventario y pronóstico de demanda."
        ),
        docs_url=None if settings.is_production else "/docs",
    )
    app.include_router(health.router)

    logger.info("%s v%s started in %s mode", settings.app_name, settings.app_version, settings.app_env.value)
    return app


app = create_app()
