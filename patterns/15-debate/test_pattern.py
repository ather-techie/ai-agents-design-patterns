"""Tests for the Debate pattern.

Self-contained: uses scripted mock planners and loads ``pattern.py`` by path via
``load_pattern_module`` so multiple patterns can coexist in the same test process.
"""

from __future__ import annotations

import pytest

from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

debate = load_pattern_module("15-debate")


def _usage() -> Usage:
    return Usage(input_tokens=40, output_tokens=20)


_SCRIPTED_RESPONSES = [
    "Python has a mature ecosystem for backend development.",
    "JavaScript/Node.js offers a unified stack for full-stack teams.",
    "Python's async support via FastAPI rivals Node.js for concurrency.",
    "JavaScript's event loop model is architecturally superior.",
    "Both are excellent; the choice depends on team expertise and workload.",
]


def _make_planner(responses: list[str]) -> MockClient:
    """Return a MockClient that serves responses in order."""
    call_index = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_index["n"] % len(responses)
        call_index["n"] += 1
        return LLMResponse(text=responses[idx], stop_reason="end_turn", usage=_usage())

    return MockClient(planner)


def test_rounds2_records_five_steps() -> None:
    """rounds=2 should produce 2 delegate + 2 critique + 1 answer steps."""
    client = _make_planner(_SCRIPTED_RESPONSES)
    result = debate.run_debate(
        "Python is better than JavaScript for backend development.",
        client,
        rounds=2,
    )
    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("delegate") == 2
    assert kinds.count("critique") == 2
    assert kinds.count("answer") == 1
    assert len(result.trace.steps) == 5


def test_rounds1_records_three_steps_and_empty_rebuttals() -> None:
    """rounds=1 should produce 2 delegate + 1 answer, with empty rebuttal fields."""
    client = _make_planner(_SCRIPTED_RESPONSES)
    result = debate.run_debate(
        "Python is better than JavaScript for backend development.",
        client,
        rounds=1,
    )
    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("delegate") == 2
    assert kinds.count("critique") == 0
    assert kinds.count("answer") == 1
    assert len(result.trace.steps) == 3
    assert result.rebuttal_aff == ""
    assert result.rebuttal_neg == ""


def test_verdict_is_non_empty() -> None:
    """The judge's verdict should always be a non-empty string."""
    client = _make_planner(_SCRIPTED_RESPONSES)
    result = debate.run_debate("Python is better than JavaScript.", client, rounds=2)
    assert result.verdict.strip() != ""


def test_trace_succeeded() -> None:
    """trace.succeeded should be True after a complete debate."""
    client = _make_planner(_SCRIPTED_RESPONSES)
    result = debate.run_debate("Python is better than JavaScript.", client, rounds=2)
    assert result.trace.succeeded
