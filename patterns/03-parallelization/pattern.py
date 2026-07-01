"""Parallelization: fan out to N independent branches, fan in to one aggregate.

All branches receive the same task but with different system prompts, letting
each approach the problem from a distinct angle simultaneously. A single
``ThreadPoolExecutor`` issues all LLM calls concurrently; once every branch
returns, a final aggregation call synthesises the individual outputs.

Wall-clock time equals the slowest branch, not the sum — cost scales with the
number of branches but latency does not.
"""

from __future__ import annotations

import concurrent.futures
import time
from dataclasses import dataclass, field

from shared.errors import AgentError
from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message, Usage

_DEFAULT_AGGREGATOR = (
    "You received these independent analyses:\n\n{outputs}\n\n"
    "Synthesize them into one coherent answer."
)


@dataclass
class Branch:
    """A named LLM branch with a specialised system prompt."""

    name: str
    system_prompt: str  # e.g. "You are a critic", "You are an optimist"


@dataclass
class ParallelResult:
    """The outcome of a parallelization run."""

    answers: dict[str, str]  # branch name -> response text
    aggregate: str           # final synthesised answer
    trace: Trace


def run_parallelization(
    task: str,
    branches: list[Branch],
    client: LLMClient,
    *,
    aggregator_prompt: str | None = None,
    trace: Trace | None = None,
) -> ParallelResult:
    """Fan out ``task`` across all ``branches`` concurrently, then aggregate.

    Each branch is called with ``"{branch.system_prompt}\\n\\n{task}"`` as the
    user message. After all branches complete a second LLM call synthesises
    their outputs into a single answer.

    Raises :class:`~shared.errors.AgentError` if ``branches`` is empty.
    """
    if not branches:
        raise AgentError("run_parallelization requires at least one branch")

    trace = trace or Trace(title=f"Parallelization · {task[:60]}")

    answers: dict[str, str] = {}
    total_usage = Usage()

    def _call_branch(branch: Branch) -> tuple[str, str, Usage, float]:
        """Call the LLM for one branch; return (name, text, usage, elapsed_ms)."""
        start = time.perf_counter()
        response = client.complete(
            [Message(role="user", content=f"{branch.system_prompt}\n\n{task}")]
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return branch.name, response.text, response.usage, elapsed_ms

    # Fan out: run all branches concurrently.
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(branches)) as executor:
        futures = {executor.submit(_call_branch, b): b for b in branches}
        for future in concurrent.futures.as_completed(futures):
            name, text, usage, elapsed_ms = future.result()
            answers[name] = text
            total_usage = total_usage + usage
            trace.add(
                "worker",
                f"[{name}] {text[:80]}",
                duration_ms=elapsed_ms,
            )

    # Fan in: aggregate branch outputs with one more LLM call.
    outputs_block = "\n\n".join(
        f"=== {name} ===\n{text}" for name, text in answers.items()
    )
    agg_template = aggregator_prompt if aggregator_prompt is not None else _DEFAULT_AGGREGATOR
    agg_message = agg_template.format(outputs=outputs_block)

    agg_start = time.perf_counter()
    agg_response = client.complete([Message(role="user", content=agg_message)])
    agg_elapsed_ms = (time.perf_counter() - agg_start) * 1000.0
    total_usage = total_usage + agg_response.usage

    trace.add(
        "reasoning",
        f"aggregated {len(branches)} branch output{'s' if len(branches) != 1 else ''}",
        duration_ms=agg_elapsed_ms,
    )
    trace.record_usage(total_usage)
    trace.add("answer", agg_response.text)

    return ParallelResult(
        answers=answers,
        aggregate=agg_response.text,
        trace=trace,
    )
