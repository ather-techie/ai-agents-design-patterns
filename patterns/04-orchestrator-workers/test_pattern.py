"""Tests for the Orchestrator-Workers pattern.

Self-contained: separate MockClient instances for the orchestrator and each
worker, scripted planners, and ``pattern.py`` loaded by path so it coexists
with other pattern modules of the same name.
"""

from __future__ import annotations

import json

import pytest

from shared.errors import AgentError
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

ow = load_pattern_module("04-orchestrator-workers")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_orchestrator_planner(
    assignments: list[dict],
    synthesis: str = "Final synthesized answer.",
) -> object:
    """Return a planner that emits a JSON plan, then a synthesis text."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        last = messages[-1].content
        if "Synthesize" in last:
            return LLMResponse(text=synthesis, usage=Usage(input_tokens=50, output_tokens=20))
        plan_json = json.dumps({"assignments": assignments})
        return LLMResponse(text=plan_json, usage=Usage(input_tokens=40, output_tokens=15))

    return planner


def _worker_planner(response_text: str):
    """Return a planner that always replies with a fixed string."""

    def planner(_messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text=response_text, usage=Usage(input_tokens=30, output_tokens=10))

    return planner


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_full_run_returns_expected_fields() -> None:
    """Orchestrator plans, workers execute, synthesis is returned."""
    Worker = ow.Worker
    assignments = [
        {"worker": "researcher", "subtask": "find key facts"},
        {"worker": "analyst", "subtask": "interpret implications"},
        {"worker": "writer", "subtask": "write a polished paragraph"},
    ]
    orchestrator = MockClient(
        _make_orchestrator_planner(assignments, synthesis="Great synthesis here.")
    )
    workers = [
        Worker("researcher", "finds facts", MockClient(_worker_planner("Fact: CO2 is rising."))),
        Worker("analyst", "interprets data", MockClient(_worker_planner("Implication: crops will suffer."))),
        Worker("writer", "writes prose", MockClient(_worker_planner("Climate change threatens food supply."))),
    ]

    result = ow.run_orchestrator_workers(
        "climate change impacts on agriculture", orchestrator, workers
    )

    assert result.synthesis == "Great synthesis here."
    assert result.worker_results["researcher"] == "Fact: CO2 is rising."
    assert result.worker_results["analyst"] == "Implication: crops will suffer."
    assert result.worker_results["writer"] == "Climate change threatens food supply."
    assert result.trace.succeeded


def test_trace_contains_expected_step_kinds() -> None:
    """Trace must have plan, delegate (x2), worker (x2), and answer steps."""
    Worker = ow.Worker
    assignments = [
        {"worker": "alpha", "subtask": "subtask A"},
        {"worker": "beta", "subtask": "subtask B"},
    ]
    orchestrator = MockClient(_make_orchestrator_planner(assignments))
    workers = [
        Worker("alpha", "does alpha things", MockClient(_worker_planner("Alpha result"))),
        Worker("beta", "does beta things", MockClient(_worker_planner("Beta result"))),
    ]

    result = ow.run_orchestrator_workers("some complex task", orchestrator, workers)

    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("plan") == 1
    assert kinds.count("delegate") == 2
    assert kinds.count("worker") == 2
    assert kinds.count("answer") == 1


def test_empty_workers_raises_agent_error() -> None:
    """Passing an empty workers list must raise AgentError immediately."""
    orchestrator = MockClient(_make_orchestrator_planner([]))
    with pytest.raises(AgentError, match="at least one worker required"):
        ow.run_orchestrator_workers("any task", orchestrator, [])


def test_unknown_worker_name_is_error_step_not_crash() -> None:
    """An unknown worker name in the plan is recorded as an error step, not a crash."""
    Worker = ow.Worker
    assignments = [
        {"worker": "known", "subtask": "real subtask"},
        {"worker": "ghost", "subtask": "this worker does not exist"},
    ]
    orchestrator = MockClient(_make_orchestrator_planner(assignments))
    workers = [
        Worker("known", "handles real subtasks", MockClient(_worker_planner("Known result"))),
    ]

    result = ow.run_orchestrator_workers("test unknown worker", orchestrator, workers)

    # The run must not crash; the known worker must still produce a result.
    assert "known" in result.worker_results
    assert "ghost" not in result.worker_results

    # There must be an error observation step for the unknown worker.
    error_steps = [s for s in result.trace.steps if s.is_error]
    assert len(error_steps) == 1
    assert "ghost" in error_steps[0].summary
