"""Reflection: a single model critiques its own draft and revises until satisfied.

Unlike the Evaluator-Optimizer pattern (05), which uses two separate clients —
one to generate, one to evaluate — Reflection uses **one client for everything**.
The same model acts as author and critic. This removes the need for an external
evaluator and makes the pattern cheap to deploy, at the cost of potential
self-serving bias (a model may be too easy or too inconsistent a judge of its
own work).

Loop structure::

    task → [draft] → [critique] → NO_CHANGES → answer
                          ↓
                     [revision] → [critique] → …

The loop runs until the critique begins with ``NO_CHANGES`` or ``max_iterations``
is exhausted, whichever comes first.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_CRITIQUE_PROMPT_TEMPLATE = """\
Review this draft and identify any flaws, gaps, or improvements needed.
If the draft is already excellent, respond with exactly: NO_CHANGES

Draft:
{draft}

Original task: {task}"""

_REVISION_PROMPT_TEMPLATE = """\
Revise this draft based on the following critique.

Original task: {task}
Current draft: {draft}
Critique: {critique}

Provide only the revised text."""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ReflectionResult:
    """The outcome of a :func:`run_reflection` run.

    Attributes:
        draft:      The initial draft produced before any critique-revision cycles.
        final:      The final (possibly revised) output returned to the caller.
        iterations: How many critique-revision cycles ran.  ``0`` means the
                    first critique returned ``NO_CHANGES`` — the draft was
                    already excellent.
        trace:      The full step-by-step execution trace.
    """

    draft: str
    final: str
    iterations: int
    trace: Trace


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------


def run_reflection(
    task: str,
    client: LLMClient,
    *,
    max_iterations: int = 3,
    trace: Trace | None = None,
) -> ReflectionResult:
    """Generate a draft and iteratively self-critique/revise it until satisfied.

    Args:
        task:           The user task the model should complete.
        client:         A single :class:`~shared.llm_client.LLMClient` used for
                        all calls — draft generation, critique, and revision.
        max_iterations: Maximum number of critique-revision cycles.  When the
                        model returns ``NO_CHANGES`` the loop exits early; if it
                        never says ``NO_CHANGES`` the loop stops after this many
                        cycles and returns the last draft.
        trace:          Optional existing :class:`~shared.trace.Trace` to append
                        steps to.  A new trace is created when omitted.

    Returns:
        :class:`ReflectionResult` with the initial draft, final output,
        iteration count, and the full trace.
    """
    trace = trace or Trace(title=f"Reflection · {task[:60]}")

    # ------------------------------------------------------------------
    # Step 1: generate initial draft
    # ------------------------------------------------------------------
    start = time.perf_counter()
    response = client.complete([Message(role="user", content=task)])
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    trace.record_usage(response.usage)
    draft = response.text
    initial_draft = draft
    trace.add(
        "reasoning",
        f"draft: {draft[:80]}",
        duration_ms=elapsed_ms,
    )

    # ------------------------------------------------------------------
    # Step 2: reflection loop — critique then (conditionally) revise
    # ------------------------------------------------------------------
    iterations = 0

    for i in range(max_iterations):
        # --- Critique ---------------------------------------------------
        critique_prompt = _CRITIQUE_PROMPT_TEMPLATE.format(draft=draft, task=task)
        start = time.perf_counter()
        critique_response = client.complete(
            [Message(role="user", content=critique_prompt)]
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        trace.record_usage(critique_response.usage)
        critique_text = critique_response.text
        trace.add(
            "critique",
            critique_text[:80],
            duration_ms=elapsed_ms,
        )

        if critique_text.strip().upper().startswith("NO_CHANGES"):
            break

        # --- Revision ---------------------------------------------------
        revision_prompt = _REVISION_PROMPT_TEMPLATE.format(
            task=task,
            draft=draft,
            critique=critique_text,
        )
        start = time.perf_counter()
        revision_response = client.complete(
            [Message(role="user", content=revision_prompt)]
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        trace.record_usage(revision_response.usage)
        draft = revision_response.text
        iterations = i + 1
        trace.add(
            "revision",
            f"iteration {i + 1}: {draft[:80]}",
            duration_ms=elapsed_ms,
        )

    trace.add("answer", draft)
    return ReflectionResult(
        draft=initial_draft,
        final=draft,
        iterations=iterations,
        trace=trace,
    )
