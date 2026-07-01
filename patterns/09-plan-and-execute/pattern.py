"""Plan-and-Execute: separate planning from execution in three distinct phases.

Unlike ReAct (07), which interleaves reasoning and acting step-by-step, this
pattern separates concerns into three sequential phases:

  Phase 1 — Plan:    The model produces a complete numbered plan upfront.
  Phase 2 — Execute: Each plan step is executed independently (with tools).
  Phase 3 — Synthesize: All step results are combined into a final answer.

Key tradeoff vs. ReAct
----------------------
ReAct adapts dynamically: each observation can change the next action.
Plan-and-Execute commits to a plan before any execution begins, which means:
  + The plan is inspectable and validatable before costly steps run.
  + Sub-steps are independent, making parallelism or human review easy.
  - The plan cannot adapt to surprising intermediate results.
  - Works best for tasks with predictable, enumerable sub-steps.

Use ReAct when the number of steps is unknown or depends on intermediate
results. Use Plan-and-Execute when upfront planning adds clarity or safety.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from shared.llm_client import LLMClient
from shared.tools import ToolRegistry
from shared.trace import Trace
from shared.types import Message


@dataclass
class PlanStep:
    """A single step in the model-generated plan."""

    index: int
    description: str


@dataclass
class PlanExecuteResult:
    """The outcome of a Plan-and-Execute run."""

    plan: list[PlanStep]
    step_results: list[str]  # one result per plan step
    answer: str
    trace: Trace


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_PLANNING_PROMPT = """\
Create a step-by-step plan to complete the task below.
Output ONLY a numbered list, one step per line, like:
1. First step
2. Second step
...

Keep it to at most {max_plan_steps} steps. Be specific and actionable.

Task: {task}"""

_EXECUTION_PROMPT = """\
Execute this step of the plan: {step_description}

Context: You are working on: {task}"""

_SYNTHESIS_PROMPT = """\
You completed these steps:
{numbered_results}

Provide a concise final answer for the original task: {task}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_plan(text: str) -> list[PlanStep]:
    """Parse a numbered list response into PlanStep objects.

    Accepts lines like "1. First step" or "2. Second step". Falls back to
    treating the entire response as a single step if no numbered lines found.
    """
    steps: list[PlanStep] = []
    for line in text.splitlines():
        line = line.strip()
        # Match lines starting with digit(s) + period + space
        if len(line) >= 3 and line[0].isdigit():
            dot_pos = line.index(".") if "." in line else -1
            if dot_pos > 0 and dot_pos < len(line) - 1 and line[:dot_pos].isdigit():
                description = line[dot_pos + 1:].strip()
                if description:
                    steps.append(PlanStep(index=len(steps) + 1, description=description))
    if not steps:
        # Fallback: treat the whole response as a single step
        steps.append(PlanStep(index=1, description=text.strip()))
    return steps


def _execute_step(
    step: PlanStep,
    task: str,
    registry: ToolRegistry,
    client: LLMClient,
    trace: Trace,
) -> str:
    """Execute one plan step, handling any tool calls the model makes.

    Mirrors the ReAct tool loop but is scoped to a single plan step.
    Returns the final text result for the step.
    """
    tools = registry.definitions() or None
    messages: list[Message] = [
        Message(
            role="user",
            content=_EXECUTION_PROMPT.format(
                step_description=step.description,
                task=task,
            ),
        )
    ]

    # Inner tool loop — continue until the model stops calling tools
    while True:
        start = time.perf_counter()
        response = client.complete(messages, tools)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        trace.record_usage(response.usage)

        if not response.wants_tools:
            # Model is done with this step
            return response.text or "(no result)"

        # Record the assistant turn so tool_result blocks resolve correctly
        messages.append(
            Message(role="assistant", content=response.text, tool_calls=response.tool_calls)
        )

        for call in response.tool_calls:
            arg_str = ", ".join(f"{k}={v!r}" for k, v in call.arguments.items())
            trace.add("tool_call", f"{call.name}({arg_str})", duration_ms=elapsed_ms)
            result = registry.call(call.name, call.arguments, call.id)
            trace.add(
                "observation",
                f"{call.name} -> {result.content}",
                is_error=result.is_error,
            )
            messages.append(
                Message(
                    role="tool",
                    content=result.content,
                    tool_call_id=call.id,
                    name=call.name,
                )
            )
        # Reset elapsed_ms for subsequent iterations (will be updated on next complete())
        elapsed_ms = 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_plan_and_execute(
    task: str,
    registry: ToolRegistry,
    client: LLMClient,
    *,
    max_plan_steps: int = 6,
    trace: Trace | None = None,
) -> PlanExecuteResult:
    """Run the Plan-and-Execute loop for ``task`` and return the result + trace.

    Three phases:
      1. Planning  — ask the model for a numbered step list; parse into PlanSteps.
      2. Execution — for each step, call the model (with tools); record result.
      3. Synthesis — ask the model to combine all step results into a final answer.
    """
    trace = trace or Trace(title=f"Plan-and-Execute · {task}")

    # ------------------------------------------------------------------
    # Phase 1: Planning
    # ------------------------------------------------------------------
    planning_messages: list[Message] = [
        Message(
            role="user",
            content=_PLANNING_PROMPT.format(max_plan_steps=max_plan_steps, task=task),
        )
    ]

    plan_start = time.perf_counter()
    plan_response = client.complete(planning_messages)
    plan_elapsed_ms = (time.perf_counter() - plan_start) * 1000.0
    trace.record_usage(plan_response.usage)

    plan = _parse_plan(plan_response.text)
    trace.add(
        "plan",
        f"planned {len(plan)} steps",
        detail=plan_response.text,
        duration_ms=plan_elapsed_ms,
    )

    # ------------------------------------------------------------------
    # Phase 2: Execution
    # ------------------------------------------------------------------
    step_results: list[str] = []

    for step in plan:
        result_text = _execute_step(step, task, registry, client, trace)
        trace.add("reasoning", f"step {step.index}: {result_text[:80]}")
        step_results.append(result_text)

    # ------------------------------------------------------------------
    # Phase 3: Synthesis
    # ------------------------------------------------------------------
    numbered_results = "\n".join(
        f"{i + 1}. {res}" for i, res in enumerate(step_results)
    )
    synthesis_messages: list[Message] = [
        Message(
            role="user",
            content=_SYNTHESIS_PROMPT.format(
                numbered_results=numbered_results,
                task=task,
            ),
        )
    ]

    synth_start = time.perf_counter()
    synth_response = client.complete(synthesis_messages)
    synth_elapsed_ms = (time.perf_counter() - synth_start) * 1000.0
    trace.record_usage(synth_response.usage)

    synthesis = synth_response.text or "(no synthesis)"
    trace.add("answer", synthesis, duration_ms=synth_elapsed_ms)

    return PlanExecuteResult(
        plan=plan,
        step_results=step_results,
        answer=synthesis,
        trace=trace,
    )
