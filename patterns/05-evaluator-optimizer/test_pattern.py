"""Tests for the Evaluator-Optimizer pattern.

These tests are self-contained: they use scripted MockClient planners rather
than the live demo, and load ``pattern.py`` by path via ``load_pattern_module``
so multiple pattern modules can coexist in the same test session without name
collisions.
"""

from __future__ import annotations

import pytest

from shared.errors import AgentError
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

eo = load_pattern_module("05-evaluator-optimizer")


def _usage(n: int = 1) -> Usage:
    return Usage(input_tokens=10 * n, output_tokens=5 * n)


# ---------------------------------------------------------------------------
# Test 1: passes on first evaluation (no revisions needed)
# ---------------------------------------------------------------------------


def test_passes_on_first_evaluation() -> None:
    """When the evaluator returns PASS immediately, iterations=1 and passed=True."""

    def gen_planner(messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text="Apex Pro: The Future is Here — Launch Today!", usage=_usage())

    def eval_planner(messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text="PASS", usage=_usage())

    result = eo.run_evaluator_optimizer(
        task="Write a product launch subject line for Apex Pro.",
        criteria=[
            eo.Criterion(description="Under 10 words"),
            eo.Criterion(description="Contains 'Apex'"),
        ],
        generator=MockClient(gen_planner),
        evaluator=MockClient(eval_planner),
        max_iterations=3,
    )

    assert result.passed is True
    assert result.iterations == 1
    assert "Apex" in result.output

    # Trace must have: 1 reasoning (initial draft) + 1 critique + 1 answer
    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("reasoning") == 1
    assert kinds.count("critique") == 1
    assert kinds.count("revision") == 0
    assert kinds[-1] == "answer"
    assert result.trace.succeeded


# ---------------------------------------------------------------------------
# Test 2: fails first eval, passes on second (one revision)
# ---------------------------------------------------------------------------


def test_fails_first_passes_second() -> None:
    """Evaluator fails the first draft and passes the revision; iterations=2."""
    eval_call_count = 0

    def gen_planner(messages: list[Message], _tools: object) -> LLMResponse:
        # Both initial and revised drafts are fine from the generator's side.
        return LLMResponse(text="Introducing Apex Pro — Act Now!", usage=_usage())

    def eval_planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal eval_call_count
        eval_call_count += 1
        if eval_call_count == 1:
            return LLMResponse(text="FAIL: too long, exceeds 10 words", usage=_usage())
        return LLMResponse(text="PASS", usage=_usage())

    result = eo.run_evaluator_optimizer(
        task="Write a short product launch subject line.",
        criteria=[eo.Criterion(description="Under 10 words")],
        generator=MockClient(gen_planner),
        evaluator=MockClient(eval_planner),
        max_iterations=3,
    )

    assert result.passed is True
    assert result.iterations == 2

    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("critique") == 2
    assert kinds.count("revision") == 1
    # The revision step summary should mention iteration number.
    revision_steps = [s for s in result.trace.steps if s.kind == "revision"]
    assert "iteration 1" in revision_steps[0].summary


# ---------------------------------------------------------------------------
# Test 3: never passes — reaches max_iterations
# ---------------------------------------------------------------------------


def test_never_passes_reaches_max_iterations() -> None:
    """If the evaluator always returns FAIL, passed=False and we get the last draft."""
    gen_call_count = 0

    def gen_planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal gen_call_count
        gen_call_count += 1
        return LLMResponse(text=f"draft-{gen_call_count}", usage=_usage())

    def eval_planner(messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text="FAIL: still not good enough", usage=_usage())

    max_iter = 2
    result = eo.run_evaluator_optimizer(
        task="Write something.",
        criteria=[eo.Criterion(description="Must be perfect")],
        generator=MockClient(gen_planner),
        evaluator=MockClient(eval_planner),
        max_iterations=max_iter,
    )

    assert result.passed is False
    assert result.iterations == max_iter
    # Output should be the last generated draft.
    assert result.output == f"draft-{gen_call_count}"

    kinds = [s.kind for s in result.trace.steps]
    # max_iter evaluations and max_iter revisions (no PASS was ever returned).
    assert kinds.count("critique") == max_iter
    assert kinds.count("revision") == max_iter
    assert kinds[-1] == "answer"


# ---------------------------------------------------------------------------
# Test 4: empty criteria raises AgentError
# ---------------------------------------------------------------------------


def test_empty_criteria_raises_agent_error() -> None:
    """Passing an empty criteria list raises AgentError immediately."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text="should not be called", usage=_usage())

    client = MockClient(planner)

    with pytest.raises(AgentError, match="at least one criterion required"):
        eo.run_evaluator_optimizer(
            task="anything",
            criteria=[],
            generator=client,
            evaluator=client,
        )
