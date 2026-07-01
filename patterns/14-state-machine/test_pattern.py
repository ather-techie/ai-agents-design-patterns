"""Tests for the State Machine pattern.

Self-contained: builds its own states and scripted mock planners; loads
``pattern.py`` by path via ``load_pattern_module`` so multiple patterns can
coexist in the same test process.
"""

from __future__ import annotations

import pytest

from shared.errors import MaxStepsExceeded
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

sm = load_pattern_module("14-state-machine")


def _usage() -> Usage:
    return Usage(input_tokens=20, output_tokens=5)


def _make_states() -> list:
    """Three-state FSM: triage -> diagnose -> resolve (terminal)."""

    def triage(input: str, ctx: str) -> str:
        return "triaged"

    def diagnose(input: str, ctx: str) -> str:
        return "diagnosed"

    def resolve(input: str, ctx: str) -> str:
        return "resolved"

    return [
        sm.State(
            name="triage",
            description="Assess the ticket.",
            handler=triage,
            transitions=["diagnose"],
            terminal=False,
        ),
        sm.State(
            name="diagnose",
            description="Find root cause.",
            handler=diagnose,
            transitions=["resolve"],
            terminal=False,
        ),
        sm.State(
            name="resolve",
            description="Fix the issue.",
            handler=resolve,
            transitions=[],
            terminal=True,
        ),
    ]


def _sequential_planner() -> MockClient:
    """Planner that returns the first bullet-point transition listed in the prompt.

    The prompt uses lines like ``- diagnose`` for each transition; we look for
    lines that start with ``- `` and return the first such name.
    """

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        content = messages[-1].content if messages else ""
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                return LLMResponse(
                    text=stripped[2:].strip(),
                    stop_reason="end_turn",
                    usage=_usage(),
                )
        return LLMResponse(text="resolve", stop_reason="end_turn", usage=_usage())

    return MockClient(planner)


def test_reaches_terminal_state_and_returns_answer() -> None:
    """The FSM should reach the terminal state and return its handler output."""
    result = sm.run_state_machine(
        "test input",
        _make_states(),
        _sequential_planner(),
        initial_state="triage",
        max_transitions=10,
    )
    assert result.answer == "resolved"
    assert result.trace.succeeded


def test_states_visited_order() -> None:
    """states_visited should record each state name in the order visited."""
    result = sm.run_state_machine(
        "test input",
        _make_states(),
        _sequential_planner(),
        initial_state="triage",
        max_transitions=10,
    )
    assert result.states_visited == ["triage", "diagnose", "resolve"]


def test_unknown_initial_state_raises() -> None:
    """Passing a non-existent initial_state should raise StateError immediately."""
    with pytest.raises(sm.StateError):
        sm.run_state_machine(
            "test input",
            _make_states(),
            _sequential_planner(),
            initial_state="nonexistent",
            max_transitions=10,
        )


def test_invalid_transition_name_raises() -> None:
    """LLM returning a name not in the transition list should raise StateError."""

    def bad_planner(messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text="totally_made_up_state", stop_reason="end_turn", usage=_usage())

    result_client = MockClient(bad_planner)
    with pytest.raises(sm.StateError):
        sm.run_state_machine(
            "test input",
            _make_states(),
            result_client,
            initial_state="triage",
            max_transitions=10,
        )


def test_max_transitions_exceeded() -> None:
    """A non-terminal FSM that never stops should raise MaxStepsExceeded."""

    def loop_handler(input: str, ctx: str) -> str:
        return "looping"

    looping_states = [
        sm.State(
            name="a",
            description="Goes to b.",
            handler=loop_handler,
            transitions=["b"],
            terminal=False,
        ),
        sm.State(
            name="b",
            description="Goes to a.",
            handler=loop_handler,
            transitions=["a"],
            terminal=False,
        ),
    ]

    call_count = {"n": 0}

    def looping_planner(messages: list[Message], _tools: object) -> LLMResponse:
        call_count["n"] += 1
        # Alternate between "b" and "a"
        return LLMResponse(
            text="b" if call_count["n"] % 2 == 1 else "a",
            stop_reason="end_turn",
            usage=_usage(),
        )

    with pytest.raises(MaxStepsExceeded):
        sm.run_state_machine(
            "loop",
            looping_states,
            MockClient(looping_planner),
            initial_state="a",
            max_transitions=4,
        )
