"""Constitutional AI: iteratively critique and revise a draft against principles.

The agent first generates an initial draft, then applies each
:class:`Principle` as a critic lens to produce targeted critiques, and finally
asks the model to revise the draft in light of all critiques. The
critique-revision loop repeats up to ``max_revisions`` times.

If ``principles`` is empty the initial draft is returned as-is with no critique
or revision steps, which is useful when only a single-pass generation is needed.

The function depends only on the :class:`~shared.llm_client.LLMClient` protocol
so it runs unchanged against the live Anthropic client or the offline mock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message


@dataclass
class Principle:
    """A single constitutional principle the draft must satisfy."""

    name: str
    description: str


@dataclass
class ConstitutionalResult:
    """The outcome of a constitutional review run."""

    draft: str
    critiques: list[tuple[str, str]]   # (principle_name, critique_text)
    final: str
    trace: Trace
    revisions: int


def _call(
    client: LLMClient,
    prompt: str,
    trace: Trace,
    step_kind: str,
    step_summary: str,
) -> str:
    """Single LLM call with its own isolated message list."""
    messages: list[Message] = [Message(role="user", content=prompt)]
    start = time.perf_counter()
    response = client.complete(messages)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    trace.record_usage(response.usage)
    trace.add(step_kind, step_summary, duration_ms=elapsed_ms)  # type: ignore[arg-type]
    return response.text


def run_constitutional(
    task: str,
    principles: list[Principle],
    client: LLMClient,
    *,
    max_revisions: int = 2,
    trace: Trace | None = None,
) -> ConstitutionalResult:
    """Generate a draft for ``task``, critique it against ``principles``, and revise.

    Returns the final revised draft with all critiques collected.
    If ``principles`` is empty, returns the initial draft directly.
    """
    trace = trace or Trace(title=f"Constitutional · {task}")

    draft = _call(
        client,
        f"Complete the following task:\n\n{task}",
        trace,
        "reasoning",
        "initial draft",
    )

    if not principles:
        trace.add("answer", draft)
        return ConstitutionalResult(
            draft=draft,
            critiques=[],
            final=draft,
            trace=trace,
            revisions=0,
        )

    all_critiques: list[tuple[str, str]] = []
    current_draft = draft

    for pass_num in range(1, max_revisions + 1):
        pass_critiques: list[tuple[str, str]] = []

        for principle in principles:
            critique_prompt = (
                f"Review the following draft against this principle.\n\n"
                f"Principle — {principle.name}: {principle.description}\n\n"
                f"Draft:\n{current_draft}\n\n"
                f"Provide a short, specific critique (1-2 sentences) stating how well "
                f"the draft satisfies the principle and what should change."
            )
            critique_text = _call(
                client,
                critique_prompt,
                trace,
                "critique",
                f"{principle.name}: {critique_prompt[:60]}",
            )
            pass_critiques.append((principle.name, critique_text))

        all_critiques.extend(pass_critiques)

        critiques_block = "\n".join(
            f"- [{name}] {text}" for name, text in pass_critiques
        )
        revision_prompt = (
            f"Revise the following draft to address all critiques below.\n\n"
            f"Original draft:\n{current_draft}\n\n"
            f"Critiques:\n{critiques_block}\n\n"
            f"Provide only the revised text."
        )
        current_draft = _call(
            client,
            revision_prompt,
            trace,
            "revision",
            f"revision {pass_num}",
        )

    trace.add("answer", current_draft)
    return ConstitutionalResult(
        draft=draft,
        critiques=all_critiques,
        final=current_draft,
        trace=trace,
        revisions=max_revisions,
    )
