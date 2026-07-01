"""Runnable Prompt Chaining demo — 3-step writing pipeline, in offline mock mode.

Run it with no API key:

    python patterns/01-prompt-chaining/example.py

It scripts a brainstorm -> outline -> draft_intro conversation through the
deterministic mock client and prints the reasoning trace tree. With
``ANTHROPIC_API_KEY`` set (and ``USE_MOCK`` unset) the very same pattern code
runs against the live model instead.
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

from pattern import ChainStep, run_prompt_chain  # noqa: E402  (sibling module)


# --- Scripted mock responses -------------------------------------------------

_STEP_RESPONSES = [
    # Step 1: brainstorm
    (
        "- Reduces carbon emissions\n"
        "- Creates long-term jobs\n"
        "- Lowers energy costs over time\n"
        "- Improves energy security\n"
        "- Drives technological innovation"
    ),
    # Step 2: outline
    (
        "I. Introduction\n"
        "II. Environmental Benefits\n"
        "   A. Reduces carbon emissions\n"
        "   B. Improves air quality\n"
        "III. Economic Benefits\n"
        "   A. Job creation\n"
        "   B. Lower long-term energy costs\n"
        "IV. Strategic Benefits\n"
        "   A. Energy security\n"
        "   B. Technological leadership\n"
        "V. Conclusion"
    ),
    # Step 3: draft_intro
    (
        "Renewable energy stands at the forefront of humanity's response to climate "
        "change, offering a triple dividend of environmental protection, economic "
        "opportunity, and strategic independence. As solar panels blanket rooftops "
        "and wind turbines reshape horizons, the transition away from fossil fuels "
        "promises not only to curb the carbon emissions accelerating global warming "
        "but also to cultivate an entirely new industrial ecosystem—one that creates "
        "durable jobs, slashes long-term energy costs, and frees nations from the "
        "geopolitical volatility of fuel imports."
    ),
]


def make_planner():
    """Return a planner that serves scripted responses in sequence."""
    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        idx = min(call_count, len(_STEP_RESPONSES) - 1)
        text = _STEP_RESPONSES[idx]
        call_count += 1
        return LLMResponse(text=text, usage=Usage(input_tokens=120, output_tokens=60))

    return planner


# --- Pipeline definition -----------------------------------------------------

_STEPS = [
    ChainStep(
        name="brainstorm",
        prompt_template=(
            "Brainstorm 5 key benefits of the following topic as concise bullet points.\n\n"
            "Topic: {input}"
        ),
    ),
    ChainStep(
        name="outline",
        prompt_template=(
            "Turn the following bullet points into a structured essay outline.\n\n"
            "Bullet points:\n{input}"
        ),
    ),
    ChainStep(
        name="draft_intro",
        prompt_template=(
            "Write an engaging introduction paragraph for an essay based on this outline.\n\n"
            "Outline:\n{input}"
        ),
    ),
]


def main() -> None:
    topic = "renewable energy benefits"
    config = Config.from_env()
    client = build_client(config, mock_planner=make_planner())

    result = run_prompt_chain(topic, _STEPS, client)

    console = Console()
    console.print(f"\n[bold]Mode:[/bold] {'mock (offline)' if config.use_mock else 'live'}")
    console.print(f"[bold]Topic:[/bold] {topic}\n")
    result.trace.render(console)
    console.print(f"\n[bold green]Final output:[/bold green]\n{result.output}\n")


if __name__ == "__main__":
    main()
