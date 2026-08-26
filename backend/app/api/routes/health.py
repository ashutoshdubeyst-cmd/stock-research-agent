from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.dependencies import SettingsDep


router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    environment: str
    ai_provider: str
    market_data_provider: str


class ReadinessResponse(BaseModel):
    status: str
    configuration_loaded: bool
    database_checked: bool
    ai_provider_checked: bool
    market_data_provider_checked: bool


@router.get("", response_model=HealthResponse, summary="Application health check")
async def health_check(settings: SettingsDep) -> HealthResponse:
    """Confirm that the API process is running and configuration is loaded."""

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC),
        environment=settings.app_env,
        ai_provider=settings.ai_provider,
        market_data_provider=settings.market_data_provider,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Dependency readiness check",
)
async def readiness_check() -> ReadinessResponse:
    """Report which external dependencies are currently verified.

    Database and provider checks remain false until those integrations are
    implemented. Returning them explicitly avoids claiming that untested
    dependencies are ready.
    """

    return ReadinessResponse(
        status="partially_ready",
        configuration_loaded=True,
        database_checked=False,
        ai_provider_checked=False,
        market_data_provider_checked=False,
    )
