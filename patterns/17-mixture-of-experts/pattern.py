"""Mixture-of-Experts: route a query to specialist LLMs and synthesize results.

A router LLM selects the top-k most relevant experts for a query, each expert
answers independently using its own system prompt, and a synthesis call merges
the answers into a single coherent response. This is useful when a query spans
multiple domains and no single expert prompt handles all facets well.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from shared.errors import AgentError
from shared.llm_client import LLMClient
from shared.tools import ToolRegistry
from shared.trace import Trace
from shared.types import Message


class ExpertError(AgentError):
    """Raised when an expert name returned by the router is not registered."""


@dataclass
class Expert:
    """A named specialist with its own system prompt and optional tool registry."""

    name: str
    domain: str
    system_prompt: str
    registry: ToolRegistry | None = None


@dataclass
class MoEResult:
    """The outcome of a Mixture-of-Experts run."""

    selected_experts: list[str]
    expert_answers: dict[str, str]
    synthesis: str
    trace: Trace


def run_mixture_of_experts(
    query: str,
    experts: list[Expert],
    client: LLMClient,
    *,
    top_k: int = 2,
    trace: Trace | None = None,
) -> MoEResult:
    """Route ``query`` to the best ``top_k`` experts and synthesize their answers.

    Raises :class:`ExpertError` if the router selects an expert name that is not
    in the ``experts`` list.
    """
    trace = trace or Trace(title=f"MoE · {query[:60]}")
    expert_map = {e.name: e for e in experts}

    # Step 1: Router call — select top_k experts.
    expert_list = "\n".join(
        f"  - {e.name}: {e.domain}" for e in experts
    )
    router_prompt = (
        f"You are an expert router. Given the query below, select the {top_k} "
        f"most relevant experts to answer it.\n\n"
        f"Available experts:\n{expert_list}\n\n"
        f"Query: {query}\n\n"
        f"Respond with a JSON array of expert names only, e.g. [\"name1\", \"name2\"]."
    )
    router_messages: list[Message] = [Message(role="user", content=router_prompt)]

    start = time.perf_counter()
    router_response = client.complete(router_messages, None)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    trace.record_usage(router_response.usage)

    raw = router_response.text.strip()
    # Extract JSON array from the response (may be wrapped in markdown fences).
    start_idx = raw.find("[")
    end_idx = raw.rfind("]")
    if start_idx != -1 and end_idx != -1:
        raw = raw[start_idx : end_idx + 1]
    selected: list[str] = json.loads(raw)

    # Validate selected names.
    for name in selected:
        if name not in expert_map:
            raise ExpertError(
                f"Router selected unknown expert {name!r}. "
                f"Valid experts: {list(expert_map)}"
            )

    trace.add(
        "route",
        f"selected: {', '.join(selected)}",
        duration_ms=elapsed_ms,
    )

    # Step 2: Each selected expert answers the query.
    expert_answers: dict[str, str] = {}
    for name in selected:
        expert = expert_map[name]
        messages: list[Message] = [
            Message(role="user", content=f"{expert.system_prompt}\n\nQuery: {query}"),
        ]
        start = time.perf_counter()
        response = client.complete(messages, None)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        trace.record_usage(response.usage)
        expert_answers[name] = response.text
        trace.add(
            "delegate",
            f"expert:{expert.name}",
            duration_ms=elapsed_ms,
        )

    # Step 3: Synthesis (or direct passthrough for top_k == 1).
    if top_k == 1 and len(selected) == 1:
        synthesis = expert_answers[selected[0]]
    else:
        answers_block = "\n\n".join(
            f"[{name}]:\n{answer}" for name, answer in expert_answers.items()
        )
        synthesis_prompt = (
            f"You have received answers from multiple experts for the query:\n"
            f"{query}\n\n"
            f"Expert answers:\n{answers_block}\n\n"
            f"Synthesize these into a single, unified answer."
        )
        synthesis_messages: list[Message] = [
            Message(role="user", content=synthesis_prompt)
        ]
        start = time.perf_counter()
        synthesis_response = client.complete(synthesis_messages, None)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        trace.record_usage(synthesis_response.usage)
        synthesis = synthesis_response.text
        trace.add("reasoning", "synthesis", duration_ms=elapsed_ms)

    trace.add("answer", synthesis[:120])

    return MoEResult(
        selected_experts=selected,
        expert_answers=expert_answers,
        synthesis=synthesis,
        trace=trace,
    )
