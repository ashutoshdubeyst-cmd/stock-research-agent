from typing import Any
from uuid import uuid4

from app.agents.instructions import build_stock_agent_instructions
from app.agents.response_builder import (
    AgentRunResult,
    ToolExecutionRecord,
    build_agent_result,
)
from app.agents.tool_executor import ToolExecutor
from app.agents.tool_registry import ToolRegistry
from app.config import Settings


class StockResearchAgent:
    """Bounded tool-calling loop for stock research questions."""

    def __init__(
        self,
        *,
        client: Any,
        settings: Settings,
        registry: ToolRegistry,
    ) -> None:
        self.client = client
        self.settings = settings
        self.registry = registry
        self.executor = ToolExecutor(
            registry=registry,
            max_tool_calls=settings.ai_max_tool_calls,
        )

    async def run(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AgentRunResult:
        trace_id = str(uuid4())
        model = self.settings.active_ai_model()
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": build_stock_agent_instructions(self.settings),
            }
        ]
        messages.extend(self._safe_history(history or []))
        messages.append({"role": "user", "content": message.strip()})

        all_records: list[ToolExecutionRecord] = []
        tool_schemas = self.registry.schemas()

        # Each round can result in a final answer or one/more requested tools.
        for _ in range(self.settings.ai_max_tool_calls + 1):
            request: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 900,
            }
            if tool_schemas:
                request["tools"] = tool_schemas
                request["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**request)
            assistant = response.choices[0].message
            calls = self._extract_tool_calls(assistant)

            if not calls:
                answer = assistant.content or (
                    "The model returned no answer. Please try a more specific question."
                )
                return build_agent_result(
                    answer=answer,
                    provider=self.settings.ai_provider,
                    model=model,
                    records=all_records,
                    trace_id=trace_id,
                )

            messages.append(self._assistant_tool_message(assistant, calls))
            remaining_calls = self.settings.ai_max_tool_calls - len(all_records)
            if remaining_calls <= 0:
                break

            records = await self.executor.execute_many(
                calls[:remaining_calls],
                trace_id,
            )
            all_records.extend(records)

            for record in records:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": record.call_id,
                        "name": record.name,
                        "content": record.message_content(),
                    }
                )

        return build_agent_result(
            answer=(
                "The analysis stopped after reaching the configured tool-call limit. "
                "Please narrow the request."
            ),
            provider=self.settings.ai_provider,
            model=model,
            records=all_records,
            trace_id=trace_id,
        )

    @staticmethod
    def _safe_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
        safe: list[dict[str, str]] = []
        for item in history[-20:]:
            role = item.get("role")
            content = item.get("content", "").strip()
            if role in {"user", "assistant"} and content:
                safe.append({"role": role, "content": content[:10_000]})
        return safe

    @staticmethod
    def _extract_tool_calls(message: Any) -> list[dict[str, Any]]:
        extracted: list[dict[str, Any]] = []
        for call in getattr(message, "tool_calls", None) or []:
            function = getattr(call, "function", None)
            if function is None:
                continue
            extracted.append(
                {
                    "id": str(getattr(call, "id", "")),
                    "name": str(getattr(function, "name", "")),
                    "arguments": getattr(function, "arguments", "{}"),
                }
            )
        return extracted

    @staticmethod
    def _assistant_tool_message(
        message: Any,
        calls: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": getattr(message, "content", None),
            "tool_calls": [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": call["arguments"],
                    },
                }
                for call in calls
            ],
        }