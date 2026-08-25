"""Integration tests for the agent chat API without external AI calls."""

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.dependencies import get_ai_client
from app.main import create_application


class FakeCompletions:
    def __init__(self, content: str | None = "Educational test response.") -> None:
        self.content = content
        self.calls: list[dict[str, Any]] = []
        self.error: Exception | None = None

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeAiClient:
    def __init__(self, content: str | None = "Educational test response.") -> None:
        self.completions = FakeCompletions(content)
        self.chat = SimpleNamespace(completions=self.completions)


@pytest.fixture
def fake_client() -> FakeAiClient:
    return FakeAiClient()


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        testing=True,
        ai_provider="groq",
        groq_model="test-groq-model",
        max_request_characters=2_000,
        sentry_dsn=None,
    )


@pytest.fixture
def application(
    fake_client: FakeAiClient, test_settings: Settings
) -> Iterator[FastAPI]:
    app = create_application()
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_ai_client] = lambda: fake_client
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application) as test_client:
        yield test_client


def test_agent_chat_returns_provider_response(
    client: TestClient,
    fake_client: FakeAiClient,
) -> None:
    response = client.post(
        "/api/v1/agent/chat",
        json={"message": "Explain what RSI means."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Educational test response."
    assert body["provider"] == "groq"
    assert body["model"] == "test-groq-model"
    assert body["tools_used"] == []
    assert body["sources"] == []
    assert "Educational response only" in body["warning"]
    UUID(body["trace_id"])

    call = fake_client.completions.calls[0]
    assert call["model"] == "test-groq-model"
    assert call["temperature"] == 0.2
    assert call["max_tokens"] == 700
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][-1] == {
        "role": "user",
        "content": "Explain what RSI means.",
    }


def test_agent_chat_passes_history_in_order(
    client: TestClient,
    fake_client: FakeAiClient,
) -> None:
    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "Now explain EMA.",
            "history": [
                {"role": "user", "content": "Explain SMA."},
                {"role": "assistant", "content": "SMA is a simple average."},
            ],
        },
    )

    assert response.status_code == 200
    messages = fake_client.completions.calls[0]["messages"]
    assert [message["role"] for message in messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert messages[-1]["content"] == "Now explain EMA."


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": ""},
        {"message": "x" * 2_001},
        {"message": "test", "history": [{"role": "system", "content": "unsafe"}]},
        {
            "message": "test",
            "history": [
                {"role": "user", "content": f"message-{index}"} for index in range(21)
            ],
        },
    ],
)
def test_agent_chat_rejects_invalid_payloads(
    client: TestClient,
    fake_client: FakeAiClient,
    payload: dict[str, Any],
) -> None:
    response = client.post("/api/v1/agent/chat", json=payload)

    assert response.status_code == 422
    assert fake_client.completions.calls == []


def test_configured_message_limit_is_enforced(
    application: FastAPI,
    fake_client: FakeAiClient,
) -> None:
    restrictive_settings = Settings(
        testing=True,
        ai_provider="groq",
        groq_model="test-groq-model",
        max_request_characters=10,
    )
    application.dependency_overrides[get_settings] = lambda: restrictive_settings

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"message": "This message is too long."},
        )

    assert response.status_code == 422
    assert "10-character limit" in response.json()["detail"]
    assert fake_client.completions.calls == []


def test_provider_failure_returns_bad_gateway(
    client: TestClient,
    fake_client: FakeAiClient,
) -> None:
    fake_client.completions.error = TimeoutError("provider timed out")

    response = client.post(
        "/api/v1/agent/chat",
        json={"message": "Explain price-to-earnings ratio."},
    )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "configured AI provider" in detail
    trace_id = detail.rsplit(": ", maxsplit=1)[-1]
    UUID(trace_id)
    assert "provider timed out" not in detail


def test_empty_provider_response_returns_bad_gateway(
    application: FastAPI,
    test_settings: Settings,
) -> None:
    empty_client = FakeAiClient(content=None)
    application.dependency_overrides[get_settings] = lambda: test_settings
    application.dependency_overrides[get_ai_client] = lambda: empty_client

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"message": "Explain market capitalization."},
        )

    assert response.status_code == 502
    assert len(empty_client.completions.calls) == 1


def test_huggingface_configuration_uses_active_model(
    application: FastAPI,
    fake_client: FakeAiClient,
) -> None:
    settings = Settings(
        testing=True,
        ai_provider="huggingface",
        huggingface_model="test-hf-model",
    )
    application.dependency_overrides[get_settings] = lambda: settings

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"message": "What is a moving average?"},
        )

    assert response.status_code == 200
    assert response.json()["model"] == "test-hf-model"
    assert fake_client.completions.calls[0]["model"] == "test-hf-model"
