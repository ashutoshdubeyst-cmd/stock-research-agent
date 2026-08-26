from typing import Any, Literal
from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import AiClientDep, SettingsDep


router = APIRouter(prefix="/agent", tags=["agent"])
logger = structlog.get_logger(__name__)


SYSTEM_INSTRUCTIONS = """
You are an educational stock-market research assistant.

Rules:
1. Do not invent current prices, indicators, financial metrics, or news.
2. State clearly when verified market-data tools are not yet available.
3. Do not guarantee returns or provide personalized investment advice.
4. Explain general financial concepts in plain language.
5. Separate factual observations from interpretation.
6. Keep answers concise and identify important limitations.
""".strip()


class AgentMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10_000)


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2_000)
    history: list[AgentMessage] = Field(default_factory=list, max_length=20)


class AgentChatResponse(BaseModel):
    answer: str
    trace_id: str
    provider: str
    model: str
    tools_used: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    warning: str = (
        "Educational response only; verified market-data tools are not connected yet."
    )


def build_messages(request: AgentChatRequest) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS}
    ]
    messages.extend(
        {"role": message.role, "content": message.content}
        for message in request.history
    )
    messages.append({"role": "user", "content": request.message})
    return messages


async def create_provider_completion(
    client: Any,
    settings: SettingsDep,
    messages: list[dict[str, str]],
) -> str:
    """Call the configured provider using its chat-completions interface."""

    model = settings.active_ai_model()

    if settings.ai_provider == "huggingface":
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=700,
            temperature=0.2,
        )
    else:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=700,
            temperature=0.2,
        )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The AI provider returned an empty response.")
    return content


@router.post(
    "/chat",
    response_model=AgentChatResponse,
    summary="Chat with the stock research assistant",
)
async def chat_with_agent(
    request: AgentChatRequest,
    settings: SettingsDep,
    client: AiClientDep,
) -> AgentChatResponse:
    """Generate a general educational response using the selected AI provider.

    This is the initial conversational slice. Market-data tools will be added to
    this endpoint next; until then, the system instruction prohibits claims about
    current or verified market values.
    """

    if len(request.message) > settings.max_request_characters:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Message is longer than the configured "
                f"{settings.max_request_characters}-character limit."
            ),
        )

    trace_id = str(uuid4())
    try:
        answer = await create_provider_completion(
            client=client,
            settings=settings,
            messages=build_messages(request),
        )
    except Exception as exc:
        await logger.aexception(
            "agent_provider_request_failed",
            trace_id=trace_id,
            provider=settings.ai_provider,
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The configured AI provider could not complete the request. "
                f"Reference trace ID: {trace_id}"
            ),
        ) from exc

    return AgentChatResponse(
        answer=answer,
        trace_id=trace_id,
        provider=settings.ai_provider,
        model=settings.active_ai_model(),
    )
