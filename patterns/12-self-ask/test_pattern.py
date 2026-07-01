"""Tests for the Self-Ask pattern.

Self-contained: scripted mock planners drive all LLM calls. Loads ``pattern.py``
by path via ``load_pattern_module`` so the module name doesn't collide with
other patterns.
"""

from __future__ import annotations

import pytest

from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

self_ask = load_pattern_module("12-self-ask")


def _usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5)


def test_produces_sub_questions_with_correct_answers() -> None:
    """Decompose + sub-answer + synthesize round-trip produces expected results."""

    call_count = [0]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        n = call_count[0]
        call_count[0] += 1
        if n == 0:
            return LLMResponse(
                text='["What is X?", "What is Y?"]',
                stop_reason="end_turn",
                usage=_usage(),
            )
        if n == 1:
            return LLMResponse(text="X is 1", stop_reason="end_turn", usage=_usage())
        if n == 2:
            return LLMResponse(text="Y is 2", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="X=1 and Y=2.", stop_reason="end_turn", usage=_usage())

    result = self_ask.run_self_ask("What are X and Y?", MockClient(planner))

    assert len(result.sub_questions) == 2
    assert result.sub_questions[0].question == "What is X?"
    assert result.sub_questions[0].answer == "X is 1"
    assert result.sub_questions[1].question == "What is Y?"
    assert result.sub_questions[1].answer == "Y is 2"


def test_final_answer_is_non_empty() -> None:
    """The synthesized final answer is non-empty."""

    call_count = [0]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        n = call_count[0]
        call_count[0] += 1
        if n == 0:
            return LLMResponse(
                text='["Single question?"]',
                stop_reason="end_turn",
                usage=_usage(),
            )
        if n == 1:
            return LLMResponse(text="Single answer.", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="Combined answer.", stop_reason="end_turn", usage=_usage())

    result = self_ask.run_self_ask("Something complex?", MockClient(planner))

    assert result.answer
    assert result.answer == "Combined answer."


def test_max_sub_questions_caps_the_list() -> None:
    """Only the first max_sub_questions items are used from the JSON array."""

    call_count = [0]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        n = call_count[0]
        call_count[0] += 1
        if n == 0:
            # Return 5 sub-questions but cap is 2.
            return LLMResponse(
                text='["Q1", "Q2", "Q3", "Q4", "Q5"]',
                stop_reason="end_turn",
                usage=_usage(),
            )
        if n == 1:
            return LLMResponse(text="A1", stop_reason="end_turn", usage=_usage())
        if n == 2:
            return LLMResponse(text="A2", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="Final.", stop_reason="end_turn", usage=_usage())

    result = self_ask.run_self_ask(
        "Big question?", MockClient(planner), max_sub_questions=2
    )

    assert len(result.sub_questions) == 2
    assert result.sub_questions[0].question == "Q1"
    assert result.sub_questions[1].question == "Q2"


def test_malformed_json_falls_back_to_single_sub_question() -> None:
    """When decompose returns non-JSON, treat the raw text as one sub-question."""

    call_count = [0]

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        n = call_count[0]
        call_count[0] += 1
        if n == 0:
            # Deliberately broken JSON.
            return LLMResponse(
                text="not json at all",
                stop_reason="end_turn",
                usage=_usage(),
            )
        if n == 1:
            return LLMResponse(text="fallback answer", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="synthesized", stop_reason="end_turn", usage=_usage())

    result = self_ask.run_self_ask("Broken?", MockClient(planner))

    assert len(result.sub_questions) == 1
    assert result.sub_questions[0].question == "not json at all"
    assert result.sub_questions[0].answer == "fallback answer"
