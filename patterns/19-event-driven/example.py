"""Runnable Event-Driven demo — CPU metric events, offline mock.

Run with no API key:

    python patterns/19-event-driven/example.py

It scripts a 3-event sequence through the deterministic mock client: two metric
events that update state and one report event that produces no tool calls. Then
a final summary is generated. With ``ANTHROPIC_API_KEY`` set (and ``USE_MOCK``
unset) the same pattern code runs against the live model instead.
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

from pattern import AgentState, Event, run_event_driven  # noqa: E402


# --- Deterministic mock planner ---------------------------------------------


def make_planner() -> Any:
    """Return a planner that scripts the demo conversation.

    Event 1 (cpu_usage=95%): agent calls state_set(key=alert, value=cpu_high), then ends.
    Event 2 (cpu_usage=45%): agent calls state_set(key=alert, value=resolved), then ends.
    Event 3 (generate status): agent ends immediately with no tools.
    Final summary: plain text answer.
    """
    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        usage = Usage(input_tokens=80, output_tokens=30)

        tool_results = sum(1 for m in messages if m.role == "tool")

        # Detect which event we're processing from the user message content.
        user_content = ""
        for m in messages:
            if m.role == "user":
                user_content = m.content
                break

        # Final summary call — no event keyword, just state snapshot.
        if "Summarize what happened" in user_content:
            return LLMResponse(
                text=(
                    "CPU alert was triggered (cpu_high) due to 95% usage, then "
                    "resolved when usage dropped to 45%. Current status: resolved."
                ),
                stop_reason="end_turn",
                usage=usage,
            )

        # Event 1: high CPU — call state_set once.
        if "cpu_usage=95%" in user_content:
            if tool_results == 0:
                return LLMResponse(
                    text="CPU usage is critical. Setting alert.",
                    tool_calls=[
                        ToolCall(
                            id="ss1",
                            name="state_set",
                            arguments={"key": "alert", "value": "cpu_high"},
                        )
                    ],
                    stop_reason="tool_use",
                    usage=usage,
                )
            return LLMResponse(
                text="Alert state updated to cpu_high.",
                stop_reason="end_turn",
                usage=usage,
            )

        # Event 2: low CPU — call state_set once.
        if "cpu_usage=45%" in user_content:
            if tool_results == 0:
                return LLMResponse(
                    text="CPU usage is normal. Resolving alert.",
                    tool_calls=[
                        ToolCall(
                            id="ss2",
                            name="state_set",
                            arguments={"key": "alert", "value": "resolved"},
                        )
                    ],
                    stop_reason="tool_use",
                    usage=usage,
                )
            return LLMResponse(
                text="Alert resolved.",
                stop_reason="end_turn",
                usage=usage,
            )

        # Event 3: report — end immediately.
        return LLMResponse(
            text="Status report: monitoring active.",
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


def main() -> None:
    events = [
        Event(type="metric", payload="cpu_usage=95%"),
        Event(type="metric", payload="cpu_usage=45%"),
        Event(type="report", payload="generate status"),
    ]
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())
    registry = ToolRegistry()

    result = run_event_driven(events, registry, client, max_steps_per_event=4)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"[bold]Events processed:[/bold] {result.events_processed}")
    console.print(f"[bold]Final state:[/bold]\n{result.state.snapshot()}")
    result.trace.render(console)
    console.print(f"\n[bold green]Summary:[/bold green] {result.final_summary}\n")


if __name__ == "__main__":
    main()
