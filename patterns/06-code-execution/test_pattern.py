"""Tests for the Code Execution pattern.

These are self-contained: they use scripted mock planners and executors rather
than importing the demo, and load ``pattern.py`` by path so the suite can hold
multiple patterns' identically-named modules at once.
"""

from __future__ import annotations

import pytest

from shared.errors import MaxStepsExceeded
from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.types import LLMResponse, Message, Usage

ce = load_pattern_module("06-code-execution")


def _usage(n: int = 1) -> Usage:
    return Usage(input_tokens=10 * n, output_tokens=5 * n)


# ---------------------------------------------------------------------------
# Test 1: successful on first attempt
# ---------------------------------------------------------------------------

def test_successful_first_attempt() -> None:
    """Code runs cleanly on the first attempt; trace has reasoning+observation+answer."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        last = messages[-1].content
        if "Answer the original task" in last:
            return LLMResponse(text="The sum is 328.", usage=_usage())
        # First call — return valid Python code.
        return LLMResponse(
            text="primes = [n for n in range(2,50) if all(n%i for i in range(2,n))]\nprint(sum(primes))",
            usage=_usage(),
        )

    def executor(code: str) -> str:
        return "328"

    result = ce.run_code_execution(
        "Calculate the sum of all prime numbers below 50",
        executor,
        MockClient(planner),
    )

    assert result.attempts == 1
    assert result.output == "328"
    assert "328" in result.answer

    kinds = [s.kind for s in result.trace.steps]
    assert kinds.count("reasoning") == 1
    assert kinds.count("observation") == 1
    assert kinds.count("answer") == 1
    assert kinds[-1] == "answer"
    assert result.trace.succeeded


# ---------------------------------------------------------------------------
# Test 2: first attempt errors, second attempt succeeds
# ---------------------------------------------------------------------------

def test_retry_on_error_succeeds_second_attempt() -> None:
    """When the executor raises on attempt 1, the model is given the error and retries."""

    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        last = messages[-1].content
        if "Answer the original task" in last:
            return LLMResponse(text="The factorial of 10 is 3628800.", usage=_usage())
        if call_count == 1:
            # Intentionally broken code.
            return LLMResponse(text="print(math.factorial(10))", usage=_usage())
        # Second code generation attempt — correct code.
        return LLMResponse(text="import math\nprint(math.factorial(10))", usage=_usage())

    exec_count = 0

    def executor(code: str) -> str:
        nonlocal exec_count
        exec_count += 1
        if exec_count == 1:
            raise RuntimeError("NameError: name 'math' is not defined")
        return "3628800"

    result = ce.run_code_execution(
        "Calculate the factorial of 10",
        executor,
        MockClient(planner),
        max_attempts=3,
    )

    assert result.attempts == 2
    assert result.output == "3628800"
    assert "3628800" in result.answer

    # Should have: reasoning, error-observation, reasoning, observation, answer
    steps = result.trace.steps
    error_steps = [s for s in steps if s.is_error]
    assert len(error_steps) == 1
    assert error_steps[0].kind == "observation"
    assert result.trace.succeeded


# ---------------------------------------------------------------------------
# Test 3: all attempts fail → MaxStepsExceeded
# ---------------------------------------------------------------------------

def test_all_attempts_fail_raises_max_steps_exceeded() -> None:
    """When every execution attempt raises, MaxStepsExceeded is raised."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text="raise ValueError('always fails')", usage=_usage())

    def executor(code: str) -> str:
        raise RuntimeError("execution failed")

    with pytest.raises(MaxStepsExceeded):
        ce.run_code_execution(
            "Do something impossible",
            executor,
            MockClient(planner),
            max_attempts=3,
        )


# ---------------------------------------------------------------------------
# Test 4: code extraction strips markdown fences
# ---------------------------------------------------------------------------

def test_extract_code_strips_markdown_fences() -> None:
    """_extract_code handles ```python fences, plain ``` fences, and bare code."""
    extract = ce._extract_code

    # ```python fence
    fenced_py = "```python\nprint('hello')\n```"
    assert extract(fenced_py) == "print('hello')"

    # plain ``` fence
    fenced_plain = "```\nprint('hello')\n```"
    assert extract(fenced_plain) == "print('hello')"

    # no fence — returned as-is (stripped)
    bare = "  print('hello')  "
    assert extract(bare) == "print('hello')"
