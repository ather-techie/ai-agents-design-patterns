"""Routing: classify the input, then dispatch to a specialized handler.

A single classification call decides which downstream handler should answer,
then that handler runs. It's the cheapest useful agent shape — one model call to
route, then deterministic dispatch — and a good baseline to benchmark richer
patterns against.

Like every pattern here, ``run_routing`` depends only on the shared
:class:`~shared.llm_client.LLMClient` protocol, so it runs unchanged against the
live model or the offline mock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from shared.errors import AgentError
from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message

RouteHandler = Callable[[str], str]


@dataclass
class Route:
    """A named destination: a description used for classification + a handler."""

    name: str
    description: str
    handler: RouteHandler


@dataclass
class RoutingResult:
    """The outcome of a routing run."""

    route: str
    answer: str
    trace: Trace


def _classify_prompt(query: str, routes: list[Route]) -> str:
    catalog = "\n".join(f"- {r.name}: {r.description}" for r in routes)
    return (
        "Classify the user's request into exactly one category. Reply with only "
        "the category name.\n\n"
        f"Categories:\n{catalog}\n\n"
        f"Request: {query}\n\nCategory:"
    )


def _match_route(text: str, routes: list[Route]) -> Route | None:
    """Map a classifier response to a route by name (case-insensitive)."""
    cleaned = text.strip().lower()
    for route in routes:
        if route.name.lower() == cleaned:
            return route
    # Fall back to a substring hit, so "Category: billing" still resolves.
    for route in routes:
        if route.name.lower() in cleaned:
            return route
    return None


def run_routing(
    query: str,
    routes: list[Route],
    client: LLMClient,
    *,
    fallback: str | None = None,
    trace: Trace | None = None,
) -> RoutingResult:
    """Classify ``query`` against ``routes`` and dispatch to the chosen handler.

    If classification doesn't match any route, the ``fallback`` route (by name)
    is used; without one, an :class:`AgentError` is raised.
    """
    if not routes:
        raise AgentError("run_routing requires at least one route")

    trace = trace or Trace(title=f"Routing · {query}")

    start = time.perf_counter()
    response = client.complete([Message(role="user", content=_classify_prompt(query, routes))])
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    trace.record_usage(response.usage)

    chosen = _match_route(response.text, routes)
    if chosen is None:
        by_name = {r.name: r for r in routes}
        if fallback and fallback in by_name:
            chosen = by_name[fallback]
            trace.add(
                "route",
                f"unclassified ({response.text.strip()!r}) -> fallback '{chosen.name}'",
                duration_ms=elapsed_ms,
            )
        else:
            raise AgentError(f"could not classify request: {response.text.strip()!r}")
    else:
        trace.add("route", f"classified as '{chosen.name}'", duration_ms=elapsed_ms)

    answer = chosen.handler(query)
    trace.add("answer", answer)
    return RoutingResult(route=chosen.name, answer=answer, trace=trace)
