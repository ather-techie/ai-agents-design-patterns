"""Orchestrator-Workers demo — market analysis of electric vehicles, offline.

Run it with no API key:

    python patterns/04-orchestrator-workers/example.py

An orchestrator LLM breaks the task into three subtasks (research, analysis,
writing) and dispatches each to a specialist worker. The trace shows the plan,
each delegation, each worker result, and the final synthesis. With
``ANTHROPIC_API_KEY`` set, the same code runs against the live model.
"""

from __future__ import annotations

import json
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
from shared.llm_client import MockClient, build_client  # noqa: E402
from shared.types import LLMResponse, Message, Usage  # noqa: E402

from pattern import Worker, run_orchestrator_workers  # noqa: E402


_TASK = "Prepare a brief market analysis of electric vehicles"

_PLAN = json.dumps({
    "assignments": [
        {"worker": "researcher", "subtask": "Find the latest EV market size, growth rate, and key players"},
        {"worker": "analyst", "subtask": "Identify the main opportunities and risks in the EV market"},
        {"worker": "writer", "subtask": "Write a polished two-paragraph market analysis summary"},
    ]
})

_ORCHESTRATOR_SYNTHESIS = (
    "The electric vehicle market is experiencing rapid growth, driven by strong "
    "consumer demand and supportive government policy. Key players like Tesla, BYD, "
    "and legacy OEMs are competing for share in a market projected to exceed $1 trillion "
    "by 2030. While raw-material constraints and infrastructure gaps pose near-term "
    "risks, the long-term trajectory points firmly toward widespread electrification."
)

_RESEARCHER_RESPONSE = (
    "The global EV market was valued at ~$388 billion in 2023 and is projected to grow "
    "at a CAGR of ~18% through 2030. Leading players include Tesla, BYD, Volkswagen, "
    "GM, and a cohort of Chinese start-ups."
)

_ANALYST_RESPONSE = (
    "Opportunities: falling battery costs, rising fuel prices, regulatory mandates, and "
    "expanding charging networks. Risks: lithium and cobalt supply constraints, longer "
    "charging times versus ICE refuelling, and uncertainty around consumer adoption in "
    "emerging markets."
)

_WRITER_RESPONSE = (
    "Electric vehicles are reshaping the automotive landscape. Backed by regulatory "
    "tailwinds and steadily improving economics, EV adoption is accelerating globally. "
    "Market leaders are investing heavily in battery technology and manufacturing scale, "
    "while new entrants challenge incumbents with software-defined vehicle architectures."
)


def _make_orchestrator_planner() -> Any:
    """Scripted orchestrator: returns JSON plan first, synthesis on the second call."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        last = messages[-1].content
        if "Synthesize" in last:
            return LLMResponse(
                text=_ORCHESTRATOR_SYNTHESIS,
                usage=Usage(input_tokens=120, output_tokens=60),
            )
        return LLMResponse(text=_PLAN, usage=Usage(input_tokens=80, output_tokens=40))

    return planner


def _worker_planner(response: str) -> Any:
    def planner(_messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text=response, usage=Usage(input_tokens=50, output_tokens=30))

    return planner


def main() -> None:
    config = Config.from_env()

    if config.use_mock:
        orchestrator_client = MockClient(_make_orchestrator_planner(), model="mock:orchestrator")
        researcher_client = MockClient(_worker_planner(_RESEARCHER_RESPONSE), model="mock:researcher")
        analyst_client = MockClient(_worker_planner(_ANALYST_RESPONSE), model="mock:analyst")
        writer_client = MockClient(_worker_planner(_WRITER_RESPONSE), model="mock:writer")
    else:
        orchestrator_client = build_client(config)
        researcher_client = build_client(config)
        analyst_client = build_client(config)
        writer_client = build_client(config)

    workers = [
        Worker("researcher", "finds market data, statistics, and key players", researcher_client),
        Worker("analyst", "identifies opportunities, risks, and strategic implications", analyst_client),
        Worker("writer", "synthesizes findings into polished prose", writer_client),
    ]

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"[bold]Task:[/bold] {_TASK}\n")

    result = run_orchestrator_workers(_TASK, orchestrator_client, workers)
    result.trace.render(console)

    console.print("\n[bold green]Final Answer:[/bold green]")
    console.print(result.synthesis)


if __name__ == "__main__":
    main()
