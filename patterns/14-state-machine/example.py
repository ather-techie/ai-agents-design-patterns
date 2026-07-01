"""Runnable State Machine demo — 3-state support ticket FSM, offline mock mode.

Run it with no API key:

    python patterns/14-state-machine/example.py

It scripts a triage -> diagnose -> resolve conversation through the deterministic
mock client and prints the transition trace tree. With ``ANTHROPIC_API_KEY`` set
(and ``USE_MOCK`` unset) the very same pattern code runs against the live model.
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

from pattern import State, run_state_machine  # noqa: E402  (sibling module, run by file path)


# --- States -----------------------------------------------------------------


def triage_handler(input: str, context: str) -> str:
    return f"Ticket received: '{input}'. Severity assessed as HIGH. Routing to diagnostics."


def diagnose_handler(input: str, context: str) -> str:
    return "Root cause identified: authentication service timeout after 30s."


def resolve_handler(input: str, context: str) -> str:
    return (
        "Resolution applied: increased auth service timeout to 120s and restarted pods. "
        "Issue resolved."
    )


def build_states() -> list[State]:
    return [
        State(
            name="triage",
            description="Assess the severity and nature of the incoming ticket.",
            handler=triage_handler,
            transitions=["diagnose"],
            terminal=False,
        ),
        State(
            name="diagnose",
            description="Identify the root cause of the problem.",
            handler=diagnose_handler,
            transitions=["resolve"],
            terminal=False,
        ),
        State(
            name="resolve",
            description="Apply a fix and confirm the issue is resolved.",
            handler=resolve_handler,
            transitions=[],
            terminal=True,
        ),
    ]


# --- Deterministic mock planner --------------------------------------------


def make_planner() -> Any:
    """Return a planner that always picks the first available transition.

    The transition prompt lists each next state as a ``- name`` bullet line.
    We scan for the first such line and return its name.
    """

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        usage = Usage(input_tokens=30, output_tokens=10)
        content = messages[-1].content if messages else ""
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                return LLMResponse(
                    text=stripped[2:].strip(),
                    stop_reason="end_turn",
                    usage=usage,
                )
        return LLMResponse(text="resolve", stop_reason="end_turn", usage=usage)

    return planner


def main() -> None:
    ticket = "Users are unable to log in — getting 504 errors since 09:00 UTC."
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())
    states = build_states()

    result = run_state_machine(
        ticket,
        states,
        client,
        initial_state="triage",
        max_transitions=config.max_steps,
    )

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    result.trace.render(console)
    console.print(f"\n[bold]States visited:[/bold] {' -> '.join(result.states_visited)}")
    console.print(f"\n[bold green]Answer:[/bold green] {result.answer}\n")


if __name__ == "__main__":
    main()
