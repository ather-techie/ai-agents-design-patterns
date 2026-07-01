"""Orchestrator-Workers: a central LLM plans, then delegates to specialists.

The orchestrator receives the full task and a menu of available workers. It
emits a JSON plan that assigns subtasks to named workers; the framework
dispatches each subtask to the matching worker client. Finally the orchestrator
synthesizes all results into a single answer.

Workers are fully isolated — each sees only its own subtask, not the whole
conversation — which keeps context small and specialisation crisp.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from shared.errors import AgentError
from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message, Usage

_PLAN_PROMPT = """\
You are an orchestrator. Break the task into subtasks for the available workers.
Respond with valid JSON only: {{"assignments": [{{"worker": "<name>", "subtask": "<description>"}}, ...]}}.

Available workers:
{worker_list}

Task: {task}"""

_SYNTHESIS_PROMPT = """\
You received these worker results:
{results_block}

Synthesize them into a final, coherent answer for the original task: {task}"""


@dataclass
class Worker:
    """A named, specialised LLM worker."""

    name: str
    specialty: str  # shown to the orchestrator so it knows what this worker can do
    client: LLMClient


@dataclass
class OrchestratorResult:
    """The outcome of an orchestrator-workers run."""

    plan: str
    worker_results: dict[str, str]  # worker name -> result
    synthesis: str
    trace: Trace


def run_orchestrator_workers(
    task: str,
    orchestrator: LLMClient,
    workers: list[Worker],
    *,
    trace: Trace | None = None,
) -> OrchestratorResult:
    """Run the orchestrator-workers pattern and return results + trace.

    1. The orchestrator LLM is asked to produce a JSON plan assigning subtasks
       to named workers.
    2. Each assignment is dispatched to the matching worker; results collected.
    3. The orchestrator synthesizes all worker results into a final answer.

    Raises :class:`~shared.errors.AgentError` if ``workers`` is empty.
    """
    if not workers:
        raise AgentError("at least one worker required")

    trace = trace or Trace(title=f"Orchestrator-Workers · {task[:60]}")
    total_usage = Usage()

    # ------------------------------------------------------------------ #
    # 1. Plan phase                                                        #
    # ------------------------------------------------------------------ #
    worker_list = "\n".join(f"- {w.name}: {w.specialty}" for w in workers)
    plan_prompt = _PLAN_PROMPT.format(worker_list=worker_list, task=task)

    plan_start = time.perf_counter()
    plan_response = orchestrator.complete([Message(role="user", content=plan_prompt)])
    plan_elapsed_ms = (time.perf_counter() - plan_start) * 1000.0
    total_usage = total_usage + plan_response.usage

    plan_text = plan_response.text

    try:
        plan_data = json.loads(plan_text)
        assignments: list[dict] = plan_data.get("assignments", [])
    except (json.JSONDecodeError, AttributeError):
        # Fallback: assign the full task to every worker.
        assignments = [{"worker": w.name, "subtask": task} for w in workers]

    trace.add(
        "plan",
        f"orchestrator produced {len(assignments)}-step plan",
        plan_text,
        duration_ms=plan_elapsed_ms,
    )

    # ------------------------------------------------------------------ #
    # 2. Delegate phase                                                    #
    # ------------------------------------------------------------------ #
    worker_map = {w.name: w for w in workers}
    worker_results: dict[str, str] = {}

    for assignment in assignments:
        worker_name = assignment.get("worker", "")
        subtask = assignment.get("subtask", task)

        if worker_name not in worker_map:
            trace.add(
                "observation",
                f"unknown worker: {worker_name}",
                is_error=True,
            )
            continue

        trace.add("delegate", f"-> {worker_name}: {subtask[:60]}")

        worker = worker_map[worker_name]
        worker_start = time.perf_counter()
        worker_response = worker.client.complete(
            [Message(role="user", content=f"Your task: {subtask}")]
        )
        worker_elapsed_ms = (time.perf_counter() - worker_start) * 1000.0
        total_usage = total_usage + worker_response.usage

        result_text = worker_response.text
        worker_results[worker_name] = result_text

        trace.add(
            "worker",
            f"[{worker_name}] {result_text[:80]}",
            duration_ms=worker_elapsed_ms,
        )

    # ------------------------------------------------------------------ #
    # 3. Synthesize phase                                                  #
    # ------------------------------------------------------------------ #
    results_block = "\n\n".join(
        f"=== {name} ===\n{text}" for name, text in worker_results.items()
    )
    synthesis_prompt = _SYNTHESIS_PROMPT.format(results_block=results_block, task=task)

    synth_start = time.perf_counter()
    synth_response = orchestrator.complete(
        [Message(role="user", content=synthesis_prompt)]
    )
    synth_elapsed_ms = (time.perf_counter() - synth_start) * 1000.0
    total_usage = total_usage + synth_response.usage

    synthesis = synth_response.text

    trace.record_usage(total_usage)
    trace.add("answer", synthesis, duration_ms=synth_elapsed_ms)

    return OrchestratorResult(
        plan=plan_text,
        worker_results=worker_results,
        synthesis=synthesis,
        trace=trace,
    )
