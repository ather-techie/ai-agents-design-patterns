"""Tests for the Least-to-Most pattern.

Self-contained: builds scripted mock planners and loads ``pattern.py`` by path
via ``load_pattern_module``.
"""

from __future__ import annotations

from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

ltm = load_pattern_module("20-least-to-most")


# --- Helpers ----------------------------------------------------------------


def _usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5)


# --- Tests ------------------------------------------------------------------


def test_sub_problems_solved_in_order() -> None:
    """Sub-problems are solved sequentially and stored with correct indices."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx == 0:
            return LLMResponse(
                text='["Step 1", "Step 2", "Step 3"]',
                stop_reason="end_turn",
                usage=_usage(),
            )
        return LLMResponse(text=f"Answer {idx}.", stop_reason="end_turn", usage=_usage())

    result = ltm.run_least_to_most("Problem", MockClient(planner))

    assert len(result.sub_problems) == 3
    for i, sp in enumerate(result.sub_problems):
        assert sp.index == i
    assert result.sub_problems[0].problem == "Step 1"
    assert result.sub_problems[2].problem == "Step 3"


def test_later_sub_problems_receive_prior_answers_in_context() -> None:
    """Prompts for later sub-problems include the Q&A from earlier ones."""

    call_count = {"n": 0}
    prompts_seen: list[str] = []

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        user_content = next((m.content for m in messages if m.role == "user"), "")
        prompts_seen.append(user_content)
        if idx == 0:
            return LLMResponse(
                text='["Easy sub-problem", "Hard sub-problem"]',
                stop_reason="end_turn",
                usage=_usage(),
            )
        return LLMResponse(text=f"Answer {idx}.", stop_reason="end_turn", usage=_usage())

    ltm.run_least_to_most("Complex task", MockClient(planner))

    # The second sub-problem's prompt should reference the first sub-problem's answer.
    second_sub_prompt = prompts_seen[2]  # idx 0=decompose, 1=first, 2=second
    assert "Easy sub-problem" in second_sub_prompt
    assert "Answer 1." in second_sub_prompt


def test_max_sub_problems_cap() -> None:
    """A decomposition returning more sub-problems than max is truncated."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx == 0:
            many = ["Step " + str(i) for i in range(1, 11)]
            import json
            return LLMResponse(text=json.dumps(many), stop_reason="end_turn", usage=_usage())
        return LLMResponse(text=f"Answer {idx}.", stop_reason="end_turn", usage=_usage())

    result = ltm.run_least_to_most("Big problem", MockClient(planner), max_sub_problems=3)

    assert len(result.sub_problems) == 3


def test_single_sub_problem_degenerate_case() -> None:
    """A JSON list with one element works correctly."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx == 0:
            return LLMResponse(
                text='["The only sub-problem"]',
                stop_reason="end_turn",
                usage=_usage(),
            )
        return LLMResponse(text="The only answer.", stop_reason="end_turn", usage=_usage())

    result = ltm.run_least_to_most("Simple task", MockClient(planner))

    assert len(result.sub_problems) == 1
    assert result.answer == "The only answer."
    assert result.sub_problems[0].problem == "The only sub-problem"


def test_json_parse_failure_falls_back_to_single_sub_problem() -> None:
    """If the decomposition response is not valid JSON, treat it as one sub-problem."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx == 0:
            return LLMResponse(
                text="This is not JSON at all, just a plain problem statement.",
                stop_reason="end_turn",
                usage=_usage(),
            )
        return LLMResponse(text="Fallback answer.", stop_reason="end_turn", usage=_usage())

    result = ltm.run_least_to_most("Any problem", MockClient(planner))

    assert len(result.sub_problems) == 1
    assert result.answer == "Fallback answer."
