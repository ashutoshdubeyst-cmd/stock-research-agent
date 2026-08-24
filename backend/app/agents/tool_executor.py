import json
from typing import Any

import structlog
from pydantic import ValidationError

from app.agents.tool_registry import ToolRegistry
from app.agents.response_builder import ToolExecutionRecord


logger = structlog.get_logger(__name__)


class ToolExecutor:
    """Validate and execute model-requested tools from an allowlisted registry."""

    def __init__(self, registry: ToolRegistry, max_tool_calls: int = 5) -> None:
        self.registry = registry
        self.max_tool_calls = max_tool_calls

    async def execute(
        self,
        *,
        call_id: str,
        name: str,
        raw_arguments: str | dict[str, Any],
        trace_id: str,
    ) -> ToolExecutionRecord:
        tool = self.registry.get(name)
        if tool is None:
            return ToolExecutionRecord(
                call_id=call_id,
                name=name,
                status="error",
                error="The requested tool is not registered or allowed.",
            )

        try:
            arguments = (
                json.loads(raw_arguments)
                if isinstance(raw_arguments, str)
                else raw_arguments
            )
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be a JSON object.")
            validated = tool.argument_model.model_validate(arguments)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            return ToolExecutionRecord(
                call_id=call_id,
                name=name,
                status="error",
                error=f"Invalid tool arguments: {exc}",
            )

        try:
            result = await tool.handler(validated)
        except Exception as exc:
            await logger.aexception(
                "tool_execution_failed",
                trace_id=trace_id,
                tool=name,
                error_type=type(exc).__name__,
            )
            return ToolExecutionRecord(
                call_id=call_id,
                name=name,
                status="error",
                error="The tool could not complete the request.",
            )

        return ToolExecutionRecord(
            call_id=call_id,
            name=name,
            status="success",
            arguments=validated.model_dump(mode="json"),
            result=result,
        )

    async def execute_many(
        self,
        calls: list[dict[str, Any]],
        trace_id: str,
    ) -> list[ToolExecutionRecord]:
        if len(calls) > self.max_tool_calls:
            calls = calls[: self.max_tool_calls]

        records: list[ToolExecutionRecord] = []
        for call in calls:
            records.append(
                await self.execute(
                    call_id=str(call["id"]),
                    name=str(call["name"]),
                    raw_arguments=call.get("arguments", {}),
                    trace_id=trace_id,
                )
            )
        return records
