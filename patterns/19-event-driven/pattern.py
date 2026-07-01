"""Event-Driven: process a stream of events with a stateful reactive agent.

Each incoming event triggers a bounded ReAct mini-loop: the agent reads the
current state, calls tools (including ``state_set`` to persist facts), and
reacts to the event payload. State persists across events so the agent can
correlate information — e.g. track alert levels, accumulate counts, or record
outcomes from earlier events. A final summary call reports what happened.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from shared.llm_client import LLMClient
from shared.tools import Tool, ToolRegistry
from shared.trace import Trace
from shared.types import Message


@dataclass
class Event:
    """A single incoming event with a type tag and free-text payload."""

    type: str
    payload: str


@dataclass
class AgentState:
    """Mutable key-value store that persists across events in a run."""

    data: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> str:
        if not self.data:
            return "(empty state)"
        return "\n".join(f"  {k}: {v}" for k, v in self.data.items())


@dataclass
class EventResult:
    """The outcome of an event-driven agent run."""

    final_summary: str
    trace: Trace
    events_processed: int
    state: AgentState


def run_event_driven(
    events: list[Event],
    registry: ToolRegistry,
    client: LLMClient,
    *,
    state: AgentState | None = None,
    max_steps_per_event: int = 4,
    trace: Trace | None = None,
) -> EventResult:
    """Process each event in ``events`` with a stateful ReAct mini-loop.

    A ``state_set(key, value)`` tool is automatically registered alongside any
    tools already in ``registry``. State persists across events so agents can
    correlate information between them.
    """
    trace = trace or Trace(title="Event-Driven Agent")
    state = state or AgentState()

    # Auto-register state_set tool that writes into the shared state dict.
    _build_registry(registry, state)

    if not events:
        trace.add("answer", "No events processed.")
        return EventResult(
            final_summary="No events processed.",
            trace=trace,
            events_processed=0,
            state=state,
        )

    tools = registry.definitions()

    for event in events:
        # Record event step.
        trace.add("event", f"{event.type}: {event.payload[:60]}")

        # Build initial prompt for this event.
        event_prompt = (
            f"Event: {event.type}\n"
            f"Payload: {event.payload}\n\n"
            f"Current state:\n{state.snapshot()}\n\n"
            f"Process this event. Use state_set to persist any important "
            f"information. When finished, reply without calling any tools."
        )
        messages: list[Message] = [Message(role="user", content=event_prompt)]

        # Bounded ReAct mini-loop for this event.
        for _ in range(max_steps_per_event):
            start = time.perf_counter()
            response = client.complete(messages, tools)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            trace.record_usage(response.usage)

            if not response.wants_tools:
                break

            # Record the assistant turn with tool calls.
            messages.append(
                Message(
                    role="assistant",
                    content=response.text,
                    tool_calls=response.tool_calls,
                )
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

    # Final summary after all events.
    summary_prompt = (
        f"Given the following state after processing all events:\n"
        f"{state.snapshot()}\n\n"
        f"Summarize what happened and the current status."
    )
    summary_messages: list[Message] = [Message(role="user", content=summary_prompt)]
    start = time.perf_counter()
    summary_response = client.complete(summary_messages, None)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    trace.record_usage(summary_response.usage)
    final_summary = summary_response.text
    trace.add("answer", final_summary[:120], duration_ms=elapsed_ms)

    return EventResult(
        final_summary=final_summary,
        trace=trace,
        events_processed=len(events),
        state=state,
    )


def _build_registry(registry: ToolRegistry, state: AgentState) -> None:
    """Add the ``state_set`` tool to ``registry`` if not already present."""
    if "state_set" in registry:
        return

    def state_set(key: str, value: str) -> str:
        state.data[key] = value
        return f"state[{key!r}] = {value!r}"

    registry.register(
        Tool(
            name="state_set",
            description="Persist a key-value pair in the agent's state.",
            input_schema={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
            handler=state_set,
        )
    )
