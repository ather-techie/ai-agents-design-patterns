"""Tests for the Memory-Augmented Agent pattern.

Self-contained: builds its own MemoryStore, ToolRegistry, and scripted mock
planner rather than importing the demo. Loads ``pattern.py`` by path via
``load_pattern_module`` so the module name doesn't collide with other patterns.
"""

from __future__ import annotations

import pytest

from shared.errors import MaxStepsExceeded
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.tools import ToolRegistry
from shared.types import LLMResponse, Message, ToolCall, Usage

memory = load_pattern_module("11-memory")


def _usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5)


def _fresh_registry() -> ToolRegistry:
    """Return an empty registry — memory tools are registered by the agent."""
    return ToolRegistry()


def test_remember_recall_roundtrip() -> None:
    """remember followed by recall returns the stored content."""

    call_count = [0]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        n = call_count[0]
        call_count[0] += 1
        if n == 0:
            return LLMResponse(
                tool_calls=[ToolCall(id="c1", name="remember", arguments={"key": "city", "content": "London"})],
                stop_reason="tool_use",
                usage=_usage(),
            )
        if n == 1:
            return LLMResponse(
                tool_calls=[ToolCall(id="c2", name="recall", arguments={"query": "city"})],
                stop_reason="tool_use",
                usage=_usage(),
            )
        return LLMResponse(text="The city is London.", stop_reason="end_turn", usage=_usage())

    store = memory.MemoryStore()
    result = memory.run_memory_agent(
        "what city?", _fresh_registry(), MockClient(planner), store, max_steps=8
    )

    assert result.answer == "The city is London."
    assert result.store._entries.get("city") == "London"
    recall_steps = [s for s in result.trace.steps if s.kind == "memory" and "recall" in s.summary]
    assert any("London" in s.summary for s in recall_steps)


def test_forget_removes_entry() -> None:
    """After forget, recall no longer finds the removed key."""

    call_count = [0]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        n = call_count[0]
        call_count[0] += 1
        if n == 0:
            return LLMResponse(
                tool_calls=[ToolCall(id="c1", name="remember", arguments={"key": "temp", "content": "temporary"})],
                stop_reason="tool_use",
                usage=_usage(),
            )
        if n == 1:
            return LLMResponse(
                tool_calls=[ToolCall(id="c2", name="forget", arguments={"key": "temp"})],
                stop_reason="tool_use",
                usage=_usage(),
            )
        if n == 2:
            return LLMResponse(
                tool_calls=[ToolCall(id="c3", name="recall", arguments={"query": "temp"})],
                stop_reason="tool_use",
                usage=_usage(),
            )
        return LLMResponse(text="Nothing found.", stop_reason="end_turn", usage=_usage())

    store = memory.MemoryStore()
    result = memory.run_memory_agent(
        "forget temp then recall", _fresh_registry(), MockClient(planner), store, max_steps=8
    )

    assert "temp" not in result.store._entries
    recall_steps = [s for s in result.trace.steps if s.kind == "memory" and "recall" in s.summary]
    assert any("No matching" in s.summary for s in recall_steps)


def test_max_steps_exceeded() -> None:
    """A planner that never stops calling tools hits the step bound."""

    def planner(_messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(
            tool_calls=[ToolCall(id="t", name="remember", arguments={"key": "k", "content": "v"})],
            stop_reason="tool_use",
            usage=_usage(),
        )

    store = memory.MemoryStore()
    with pytest.raises(MaxStepsExceeded):
        memory.run_memory_agent(
            "loop", _fresh_registry(), MockClient(planner), store, max_steps=3
        )


def test_memory_steps_have_memory_kind() -> None:
    """Tool calls to remember/recall/forget are recorded with kind=='memory'."""

    call_count = [0]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        n = call_count[0]
        call_count[0] += 1
        if n == 0:
            return LLMResponse(
                tool_calls=[ToolCall(id="c1", name="remember", arguments={"key": "x", "content": "42"})],
                stop_reason="tool_use",
                usage=_usage(),
            )
        return LLMResponse(text="done", stop_reason="end_turn", usage=_usage())

    store = memory.MemoryStore()
    result = memory.run_memory_agent(
        "store x", _fresh_registry(), MockClient(planner), store, max_steps=4
    )

    memory_steps = [s for s in result.trace.steps if s.kind == "memory"]
    assert len(memory_steps) >= 1
    observation_steps = [s for s in result.trace.steps if s.kind == "observation"]
    # No regular observation steps — only memory steps for these tool calls
    assert len(observation_steps) == 0
