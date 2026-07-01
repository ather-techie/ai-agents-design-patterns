"""A validated tool registry.

Tools are plain Python callables wrapped with a name, description, and a JSON
Schema for their inputs. The registry validates arguments against that schema
before invoking the handler, so a malformed tool call from the model becomes a
clean :class:`ToolValidationError` instead of a random ``TypeError`` deep in
user code. Validation is intentionally lightweight (types + required keys) to
avoid pulling in a JSON Schema dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .errors import ToolError, ToolValidationError
from .types import ToolResult

ToolHandler = Callable[..., Any]

# JSON Schema type name -> Python type(s) accepted for it.
_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


@dataclass
class Tool:
    """A single callable tool the model may invoke."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler

    def to_anthropic(self) -> dict[str, Any]:
        """Render the tool definition in the Anthropic Messages API shape."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    """Holds the tools available to a pattern and dispatches validated calls."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ToolError(f"tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    @property
    def names(self) -> list[str]:
        return list(self._tools)

    def definitions(self) -> list[dict[str, Any]]:
        """Anthropic-shaped definitions for every registered tool."""
        return [t.to_anthropic() for t in self._tools.values()]

    def validate(self, name: str, arguments: dict[str, Any]) -> None:
        """Validate ``arguments`` against the tool's schema.

        Raises :class:`ToolValidationError` for an unknown tool, missing
        required keys, or a value whose type doesn't match the schema.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise ToolValidationError(f"unknown tool {name!r}")

        schema = tool.input_schema
        properties: dict[str, Any] = schema.get("properties", {})
        required: list[str] = schema.get("required", [])

        missing = [key for key in required if key not in arguments]
        if missing:
            raise ToolValidationError(
                f"tool {name!r} missing required argument(s): {', '.join(missing)}"
            )

        for key, value in arguments.items():
            prop = properties.get(key)
            if prop is None:
                # Unknown key — only reject when the schema forbids extras.
                if schema.get("additionalProperties") is False:
                    raise ToolValidationError(
                        f"tool {name!r} got unexpected argument {key!r}"
                    )
                continue
            expected = prop.get("type")
            if expected is None:
                continue
            accepted = _JSON_TYPES.get(expected)
            # `bool` is a subtype of `int`; reject it for numeric fields.
            if expected in {"integer", "number"} and isinstance(value, bool):
                raise ToolValidationError(
                    f"tool {name!r} argument {key!r} should be {expected}, got bool"
                )
            if accepted is not None and not isinstance(value, accepted):
                raise ToolValidationError(
                    f"tool {name!r} argument {key!r} should be {expected}, "
                    f"got {type(value).__name__}"
                )

    def call(self, name: str, arguments: dict[str, Any], tool_call_id: str) -> ToolResult:
        """Validate and execute a tool, capturing handler failures as errors.

        Validation failures propagate as :class:`ToolValidationError`; failures
        *inside* the handler are returned as a ``ToolResult`` with
        ``is_error=True`` so the agent loop can feed them back to the model.
        """
        self.validate(name, arguments)
        tool = self._tools[name]
        try:
            output = tool.handler(**arguments)
        except Exception as exc:  # noqa: BLE001 - surfaced to the model, not swallowed
            return ToolResult(
                tool_call_id=tool_call_id,
                name=name,
                content=f"{type(exc).__name__}: {exc}",
                is_error=True,
            )
        return ToolResult(
            tool_call_id=tool_call_id,
            name=name,
            content=str(output),
            is_error=False,
        )
