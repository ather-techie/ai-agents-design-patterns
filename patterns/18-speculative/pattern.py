"""Speculative Execution: generate multiple candidate solutions and score them.

The pattern generates ``n_candidates`` independent solutions in parallel (here
sequential for simplicity), then uses an evaluator LLM to score each on
correctness, clarity, and completeness. The highest-scoring candidate wins.
This trades latency for quality — particularly effective when the solution space
is large and a single attempt may miss an important corner case.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message


@dataclass
class Candidate:
    """One generated solution with its evaluation score."""

    index: int
    content: str
    score: float
    rationale: str


@dataclass
class SpeculativeResult:
    """The outcome of a speculative execution run."""

    winner: Candidate
    candidates: list[Candidate]
    trace: Trace


def run_speculative(
    task: str,
    client: LLMClient,
    *,
    n_candidates: int = 3,
    trace: Trace | None = None,
) -> SpeculativeResult:
    """Generate ``n_candidates`` solutions for ``task``, score each, and return the best.

    When ``n_candidates == 1`` the single candidate is returned directly as the
    winner with a score of 10.0 (no evaluator call is made).
    """
    trace = trace or Trace(title=f"Speculative · {task[:60]}")

    # Step 1: Generate all candidates.
    raw_candidates: list[str] = []
    for i in range(n_candidates):
        prompt = f"Solve this problem (attempt {i + 1} of {n_candidates}): {task}"
        messages: list[Message] = [Message(role="user", content=prompt)]
        start = time.perf_counter()
        response = client.complete(messages, None)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        trace.record_usage(response.usage)
        raw_candidates.append(response.text)
        trace.add("candidate", f"candidate {i + 1}", duration_ms=elapsed_ms)

    # Step 2: Score each candidate (or skip for n_candidates == 1).
    candidates: list[Candidate] = []

    if n_candidates == 1:
        candidates.append(
            Candidate(
                index=0,
                content=raw_candidates[0],
                score=10.0,
                rationale="only candidate",
            )
        )
    else:
        all_candidates_text = "\n\n".join(
            f"Candidate {i + 1}:\n{text}"
            for i, text in enumerate(raw_candidates)
        )
        for i, content in enumerate(raw_candidates):
            eval_prompt = (
                f"You are an expert evaluator. Score the following candidate "
                f"solution for the task:\n\nTask: {task}\n\n"
                f"All candidates for context:\n{all_candidates_text}\n\n"
                f"Candidate to score (#{i + 1}):\n{content}\n\n"
                f"Score this candidate 0.0-10.0 for correctness, clarity, and "
                f"completeness. Respond with:\n"
                f"SCORE: X.X\nRATIONALE: ..."
            )
            eval_messages: list[Message] = [Message(role="user", content=eval_prompt)]
            start = time.perf_counter()
            eval_response = client.complete(eval_messages, None)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            trace.record_usage(eval_response.usage)

            score = _parse_score(eval_response.text)
            rationale = _parse_rationale(eval_response.text)

            trace.add(
                "critique",
                f"score {score:.1f}: candidate {i + 1}",
                duration_ms=elapsed_ms,
            )
            candidates.append(
                Candidate(index=i, content=content, score=score, rationale=rationale)
            )

    # Step 3: Select the winner.
    winner = max(candidates, key=lambda c: c.score)
    trace.add("answer", winner.content[:100])

    return SpeculativeResult(winner=winner, candidates=candidates, trace=trace)


def _parse_score(text: str) -> float:
    """Extract the numeric score from an evaluator response."""
    match = re.search(r"SCORE:\s*([0-9]+(?:\.[0-9]+)?)", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    return 0.0


def _parse_rationale(text: str) -> str:
    """Extract the rationale from an evaluator response."""
    match = re.search(r"RATIONALE:\s*(.*)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()
