"""Tests for the Routing pattern.

Self-contained: own routes + scripted planner, and ``pattern.py`` loaded by path
so it can coexist with the ReAct pattern module of the same name.
"""

from __future__ import annotations

import pytest

from shared.errors import AgentError
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

routing = load_pattern_module("02-routing")


def _routes() -> list:
    Route = routing.Route
    return [
        Route("billing", "money stuff", lambda q: "billing-answer"),
        Route("technical", "tech stuff", lambda q: "technical-answer"),
        Route("general", "everything else", lambda q: "general-answer"),
    ]


def _planner_returning(label: str):
    def planner(_messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text=label, usage=Usage(input_tokens=20, output_tokens=1))

    return planner


def test_dispatches_to_classified_route() -> None:
    result = routing.run_routing(
        "refund please", _routes(), MockClient(_planner_returning("billing"))
    )
    assert result.route == "billing"
    assert result.answer == "billing-answer"
    assert [s.kind for s in result.trace.steps] == ["route", "answer"]
    assert result.trace.succeeded


def test_substring_classification_resolves() -> None:
    """A noisy 'Category: technical' response still maps to the route."""
    result = routing.run_routing(
        "it crashed", _routes(), MockClient(_planner_returning("Category: technical"))
    )
    assert result.route == "technical"


def test_unclassified_uses_fallback() -> None:
    result = routing.run_routing(
        "???",
        _routes(),
        MockClient(_planner_returning("nonsense-label")),
        fallback="general",
    )
    assert result.route == "general"
    assert "fallback" in result.trace.steps[0].summary


def test_unclassified_without_fallback_raises() -> None:
    with pytest.raises(AgentError):
        routing.run_routing("???", _routes(), MockClient(_planner_returning("nonsense")))


def test_empty_routes_raises() -> None:
    with pytest.raises(AgentError):
        routing.run_routing("hi", [], MockClient(_planner_returning("x")))
