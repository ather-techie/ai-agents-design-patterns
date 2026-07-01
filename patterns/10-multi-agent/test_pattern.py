"""Tests for the Multi-Agent pattern.

Self-contained: separate MockClient instances for the supervisor and each
agent, scripted planners, and ``pattern.py`` loaded by path so it coexists
with other pattern modules of the same name.
"""

from __future__ import annotations

import json

import pytest

from shared.errors import AgentError
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

ma = load_pattern_module("10-multi-agent")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_supervisor_planner(
    selected: list[str],
    synthesis: str = "Final synthesized answer.",
) -> object:
    """Return a planner that emits a JSON routing decision, then synthesis text."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        last = messages[-1].content
        if "Synthesize" in last:
            return LLMResponse(text=synthesis, usage=Usage(input_tokens=50, output_tokens=20))
        routing_json = json.dumps({"selected": selected})
        return LLMResponse(text=routing_json, usage=Usage(input_tokens=40, output_tokens=15))

    return planner


def _agent_planner(response_text: str):
    """Return a planner that always replies with a fixed string."""

    def planner(_messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text=response_text, usage=Usage(input_tokens=30, output_tokens=10))

    return planner


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_full_run_returns_expected_fields() -> None:
    """Supervisor selects agents, each produces output, synthesis is returned."""
    Agent = ma.Agent

    supervisor = MockClient(
        _make_supervisor_planner(
            ["researcher", "writer"],
            synthesis="AI will revolutionize healthcare through personalized medicine.",
        )
    )
    agents = [
        Agent(
            "researcher",
            "You are a medical AI researcher. Provide key facts about AI in healthcare.",
            MockClient(_agent_planner("AI improves diagnostic accuracy by 20%.")),
        ),
        Agent(
            "writer",
            "You are a content writer. Create a structured blog outline.",
            MockClient(_agent_planner("Outline: 1. Intro 2. Key trends 3. Challenges 4. Future")),
        ),
    ]

    result = ma.run_multi_agent(
        "Write a blog post outline about AI in healthcare", agents, supervisor
    )

    assert result.answer == "AI will revolutionize healthcare through personalized medicine."
    assert result.selected_agents == ["researcher", "writer"]
    assert result.agent_outputs["researcher"] == "AI improves diagnostic accuracy by 20%."
    assert result.agent_outputs["writer"] == "Outline: 1. Intro 2. Key trends 3. Challenges 4. Future"
    assert result.trace.succeeded


def test_trace_contains_expected_step_kinds() -> None:
    """Trace must have plan, delegate (x2), worker (x2), and answer steps."""
    Agent = ma.Agent

    supervisor = MockClient(_make_supervisor_planner(["alpha", "beta"]))
    agents = [
        Agent("alpha", "You are agent alpha.", MockClient(_agent_planner("Alpha output"))),
        Agent("beta", "You are agent beta.", MockClient(_agent_planner("Beta output"))),
    ]

    result = ma.run_multi_agent("some complex task", agents, supervisor)

    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("plan") == 1
    assert kinds.count("delegate") == 2
    assert kinds.count("worker") == 2
    assert kinds.count("answer") == 1


def test_empty_agents_raises_agent_error() -> None:
    """Passing an empty agents list must raise AgentError immediately."""
    supervisor = MockClient(_make_supervisor_planner([]))
    with pytest.raises(AgentError, match="at least one agent required"):
        ma.run_multi_agent("any task", [], supervisor)


def test_unknown_agent_name_is_error_step_not_crash() -> None:
    """An unknown agent name in the selection is recorded as an error step, not a crash."""
    Agent = ma.Agent

    supervisor = MockClient(
        _make_supervisor_planner(["known", "ghost"])
    )
    agents = [
        Agent(
            "known",
            "You are the known agent.",
            MockClient(_agent_planner("Known agent output")),
        ),
    ]

    result = ma.run_multi_agent("test unknown agent", agents, supervisor)

    # The run must not crash; the known agent must still produce a result.
    assert "known" in result.agent_outputs
    assert "ghost" not in result.agent_outputs

    # There must be an error observation step for the unknown agent.
    error_steps = [s for s in result.trace.steps if s.is_error]
    assert len(error_steps) == 1
    assert "ghost" in error_steps[0].summary
