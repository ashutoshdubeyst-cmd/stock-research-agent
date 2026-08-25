"""Request and response models for the stock research agent API."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

AgentRole = Literal["user", "assistant"]
ConfidenceLevel = Literal["verified", "document_based", "inferred", "unavailable"]


class AgentMessage(BaseModel):
    """One safe conversational message supplied to the agent."""

    model_config = ConfigDict(str_strip_whitespace=True)
    role: AgentRole
    content: str = Field(min_length=1, max_length=10_000)


class AgentChatRequest(BaseModel):
    """A new question plus bounded conversational context."""

    model_config = ConfigDict(str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=2_000)
    history: list[AgentMessage] = Field(default_factory=list, max_length=20)


class SourceReference(BaseModel):
    """A market-data or document source supporting the response."""

    label: str = Field(min_length=1, max_length=200)
    url: HttpUrl | None = None
    as_of: str | None = Field(default=None, max_length=50)


class ToolActivity(BaseModel):
    """User-safe summary of one tool execution."""

    name: str = Field(min_length=1, max_length=100)
    status: Literal["success", "error"]
    arguments: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = Field(default=None, ge=0)
    error: str | None = Field(default=None, max_length=500)

    @field_validator("error")
    @classmethod
    def require_error_for_failed_tool(cls, value: str | None, info: Any) -> str | None:
        if info.data.get("status") == "error" and not value:
            return "The tool could not complete the request."
        return value


class AgentChatResponse(BaseModel):
    """Evidence-aware answer returned by the agent endpoint."""

    answer: str = Field(min_length=1)
    trace_id: UUID
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    tools_used: list[str] = Field(default_factory=list)
    tool_activity: list[ToolActivity] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: ConfidenceLevel = "inferred"
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Educational research only; this is not personalized investment advice."
    )

    @field_validator("tools_used")
    @classmethod
    def unique_tools(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))
