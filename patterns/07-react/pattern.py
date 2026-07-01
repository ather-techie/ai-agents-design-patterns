"""ReAct: interleave reasoning and acting in a bounded loop.

The agent alternates between *reasoning* (the model thinks about what to do) and
*acting* (it calls a tool), feeding each tool's *observation* back into the
context until it produces a final answer or hits a step bound. The loop is
deliberately bounded — ``max_steps`` guarantees termination even if the model
never stops calling tools.

The function depends only on the :class:`~shared.llm_client.LLMClient` protocol
and a :class:`~shared.tools.ToolRegistry`, so it runs unchanged against the live
Anthropic client or the offline mock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from shared.errors import MaxStepsExceeded
from shared.llm_client import LLMClient
from shared.tools import ToolRegistry
from shared.trace import Trace
from shared.types import Message

SYSTEM_PROMPT = (
    "You are a ReAct agent. Reason step by step about the task, then use the "
    "available tools to gather facts. After each tool result, decide whether you "
    "have enough information. When you do, reply with a final answer and no tool "
    "call. Prefer tools over guessing."
)


@dataclass
class ReactResult:
    """The outcome of a ReAct run."""

    answer: str
    trace: Trace
    steps: int


def run_react(
    task: str,
    registry: ToolRegistry,
    client: LLMClient,
    *,
    max_steps: int = 6,
    trace: Trace | None = None,
) -> ReactResult:
    """Run the ReAct loop for ``task`` and return the final answer + trace.

    Raises :class:`MaxStepsExceeded` if the model keeps calling tools past
    ``max_steps`` without producing a final answer.
    """
    trace = trace or Trace(title=f"ReAct · {task}")
    tools = registry.definitions()
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
            return ReactResult(answer=response.text, trace=trace, steps=trace.step_count)

        # Record the assistant turn (with its tool_use blocks) so the next
        # request's tool_result blocks resolve correctly in live mode.
        messages.append(
            Message(role="assistant", content=response.text, tool_calls=response.tool_calls)
        )

        for call in response.tool_calls:
            arg_str = ", ".join(f"{k}={v!r}" for k, v in call.arguments.items())
            trace.add("tool_call", f"{call.name}({arg_str})")
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
