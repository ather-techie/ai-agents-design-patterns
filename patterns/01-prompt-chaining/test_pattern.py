"""Tests for the Prompt Chaining pattern.

These are self-contained: they use a scripted mock planner rather than
importing the demo, and load ``pattern.py`` by path so the suite can hold
multiple patterns' identically-named modules at once.
"""

from __future__ import annotations

import pytest

from shared.errors import AgentError
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

chain = load_pattern_module("01-prompt-chaining")


def _usage(n: int = 1) -> Usage:
    return Usage(input_tokens=10 * n, output_tokens=5 * n)


def test_three_step_chain_records_trace_and_returns_last_output() -> None:
    """A 3-step chain records one reasoning step per LLM call plus a final answer."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        return LLMResponse(text=f"step-output-{call_count}", usage=_usage())

    steps = [
        chain.ChainStep(name="brainstorm", prompt_template="Brainstorm: {input}"),
        chain.ChainStep(name="outline", prompt_template="Outline this: {input}"),
        chain.ChainStep(name="draft", prompt_template="Draft from: {input}"),
    ]

    result = chain.run_prompt_chain("test topic", steps, MockClient(planner))

    # Final output should be the last step's response text.
    assert result.output == "step-output-3"

    # One "reasoning" step per LLM call + one "answer" step at the end.
    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("reasoning") == 3
    assert kinds.count("answer") == 1
    assert kinds[-1] == "answer"

    # The trace should be marked as succeeded.
    assert result.trace.succeeded


def test_empty_steps_raises_agent_error() -> None:
    """Passing an empty steps list raises AgentError immediately."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text="should not be called", usage=_usage())

    with pytest.raises(AgentError, match="at least one step"):
        chain.run_prompt_chain("anything", [], MockClient(planner))


def test_usage_is_accumulated_across_steps() -> None:
    """Token usage from every step is summed in the trace."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        # Each call reports 10 input + 5 output = 15 total.
        return LLMResponse(text=f"step-output-{call_count}", usage=_usage())

    steps = [
        chain.ChainStep(name="s1", prompt_template="Step 1: {input}"),
        chain.ChainStep(name="s2", prompt_template="Step 2: {input}"),
        chain.ChainStep(name="s3", prompt_template="Step 3: {input}"),
    ]

    result = chain.run_prompt_chain("topic", steps, MockClient(planner))

    # 3 calls × (10 input + 5 output) = 45 total tokens.
    assert result.trace.usage.input_tokens == 30
    assert result.trace.usage.output_tokens == 15
    assert result.trace.usage.total_tokens == 45


def test_each_step_receives_previous_output() -> None:
    """Each step's prompt is formatted with the previous step's output."""
    received_prompts: list[str] = []

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        received_prompts.append(messages[0].content)
        call_count = len(received_prompts)
        return LLMResponse(text=f"out-{call_count}", usage=_usage())

    steps = [
        chain.ChainStep(name="first", prompt_template="A:{input}"),
        chain.ChainStep(name="second", prompt_template="B:{input}"),
    ]

    chain.run_prompt_chain("start", steps, MockClient(planner))

    assert received_prompts[0] == "A:start"
    assert received_prompts[1] == "B:out-1"
