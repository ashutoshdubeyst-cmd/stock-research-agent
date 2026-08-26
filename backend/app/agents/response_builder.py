from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    label: str
    url: str | None = None
    as_of: str | None = None


class ToolExecutionRecord(BaseModel):
    call_id: str
    name: str
    status: Literal["success", "error"]
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None

    def message_content(self) -> str:
        """Return a compact JSON string suitable for a tool message."""

        return self.model_dump_json(exclude_none=True)


class AgentRunResult(BaseModel):
    answer: str
    trace_id: str
    provider: str
    model: str
    tools_used: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: Literal["verified", "document_based", "inferred", "unavailable"]
    warnings: list[str] = Field(default_factory=list)


def collect_sources(records: list[ToolExecutionRecord]) -> list[SourceReference]:
    collected: list[SourceReference] = []
    seen: set[tuple[str, str | None]] = set()

    for record in records:
        if record.status != "success" or not record.result:
            continue

        candidates: list[dict[str, Any]] = []
        source = record.result.get("source")
        if isinstance(source, str):
            candidates.append(
                {
                    "label": source,
                    "url": record.result.get("source_url"),
                    "as_of": record.result.get("as_of"),
                }
            )

        sources = record.result.get("sources")
        if isinstance(sources, list):
            candidates.extend(item for item in sources if isinstance(item, dict))

        for candidate in candidates:
            label = str(candidate.get("label") or candidate.get("name") or "Source")
            url_value = candidate.get("url")
            url = str(url_value) if url_value else None
            key = (label, url)
            if key in seen:
                continue
            seen.add(key)
            collected.append(
                SourceReference(
                    label=label,
                    url=url,
                    as_of=(
                        str(candidate["as_of"])
                        if candidate.get("as_of") is not None
                        else None
                    ),
                )
            )

    return collected


def build_agent_result(
    *,
    answer: str,
    provider: str,
    model: str,
    records: list[ToolExecutionRecord],
    trace_id: str | None = None,
) -> AgentRunResult:
    successful = [record for record in records if record.status == "success"]
    failed = [record for record in records if record.status == "error"]
    sources = collect_sources(records)

    if successful and sources:
        confidence: Literal["verified", "document_based", "inferred", "unavailable"] = (
            "verified"
        )
    elif successful:
        confidence = "inferred"
    elif records:
        confidence = "unavailable"
    else:
        confidence = "inferred"

    warnings: list[str] = []
    if not records:
        warnings.append("No market-data tool was used for this response.")
    if failed:
        warnings.append(f"{len(failed)} requested tool call(s) failed.")

    return AgentRunResult(
        answer=answer,
        trace_id=trace_id or str(uuid4()),
        provider=provider,
        model=model,
        tools_used=list(dict.fromkeys(record.name for record in successful)),
        sources=sources,
        confidence=confidence,
        warnings=warnings,
    )
