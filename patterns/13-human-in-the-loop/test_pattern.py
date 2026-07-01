"""Tests for the Human-in-the-Loop pattern.

Self-contained: builds its own tool registry, mock planner, and MockHumanIO.
Loads ``pattern.py`` by path via ``load_pattern_module`` so the module name
doesn't collide with other patterns.
"""

from __future__ import annotations

import pytest

from shared.errors import MaxStepsExceeded
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.tools import Tool, ToolRegistry
from shared.types import LLMResponse, Message, ToolCall, Usage

hitl = load_pattern_module("13-human-in-the-loop")


def _usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5)


def _echo_tool(name: str = "echo") -> Tool:
    return Tool(
        name=name,
        description=f"Echo a value ({name}).",
        input_schema={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        handler=lambda value: f"echoed:{value}",
    )


def _registry(*names: str) -> ToolRegistry:
    return ToolRegistry([_echo_tool(n) for n in (names or ("echo",))])


def test_checkpoint_tool_triggers_human_input_step() -> None:
    """A checkpointed tool call produces a human_input trace step."""

    call_count = [0]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        n = call_count[0]
        call_count[0] += 1
        if n == 0:
            return LLMResponse(
                tool_calls=[ToolCall(id="t1", name="echo", arguments={"value": "hi"})],
                stop_reason="tool_use",
                usage=_usage(),
            )
        return LLMResponse(text="done", stop_reason="end_turn", usage=_usage())

    human_io = hitl.MockHumanIO(responses=["yes"])
    result = hitl.run_human_in_loop(
        "task",
        _registry(),
        MockClient(planner),
        human_io,
        checkpoints={"echo"},
        max_steps=4,
    )

    human_steps = [s for s in result.trace.steps if s.kind == "human_input"]
    assert len(human_steps) == 1
    assert "human: yes" in human_steps[0].summary


def test_human_no_raises_human_aborted() -> None:
    """A human response of 'no' raises HumanAborted."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        if any(m.role == "tool" for m in messages):
            return LLMResponse(text="done", stop_reason="end_turn", usage=_usage())
        return LLMResponse(
            tool_calls=[ToolCall(id="t1", name="echo", arguments={"value": "danger"})],
            stop_reason="tool_use",
            usage=_usage(),
        )

    human_io = hitl.MockHumanIO(responses=["no"])
    with pytest.raises(hitl.HumanAborted):
        hitl.run_human_in_loop(
            "task",
            _registry(),
            MockClient(planner),
            human_io,
            checkpoints={"echo"},
            max_steps=4,
        )


def test_non_checkpoint_tool_skips_human() -> None:
    """A tool not in checkpoints executes without any human_input step."""

    call_count = [0]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        n = call_count[0]
        call_count[0] += 1
        if n == 0:
            return LLMResponse(
                tool_calls=[ToolCall(id="t1", name="safe", arguments={"value": "x"})],
                stop_reason="tool_use",
                usage=_usage(),
            )
        return LLMResponse(text="done", stop_reason="end_turn", usage=_usage())

    human_io = hitl.MockHumanIO(responses=["yes"])
    result = hitl.run_human_in_loop(
        "task",
        _registry("safe"),
        MockClient(planner),
        human_io,
        checkpoints={"other_tool"},  # "safe" is NOT a checkpoint
        max_steps=4,
    )

    human_steps = [s for s in result.trace.steps if s.kind == "human_input"]
    assert len(human_steps) == 0
    assert result.human_turns == 0


def test_human_turns_count_matches_approval_count() -> None:
    """human_turns equals the number of times human_io.request was called."""

    call_count = [0]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        n = call_count[0]
        call_count[0] += 1
        tool_results = sum(1 for m in messages if m.role == "tool")
        if tool_results < 2:
            return LLMResponse(
                tool_calls=[ToolCall(id=f"t{n}", name="echo", arguments={"value": str(n)})],
                stop_reason="tool_use",
                usage=_usage(),
            )
        return LLMResponse(text="done", stop_reason="end_turn", usage=_usage())

    human_io = hitl.MockHumanIO(responses=["yes"])
    result = hitl.run_human_in_loop(
        "task",
        _registry(),
        MockClient(planner),
        human_io,
        checkpoints={"echo"},
        max_steps=6,
    )

    assert result.human_turns == 2


def test_max_steps_exceeded() -> None:
    """A planner that never stops calling tools hits the step bound."""

    def planner(_messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(
            tool_calls=[ToolCall(id="t", name="echo", arguments={"value": "x"})],
            stop_reason="tool_use",
            usage=_usage(),
        )

    human_io = hitl.MockHumanIO(responses=["yes"])
    with pytest.raises(MaxStepsExceeded):
        hitl.run_human_in_loop(
            "loop",
            _registry(),
            MockClient(planner),
            human_io,
            checkpoints=set(),
            max_steps=3,
        )
