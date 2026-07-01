"""Tests for the Reflection pattern.

These tests are self-contained: they use scripted MockClient planners rather
than the live demo, and load ``pattern.py`` by path via ``load_pattern_module``
so multiple pattern modules can coexist in the same test session without name
collisions.
"""

from __future__ import annotations

from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

ref = load_pattern_module("08-reflection")


def _usage(n: int = 1) -> Usage:
    return Usage(input_tokens=10 * n, output_tokens=5 * n)


# ---------------------------------------------------------------------------
# Test 1: draft is already good — first critique returns NO_CHANGES
# ---------------------------------------------------------------------------


def test_no_changes_on_first_critique() -> None:
    """When the first critique is NO_CHANGES, iterations=0 and final == draft."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Initial draft
            return LLMResponse(text="Silicon dreams in code", usage=_usage())
        # Critique: already excellent
        return LLMResponse(text="NO_CHANGES", usage=_usage())

    result = ref.run_reflection(
        task="Write a haiku about artificial intelligence",
        client=MockClient(planner),
        max_iterations=3,
    )

    assert result.iterations == 0
    assert result.final == result.draft
    assert result.final == "Silicon dreams in code"

    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("reasoning") == 1
    assert kinds.count("critique") == 1
    assert kinds.count("revision") == 0
    assert kinds[-1] == "answer"
    assert result.trace.succeeded


# ---------------------------------------------------------------------------
# Test 2: one critique-revision cycle, then NO_CHANGES
# ---------------------------------------------------------------------------


def test_one_critique_revision_cycle() -> None:
    """One cycle of critique + revision, then NO_CHANGES; iterations=1."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(text="AI haiku first draft", usage=_usage())
        if call_count == 2:
            return LLMResponse(
                text="The syllable count is off — 5/7/5 not followed.",
                usage=_usage(),
            )
        if call_count == 3:
            return LLMResponse(
                text="Circuits hum and think / Patterns bloom in silent math / Dawn of new minds stirs",
                usage=_usage(),
            )
        # Fourth call: critique of the revised haiku
        return LLMResponse(text="NO_CHANGES", usage=_usage())

    result = ref.run_reflection(
        task="Write a haiku about artificial intelligence",
        client=MockClient(planner),
        max_iterations=3,
    )

    assert result.iterations == 1
    assert result.draft == "AI haiku first draft"
    assert result.final == "Circuits hum and think / Patterns bloom in silent math / Dawn of new minds stirs"

    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("reasoning") == 1
    assert kinds.count("critique") == 2
    assert kinds.count("revision") == 1
    assert kinds[-1] == "answer"

    # Revision step summary should mention the iteration number
    revision_steps = [s for s in result.trace.steps if s.kind == "revision"]
    assert "iteration 1" in revision_steps[0].summary

    assert result.trace.succeeded


# ---------------------------------------------------------------------------
# Test 3: never says NO_CHANGES — reaches max_iterations
# ---------------------------------------------------------------------------


def test_reaches_max_iterations() -> None:
    """If the model never says NO_CHANGES, stop after max_iterations cycles."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        # Odd calls: draft or revision.  Even calls: critique that always finds flaws.
        if call_count % 2 == 1:
            return LLMResponse(text=f"draft-{call_count}", usage=_usage())
        return LLMResponse(text="Syllables are still wrong.", usage=_usage())

    max_iter = 2
    result = ref.run_reflection(
        task="Write a haiku about artificial intelligence",
        client=MockClient(planner),
        max_iterations=max_iter,
    )

    assert result.iterations == max_iter

    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("critique") == max_iter
    assert kinds.count("revision") == max_iter
    assert kinds[-1] == "answer"

    # The final output should be the last revised draft
    assert result.final == f"draft-{call_count}"


# ---------------------------------------------------------------------------
# Test 4: usage accumulates across all calls
# ---------------------------------------------------------------------------


def test_usage_accumulates() -> None:
    """Token usage from every LLM call is summed onto the trace."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(text="first draft", usage=Usage(input_tokens=10, output_tokens=5))
        if call_count == 2:
            return LLMResponse(text="needs work", usage=Usage(input_tokens=20, output_tokens=8))
        if call_count == 3:
            return LLMResponse(text="revised draft", usage=Usage(input_tokens=30, output_tokens=12))
        return LLMResponse(text="NO_CHANGES", usage=Usage(input_tokens=15, output_tokens=3))

    result = ref.run_reflection(
        task="Write a short bio.",
        client=MockClient(planner),
        max_iterations=3,
    )

    # 4 calls total: draft + critique + revision + NO_CHANGES critique
    assert result.trace.usage.input_tokens == 10 + 20 + 30 + 15
    assert result.trace.usage.output_tokens == 5 + 8 + 12 + 3
    assert result.trace.usage.total_tokens == (10 + 20 + 30 + 15) + (5 + 8 + 12 + 3)
