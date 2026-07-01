"""Runnable Reflection demo — self-critique loop, in offline mock mode.

Run it with no API key:

    python patterns/08-reflection/example.py

It scripts a draft -> critique -> revision -> NO_CHANGES conversation through
the deterministic mock client and prints the critique-revision trace tree. With
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

from pattern import run_reflection  # noqa: E402  (sibling module, run by file path)


# --- Scripted mock responses ------------------------------------------------

_DRAFT = (
    "Machine learning is a type of artificial intelligence where algorithms "
    "analyze data and improve their performance over time. By training neural "
    "networks on large datasets, these systems can recognize patterns and make "
    "predictions without being explicitly programmed for each task."
)

_CRITIQUE = (
    "The explanation uses too much jargon. Simplify 'algorithms' and remove "
    "'neural networks' — those terms will confuse a non-technical audience. "
    "Also add a relatable everyday analogy."
)

_REVISION = (
    "Machine learning is a way for computers to get better at tasks by "
    "practicing, just like how you improve at a sport the more you play. "
    "Instead of following rigid rules written by a programmer, the computer "
    "studies lots of examples and gradually learns to spot patterns — like "
    "recognising whether an email is spam or flagging unusual bank transactions."
)


def make_planner() -> Any:
    """Return a planner that scripts the four-call demo conversation."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        usage = Usage(input_tokens=120, output_tokens=60)
        if call_count == 1:
            # Initial draft
            return LLMResponse(text=_DRAFT, usage=usage)
        if call_count == 2:
            # First critique: needs simplification
            return LLMResponse(text=_CRITIQUE, usage=usage)
        if call_count == 3:
            # Revision: simpler version
            return LLMResponse(text=_REVISION, usage=usage)
        # Second critique: now it's excellent
        return LLMResponse(text="NO_CHANGES", usage=usage)

    return planner


def main() -> None:
    task = (
        "Write a concise description of machine learning "
        "for a non-technical audience."
    )
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())

    result = run_reflection(task, client, max_iterations=3)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"[bold]Task:[/bold] {task}\n")
    result.trace.render(console)
    console.print(f"\n[bold green]Final answer:[/bold green]\n{result.final}\n")
    console.print(
        f"[dim]Critique-revision cycles: {result.iterations} "
        f"(draft preserved: {result.draft != result.final})[/dim]\n"
    )


if __name__ == "__main__":
    main()
