"""Runnable ReAct demo — calculator + search, in offline mock mode.

Run it with no API key:

    python patterns/07-react/example.py

It scripts a two-tool conversation through the deterministic mock client and
prints the reasoning -> tool -> observation trace tree. With ``ANTHROPIC_API_KEY``
set (and ``USE_MOCK`` unset) the very same pattern code runs against the live
model instead.
"""

from __future__ import annotations

import ast
import operator
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

from pattern import run_react  # noqa: E402  (sibling module, run by file path)

# --- Tools ------------------------------------------------------------------

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(node: ast.AST) -> float:
    """Evaluate a parsed arithmetic expression without using ``eval``."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression."""
    result = _safe_eval(ast.parse(expression, mode="eval"))
    return str(int(result) if result == int(result) else result)


_FACTS = {
    "capital of france": "Paris",
    "capital of japan": "Tokyo",
}


def search(query: str) -> str:
    """Look up a fact (a stand-in for a real web search)."""
    return _FACTS.get(query.strip().lower(), "no result found")


def build_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            Tool(
                name="calculator",
                description="Evaluate a basic arithmetic expression.",
                input_schema={
                    "type": "object",
                    "properties": {"expression": {"type": "string"}},
                    "required": ["expression"],
                },
                handler=calculator,
            ),
            Tool(
                name="search",
                description="Look up a fact by query.",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                handler=search,
            ),
        ]
    )


# --- Deterministic mock planner --------------------------------------------


def make_planner() -> Any:
    """Return a planner that scripts the demo conversation.

    State is derived from how many tool results are already in the history, so
    the same planner drives every step without external mutable state leaking
    between runs.
    """

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        tool_results = sum(1 for m in messages if m.role == "tool")
        usage = Usage(input_tokens=120, output_tokens=30)
        if tool_results == 0:
            return LLMResponse(
                text="I need the product 25 * 17 first.",
                tool_calls=[ToolCall(id="c1", name="calculator", arguments={"expression": "25 * 17"})],
                stop_reason="tool_use",
                usage=usage,
            )
        if tool_results == 1:
            return LLMResponse(
                text="Now I'll look up the capital of France.",
                tool_calls=[ToolCall(id="c2", name="search", arguments={"query": "capital of France"})],
                stop_reason="tool_use",
                usage=usage,
            )
        return LLMResponse(
            text="25 * 17 = 425, and the capital of France is Paris.",
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


def main() -> None:
    task = "What is 25 * 17, and what is the capital of France?"
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())
    registry = build_registry()

    result = run_react(task, registry, client, max_steps=config.max_steps)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    result.trace.render(console)
    console.print(f"\n[bold green]Answer:[/bold green] {result.answer}\n")


if __name__ == "__main__":
    main()
