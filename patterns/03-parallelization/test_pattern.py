"""Tests for the parallelization pattern.

These are self-contained: each test builds its own mock planner and loads
``pattern.py`` by path so the suite can hold multiple patterns' identically-
named modules at once.
"""

from __future__ import annotations

import pytest

from shared.errors import AgentError
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

para = load_pattern_module("03-parallelization")


def _usage(inp: int = 10, out: int = 5) -> Usage:
    return Usage(input_tokens=inp, output_tokens=out)


def _fixed_planner(text: str = "branch-answer") -> object:
    """Return a planner that always replies with ``text``."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text=text, usage=_usage())

    return planner


# ---------------------------------------------------------------------------
# Test 1 — all branches run and answers + aggregate are returned
# ---------------------------------------------------------------------------


def test_all_branches_run_and_aggregate_returned() -> None:
    """Each branch produces an entry in answers; aggregate is non-empty."""
    branches = [
        para.Branch(name="alpha", system_prompt="You are alpha."),
        para.Branch(name="beta", system_prompt="You are beta."),
        para.Branch(name="gamma", system_prompt="You are gamma."),
    ]
    client = MockClient(_fixed_planner("my answer"))

    result = para.run_parallelization("test task", branches, client)

    assert set(result.answers.keys()) == {"alpha", "beta", "gamma"}
    for name, text in result.answers.items():
        assert text == "my answer", f"branch {name!r} had unexpected text"
    assert result.aggregate  # non-empty string
    assert isinstance(result.aggregate, str)


# ---------------------------------------------------------------------------
# Test 2 — trace contains a "worker" step per branch and a "reasoning" step
# ---------------------------------------------------------------------------


def test_trace_has_worker_and_reasoning_steps() -> None:
    """Trace records one worker step per branch and one reasoning step."""
    branches = [
        para.Branch(name="x", system_prompt="Prompt X"),
        para.Branch(name="y", system_prompt="Prompt Y"),
    ]
    client = MockClient(_fixed_planner())

    result = para.run_parallelization("trace check", branches, client)

    kinds = [s.kind for s in result.trace.steps]
    worker_steps = [s for s in result.trace.steps if s.kind == "worker"]
    reasoning_steps = [s for s in result.trace.steps if s.kind == "reasoning"]
    answer_steps = [s for s in result.trace.steps if s.kind == "answer"]

    assert len(worker_steps) == 2, f"expected 2 worker steps, got {len(worker_steps)}"
    assert len(reasoning_steps) == 1, f"expected 1 reasoning step, got {len(reasoning_steps)}"
    assert len(answer_steps) == 1, f"expected 1 answer step, got {len(answer_steps)}"
    assert "answer" in kinds
    assert result.trace.succeeded


# ---------------------------------------------------------------------------
# Test 3 — empty branches list raises AgentError
# ---------------------------------------------------------------------------


def test_empty_branches_raises_agent_error() -> None:
    """Passing no branches raises AgentError immediately."""
    client = MockClient(_fixed_planner())

    with pytest.raises(AgentError, match="at least one branch"):
        para.run_parallelization("anything", [], client)


# ---------------------------------------------------------------------------
# Test 4 — usage is accumulated across all calls (N branches + 1 aggregation)
# ---------------------------------------------------------------------------


def test_usage_accumulated_across_all_calls() -> None:
    """Token usage sums over all branch calls plus the aggregation call."""
    branches = [
        para.Branch(name="a", system_prompt="A"),
        para.Branch(name="b", system_prompt="B"),
    ]
    # planner returns Usage(10, 5) = 15 tokens per call
    client = MockClient(_fixed_planner())

    result = para.run_parallelization("usage test", branches, client)

    # 2 branches + 1 aggregation = 3 calls, each 15 tokens => 45 total
    assert result.trace.usage.total_tokens == 45, (
        f"expected 45 total tokens, got {result.trace.usage.total_tokens}"
    )
