"""Runnable Code Execution demo — factorial via LLM-generated Python, in offline mock mode.

Run it with no API key:

    python patterns/06-code-execution/example.py

The mock LLM returns real, executable Python code. The executor is a *real*
subprocess call, so the math is verified live. With ``ANTHROPIC_API_KEY`` set
(and ``USE_MOCK`` unset) the very same pattern code runs against the live model.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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

from pattern import CodeExecutionResult, run_code_execution  # noqa: E402  (sibling module)


# ---------------------------------------------------------------------------
# Real subprocess executor
# ---------------------------------------------------------------------------

def safe_executor(code: str) -> str:
    """Run *code* in a fresh Python subprocess with a 5-second timeout."""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Mock planner
# ---------------------------------------------------------------------------

def make_planner():
    """Return a planner that serves working Python code then an interpretation."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        last_content = messages[-1].content

        if "Answer the original task" in last_content:
            # Interpretation turn — model has seen the output ("3628800").
            return LLMResponse(
                text="The factorial of 10 is 3,628,800.",
                usage=Usage(input_tokens=80, output_tokens=20),
            )

        # Code-generation turn (first and only, since the code is valid).
        return LLMResponse(
            text="import math\nprint(math.factorial(10))",
            usage=Usage(input_tokens=120, output_tokens=15),
        )

    return planner


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    task = "Write code to calculate the factorial of 10"
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())

    result: CodeExecutionResult = run_code_execution(task, safe_executor, client)

    console = Console()
    console.print(
        f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}"
    )
    console.print(f"[bold]Task:[/bold] {task}\n")
    result.trace.render(console)
    console.print(f"\n[bold]Generated code:[/bold]\n[cyan]{result.code}[/cyan]")
    console.print(f"\n[bold]Execution output:[/bold] {result.output}")
    console.print(f"\n[bold green]Answer:[/bold green] {result.answer}")
    console.print(f"\n[dim]Attempts: {result.attempts}[/dim]\n")


if __name__ == "__main__":
    main()
