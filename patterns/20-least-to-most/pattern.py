"""Least-to-Most: decompose a hard problem into ordered sub-problems and solve up.

The LLM first breaks a complex problem into sub-problems ordered from easiest
to hardest. Then it solves each sub-problem in sequence, feeding prior answers
into the context for every subsequent step. The final answer is the response to
the hardest (last) sub-problem — which by then has all the simpler building
blocks available in context. This mirrors how humans scaffold difficult reasoning.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message


@dataclass
class SubProblem:
    """One ordered sub-problem and the LLM's answer to it."""

    index: int
    problem: str
    answer: str


@dataclass
class LeastToMostResult:
    """The outcome of a least-to-most reasoning run."""

    answer: str
    sub_problems: list[SubProblem]
    trace: Trace


def run_least_to_most(
    problem: str,
    client: LLMClient,
    *,
    max_sub_problems: int = 5,
    trace: Trace | None = None,
) -> LeastToMostResult:
    """Decompose ``problem`` into sub-problems and solve them from easy to hard.

    If the decomposition response is not valid JSON, the entire response text is
    used as a single sub-problem so the run degrades gracefully.
    """
    trace = trace or Trace(title=f"Least-to-Most · {problem[:60]}")

    # Step 1: Decompose the problem.
    decompose_prompt = (
        f"Break the following problem into a sequence of simpler sub-problems, "
        f"ordered from easiest to hardest. Each sub-problem should build on the "
        f"previous ones. Return ONLY a JSON array of strings — the sub-problem "
        f"statements — with no extra commentary.\n\n"
        f"Problem: {problem}"
    )
    decompose_messages: list[Message] = [Message(role="user", content=decompose_prompt)]

    start = time.perf_counter()
    decompose_response = client.complete(decompose_messages, None)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    trace.record_usage(decompose_response.usage)

    sub_problem_texts = _parse_sub_problems(decompose_response.text)
    sub_problem_texts = sub_problem_texts[:max_sub_problems]
    trace.add("plan", f"{len(sub_problem_texts)} sub-problems", duration_ms=elapsed_ms)

    # Step 2: Solve each sub-problem, building on prior answers.
    solved: list[SubProblem] = []
    for i, sub_problem in enumerate(sub_problem_texts):
        # Build context from all prior Q&A pairs.
        prior_context = ""
        if solved:
            pairs = "\n\n".join(
                f"Sub-problem {sp.index + 1}: {sp.problem}\nAnswer: {sp.answer}"
                for sp in solved
            )
            prior_context = f"\n\nPreviously solved sub-problems:\n{pairs}\n"

        solve_prompt = (
            f"Original problem: {problem}"
            f"{prior_context}\n\n"
            f"Now solve sub-problem {i + 1}: {sub_problem}"
        )
        solve_messages: list[Message] = [Message(role="user", content=solve_prompt)]

        start = time.perf_counter()
        solve_response = client.complete(solve_messages, None)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        trace.record_usage(solve_response.usage)

        sp = SubProblem(index=i, problem=sub_problem, answer=solve_response.text)
        solved.append(sp)
        trace.add(
            "reasoning",
            f"[{i + 1}] {sub_problem[:60]}",
            duration_ms=elapsed_ms,
        )

    # Step 3: Final answer is the last sub-problem's answer.
    final_answer = solved[-1].answer if solved else ""
    trace.add("answer", final_answer[:100])

    return LeastToMostResult(
        answer=final_answer,
        sub_problems=solved,
        trace=trace,
    )


def _parse_sub_problems(text: str) -> list[str]:
    """Parse a JSON array of sub-problems from the LLM response.

    Falls back to treating the entire response as a single sub-problem if
    JSON parsing fails.
    """
    raw = text.strip()
    start_idx = raw.find("[")
    end_idx = raw.rfind("]")
    if start_idx != -1 and end_idx != -1:
        try:
            parsed = json.loads(raw[start_idx : end_idx + 1])
            if isinstance(parsed, list) and all(isinstance(s, str) for s in parsed):
                return [s for s in parsed if s.strip()]
        except (json.JSONDecodeError, ValueError):
            pass
    return [raw]
