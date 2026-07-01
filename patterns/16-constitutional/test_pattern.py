"""Tests for the Constitutional pattern.

Self-contained: uses scripted mock planners and loads ``pattern.py`` by path via
``load_pattern_module`` so multiple patterns can coexist in the same test process.
"""

from __future__ import annotations

import pytest

from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

constitutional = load_pattern_module("16-constitutional")


def _usage() -> Usage:
    return Usage(input_tokens=30, output_tokens=15)


def _make_principles() -> list:
    return [
        constitutional.Principle("clarity", "Must be clear and jargon-free"),
        constitutional.Principle("brevity", "Must be under 50 words"),
    ]


def _sequential_planner(responses: list[str]) -> MockClient:
    """MockClient that serves responses in the given order, cycling if needed."""
    call_index = {"n": 0}

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        idx = call_index["n"] % len(responses)
        call_index["n"] += 1
        return LLMResponse(text=responses[idx], stop_reason="end_turn", usage=_usage())

    return MockClient(planner)


def test_one_critique_step_per_principle_per_revision() -> None:
    """Each principle should produce exactly one critique step per revision pass."""
    principles = _make_principles()
    # 1 draft + 2 critiques + 1 revision + answer = 5 LLM calls for max_revisions=1
    responses = ["draft text", "critique-clarity", "critique-brevity", "revised text"]
    client = _sequential_planner(responses)

    result = constitutional.run_constitutional(
        "Write a refund policy message.",
        principles,
        client,
        max_revisions=1,
    )

    critique_steps = [s for s in result.trace.steps if s.kind == "critique"]
    assert len(critique_steps) == len(principles)


def test_revision_steps_recorded() -> None:
    """At least one 'revision' step should appear in the trace."""
    responses = ["draft", "crit-clarity", "crit-brevity", "revised"]
    client = _sequential_planner(responses)

    result = constitutional.run_constitutional(
        "Write a refund policy message.",
        _make_principles(),
        client,
        max_revisions=1,
    )

    step_kinds = [s.kind for s in result.trace.steps]
    assert "revision" in step_kinds


def test_max_revisions_cap() -> None:
    """Exactly max_revisions revision steps should be recorded."""
    principles = _make_principles()
    max_rev = 2
    # For 2 revision passes with 2 principles:
    # 1 draft + (2 critiques + 1 revision) * 2 + answer = 8 LLM calls
    responses = [
        "draft",
        "crit-clarity-1", "crit-brevity-1", "revised-1",
        "crit-clarity-2", "crit-brevity-2", "revised-2",
    ]
    client = _sequential_planner(responses)

    result = constitutional.run_constitutional(
        "Write a refund policy message.",
        principles,
        client,
        max_revisions=max_rev,
    )

    revision_steps = [s for s in result.trace.steps if s.kind == "revision"]
    assert len(revision_steps) == max_rev


def test_empty_principles_returns_draft_as_answer() -> None:
    """With no principles, the initial draft should become the answer with no critiques."""
    responses = ["initial draft text"]
    client = _sequential_planner(responses)

    result = constitutional.run_constitutional(
        "Write something.",
        [],
        client,
        max_revisions=2,
    )

    step_kinds = [s.kind for s in result.trace.steps]
    assert "critique" not in step_kinds
    assert "revision" not in step_kinds
    assert "answer" in step_kinds
    assert result.final == result.draft
    assert result.critiques == []


def test_critiques_list_has_one_entry_per_principle() -> None:
    """The returned critiques list should have len(principles) entries (per pass)."""
    principles = _make_principles()
    responses = ["draft", "crit-clarity", "crit-brevity", "revised"]
    client = _sequential_planner(responses)

    result = constitutional.run_constitutional(
        "Write a refund policy message.",
        principles,
        client,
        max_revisions=1,
    )

    # One pass with 2 principles -> 2 critique tuples
    assert len(result.critiques) == len(principles)
    principle_names = {name for name, _ in result.critiques}
    assert principle_names == {"clarity", "brevity"}
