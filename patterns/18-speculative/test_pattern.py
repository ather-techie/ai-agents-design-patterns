"""Tests for the Speculative Execution pattern.

Self-contained: builds scripted mock planners and loads ``pattern.py`` by path
via ``load_pattern_module``.
"""

from __future__ import annotations

from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

spec = load_pattern_module("18-speculative")


# --- Helpers ----------------------------------------------------------------


def _usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5)


# --- Tests ------------------------------------------------------------------


def test_exactly_n_candidates_generated() -> None:
    """Exactly n_candidates candidate steps appear in the trace."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx < 3:
            return LLMResponse(text=f"Candidate {idx + 1} solution.", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text=f"SCORE: 7.0\nRATIONALE: ok", stop_reason="end_turn", usage=_usage())

    result = spec.run_speculative("Solve X", MockClient(planner), n_candidates=3)

    candidate_steps = [s for s in result.trace.steps if s.kind == "candidate"]
    assert len(candidate_steps) == 3
    assert len(result.candidates) == 3


def test_winner_has_highest_score() -> None:
    """The winner is the candidate with the highest score."""

    call_count = {"n": 0}
    scores = ["SCORE: 6.0\nRATIONALE: poor", "SCORE: 9.5\nRATIONALE: excellent", "SCORE: 7.5\nRATIONALE: good"]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx < 3:
            return LLMResponse(text=f"Candidate {idx + 1}.", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text=scores[idx - 3], stop_reason="end_turn", usage=_usage())

    result = spec.run_speculative("Problem", MockClient(planner), n_candidates=3)

    assert result.winner.score == 9.5
    assert result.winner.index == 1


def test_n_candidates_1_skips_scoring() -> None:
    """With n_candidates=1, no critique step is recorded and score is 10.0."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        call_count["n"] += 1
        return LLMResponse(text="Single solution.", stop_reason="end_turn", usage=_usage())

    result = spec.run_speculative("Task", MockClient(planner), n_candidates=1)

    assert result.winner.score == 10.0
    assert result.winner.rationale == "only candidate"
    assert result.winner.content == "Single solution."
    critique_steps = [s for s in result.trace.steps if s.kind == "critique"]
    assert len(critique_steps) == 0
    # Only 1 LLM call made (the candidate itself).
    assert call_count["n"] == 1


def test_trace_has_correct_step_count_for_n_gt_1() -> None:
    """Trace has 2*n + 1 steps: n candidate + n critique + 1 answer."""

    call_count = {"n": 0}
    n = 4

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx < n:
            return LLMResponse(text=f"Candidate {idx + 1}.", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="SCORE: 8.0\nRATIONALE: fine", stop_reason="end_turn", usage=_usage())

    result = spec.run_speculative("Task", MockClient(planner), n_candidates=n)

    assert result.trace.step_count == 2 * n + 1


def test_parse_error_in_score_defaults_to_zero() -> None:
    """A malformed score response gives the candidate a score of 0.0."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx < 2:
            return LLMResponse(text=f"Candidate {idx + 1}.", stop_reason="end_turn", usage=_usage())
        # First score is malformed, second is fine.
        if idx == 2:
            return LLMResponse(text="This response has no score at all.", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="SCORE: 9.0\nRATIONALE: great", stop_reason="end_turn", usage=_usage())

    result = spec.run_speculative("Task", MockClient(planner), n_candidates=2)

    scores = {c.index: c.score for c in result.candidates}
    assert scores[0] == 0.0
    assert scores[1] == 9.0
    assert result.winner.score == 9.0
