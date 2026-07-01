"""Memory-Augmented Agent: ReAct loop with episodic memory tools.

The agent has a persistent :class:`MemoryStore` it can write to and read from
via three first-class tools — ``remember``, ``recall``, and ``forget``. Before
each run a snapshot of current memory is injected into the system prompt so the
model starts with full context; memory tool calls are recorded with the
dedicated ``"memory"`` step kind to keep them visually distinct from regular
observations in the trace tree.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from shared.errors import MaxStepsExceeded
from shared.llm_client import LLMClient
from shared.tools import Tool, ToolRegistry
from shared.trace import Trace
from shared.types import Message

SYSTEM_PROMPT = (
    "You are a memory-augmented ReAct agent. You have access to an episodic "
    "memory store via three tools: remember (store a fact), recall (search "
    "memory by keyword), and forget (remove a memory entry). Use memory to "
    "persist facts across turns. After each tool result decide whether you have "
    "enough information. When you do, reply with a final answer and no tool call."
)


@dataclass
class MemoryStore:
    """A simple key-value episodic memory store."""

    _entries: dict[str, str] = field(default_factory=dict)

    def remember(self, key: str, content: str) -> str:
        """Store a fact under ``key`` and return a confirmation string."""
        self._entries[key] = content
        return f"Remembered '{key}': {content}"

    def recall(self, query: str) -> str:
        """Search memory for entries whose key or content contains ``query``."""
        query_lower = query.lower()
        matches = {
            k: v
            for k, v in self._entries.items()
            if query_lower in k.lower() or query_lower in v.lower()
        }
        if not matches:
            return "No matching memories found."
        lines = [f"{k}: {v}" for k, v in matches.items()]
        return "\n".join(lines)

    def forget(self, key: str) -> str:
        """Remove the entry at ``key`` and return a confirmation string."""
        if key in self._entries:
            del self._entries[key]
            return f"Forgot '{key}'."
        return f"No memory entry found for '{key}'."

    def snapshot(self) -> str:
        """Return all current entries as a formatted string."""
        if not self._entries:
            return "(memory is empty)"
        lines = [f"{k}: {v}" for k, v in self._entries.items()]
        return "\n".join(lines)


def _register_memory_tools(store: MemoryStore, registry: ToolRegistry) -> None:
    """Add remember/recall/forget tools backed by ``store`` into ``registry``."""
    registry.register(
        Tool(
            name="remember",
            description="Store a fact in memory under a key.",
            input_schema={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["key", "content"],
            },
            handler=store.remember,
        )
    )
    registry.register(
        Tool(
            name="recall",
            description="Search memory by keyword and return matching entries.",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            handler=store.recall,
        )
    )
    registry.register(
        Tool(
            name="forget",
            description="Remove a memory entry by key.",
            input_schema={
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
            handler=store.forget,
        )
    )


_MEMORY_TOOL_NAMES = {"remember", "recall", "forget"}


@dataclass
class MemoryResult:
    """The outcome of a memory-augmented agent run."""

    answer: str
    trace: Trace
    store: MemoryStore


def run_memory_agent(
    task: str,
    registry: ToolRegistry,
    client: LLMClient,
    store: MemoryStore,
    *,
    max_steps: int = 8,
    trace: Trace | None = None,
) -> MemoryResult:
    """Run the memory-augmented ReAct loop and return the final answer + trace.

    Memory tools are auto-registered into ``registry``. A snapshot of current
    memory is prepended to the task prompt. Memory tool results use the
    ``"memory"`` step kind; other tool results use ``"observation"``.

    Raises :class:`MaxStepsExceeded` if the model keeps calling tools past
    ``max_steps`` without producing a final answer.
    """
    trace = trace or Trace(title=f"Memory Agent · {task}")
    _register_memory_tools(store, registry)
    tools = registry.definitions()

    memory_context = store.snapshot()
    user_content = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Current memory snapshot:\n{memory_context}\n\n"
        f"Task: {task}"
    )
    messages: list[Message] = [Message(role="user", content=user_content)]

    for _ in range(max_steps):
        start = time.perf_counter()
        response = client.complete(messages, tools)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        trace.record_usage(response.usage)

        if response.text:
            trace.add("reasoning", response.text, duration_ms=elapsed_ms)

        if not response.wants_tools:
            trace.add("answer", response.text or "(no answer text)")
            return MemoryResult(answer=response.text, trace=trace, store=store)

        messages.append(
            Message(role="assistant", content=response.text, tool_calls=response.tool_calls)
        )

        for call in response.tool_calls:
            arg_str = ", ".join(f"{k}={v!r}" for k, v in call.arguments.items())
            trace.add("tool_call", f"{call.name}({arg_str})")
            result = registry.call(call.name, call.arguments, call.id)
            step_kind = "memory" if call.name in _MEMORY_TOOL_NAMES else "observation"
            trace.add(
                step_kind,
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
