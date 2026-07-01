"""Multi-Agent: a supervisor routes a task to specialized agents by role.

A pool of named agents is made available to the supervisor. Each agent carries
a ``role`` description (e.g. "You are a medical AI researcher") rather than a
narrow subtask assignment. The supervisor examines the task and returns a JSON
routing decision — ``{"selected": ["researcher", "writer"]}`` — picking which
agents are relevant. Each selected agent then processes the *full* original task
through the lens of its own role, independently of the others. The supervisor
then synthesizes all agent outputs into a final answer.

How this differs from Orchestrator-Workers (pattern 04):
- **04 Orchestrator-Workers**: the orchestrator slices the task into explicit
  *subtasks* and assigns each subtask to a specific worker. Workers receive
  different prompts (their individual subtask).
- **10 Multi-Agent**: the supervisor selects *which agents to involve* based on
  role fit and task requirements. Every selected agent receives the same full
  task (prefixed by their role instruction) — they see the whole problem, not a
  fragment. The value is in diverse *perspectives*, not divided labor.

This pattern suits problems that benefit from multiple expert viewpoints on the
same question (e.g. researcher + critic + writer all thinking about the same
topic) and where the supervisor's job is picking the right mix of perspectives
rather than decomposing the work into non-overlapping pieces.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from shared.errors import AgentError
from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message, Usage

_ROUTING_PROMPT = """\
You are a supervisor. Select which agents should handle this task.
Respond with JSON only: {{"selected": ["<agent_name>", ...]}}

Available agents:
{agent_list}

Task: {task}"""

_SYNTHESIS_PROMPT = """\
You received these agent outputs:
{outputs_block}

Synthesize them into a final answer for the task: {task}"""


@dataclass
class Agent:
    """A named agent with a defined role and its own LLM client."""

    name: str
    role: str       # e.g. "You are a data analyst specializing in market trends"
    client: LLMClient


@dataclass
class MultiAgentResult:
    """The outcome of a multi-agent run."""

    selected_agents: list[str]       # which agents the supervisor selected
    agent_outputs: dict[str, str]    # agent name -> their output
    answer: str
    trace: Trace


def run_multi_agent(
    task: str,
    agents: list[Agent],
    supervisor: LLMClient,
    *,
    trace: Trace | None = None,
) -> MultiAgentResult:
    """Run the multi-agent pattern and return results + trace.

    1. The supervisor selects relevant agents from the pool via JSON routing.
    2. Each selected agent processes the full task through their role lens.
    3. The supervisor synthesizes all agent outputs into a final answer.

    Raises :class:`~shared.errors.AgentError` if ``agents`` is empty.
    """
    if not agents:
        raise AgentError("at least one agent required")

    trace = trace or Trace(title=f"Multi-Agent · {task[:60]}")
    total_usage = Usage()

    # ------------------------------------------------------------------ #
    # 1. Supervisor routing phase                                          #
    # ------------------------------------------------------------------ #
    agent_list = "\n".join(f"- {a.name}: {a.role}" for a in agents)
    routing_prompt = _ROUTING_PROMPT.format(agent_list=agent_list, task=task)

    routing_start = time.perf_counter()
    routing_response = supervisor.complete([Message(role="user", content=routing_prompt)])
    routing_elapsed_ms = (time.perf_counter() - routing_start) * 1000.0
    total_usage = total_usage + routing_response.usage

    routing_text = routing_response.text

    try:
        routing_data = json.loads(routing_text)
        selected: list[str] = routing_data.get("selected", [])
        if not isinstance(selected, list):
            raise ValueError("'selected' must be a list")
    except (json.JSONDecodeError, AttributeError, ValueError):
        # Fallback: use all agents.
        selected = [a.name for a in agents]

    trace.add(
        "plan",
        f"supervisor selected: {', '.join(selected)}",
        routing_text,
        duration_ms=routing_elapsed_ms,
    )

    # ------------------------------------------------------------------ #
    # 2. Agent execution phase                                             #
    # ------------------------------------------------------------------ #
    agent_map = {a.name: a for a in agents}
    agent_outputs: dict[str, str] = {}

    for name in selected:
        if name not in agent_map:
            trace.add("observation", f"unknown agent: {name}", is_error=True)
            continue

        agent = agent_map[name]
        trace.add("delegate", f"-> {agent.name}")

        agent_start = time.perf_counter()
        agent_response = agent.client.complete(
            [Message(role="user", content=f"{agent.role}\n\nTask: {task}")]
        )
        agent_elapsed_ms = (time.perf_counter() - agent_start) * 1000.0
        total_usage = total_usage + agent_response.usage

        output = agent_response.text
        agent_outputs[name] = output

        trace.add(
            "worker",
            f"[{agent.name}] {output[:80]}",
            duration_ms=agent_elapsed_ms,
        )

    # ------------------------------------------------------------------ #
    # 3. Synthesis phase                                                   #
    # ------------------------------------------------------------------ #
    outputs_block = "\n\n".join(
        f"=== {name} ===\n{text}" for name, text in agent_outputs.items()
    )
    synthesis_prompt = _SYNTHESIS_PROMPT.format(outputs_block=outputs_block, task=task)

    synth_start = time.perf_counter()
    synth_response = supervisor.complete(
        [Message(role="user", content=synthesis_prompt)]
    )
    synth_elapsed_ms = (time.perf_counter() - synth_start) * 1000.0
    total_usage = total_usage + synth_response.usage

    answer = synth_response.text

    trace.record_usage(total_usage)
    trace.add("answer", answer, duration_ms=synth_elapsed_ms)

    return MultiAgentResult(
        selected_agents=selected,
        agent_outputs=agent_outputs,
        answer=answer,
        trace=trace,
    )
