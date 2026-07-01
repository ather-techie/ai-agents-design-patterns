"""Runnable Debate demo — Python vs JavaScript for backend, offline mock mode.

Run it with no API key:

    python patterns/15-debate/example.py

It scripts a 5-call debate (open-aff, open-neg, rebut-aff, rebut-neg, verdict)
through the deterministic mock client and prints the trace tree. With
``ANTHROPIC_API_KEY`` set (and ``USE_MOCK`` unset) the very same pattern code
runs against the live model.
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

from pattern import run_debate  # noqa: E402  (sibling module, run by file path)


# --- Deterministic mock planner --------------------------------------------

_SCRIPTED = [
    "Python's rich ecosystem of libraries (Django, FastAPI, SQLAlchemy) and "
    "readable syntax make it the superior choice for backend development.",

    "JavaScript with Node.js offers unmatched performance for I/O-heavy workloads "
    "and allows teams to share code between frontend and backend.",

    "While Node.js handles concurrency well, Python's async support (asyncio, "
    "FastAPI) matches it for most use cases, and Python's data science ecosystem "
    "is unrivalled for ML-backed backends.",

    "Python's GIL limits true parallelism, and JavaScript's event loop model is "
    "fundamentally better suited for high-throughput microservices.",

    "Both languages are mature backend choices. Python excels for data-intensive "
    "and ML workloads; JavaScript shines for high-concurrency APIs. The best pick "
    "depends on team expertise and the specific workload.",
]


def make_planner() -> Any:
    """Return a planner that scripts exactly 5 debate calls."""
    call_index = {"n": 0}

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        idx = call_index["n"]
        call_index["n"] += 1
        usage = Usage(input_tokens=80, output_tokens=40)
        return LLMResponse(
            text=_SCRIPTED[idx % len(_SCRIPTED)],
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


def main() -> None:
    proposition = "Python is better than JavaScript for backend development."
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())

    result = run_debate(proposition, client, rounds=2)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"\n[bold]Proposition:[/bold] {result.proposition}")
    result.trace.render(console)
    console.print(f"\n[bold green]Verdict:[/bold green] {result.verdict}\n")


if __name__ == "__main__":
    main()
