"""State Machine Agent: route an agent through an explicit FSM.

Each :class:`State` has a handler that processes the current input and
accumulated context, and a list of allowed transitions to other states. An LLM
picks the next transition after each handler runs. The loop terminates when a
terminal state is reached or ``max_transitions`` is exceeded.

The function depends only on the :class:`~shared.llm_client.LLMClient` protocol
so it runs unchanged against the live Anthropic client or the offline mock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from shared.errors import AgentError, MaxStepsExceeded
from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message


class StateError(AgentError):
    """Raised when the FSM enters an invalid or unknown state."""


@dataclass
class State:
    """A node in the state machine."""

    name: str
    description: str
    handler: Callable[[str, str], str]   # (input, accumulated_context) -> output
    transitions: list[str]               # allowed next state names (empty = terminal)
    terminal: bool = False


@dataclass
class StateMachineResult:
    """The outcome of a state machine run."""

    answer: str
    trace: Trace
    states_visited: list[str]


def run_state_machine(
    input: str,
    states: list[State],
    client: LLMClient,
    *,
    initial_state: str,
    max_transitions: int = 10,
    trace: Trace | None = None,
) -> StateMachineResult:
    """Drive ``input`` through the FSM and return the final answer + trace.

    Raises :class:`StateError` if an unknown state name is encountered.
    Raises :class:`MaxStepsExceeded` if ``max_transitions`` is reached before a
    terminal state.
    """
    trace = trace or Trace(title=f"StateMachine · {input}")
    state_map = {s.name: s for s in states}
    states_visited: list[str] = []
    accumulated_context = ""
    current_name = initial_state

    if current_name not in state_map:
        raise StateError(f"unknown initial state: {current_name!r}")

    for _ in range(max_transitions):
        state = state_map[current_name]
        states_visited.append(current_name)

        start = time.perf_counter()
        output = state.handler(input, accumulated_context)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        trace.add(
            "transition",
            f"{state.name}: {output[:80]}",
            duration_ms=elapsed_ms,
        )

        if state.terminal or not state.transitions:
            trace.add("answer", output)
            return StateMachineResult(
                answer=output,
                trace=trace,
                states_visited=states_visited,
            )

        accumulated_context = (accumulated_context + "\n" + output).strip()

        transitions_list = "\n".join(f"- {t}" for t in state.transitions)
        prompt = (
            f"You just completed state '{state.name}'.\n"
            f"Output: {output}\n\n"
            f"Available next states:\n{transitions_list}\n\n"
            f"Reply with exactly one state name from the list above."
        )
        messages: list[Message] = [Message(role="user", content=prompt)]

        llm_start = time.perf_counter()
        response = client.complete(messages)
        llm_elapsed_ms = (time.perf_counter() - llm_start) * 1000.0
        trace.record_usage(response.usage)

        next_name = response.text.strip()
        matched = next(
            (t for t in state.transitions if t.lower() == next_name.lower()),
            None,
        )
        if matched is None:
            raise StateError(f"invalid transition: {next_name!r}")

        trace.add(
            "reasoning",
            f"-> {matched}",
            duration_ms=llm_elapsed_ms,
        )
        current_name = matched

    raise MaxStepsExceeded(max_transitions)
