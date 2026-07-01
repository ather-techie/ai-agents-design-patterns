"""Runnable Plan-and-Execute demo — Tokyo population lookup, in offline mock mode.

Run it with no API key:

    python patterns/09-plan-and-execute/example.py

It scripts a three-phase conversation through the deterministic mock client and
prints the plan -> execution -> synthesis trace tree. With ``ANTHROPIC_API_KEY``
set (and ``USE_MOCK`` unset) the very same pattern code runs against the live
model instead.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Make the repo root importable when run by file path (this dir is not a package).
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

from pattern import run_plan_and_execute  # noqa: E402  (sibling module, run by file path)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def lookup(query: str) -> str:
    """Mock lookup tool — returns a fixed population fact for any query."""
    return "Tokyo population: 13,960,000"


def build_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            Tool(
                name="lookup",
                description="Look up a population or demographic fact.",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                handler=lookup,
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Deterministic mock planner
# ---------------------------------------------------------------------------

_PLAN_TEXT = (
    "1. Look up Tokyo's current population\n"
    "2. Convert the population figure to millions\n"
    "3. Summarize the result"
)


def make_planner() -> Any:
    """Return a planner that scripts the three-phase demo conversation.

    Phase 1 (planning): detected by "Create a step-by-step plan" in the prompt.
    Phase 2 (execution): step 1 triggers the lookup tool; subsequent steps
      return text after the tool result arrives.
    Phase 3 (synthesis): detected by "Provide a concise final answer" in the prompt.
    """
    call_count = 0

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        nonlocal call_count
        call_count += 1

        usage = Usage(input_tokens=120, output_tokens=30)
        last_content = messages[-1].content if messages else ""

        # Phase 3: synthesis
        if "Provide a concise final answer" in last_content:
            return LLMResponse(
                text=(
                    "Tokyo's population is approximately 13,960,000, "
                    "which is roughly 13.96 million people."
                ),
                stop_reason="end_turn",
                usage=usage,
            )

        # Phase 1: planning (first call, contains the planning prompt keyword)
        if "Create a step-by-step plan" in last_content:
            return LLMResponse(
                text=_PLAN_TEXT,
                stop_reason="end_turn",
                usage=usage,
            )

        # Phase 2: execution calls
        # If there's already a tool result in the conversation, return text
        if any(m.role == "tool" for m in messages):
            tool_result = next(m.content for m in messages if m.role == "tool")
            return LLMResponse(
                text=f"The lookup returned: {tool_result}. Step complete.",
                stop_reason="end_turn",
                usage=usage,
            )

        # First execution call (step 1 — lookup): trigger the lookup tool
        if "Look up Tokyo" in last_content:
            return LLMResponse(
                text="I will look up Tokyo's population now.",
                tool_calls=[
                    ToolCall(
                        id="lk1",
                        name="lookup",
                        arguments={"query": "Tokyo population"},
                    )
                ],
                stop_reason="tool_use",
                usage=usage,
            )

        # Other execution steps (convert, summarize): return plain text
        return LLMResponse(
            text=f"Step completed (call {call_count}).",
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    task = "Find the population of Tokyo and convert it to millions."
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())
    registry = build_registry()

    result = run_plan_and_execute(task, registry, client, max_plan_steps=4)

    console = Console()
    console.print(
        f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}"
    )
    console.print("\n[bold]Plan:[/bold]")
    for step in result.plan:
        console.print(f"  {step.index}. {step.description}")
    result.trace.render(console)
    console.print(f"\n[bold green]Answer:[/bold green] {result.answer}\n")


if __name__ == "__main__":
    main()
