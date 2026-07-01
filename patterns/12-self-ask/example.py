"""Runnable Self-Ask demo — offline mock mode.

Run it with no API key:

    python patterns/12-self-ask/example.py

Scripts a 5-call conversation: decompose into 3 sub-questions, answer each,
then synthesize a final answer. With ``ANTHROPIC_API_KEY`` set (and ``USE_MOCK``
unset) the very same pattern code runs against the live model instead.
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

from pattern import run_self_ask  # noqa: E402  (sibling module)


# --- Deterministic mock planner --------------------------------------------


def make_planner() -> Any:
    """Return a planner that scripts the demo conversation.

    call 0 → JSON array of sub-questions (decompose)
    call 1 → "Paris"                      (sub-q 1 answer)
    call 2 → "~2.1 million"               (sub-q 2 answer)
    call 3 → "987 AD"                     (sub-q 3 answer)
    call 4 → final synthesis answer
    """

    call_count = [0]

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        usage = Usage(input_tokens=80, output_tokens=20)
        n = call_count[0]
        call_count[0] += 1

        if n == 0:
            return LLMResponse(
                text='["What is the capital of France?", "What is its population?", "When did it become the capital?"]',
                stop_reason="end_turn",
                usage=usage,
            )
        if n == 1:
            return LLMResponse(
                text="Paris",
                stop_reason="end_turn",
                usage=usage,
            )
        if n == 2:
            return LLMResponse(
                text="~2.1 million",
                stop_reason="end_turn",
                usage=usage,
            )
        if n == 3:
            return LLMResponse(
                text="987 AD",
                stop_reason="end_turn",
                usage=usage,
            )
        return LLMResponse(
            text=(
                "The capital of France is Paris, which became the capital in 987 AD. "
                "Its current population is approximately 2.1 million."
            ),
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


def main() -> None:
    question = "What is the population of the capital of France, and what year did it become the capital?"
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())

    result = run_self_ask(question, client, max_sub_questions=5)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    result.trace.render(console)
    console.print(f"\n[bold green]Answer:[/bold green] {result.answer}\n")
    console.print("[bold]Sub-questions:[/bold]")
    for i, sq in enumerate(result.sub_questions, 1):
        console.print(f"  {i}. [cyan]{sq.question}[/cyan] → {sq.answer}")
    console.print()


if __name__ == "__main__":
    main()
