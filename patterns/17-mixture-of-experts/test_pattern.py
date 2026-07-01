"""Tests for the Mixture-of-Experts pattern.

Self-contained: builds its own experts and scripted mock planners rather than
importing the demo, and loads ``pattern.py`` by path via ``load_pattern_module``.
"""

from __future__ import annotations

import pytest

from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

moe = load_pattern_module("17-mixture-of-experts")


# --- Helpers ----------------------------------------------------------------


def _usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5)


def _experts() -> list:
    return [
        moe.Expert(
            name="legal",
            domain="tax law and legal compliance",
            system_prompt="You are a legal expert.",
        ),
        moe.Expert(
            name="medical",
            domain="healthcare and medical conditions",
            system_prompt="You are a medical expert.",
        ),
        moe.Expert(
            name="financial",
            domain="personal finance and investment",
            system_prompt="You are a financial advisor.",
        ),
    ]


# --- Tests ------------------------------------------------------------------


def test_correct_number_of_experts_selected() -> None:
    """Router selects exactly top_k experts and result reflects that count."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx == 0:
            return LLMResponse(text='["legal", "medical"]', stop_reason="end_turn", usage=_usage())
        if idx == 1:
            return LLMResponse(text="Legal answer.", stop_reason="end_turn", usage=_usage())
        if idx == 2:
            return LLMResponse(text="Medical answer.", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="Synthesized answer.", stop_reason="end_turn", usage=_usage())

    result = moe.run_mixture_of_experts(
        "Can I deduct medical expenses?", _experts(), MockClient(planner), top_k=2
    )
    assert len(result.selected_experts) == 2
    assert set(result.selected_experts) == {"legal", "medical"}


def test_synthesis_step_recorded_when_top_k_gt_1() -> None:
    """A 'reasoning' synthesis step appears in the trace when top_k > 1."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx == 0:
            return LLMResponse(text='["legal", "financial"]', stop_reason="end_turn", usage=_usage())
        if idx == 1:
            return LLMResponse(text="Legal perspective.", stop_reason="end_turn", usage=_usage())
        if idx == 2:
            return LLMResponse(text="Financial perspective.", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="Combined answer.", stop_reason="end_turn", usage=_usage())

    result = moe.run_mixture_of_experts(
        "Tax question", _experts(), MockClient(planner), top_k=2
    )
    kinds = [s.kind for s in result.trace.steps]
    assert "reasoning" in kinds  # synthesis recorded as reasoning


def test_top_k_1_skips_synthesis() -> None:
    """When top_k == 1, synthesis equals the expert's direct answer."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx == 0:
            return LLMResponse(text='["medical"]', stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="Medical only answer.", stop_reason="end_turn", usage=_usage())

    result = moe.run_mixture_of_experts(
        "Health question", _experts(), MockClient(planner), top_k=1
    )
    assert result.synthesis == result.expert_answers[result.selected_experts[0]]
    # No reasoning (synthesis) step should appear.
    kinds = [s.kind for s in result.trace.steps]
    assert "reasoning" not in kinds


def test_unknown_expert_name_raises_expert_error() -> None:
    """Router returning an unregistered expert name raises ExpertError."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(
            text='["legal", "nonexistent_expert"]',
            stop_reason="end_turn",
            usage=_usage(),
        )

    with pytest.raises(moe.ExpertError):
        moe.run_mixture_of_experts(
            "Question", _experts(), MockClient(planner), top_k=2
        )


def test_expert_answers_dict_has_keys_for_each_selected() -> None:
    """expert_answers contains one entry per selected expert."""

    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx == 0:
            return LLMResponse(
                text='["legal", "financial", "medical"]',
                stop_reason="end_turn",
                usage=_usage(),
            )
        if idx == 1:
            return LLMResponse(text="Legal.", stop_reason="end_turn", usage=_usage())
        if idx == 2:
            return LLMResponse(text="Financial.", stop_reason="end_turn", usage=_usage())
        if idx == 3:
            return LLMResponse(text="Medical.", stop_reason="end_turn", usage=_usage())
        return LLMResponse(text="Synthesized.", stop_reason="end_turn", usage=_usage())

    result = moe.run_mixture_of_experts(
        "Complex question", _experts(), MockClient(planner), top_k=3
    )
    assert set(result.expert_answers.keys()) == {"legal", "financial", "medical"}
    assert result.expert_answers["legal"] == "Legal."
    assert result.expert_answers["financial"] == "Financial."
    assert result.expert_answers["medical"] == "Medical."
