"""Provider-agnostic data structures shared by every pattern.

These dataclasses are the lingua franca between a pattern (ReAct, Routing, ...),
the LLM client, and the tool registry. Keeping them provider-neutral is what lets
the same pattern code run against the live Anthropic client or the offline mock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["user", "assistant", "tool"]


@dataclass
class ToolCall:
    """A model's request to invoke a tool with structured arguments."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    """A single turn in a conversation.

    For ``role == "tool"`` the ``content`` holds a tool result and
    ``tool_call_id`` links it back to the ``ToolCall`` that produced it. For an
    assistant turn that requested tools, ``tool_calls`` carries those requests so
    the live API sees the ``tool_use`` blocks its ``tool_result`` blocks refer to.
    """

    role: Role
    content: str
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list["ToolCall"] = field(default_factory=list)


@dataclass
class ToolResult:
    """The outcome of executing a :class:`ToolCall`."""

    tool_call_id: str
    name: str
    content: str
    is_error: bool = False


@dataclass
class Usage:
    """Token accounting for one or more LLM calls."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


@dataclass
class LLMResponse:
    """A normalized response from any :class:`~shared.llm_client.LLMClient`.

    ``text`` is the assistant's prose (may be empty when the model only emits
    tool calls). ``tool_calls`` is the list of requested tool invocations.
    ``stop_reason`` mirrors the Anthropic semantics: ``"end_turn"`` when the
    model is done, ``"tool_use"`` when it wants tools executed.
    """

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: Literal["end_turn", "tool_use", "max_tokens"] = "end_turn"
    usage: Usage = field(default_factory=Usage)

    @property
    def wants_tools(self) -> bool:
        return self.stop_reason == "tool_use" and bool(self.tool_calls)
