"""Multi-Agent demo — blog post outline about the future of AI in healthcare.

Run it with no API key:

    python patterns/10-multi-agent/example.py

A supervisor selects from a pool of three specialized agents (researcher,
critic, writer). Each agent processes the full task through their own role
lens. The trace shows the routing decision, each delegation, each agent
output, and the final synthesis. With ``ANTHROPIC_API_KEY`` set, the same
code runs against the live model.
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

from pattern import Agent, run_multi_agent  # noqa: E402


_TASK = "Write a short blog post outline about the future of AI in healthcare."

_ROUTING = json.dumps({"selected": ["researcher", "critic", "writer"]})

_SUPERVISOR_SYNTHESIS = (
    "Here is a structured blog post outline on the future of AI in healthcare:\n\n"
    "1. Introduction — The AI Revolution in Medicine\n"
    "   - Brief overview of current AI adoption in clinical settings\n"
    "   - Why this moment is pivotal\n\n"
    "2. Key Opportunities (from the researcher)\n"
    "   - Diagnostic imaging and early disease detection\n"
    "   - Drug discovery acceleration\n"
    "   - Personalized treatment plans via genomic analysis\n\n"
    "3. Risks and Challenges (from the critic)\n"
    "   - Data privacy and algorithmic bias\n"
    "   - Regulatory gaps and liability questions\n"
    "   - Risk of over-reliance reducing clinical judgment\n\n"
    "4. The Road Ahead\n"
    "   - Human-AI collaboration as the dominant model\n"
    "   - Policy and ethics as enablers, not blockers\n\n"
    "5. Conclusion — A Healthier Future, With Eyes Open"
)

_RESEARCHER_RESPONSE = (
    "Key facts about AI in healthcare:\n"
    "- AI-assisted imaging detects cancers up to 30% earlier than traditional methods.\n"
    "- Drug discovery timelines can be compressed from ~12 years to under 4 years using\n"
    "  generative AI models.\n"
    "- Predictive analytics reduce hospital readmissions by flagging at-risk patients\n"
    "  before discharge.\n"
    "- Wearable AI monitors chronic conditions (diabetes, heart disease) continuously,\n"
    "  enabling preventive intervention at scale."
)

_CRITIC_RESPONSE = (
    "Potential risks and challenges:\n"
    "- Algorithmic bias: models trained on non-diverse datasets can under-serve minority\n"
    "  populations, perpetuating health disparities.\n"
    "- Data privacy: vast patient datasets required for training raise HIPAA and GDPR\n"
    "  compliance concerns.\n"
    "- Liability gaps: unclear legal accountability when an AI recommendation leads to\n"
    "  patient harm.\n"
    "- Over-reliance risk: clinicians deferring to AI outputs without critical evaluation\n"
    "  could erode diagnostic expertise over time."
)

_WRITER_RESPONSE = (
    "Proposed blog outline structure:\n"
    "1. Hook — a short patient story illustrating AI-aided early diagnosis.\n"
    "2. 'Where We Are Now' — current real-world deployments.\n"
    "3. 'The Promise' — three breakthrough areas with supporting data.\n"
    "4. 'The Pitfalls' — honest look at risks and open questions.\n"
    "5. 'The Path Forward' — policy recommendations and the human-AI balance.\n"
    "6. Call to action — encourage readers to engage with the conversation."
)


def _make_supervisor_planner() -> Any:
    """Scripted supervisor: routing JSON on first call, synthesis on second call."""

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        last = messages[-1].content
        if "Synthesize" in last:
            return LLMResponse(
                text=_SUPERVISOR_SYNTHESIS,
                usage=Usage(input_tokens=120, output_tokens=80),
            )
        return LLMResponse(text=_ROUTING, usage=Usage(input_tokens=60, output_tokens=20))

    return planner


def _agent_planner(response: str) -> Any:
    def planner(_messages: list[Message], _tools: object) -> LLMResponse:
        return LLMResponse(text=response, usage=Usage(input_tokens=50, output_tokens=30))

    return planner


def main() -> None:
    config = Config.from_env()

    if config.use_mock:
        supervisor_client = MockClient(_make_supervisor_planner(), model="mock:supervisor")
        researcher_client = MockClient(_agent_planner(_RESEARCHER_RESPONSE), model="mock:researcher")
        critic_client = MockClient(_agent_planner(_CRITIC_RESPONSE), model="mock:critic")
        writer_client = MockClient(_agent_planner(_WRITER_RESPONSE), model="mock:writer")
    else:
        supervisor_client = build_client(config)
        researcher_client = build_client(config)
        critic_client = build_client(config)
        writer_client = build_client(config)

    agents = [
        Agent(
            "researcher",
            "You are a medical AI researcher. Provide key facts about AI in healthcare.",
            researcher_client,
        ),
        Agent(
            "critic",
            "You are a critical analyst. Identify potential risks and challenges.",
            critic_client,
        ),
        Agent(
            "writer",
            "You are a content writer. Create a structured blog outline.",
            writer_client,
        ),
    ]

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"[bold]Task:[/bold] {_TASK}\n")

    result = run_multi_agent(_TASK, agents, supervisor_client)
    result.trace.render(console)

    console.print("\n[bold green]Final Answer:[/bold green]")
    console.print(result.answer)


if __name__ == "__main__":
    main()
