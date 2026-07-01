"""Runnable Memory-Augmented Agent demo — offline mock mode.

Run it with no API key:

    python patterns/11-memory/example.py

Scripts a three-turn conversation: the agent remembers a fact, recalls it, then
uses it to produce a final answer. With ``ANTHROPIC_API_KEY`` set (and
``USE_MOCK`` unset) the very same pattern code runs against the live model.
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
from shared.tools import ToolRegistry  # noqa: E402
from shared.types import LLMResponse, Message, ToolCall, Usage  # noqa: E402

from pattern import MemoryStore, run_memory_agent  # noqa: E402  (sibling module)


# --- Deterministic mock planner --------------------------------------------


def make_planner() -> Any:
    """Return a planner that scripts a 3-turn memory demo.

    Turn 1: call remember(key="france", content="capital is Paris")
    Turn 2: call recall(query="france")
    Turn 3: return final answer using the recalled fact
    """

    call_count = [0]

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        usage = Usage(input_tokens=100, output_tokens=25)
        n = call_count[0]
        call_count[0] += 1

        if n == 0:
            return LLMResponse(
                text="I'll store the capital of France in memory first.",
                tool_calls=[
                    ToolCall(
                        id="m1",
                        name="remember",
                        arguments={"key": "france", "content": "capital is Paris"},
                    )
                ],
                stop_reason="tool_use",
                usage=usage,
            )
        if n == 1:
            return LLMResponse(
                text="Good. Now let me recall what I know about France.",
                tool_calls=[
                    ToolCall(
                        id="m2",
                        name="recall",
                        arguments={"query": "france"},
                    )
                ],
                stop_reason="tool_use",
                usage=usage,
            )
        return LLMResponse(
            text="Based on my memory, the capital of France is Paris.",
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


def main() -> None:
    task = "What is the capital of France? Use your memory tools."
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())
    registry = ToolRegistry()
    store = MemoryStore()

    result = run_memory_agent(task, registry, client, store, max_steps=config.max_steps)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    result.trace.render(console)
    console.print(f"\n[bold green]Answer:[/bold green] {result.answer}\n")
    console.print(f"[dim]Memory snapshot: {result.store.snapshot()}[/dim]\n")


if __name__ == "__main__":
    main()
