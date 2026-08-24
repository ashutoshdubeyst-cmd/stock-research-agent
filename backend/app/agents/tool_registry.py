from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.agents.tool_schemas import TOOL_ARGUMENT_MODELS, get_tool_schema


ToolHandler = Callable[[BaseModel], Awaitable[dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    name: str
    argument_model: type[BaseModel]
    handler: ToolHandler
    schema: dict[str, object]


class ToolRegistry:
    """Allowlist of tools that the model is permitted to request."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        handler: ToolHandler,
        argument_model: type[BaseModel] | None = None,
    ) -> None:
        if name in self._tools:
            raise ValueError(f"Tool {name!r} is already registered.")

        model = argument_model or TOOL_ARGUMENT_MODELS.get(name)
        if model is None:
            raise ValueError(f"No argument model is available for tool {name!r}.")

        self._tools[name] = RegisteredTool(
            name=name,
            argument_model=model,
            handler=handler,
            schema=get_tool_schema(name),
        )

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict[str, object]]:
        """Return schemas only for tools with executable handlers."""

        return [tool.schema for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)


tool_registry = ToolRegistry()


def register_tool(
    name: str,
    argument_model: type[BaseModel] | None = None,
) -> Callable[[ToolHandler], ToolHandler]:
    """Decorator for registering an asynchronous tool handler."""

    def decorator(handler: ToolHandler) -> ToolHandler:
        tool_registry.register(name, handler, argument_model)
        return handler

    return decorator
