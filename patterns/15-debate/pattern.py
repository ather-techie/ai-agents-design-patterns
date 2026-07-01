"""Debate: pit two LLM agents against each other, then let a judge decide.

An affirmative agent argues FOR a proposition; a negative agent argues AGAINST
it. With ``rounds >= 2`` each side gets a rebuttal. A neutral judge synthesizes
the strongest answer from all arguments.

Each agent call is fully independent (its own message list), which lets them run
as parallel workers in a real system. Here they run sequentially for simplicity.

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
class DebateResult:
    """The outcome of a debate run."""

    proposition: str
    affirmative: str
    negative: str
    rebuttal_aff: str    # empty string if rounds < 2
    rebuttal_neg: str    # empty string if rounds < 2
    verdict: str
    trace: Trace


def _call(
    client: LLMClient,
    system: str,
    user: str,
    trace: Trace,
    step_kind: str,
    step_summary: str,
) -> str:
    """Single LLM call with its own isolated message list."""
    messages: list[Message] = [
        Message(role="user", content=f"{system}\n\n{user}"),
    ]
    start = time.perf_counter()
    response = client.complete(messages)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    trace.record_usage(response.usage)
    trace.add(step_kind, step_summary, duration_ms=elapsed_ms)  # type: ignore[arg-type]
    return response.text


def run_debate(
    proposition: str,
    client: LLMClient,
    *,
    rounds: int = 2,
    trace: Trace | None = None,
) -> DebateResult:
    """Run a structured debate on ``proposition`` and return all arguments + verdict.

    ``rounds=1`` produces opening statements only; ``rounds=2`` adds rebuttals.
    """
    trace = trace or Trace(title=f"Debate · {proposition}")

    aff_system = (
        f"You are arguing FOR: {proposition}. "
        "Construct a concise, persuasive opening argument in 2-3 sentences."
    )
    neg_system = (
        f"You are arguing AGAINST: {proposition}. "
        "Construct a concise, persuasive opening argument in 2-3 sentences."
    )

    affirmative = _call(
        client,
        aff_system,
        "Present your opening argument.",
        trace,
        "delegate",
        "affirmative opening",
    )

    negative = _call(
        client,
        neg_system,
        "Present your opening argument.",
        trace,
        "delegate",
        "negative opening",
    )

    rebuttal_aff = ""
    rebuttal_neg = ""

    if rounds >= 2:
        rebuttal_aff = _call(
            client,
            aff_system,
            f"The opposing side argued:\n{negative}\n\nProvide your rebuttal in 2-3 sentences.",
            trace,
            "critique",
            "affirmative rebuttal",
        )

        rebuttal_neg = _call(
            client,
            neg_system,
            (
                f"The affirmative side opened with:\n{affirmative}\n\n"
                f"They then rebutted with:\n{rebuttal_aff}\n\n"
                "Provide your rebuttal in 2-3 sentences."
            ),
            trace,
            "critique",
            "negative rebuttal",
        )

    debate_transcript = (
        f"Proposition: {proposition}\n\n"
        f"Affirmative opening:\n{affirmative}\n\n"
        f"Negative opening:\n{negative}\n"
    )
    if rounds >= 2:
        debate_transcript += (
            f"\nAffirmative rebuttal:\n{rebuttal_aff}\n\n"
            f"Negative rebuttal:\n{rebuttal_neg}\n"
        )

    judge_system = (
        "You are a neutral judge. Given this debate, synthesize the strongest "
        "answer that reflects the best arguments from both sides. Be concise."
    )
    verdict = _call(
        client,
        judge_system,
        debate_transcript,
        trace,
        "answer",
        "verdict",
    )

    return DebateResult(
        proposition=proposition,
        affirmative=affirmative,
        negative=negative,
        rebuttal_aff=rebuttal_aff,
        rebuttal_neg=rebuttal_neg,
        verdict=verdict,
        trace=trace,
    )
