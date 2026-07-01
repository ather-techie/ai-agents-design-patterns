"""Runnable Constitutional demo — refund policy message, offline mock mode.

Run it with no API key:

    python patterns/16-constitutional/example.py

It scripts draft -> critique-clarity -> critique-brevity -> revision -> answer
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

from pattern import Principle, run_constitutional  # noqa: E402  (sibling module, run by file path)


# --- Deterministic mock planner --------------------------------------------

_SCRIPTED = [
    # 0: initial draft
    (
        "Our refund policy allows customers to return items within 30 days of "
        "purchase, provided they are in original condition. Refunds are processed "
        "within 5-7 business days after we receive the returned item."
    ),
    # 1: critique-clarity
    "The draft is mostly clear but uses the phrase 'original condition' which could "
    "be ambiguous. Specify what this means (e.g., unopened, unused).",
    # 2: critique-brevity
    "The draft is 38 words, slightly over the 50-word limit but still concise. "
    "Consider trimming 'provided they are in original condition' to 'if unused'.",
    # 3: revision
    "Return items within 30 days if unused. Refunds process within 5-7 business days.",
    # 4: answer (final, same as revision in this mock)
    "Return items within 30 days if unused. Refunds process within 5-7 business days.",
]


def make_planner() -> Any:
    """Return a planner that scripts the constitutional review calls."""
    call_index = {"n": 0}

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        idx = call_index["n"]
        call_index["n"] += 1
        usage = Usage(input_tokens=60, output_tokens=30)
        return LLMResponse(
            text=_SCRIPTED[idx % len(_SCRIPTED)],
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


def main() -> None:
    task = "Write a short message explaining our refund policy."
    principles = [
        Principle("clarity", "Must be clear and jargon-free"),
        Principle("brevity", "Must be under 50 words"),
    ]
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())

    result = run_constitutional(task, principles, client, max_revisions=1)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"\n[bold]Task:[/bold] {task}")
    result.trace.render(console)
    console.print(f"\n[bold]Initial draft:[/bold] {result.draft}")
    console.print(f"\n[bold]Revisions:[/bold] {result.revisions}")
    console.print(f"\n[bold green]Final:[/bold green] {result.final}\n")


if __name__ == "__main__":
    main()
