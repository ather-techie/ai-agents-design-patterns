"""Runnable Evaluator-Optimizer demo — tweet-length launch announcement, offline mock.

Run it with no API key:

    python patterns/05-evaluator-optimizer/example.py

The mock generator starts with a draft that is too long and lacks the @ApexPro
handle. The mock evaluator fails the first draft with a reason, then passes the
revision. The full reasoning trace (draft → critique → revision → answer) is
printed as a rich tree. With ``ANTHROPIC_API_KEY`` set (and ``USE_MOCK`` unset)
the very same pattern code runs against the live model instead.
"""

from __future__ import annotations

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

from pattern import Criterion, run_evaluator_optimizer  # noqa: E402  (sibling module)


# ---------------------------------------------------------------------------
# Mock generator responses
# ---------------------------------------------------------------------------

_GENERATOR_DRAFTS = [
    # Initial draft — too long and missing @ApexPro
    (
        "We are thrilled to announce the brand-new Apex Pro product, a revolutionary "
        "solution for modern professionals everywhere. This is going to change the "
        "game completely."
    ),
    # Revised draft — short, professional, includes @ApexPro
    "Apex Pro is here. Elevate your game. Follow @ApexPro for details. #LaunchDay",
]


def make_generator_planner():
    """Return a generator planner that serves scripted drafts in sequence."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        idx = min(call_count, len(_GENERATOR_DRAFTS) - 1)
        text = _GENERATOR_DRAFTS[idx]
        call_count += 1
        return LLMResponse(text=text, usage=Usage(input_tokens=80, output_tokens=40))

    return planner


# ---------------------------------------------------------------------------
# Mock evaluator responses
# ---------------------------------------------------------------------------

_EVALUATOR_RESPONSES = [
    # First evaluation — draft fails (too long, missing @ApexPro)
    "FAIL: text exceeds 280 characters and does not include @ApexPro",
    # Second evaluation — revision passes
    "PASS",
]


def make_evaluator_planner():
    """Return an evaluator planner that scripts FAIL then PASS."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        idx = min(call_count, len(_EVALUATOR_RESPONSES) - 1)
        text = _EVALUATOR_RESPONSES[idx]
        call_count += 1
        return LLMResponse(text=text, usage=Usage(input_tokens=60, output_tokens=10))

    return planner


# ---------------------------------------------------------------------------
# Criteria
# ---------------------------------------------------------------------------

_CRITERIA = [
    Criterion(description="Under 280 characters"),
    Criterion(description="Professional tone"),
    Criterion(description="Includes @ApexPro"),
]

_TASK = (
    "Write a tweet-length announcement (under 280 characters) for the launch of "
    "'Apex Pro'. The tweet must have a professional tone and include @ApexPro."
)


def main() -> None:
    config = Config.from_env()
    generator = build_client(config, mock_planner=make_generator_planner())
    evaluator = build_client(config, mock_planner=make_evaluator_planner())

    result = run_evaluator_optimizer(
        task=_TASK,
        criteria=_CRITERIA,
        generator=generator,
        evaluator=evaluator,
        max_iterations=3,
    )

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"[bold]Task:[/bold] {_TASK[:80]}...\n")
    result.trace.render(console)
    console.print(
        f"\n[bold]Passed:[/bold] {result.passed}  "
        f"[bold]Iterations:[/bold] {result.iterations}\n"
    )
    console.print(f"[bold green]Final output:[/bold green]\n{result.output}\n")


if __name__ == "__main__":
    main()
