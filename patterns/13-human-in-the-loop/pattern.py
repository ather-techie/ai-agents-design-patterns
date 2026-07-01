"""Human-in-the-Loop: a ReAct agent that pauses for human approval on checkpointed tools.

Before executing any tool whose name appears in ``checkpoints``, the agent
calls :meth:`HumanIO.request` with a prompt describing the pending action. The
human's response is recorded as a ``"human_input"`` trace step. A "no" (or
"abort" or "n") raises :class:`HumanAborted` immediately; any other response
is treated as approval. Non-checkpointed tools execute without interruption.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from shared.errors import AgentError, MaxStepsExceeded
from shared.llm_client import LLMClient
from shared.tools import ToolRegistry
from shared.trace import Trace
from shared.types import Message

SYSTEM_PROMPT = (
    "You are a ReAct agent. Reason step by step about the task, then use the "
    "available tools to gather facts or perform actions. Some tools require "
    "human approval before they execute — you will be notified of the outcome. "
    "When you have enough information, reply with a final answer and no tool call."
)

_REJECT_RESPONSES = {"no", "abort", "n"}


@runtime_checkable
class HumanIO(Protocol):
    """Protocol for anything that can ask a human a yes/no question."""

    def request(self, prompt: str) -> str: ...


class ConsoleHumanIO:
    """Ask the human via the terminal's standard input/output."""

    def request(self, prompt: str) -> str:
        return input(prompt)


class MockHumanIO:
    """Scripted responses for testing and offline demos."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._idx = 0

    def request(self, prompt: str) -> str:
        resp = self._responses[self._idx % len(self._responses)]
        self._idx += 1
        return resp


class HumanAborted(AgentError):
    """Raised when the human rejects a checkpointed tool call."""


@dataclass
class HumanLoopResult:
    """The outcome of a human-in-the-loop agent run."""

    answer: str
    trace: Trace
    human_turns: int


def run_human_in_loop(
    task: str,
    registry: ToolRegistry,
    client: LLMClient,
    human_io: HumanIO,
    *,
    checkpoints: set[str],
    max_steps: int = 6,
    trace: Trace | None = None,
) -> HumanLoopResult:
    """Run a ReAct loop with human approval gates on checkpointed tools.

    Before any tool whose name is in ``checkpoints`` is executed, ``human_io``
    is queried for approval. A rejection raises :class:`HumanAborted`. All other
    tools execute without interruption.

    Raises :class:`MaxStepsExceeded` if the model keeps calling tools past
    ``max_steps`` without producing a final answer.
    """
    trace = trace or Trace(title=f"Human-in-Loop · {task}")
    tools = registry.definitions()
    human_turns = 0

    messages: list[Message] = [
        Message(role="user", content=f"{SYSTEM_PROMPT}\n\nTask: {task}")
    ]

    for _ in range(max_steps):
        start = time.perf_counter()
        response = client.complete(messages, tools)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        trace.record_usage(response.usage)

        if response.text:
            trace.add("reasoning", response.text, duration_ms=elapsed_ms)

        if not response.wants_tools:
            trace.add("answer", response.text or "(no answer text)")
            return HumanLoopResult(
                answer=response.text,
                trace=trace,
                human_turns=human_turns,
            )

        messages.append(
            Message(role="assistant", content=response.text, tool_calls=response.tool_calls)
        )

        for call in response.tool_calls:
            arg_str = ", ".join(f"{k}={v!r}" for k, v in call.arguments.items())
            trace.add("tool_call", f"{call.name}({arg_str})")

            if call.name in checkpoints:
                approval_prompt = f"Approve {call.name}({arg_str})? [yes/no]: "
                human_response = human_io.request(approval_prompt)
                human_turns += 1
                trace.add("human_input", f"human: {human_response}")
                if human_response.strip().lower() in _REJECT_RESPONSES:
                    raise HumanAborted(call.name)

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

    raise MaxStepsExceeded(max_steps)
