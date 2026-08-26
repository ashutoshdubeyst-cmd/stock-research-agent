from app.api.router import api_router
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

import httpx
import sentry_sdk
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings


def configure_logging(settings: Settings) -> None:
    """Configure structured application logging."""

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[settings.log_level]
        ),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
    )


def configure_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and close shared application resources."""

    settings = get_settings()
    logger = structlog.get_logger(__name__)

    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.ai_request_timeout_seconds),
        follow_redirects=True,
        headers={"User-Agent": "stock-research-agent/0.1.0"},
    )

    await logger.ainfo(
        "application_started",
        environment=settings.app_env,
        ai_provider=settings.ai_provider,
        market_data_provider=settings.market_data_provider,
    )

    try:
        yield
    finally:
        await app.state.http_client.aclose()
        await logger.ainfo("application_stopped")


def create_application() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    configure_sentry(settings)

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Evidence-grounded stock research API. Market facts must come "
            "from validated tools and deterministic calculations."
        ),
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @application.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "docs": "/docs" if settings.app_env != "production" else "disabled",
        }

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {
            "status": "healthy",
            "environment": settings.app_env,
            "ai_provider": settings.ai_provider,
            "market_data_provider": settings.market_data_provider,
        }

    # Add versioned route modules here as they are implemented:
    # application.include_router(api_router, prefix=settings.api_v1_prefix)

    application.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

    return application


app = create_application()
