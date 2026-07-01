"""Evaluator-Optimizer: iteratively refine output until it meets explicit criteria.

The pattern uses two LLM clients (or one playing both roles):

1. **Generator** — produces the initial draft from the task description.
2. **Evaluator** — checks the draft against a list of :class:`Criterion` objects
   and replies with ``PASS`` (all criteria met) or ``FAIL: <reason>`` (with the
   reason the draft fell short).
3. On ``FAIL``, the **generator** is asked to revise the current draft using the
   evaluator's feedback. This loop repeats until the evaluator returns ``PASS`` or
   ``max_iterations`` is exhausted.

The design deliberately separates generation from evaluation: using different
models (or at minimum different prompts) reduces the self-serving bias a single
model exhibits when asked to judge its own output.

Loop structure::

    task → [generate] → draft_0
                          │
              ┌───────────▼───────────┐
              │  [evaluate draft_i]   │
              └─────┬─────────┬───────┘
                 PASS       FAIL: reason
                   │           │
                 answer   [generate revision]
                              │
                          draft_{i+1}  ──→ (loop)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from shared.errors import AgentError
from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message


@dataclass
class Criterion:
    """A single checkable quality criterion for the evaluator.

    Examples::

        Criterion(description="The text is under 100 words")
        Criterion(description="The tone is professional")
        Criterion(description="Contains the product name 'Apex'")
    """

    description: str


@dataclass
class EvalOptimizerResult:
    """The outcome of a :func:`run_evaluator_optimizer` run.

    Attributes:
        output:     The final draft (best achieved, even if ``passed`` is False).
        iterations: Number of evaluate-revise cycles completed (1 means the
                    initial draft was evaluated once with no revisions).
        passed:     True if the evaluator returned ``PASS`` before exhausting
                    ``max_iterations``.
        trace:      The full step-by-step execution trace.
    """

    output: str
    iterations: int
    passed: bool
    trace: Trace


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_EVAL_PROMPT_TEMPLATE = """\
Evaluate this text against the criteria below. Reply with PASS if ALL criteria are met, \
or FAIL: <reason> if any criterion is not met.

Criteria:
{criteria_list}

Text to evaluate:
{draft}"""

_REVISION_PROMPT_TEMPLATE = """\
Revise the following text to address this feedback: {feedback}

Original task: {task}
Current text: {draft}

Provide only the revised text, no explanation."""


def run_evaluator_optimizer(
    task: str,
    criteria: list[Criterion],
    generator: LLMClient,
    evaluator: LLMClient,
    *,
    max_iterations: int = 3,
    trace: Trace | None = None,
) -> EvalOptimizerResult:
    """Generate a draft and iteratively refine it until all criteria pass.

    Args:
        task:           The original user task / instruction for the generator.
        criteria:       Non-empty list of :class:`Criterion` objects the output
                        must satisfy.
        generator:      LLM client responsible for producing and revising drafts.
        evaluator:      LLM client responsible for judging drafts against criteria.
        max_iterations: Maximum number of evaluate-[revise] cycles.  The function
                        returns after at most this many evaluations regardless of
                        whether ``PASS`` was reached.
        trace:          Optional existing :class:`Trace` to append steps to.
                        A new trace is created when omitted.

    Returns:
        :class:`EvalOptimizerResult` with the final draft, iteration count,
        pass/fail status, and the full trace.

    Raises:
        :class:`~shared.errors.AgentError`: If ``criteria`` is empty.
    """
    if not criteria:
        raise AgentError("at least one criterion required")

    trace = trace or Trace(title=f"Evaluator-Optimizer · {task[:60]}")

    # ------------------------------------------------------------------
    # Step 1: generate initial draft
    # ------------------------------------------------------------------
    start = time.perf_counter()
    response = generator.complete([Message(role="user", content=task)])
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    trace.record_usage(response.usage)
    draft = response.text
    trace.add(
        "reasoning",
        f"draft: {draft[:80]}",
        duration_ms=elapsed_ms,
    )

    # ------------------------------------------------------------------
    # Step 2: evaluate → (revise →) evaluate loop
    # ------------------------------------------------------------------
    criteria_list = "\n".join(f"- {c.description}" for c in criteria)
    passed = False
    i = 0

    for i in range(1, max_iterations + 1):
        # Evaluate current draft
        eval_prompt = _EVAL_PROMPT_TEMPLATE.format(
            criteria_list=criteria_list,
            draft=draft,
        )
        start = time.perf_counter()
        eval_response = evaluator.complete(
            [Message(role="user", content=eval_prompt)]
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        trace.record_usage(eval_response.usage)
        eval_text = eval_response.text.strip()
        trace.add(
            "critique",
            eval_text[:80],
            duration_ms=elapsed_ms,
        )

        if eval_text.upper().startswith("PASS"):
            passed = True
            break

        # FAIL — extract feedback and request a revision
        # The evaluator is expected to respond "FAIL: <reason>".
        feedback = eval_text[eval_text.find(":") + 1:].strip() if ":" in eval_text else eval_text

        revision_prompt = _REVISION_PROMPT_TEMPLATE.format(
            feedback=feedback,
            task=task,
            draft=draft,
        )
        start = time.perf_counter()
        revision_response = generator.complete(
            [Message(role="user", content=revision_prompt)]
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        trace.record_usage(revision_response.usage)
        draft = revision_response.text
        trace.add(
            "revision",
            f"iteration {i}: {draft[:80]}",
            duration_ms=elapsed_ms,
        )

    trace.add("answer", draft)
    return EvalOptimizerResult(
        output=draft,
        iterations=i,
        passed=passed,
        trace=trace,
    )
