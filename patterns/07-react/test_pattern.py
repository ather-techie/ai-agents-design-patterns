"""Tests for the ReAct pattern.

These are self-contained: they build their own tiny tool registry and scripted
mock planner rather than importing the demo, and load ``pattern.py`` by path so
the suite can hold both patterns' identically-named modules at once.
"""

from __future__ import annotations

import pytest

from shared.errors import MaxStepsExceeded, ToolValidationError
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.tools import Tool, ToolRegistry
from shared.types import LLMResponse, Message, ToolCall, Usage

react = load_pattern_module("07-react")


def _echo_tool() -> Tool:
    return Tool(
        name="echo",
        description="Echo a value back.",
        input_schema={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        handler=lambda value: f"echoed:{value}",
    )


def _registry() -> ToolRegistry:
    return ToolRegistry([_echo_tool()])


def _usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5)


def test_completes_and_records_trace() -> None:
    """One tool round-trip, then a final answer, fully traced."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        if any(m.role == "tool" for m in messages):
            return LLMResponse(text="done: hi", stop_reason="end_turn", usage=_usage())
        return LLMResponse(
            text="let me echo",
            tool_calls=[ToolCall(id="t1", name="echo", arguments={"value": "hi"})],
            stop_reason="tool_use",
            usage=_usage(),
        )

    result = react.run_react("say hi", _registry(), MockClient(planner), max_steps=4)

    assert result.answer == "done: hi"
    kinds = [s.kind for s in result.trace.steps]
    assert "tool_call" in kinds and "observation" in kinds and "answer" in kinds
    assert result.trace.succeeded
    assert result.trace.usage.total_tokens == 30  # two LLM calls accounted for


def test_max_steps_exceeded() -> None:
    """A planner that never stops calling tools hits the step bound."""

    def planner(_messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(
            text="again",
            tool_calls=[ToolCall(id="t", name="echo", arguments={"value": "x"})],
            stop_reason="tool_use",
            usage=_usage(),
        )

    with pytest.raises(MaxStepsExceeded):
        react.run_react("loop", _registry(), MockClient(planner), max_steps=3)


def test_invalid_tool_arguments_raise() -> None:
    """Missing a required argument surfaces as a validation error."""

    def planner(_messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(
            tool_calls=[ToolCall(id="t", name="echo", arguments={})],
            stop_reason="tool_use",
            usage=_usage(),
        )

    with pytest.raises(ToolValidationError):
        react.run_react("bad", _registry(), MockClient(planner), max_steps=3)


def test_handler_error_becomes_observation() -> None:
    """A tool that raises is reported back as an error observation, not a crash."""

    def boom(value: str) -> str:
        raise RuntimeError("kaboom")

    registry = ToolRegistry(
        [
            Tool(
                name="echo",
                description="raises",
                input_schema={
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                },
                handler=boom,
            )
        ]
    )

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        if any(m.role == "tool" for m in messages):
            return LLMResponse(text="recovered", stop_reason="end_turn", usage=_usage())
        return LLMResponse(
            tool_calls=[ToolCall(id="t", name="echo", arguments={"value": "x"})],
            stop_reason="tool_use",
            usage=_usage(),
        )

    result = react.run_react("err", registry, MockClient(planner), max_steps=4)

    observations = [s for s in result.trace.steps if s.kind == "observation"]
    assert observations and observations[0].is_error
    assert result.answer == "recovered"
