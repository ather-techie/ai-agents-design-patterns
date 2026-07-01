"""Runnable Human-in-the-Loop demo — offline mock mode.

Run it with no API key:

    python patterns/13-human-in-the-loop/example.py

Scripts a conversation where the agent looks up a contact (no approval needed),
then requests approval to send an email (checkpoint). MockHumanIO approves.
With ``ANTHROPIC_API_KEY`` set (and ``USE_MOCK`` unset) the very same pattern
code runs against the live model instead.
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
from shared.tools import Tool, ToolRegistry  # noqa: E402
from shared.types import LLMResponse, Message, ToolCall, Usage  # noqa: E402

from pattern import MockHumanIO, run_human_in_loop  # noqa: E402  (sibling module)


# --- Tools ------------------------------------------------------------------


def lookup_contact(name: str) -> str:
    """Return a contact's email address by name (stub)."""
    contacts = {"Alice": "alice@example.com", "Bob": "bob@example.com"}
    return contacts.get(name, f"no contact found for '{name}'")


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email (stub — prints instead of actually sending)."""
    return f"Email sent to {to} with subject '{subject}'."


def build_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            Tool(
                name="lookup_contact",
                description="Look up a contact's email address by name.",
                input_schema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
                handler=lookup_contact,
            ),
            Tool(
                name="send_email",
                description="Send an email to an address.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["to", "subject", "body"],
                },
                handler=send_email,
            ),
        ]
    )


# --- Deterministic mock planner --------------------------------------------


def make_planner() -> Any:
    """Return a planner that scripts the demo conversation.

    Turn 1: call lookup_contact(name="Alice")   — no checkpoint
    Turn 2: call send_email(...)                — checkpoint, human approves
    Turn 3: final answer
    """

    call_count = [0]

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        usage = Usage(input_tokens=100, output_tokens=25)
        n = call_count[0]
        call_count[0] += 1

        if n == 0:
            return LLMResponse(
                text="I'll look up Alice's contact details first.",
                tool_calls=[
                    ToolCall(
                        id="t1",
                        name="lookup_contact",
                        arguments={"name": "Alice"},
                    )
                ],
                stop_reason="tool_use",
                usage=usage,
            )
        if n == 1:
            return LLMResponse(
                text="I found Alice's email. Now I'll send the email.",
                tool_calls=[
                    ToolCall(
                        id="t2",
                        name="send_email",
                        arguments={
                            "to": "alice@example.com",
                            "subject": "Hello",
                            "body": "Hi Alice, just checking in!",
                        },
                    )
                ],
                stop_reason="tool_use",
                usage=usage,
            )
        return LLMResponse(
            text="Done. The email has been sent to Alice at alice@example.com.",
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


def main() -> None:
    task = "Send a greeting email to Alice."
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())
    registry = build_registry()
    # Human always approves in the demo.
    human_io = MockHumanIO(responses=["yes"])

    result = run_human_in_loop(
        task,
        registry,
        client,
        human_io,
        checkpoints={"send_email"},
        max_steps=config.max_steps,
    )

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    result.trace.render(console)
    console.print(f"\n[bold green]Answer:[/bold green] {result.answer}")
    console.print(f"[dim]Human approval turns: {result.human_turns}[/dim]\n")


if __name__ == "__main__":
    main()
