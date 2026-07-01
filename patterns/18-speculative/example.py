"""Runnable Speculative Execution demo — prime-check candidates, offline mock.

Run with no API key:

    python patterns/18-speculative/example.py

It scripts a 3-candidate, 3-score conversation through the deterministic mock
client and prints the candidate -> critique -> answer trace tree. With
``ANTHROPIC_API_KEY`` set (and ``USE_MOCK`` unset) the same pattern code runs
against the live model instead.
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

from pattern import run_speculative  # noqa: E402


# --- Deterministic mock planner ---------------------------------------------

_CANDIDATES = [
    """\
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, n):
        if n % i == 0:
            return False
    return True""",
    """\
def is_prime(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True""",
    """\
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True""",
]

_SCORES = [
    "SCORE: 7.0\nRATIONALE: Correct but O(n) — too slow for large numbers.",
    "SCORE: 9.5\nRATIONALE: Correct and efficient — O(sqrt(n)) with even-number shortcut.",
    "SCORE: 8.0\nRATIONALE: Correct and O(sqrt(n)) but misses the even-number fast path.",
]


def make_planner() -> Any:
    """Return a planner that scripts the demo conversation.

    Calls 0-2: three different candidate answers.
    Calls 3-5: three scores where candidate 2 scores highest (9.5).
    """
    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        usage = Usage(input_tokens=120, output_tokens=50)

        if idx < 3:
            return LLMResponse(
                text=_CANDIDATES[idx],
                stop_reason="end_turn",
                usage=usage,
            )
        score_idx = idx - 3
        return LLMResponse(
            text=_SCORES[score_idx],
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


def main() -> None:
    task = "Write a Python function to check if a number is prime."
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())

    result = run_speculative(task, client, n_candidates=3)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"[bold]Task:[/bold] {task}")
    console.print(f"[bold]Winner score:[/bold] {result.winner.score}")
    result.trace.render(console)
    console.print(f"\n[bold green]Winning solution:[/bold green]\n{result.winner.content}\n")
    console.print(f"[bold]Rationale:[/bold] {result.winner.rationale}\n")


if __name__ == "__main__":
    main()
