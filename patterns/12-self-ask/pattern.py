"""Self-Ask: decompose a complex question into sub-questions, answer each, then synthesize.

The pattern makes three kinds of LLM calls:

1. **Decompose** — one call that returns a JSON array of sub-questions needed to
   answer the main question.
2. **Sub-answer** — one call per sub-question, with prior sub-answers injected
   as context.
3. **Synthesize** — one final call that combines every sub-question and its
   answer into the definitive response.

No tools are required; all reasoning is pure LLM inference.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message

_DECOMPOSE_SYSTEM = (
    "You are a question decomposer. Given a complex question, return a JSON "
    "array of strings — the sub-questions needed to answer the main question. "
    "Output only valid JSON and nothing else. Max {max_sub_questions} items."
)

_SUB_ANSWER_SYSTEM = (
    "You are a research assistant. Answer the given sub-question concisely and "
    "accurately. Use the provided context of already-answered sub-questions to "
    "avoid repetition."
)

_SYNTHESIZE_SYSTEM = (
    "You are a synthesis expert. Given a main question, a list of sub-questions, "
    "and their answers, produce a clear and complete final answer to the main "
    "question. Use all provided information."
)


@dataclass
class SubQuestion:
    """A single decomposed sub-question and its answer."""

    question: str
    answer: str


@dataclass
class SelfAskResult:
    """The outcome of a self-ask run."""

    answer: str
    sub_questions: list[SubQuestion]
    trace: Trace


def run_self_ask(
    question: str,
    client: LLMClient,
    *,
    max_sub_questions: int = 5,
    trace: Trace | None = None,
) -> SelfAskResult:
    """Decompose ``question`` into sub-questions, answer each, then synthesize.

    Returns a :class:`SelfAskResult` with the final answer, individual
    sub-question/answer pairs, and the execution trace.
    """
    trace = trace or Trace(title=f"Self-Ask · {question}")

    # --- Step 1: Decompose ---------------------------------------------------
    decompose_system = _DECOMPOSE_SYSTEM.format(max_sub_questions=max_sub_questions)
    decompose_messages: list[Message] = [
        Message(
            role="user",
            content=f"{decompose_system}\n\nQuestion: {question}",
        )
    ]

    start = time.perf_counter()
    decompose_response = client.complete(decompose_messages)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    trace.record_usage(decompose_response.usage)

    raw_text = decompose_response.text.strip()
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, list):
            sub_qs: list[str] = [str(item) for item in parsed[:max_sub_questions]]
        else:
            sub_qs = [raw_text]
    except (json.JSONDecodeError, ValueError):
        # Fallback: treat the whole response as a single sub-question.
        sub_qs = [raw_text]

    trace.add(
        "plan",
        f"{len(sub_qs)} sub-questions",
        detail="\n".join(f"  {i+1}. {q}" for i, q in enumerate(sub_qs)),
        duration_ms=elapsed_ms,
    )

    # --- Step 2: Answer each sub-question ------------------------------------
    answered: list[SubQuestion] = []

    for sub_q in sub_qs:
        context_lines = [
            f"Q: {sq.question}\nA: {sq.answer}" for sq in answered
        ]
        context_block = "\n\n".join(context_lines)
        if context_block:
            user_content = (
                f"{_SUB_ANSWER_SYSTEM}\n\n"
                f"Context (already answered):\n{context_block}\n\n"
                f"Sub-question: {sub_q}"
            )
        else:
            user_content = f"{_SUB_ANSWER_SYSTEM}\n\nSub-question: {sub_q}"

        sub_messages: list[Message] = [Message(role="user", content=user_content)]

        start = time.perf_counter()
        sub_response = client.complete(sub_messages)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        trace.record_usage(sub_response.usage)

        sub_answer = sub_response.text.strip()
        answered.append(SubQuestion(question=sub_q, answer=sub_answer))
        trace.add(
            "sub_question",
            sub_q,
            detail=sub_answer,
            duration_ms=elapsed_ms,
        )

    # --- Step 3: Synthesize --------------------------------------------------
    qa_block = "\n\n".join(
        f"Sub-question: {sq.question}\nAnswer: {sq.answer}" for sq in answered
    )
    synth_content = (
        f"{_SYNTHESIZE_SYSTEM}\n\n"
        f"Main question: {question}\n\n"
        f"{qa_block}"
    )
    synth_messages: list[Message] = [Message(role="user", content=synth_content)]

    start = time.perf_counter()
    synth_response = client.complete(synth_messages)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    trace.record_usage(synth_response.usage)

    final_answer = synth_response.text.strip()
    trace.add("answer", final_answer, duration_ms=elapsed_ms)

    return SelfAskResult(
        answer=final_answer,
        sub_questions=answered,
        trace=trace,
    )
