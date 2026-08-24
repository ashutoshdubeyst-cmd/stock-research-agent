from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
from fastapi import Depends, Request
from groq import AsyncGroq
from huggingface_hub import AsyncInferenceClient
from openai import AsyncOpenAI

from app.config import Settings, get_settings


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return the shared HTTP client created during application startup."""

    client: httpx.AsyncClient | None = getattr(request.app.state, "http_client", None)
    if client is None:
        raise RuntimeError("The application HTTP client has not been initialized.")
    return client


HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]


def get_ai_client(settings: SettingsDep) -> Any:
    """Create a client for the configured AI provider.

    Client creation is intentionally lazy so the API can start and expose health
    endpoints before an AI key is configured. The key is required only when an
    endpoint actually requests an AI client.
    """

    api_key = settings.require_ai_api_key()

    if settings.ai_provider == "openai":
        return AsyncOpenAI(
            api_key=api_key,
            timeout=settings.ai_request_timeout_seconds,
        )

    if settings.ai_provider == "groq":
        return AsyncGroq(
            api_key=api_key,
            timeout=settings.ai_request_timeout_seconds,
        )

    return AsyncInferenceClient(
        api_key=api_key,
        provider=settings.huggingface_inference_provider,
        timeout=settings.ai_request_timeout_seconds,
    )


AiClientDep = Annotated[Any, Depends(get_ai_client)]


async def temporary_http_client(
    settings: SettingsDep,
) -> AsyncIterator[httpx.AsyncClient]:
    """Create a short-lived client for scripts that run outside FastAPI."""

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.ai_request_timeout_seconds),
        follow_redirects=True,
    ) as client:
        yield client

