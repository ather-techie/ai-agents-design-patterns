"""Runnable Mixture-of-Experts demo — legal, medical, financial experts, offline mock.

Run with no API key:

    python patterns/17-mixture-of-experts/example.py

It scripts a multi-expert conversation through the deterministic mock client and
prints the route -> delegate -> synthesis -> answer trace tree. With
``ANTHROPIC_API_KEY`` set (and ``USE_MOCK`` unset) the same pattern code runs
against the live model instead.
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

from pattern import Expert, run_mixture_of_experts  # noqa: E402


# --- Experts ----------------------------------------------------------------


def build_experts() -> list[Expert]:
    return [
        Expert(
            name="legal",
            domain="tax law, deductions, IRS regulations",
            system_prompt=(
                "You are a legal expert specializing in US tax law and IRS regulations. "
                "Provide accurate, concise legal guidance."
            ),
        ),
        Expert(
            name="medical",
            domain="healthcare, medical expenses, health conditions",
            system_prompt=(
                "You are a medical expert. Explain what qualifies as a deductible "
                "medical expense from a clinical perspective."
            ),
        ),
        Expert(
            name="financial",
            domain="personal finance, tax planning, investment strategy",
            system_prompt=(
                "You are a personal finance advisor. Advise on the financial "
                "impact and strategies for medical expense deductions."
            ),
        ),
    ]


# --- Deterministic mock planner ---------------------------------------------


def make_planner() -> Any:
    """Return a planner that scripts the demo conversation.

    Call 0: router selects [legal, medical]
    Call 1: legal expert answer
    Call 2: medical expert answer
    Call 3: synthesis
    """
    call_count = {"n": 0}

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        idx = call_count["n"]
        call_count["n"] += 1
        usage = Usage(input_tokens=100, output_tokens=40)

        if idx == 0:
            return LLMResponse(
                text='["legal", "medical"]',
                stop_reason="end_turn",
                usage=usage,
            )
        if idx == 1:
            return LLMResponse(
                text=(
                    "Under IRC Section 213, medical expenses exceeding 7.5% of "
                    "your adjusted gross income (AGI) are deductible if you itemize. "
                    "Qualifying expenses include diagnosis, treatment, and prevention "
                    "of disease as defined by the IRS."
                ),
                stop_reason="end_turn",
                usage=usage,
            )
        if idx == 2:
            return LLMResponse(
                text=(
                    "Deductible medical expenses typically include payments for "
                    "doctors, hospitals, prescription drugs, and certain medical "
                    "equipment. Cosmetic procedures generally do not qualify unless "
                    "medically necessary."
                ),
                stop_reason="end_turn",
                usage=usage,
            )
        return LLMResponse(
            text=(
                "Yes, you can deduct qualifying medical expenses that exceed 7.5% "
                "of your AGI when you itemize deductions. Qualifying expenses include "
                "payments to doctors, hospitals, and prescriptions, but not cosmetic "
                "procedures. Consult a tax professional to maximize your deduction."
            ),
            stop_reason="end_turn",
            usage=usage,
        )

    return planner


def main() -> None:
    query = "Can I deduct medical expenses from my taxes?"
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())
    experts = build_experts()

    result = run_mixture_of_experts(query, experts, client, top_k=2)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"[bold]Query:[/bold] {query}")
    console.print(f"[bold]Selected experts:[/bold] {', '.join(result.selected_experts)}")
    result.trace.render(console)
    console.print(f"\n[bold green]Synthesis:[/bold green] {result.synthesis}\n")


if __name__ == "__main__":
    main()
