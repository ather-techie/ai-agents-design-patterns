"""Runnable Least-to-Most demo — train distance problem, offline mock.

Run with no API key:

    python patterns/20-least-to-most/example.py

It scripts a decomposition + sequential solve conversation through the
deterministic mock client and prints the plan -> reasoning -> answer trace tree.
With ``ANTHROPIC_API_KEY`` set (and ``USE_MOCK`` unset) the same pattern code
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

from pattern import run_least_to_most  # noqa: E402


# --- Deterministic mock planner ---------------------------------------------

_SUB_PROBLEM_JSON = (
    '["What is the distance for the first leg (60 mph for 2.5 hours)?", '
    '"What is the distance for the second leg (80 mph for 1.5 hours)?", '
    '"What is the total distance?", '
    '"What is the average speed for the entire journey?"]'
)

_ANSWERS = [
    "First leg distance: 60 mph × 2.5 hours = 150 miles.",
    "Second leg distance: 80 mph × 1.5 hours = 120 miles.",
    "Total distance: 150 + 120 = 270 miles.",
    "Total: 270 miles, Average: 270 miles ÷ 4.0 hours = 67.5 mph.",
]


def make_planner() -> Any:
    """Return a planner that scripts the demo conversation.

    Call 0: decomposition JSON with 4 sub-problems.
    Calls 1-4: answers to each sub-problem in order.
    """
    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        usage = Usage(input_tokens=100, output_tokens=50)

        if idx == 0:
            return LLMResponse(
                text=_SUB_PROBLEM_JSON,
                stop_reason="end_turn",
                usage=usage,
            )
        answer_idx = idx - 1
        if answer_idx < len(_ANSWERS):
            return LLMResponse(
                text=_ANSWERS[answer_idx],
                stop_reason="end_turn",
                usage=usage,
            )
        return LLMResponse(
            text="(no further answer needed)",
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


def main() -> None:
    problem = (
        "If a train travels at 60 mph for 2.5 hours, then 80 mph for 1.5 hours, "
        "what is the total distance and average speed?"
    )
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())

    result = run_least_to_most(problem, client, max_sub_problems=5)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"[bold]Problem:[/bold] {problem}")
    console.print(f"[bold]Sub-problems solved:[/bold] {len(result.sub_problems)}")
    result.trace.render(console)
    console.print(f"\n[bold green]Answer:[/bold green] {result.answer}\n")


if __name__ == "__main__":
    main()
