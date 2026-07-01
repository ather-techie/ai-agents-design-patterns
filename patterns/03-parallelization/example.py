"""Runnable parallelization demo — three-angle analysis in offline mock mode.

Run it with no API key:

    python patterns/03-parallelization/example.py

Three branches analyse "Should remote work become the default?" simultaneously
from different perspectives (advocate, skeptic, neutral expert). A fourth LLM
call aggregates their outputs into one coherent answer. With
``ANTHROPIC_API_KEY`` set (and ``USE_MOCK`` unset) the very same pattern code
runs against the live model instead.
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

from pattern import Branch, run_parallelization  # noqa: E402  (sibling module)

# --- Scripted responses for mock mode --------------------------------------

_PRO_ANSWER = (
    "Remote work offers three clear benefits: "
    "(1) it eliminates commute time, boosting productivity and well-being; "
    "(2) it expands the talent pool beyond geographic constraints; "
    "(3) it reduces office overhead costs for employers."
)

_ANTI_ANSWER = (
    "Remote work carries serious risks: "
    "(1) collaboration and spontaneous knowledge-sharing suffer without shared physical space; "
    "(2) junior employees lose mentorship opportunities that come from in-person proximity; "
    "(3) the boundary between work and home life erodes, raising burnout risk."
)

_NEUTRAL_ANSWER = (
    "The evidence is mixed. Remote work raises individual productivity for focused tasks "
    "but can weaken team cohesion over time. Hybrid models — two to three days in-office — "
    "tend to balance flexibility with collaboration needs. Any policy should account for "
    "role type, team size, and individual circumstances."
)

_AGGREGATE_ANSWER = (
    "Remote work's value depends heavily on context. Advocates rightly highlight productivity "
    "gains and talent-pool expansion, while skeptics flag real collaboration and mentorship "
    "costs. The neutral evidence points toward hybrid arrangements as the pragmatic default: "
    "flexible enough to capture remote benefits, structured enough to preserve team cohesion."
)


def make_planner() -> Any:
    """Return a deterministic planner that scripts the demo responses.

    Branch calls are detected by keywords in the system-prompt prefix; the
    aggregation call is detected by the presence of 'Synthesize' in the content.
    """

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        content = messages[-1].content if messages else ""
        usage = Usage(input_tokens=200, output_tokens=60)

        if "Synthesize" in content or "independent analyses" in content:
            return LLMResponse(text=_AGGREGATE_ANSWER, usage=usage)
        if "advocate" in content:
            return LLMResponse(text=_PRO_ANSWER, usage=usage)
        if "skeptical" in content:
            return LLMResponse(text=_ANTI_ANSWER, usage=usage)
        if "neutral" in content:
            return LLMResponse(text=_NEUTRAL_ANSWER, usage=usage)

        # Fallback: generic answer (should not be reached in normal demo flow).
        return LLMResponse(text="No scripted answer available.", usage=usage)

    return planner


# --- Demo ------------------------------------------------------------------

TASK = "Should remote work become the default for office-based roles?"

BRANCHES = [
    Branch(
        name="pro_remote",
        system_prompt="You are an advocate for remote work. Give 2-3 key benefits.",
    ),
    Branch(
        name="anti_remote",
        system_prompt="You are skeptical of remote work. Give 2-3 key concerns.",
    ),
    Branch(
        name="balanced",
        system_prompt="You are a neutral HR expert. Give a balanced 2-3 point perspective.",
    ),
]


def main() -> None:
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())

    result = run_parallelization(TASK, BRANCHES, client)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"[bold]Task:[/bold] {TASK}\n")

    console.print("[bold cyan]Branch answers:[/bold cyan]")
    for name, text in result.answers.items():
        console.print(f"  [green]{name}[/green]: {text}\n")

    result.trace.render(console)
    console.print(f"\n[bold green]Aggregate answer:[/bold green] {result.aggregate}\n")


if __name__ == "__main__":
    main()
