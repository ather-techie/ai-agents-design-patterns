"""Tests for the Event-Driven pattern.

Self-contained: builds scripted mock planners and loads ``pattern.py`` by path
via ``load_pattern_module``.
"""

from __future__ import annotations

import pytest

from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.tools import ToolRegistry
from shared.types import LLMResponse, Message, ToolCall, Usage

ev = load_pattern_module("19-event-driven")


# --- Helpers ----------------------------------------------------------------


def _usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5)


def _registry() -> ToolRegistry:
    return ToolRegistry()


# --- Tests ------------------------------------------------------------------


def test_state_persists_across_events() -> None:
    """A value set in event 1 is visible in the prompt for event 2."""

    prompts_seen: list[str] = []
    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        user_content = next((m.content for m in messages if m.role == "user"), "")
        prompts_seen.append(user_content)

        tool_results = sum(1 for m in messages if m.role == "tool")

        if "first" in user_content and tool_results == 0:
            return LLMResponse(
                text="Setting status.",
                tool_calls=[ToolCall(id="s1", name="state_set", arguments={"key": "status", "value": "active"})],
                stop_reason="tool_use",
                usage=_usage(),
            )
        if "first" in user_content:
            return LLMResponse(text="Done.", stop_reason="end_turn", usage=_usage())
        if "second" in user_content:
            return LLMResponse(text="Seen state.", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="Summary done.", stop_reason="end_turn", usage=_usage())

    events = [
        ev.Event(type="step", payload="first event"),
        ev.Event(type="step", payload="second event"),
    ]
    state = ev.AgentState()
    result = ev.run_event_driven(events, _registry(), MockClient(planner), state=state)

    # The second event's prompt should include the state set in event 1.
    second_event_prompts = [p for p in prompts_seen if "second" in p]
    assert any("status" in p for p in second_event_prompts)
    assert result.state.data.get("status") == "active"


def test_each_event_creates_event_step() -> None:
    """One 'event' trace step is recorded per event in the input list."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        call_count["n"] += 1
        user_content = next((m.content for m in messages if m.role == "user"), "")
        if "Summarize" in user_content:
            return LLMResponse(text="Summary.", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="Done.", stop_reason="end_turn", usage=_usage())

    events = [
        ev.Event(type="alpha", payload="first"),
        ev.Event(type="beta", payload="second"),
        ev.Event(type="gamma", payload="third"),
    ]
    result = ev.run_event_driven(events, _registry(), MockClient(planner))

    event_steps = [s for s in result.trace.steps if s.kind == "event"]
    assert len(event_steps) == 3


def test_max_steps_per_event_enforced() -> None:
    """A tool-calling loop that never stops is cut off at max_steps_per_event."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        user_content = next((m.content for m in messages if m.role == "user"), "")
        if "Summarize" in user_content:
            return LLMResponse(text="Summary.", stop_reason="end_turn", usage=_usage())
        # Always request another state_set — never ends naturally.
        return LLMResponse(
            text="Keep going.",
            tool_calls=[ToolCall(id="sx", name="state_set", arguments={"key": "k", "value": "v"})],
            stop_reason="tool_use",
            usage=_usage(),
        )

    events = [ev.Event(type="loop", payload="looping event")]
    max_steps = 3
    result = ev.run_event_driven(
        events, _registry(), MockClient(planner), max_steps_per_event=max_steps
    )

    # The loop must have stopped; tool_call steps should not exceed max_steps.
    tool_call_steps = [s for s in result.trace.steps if s.kind == "tool_call"]
    assert len(tool_call_steps) <= max_steps


def test_empty_events_returns_no_events_processed() -> None:
    """An empty event list returns EventResult with events_processed=0."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text="Summary.", stop_reason="end_turn", usage=_usage())

    result = ev.run_event_driven([], _registry(), MockClient(planner))

    assert result.events_processed == 0
    assert "No events processed" in result.final_summary
    assert result.trace.succeeded


def test_state_set_tool_updates_state_data() -> None:
    """Calling state_set from the event loop writes into state.data."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        user_content = next((m.content for m in messages if m.role == "user"), "")
        tool_results = sum(1 for m in messages if m.role == "tool")
        if "Summarize" in user_content:
            return LLMResponse(text="All done.", stop_reason="end_turn", usage=_usage())
        if tool_results == 0:
            return LLMResponse(
                text="Setting value.",
                tool_calls=[
                    ToolCall(id="t1", name="state_set", arguments={"key": "foo", "value": "bar"})
                ],
                stop_reason="tool_use",
                usage=_usage(),
            )
        return LLMResponse(text="Done.", stop_reason="end_turn", usage=_usage())

    state = ev.AgentState()
    events = [ev.Event(type="test", payload="set foo to bar")]
    ev.run_event_driven(events, _registry(), MockClient(planner), state=state)

    assert state.data.get("foo") == "bar"
