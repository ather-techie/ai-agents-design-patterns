"""Prompt Chaining: decompose a complex task into a fixed pipeline of LLM calls.

Each step's output is injected into the next step's prompt via ``{input}``.
The pipeline is fixed at construction time — unlike ReAct, there is no dynamic
branching or tool use. Useful when a task has clear sequential sub-goals such as
extract → transform → format, or brainstorm → outline → draft.

The function depends only on the :class:`~shared.llm_client.LLMClient` protocol,
so it runs unchanged against the live Anthropic client or the offline mock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from shared.errors import AgentError
from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message


@dataclass
class ChainStep:
    """One step in the prompt chain.

    ``prompt_template`` must contain ``{input}`` — it is formatted with the
    output from the previous step (or the initial input for the first step).
    """

    name: str
    prompt_template: str  # must contain {input}


@dataclass
class ChainResult:
    """The outcome of a prompt-chain run."""

    output: str
    trace: Trace


def run_prompt_chain(
    initial_input: str,
    steps: list[ChainStep],
    client: LLMClient,
    *,
    trace: Trace | None = None,
) -> ChainResult:
    """Run a fixed pipeline of LLM calls and return the final output + trace.

    Each step formats its ``prompt_template`` with the current ``output``, calls
    the model, records a ``"reasoning"`` trace step with wall-clock timing, and
    feeds the response text into the next step. The last step's response becomes
    the final output.

    Raises :class:`AgentError` if ``steps`` is empty.
    """
    if not steps:
        raise AgentError("run_prompt_chain requires at least one step")

    trace = trace or Trace(title=f"Prompt Chain · {initial_input[:60]}")
    output = initial_input

    for step in steps:
        prompt = step.prompt_template.format(input=output)
        messages = [Message(role="user", content=prompt)]

        start = time.perf_counter()
        response = client.complete(messages)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        trace.record_usage(response.usage)
        trace.add(
            "reasoning",
            f"[{step.name}] {response.text[:80]}",
            duration_ms=elapsed_ms,
        )
        output = response.text

    trace.add("answer", output)
    return ChainResult(output=output, trace=trace)
