"""Runnable Routing demo — support-desk triage, in offline mock mode.

Run it with no API key:

    python patterns/02-routing/example.py

A single classification call routes each request to a billing, technical, or
general handler; the trace shows the routing decision and the answer. With
``ANTHROPIC_API_KEY`` set, the same code routes via the live model.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Make the repo root importable when run by file path (this dir isn't a package).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Render the trace tree as UTF-8 where the terminal allows it (no-op on POSIX).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:  # pragma: no cover - older interpreters / odd streams
    pass

from rich.console import Console  # noqa: E402

from shared.config import Config  # noqa: E402
from shared.llm_client import build_client  # noqa: E402
from shared.types import LLMResponse, Message, Usage  # noqa: E402

from pattern import Route, run_routing  # noqa: E402  (sibling module, run by file path)


def build_routes() -> list[Route]:
    return [
        Route(
            name="billing",
            description="invoices, refunds, charges, payment methods",
            handler=lambda q: "Routed to Billing: I can help with your invoice or refund.",
        ),
        Route(
            name="technical",
            description="errors, bugs, login problems, outages",
            handler=lambda q: "Routed to Technical Support: let's troubleshoot the issue.",
        ),
        Route(
            name="general",
            description="anything else, including greetings and product questions",
            handler=lambda q: "Routed to General: happy to point you in the right direction.",
        ),
    ]


def make_planner() -> Any:
    """Keyword-based stand-in for a model classifier (deterministic, offline)."""

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        # Match only the user's request, not the route descriptions embedded in
        # the classification prompt.
        prompt = messages[-1].content
        text = prompt.split("Request:")[-1].split("Category:")[0].lower()
        if any(w in text for w in ("refund", "invoice", "charge", "payment")):
            label = "billing"
        elif any(w in text for w in ("error", "bug", "login", "down", "crash")):
            label = "technical"
        else:
            label = "general"
        return LLMResponse(text=label, usage=Usage(input_tokens=60, output_tokens=2))

    return planner


def main() -> None:
    queries = [
        "I was charged twice and need a refund",
        "The app crashes every time I log in",
        "Do you offer a student discount?",
    ]
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())
    routes = build_routes()

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    for query in queries:
        result = run_routing(query, routes, client, fallback="general")
        result.trace.render(console)
        console.print(f"[bold green]-> {result.route}:[/bold green] {result.answer}\n")


if __name__ == "__main__":
    main()
