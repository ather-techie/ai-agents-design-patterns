"""Execution tracing and the reasoning -> tool -> observation tree.

Every pattern threads a :class:`Trace` through its run and appends :class:`Step`
objects as it reasons, calls tools, and observes results. ``Trace.render()``
prints the tree the README's hero GIF shows, with per-step timings; ``Trace``
also exposes the aggregate metrics (step count, latency, token usage) the
benchmark harness reports.

Timing uses ``time.perf_counter`` for monotonic, high-resolution durations.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from rich.console import Console
from rich.tree import Tree

from .types import Usage

StepKind = Literal[
    "reasoning", "tool_call", "observation", "answer", "route",
    "plan", "critique", "revision", "delegate", "worker",
    "memory", "human_input", "event", "candidate", "vote",
    "sub_question", "transition",
]

# Label + style per step kind, used when rendering the tree. Plain ASCII tags
# keep the tree readable on every terminal (incl. the Windows cp1252 console).
_STEP_STYLE: dict[StepKind, tuple[str, str]] = {
    "reasoning":   ("reason", "cyan"),
    "tool_call":   ("tool  ", "yellow"),
    "observation": ("obs   ", "green"),
    "route":       ("route ", "magenta"),
    "answer":      ("answer", "bold white"),
    "plan":        ("plan  ", "blue"),
    "critique":    ("crit  ", "red"),
    "revision":    ("rev   ", "cyan"),
    "delegate":    ("deleg ", "yellow"),
    "worker":      ("worker", "green"),
    "memory":      ("mem   ", "bright_blue"),
    "human_input": ("human ", "bright_magenta"),
    "event":       ("event ", "bright_yellow"),
    "candidate":   ("cand  ", "bright_cyan"),
    "vote":        ("vote  ", "bright_green"),
    "sub_question":("sub-q ", "blue"),
    "transition":  ("trans ", "magenta"),
}


@dataclass
class Step:
    """One recorded action in an agent run, with its wall-clock duration."""

    kind: StepKind
    summary: str
    detail: str = ""
    duration_ms: float = 0.0
    is_error: bool = False


@dataclass
class Trace:
    """An ordered record of the steps a pattern took to answer a task."""

    title: str
    steps: list[Step] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    _t0: float = field(default_factory=time.perf_counter, repr=False)

    def add(
        self,
        kind: StepKind,
        summary: str,
        detail: str = "",
        *,
        duration_ms: float = 0.0,
        is_error: bool = False,
    ) -> Step:
        step = Step(kind, summary, detail, duration_ms, is_error)
        self.steps.append(step)
        return step

    def record_usage(self, usage: Usage) -> None:
        self.usage = self.usage + usage

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def total_ms(self) -> float:
        """Total wall-clock time since the trace was created."""
        return (time.perf_counter() - self._t0) * 1000.0

    @property
    def succeeded(self) -> bool:
        """True if the run ended with a non-error ``answer`` step."""
        return any(s.kind == "answer" and not s.is_error for s in self.steps)

    def build_tree(self) -> Tree:
        """Construct the rich :class:`~rich.tree.Tree` for this trace."""
        tree = Tree(f"[bold]{self.title}[/bold]")
        for i, step in enumerate(self.steps, start=1):
            tag, style = _STEP_STYLE.get(step.kind, ("step  ", "white"))
            timing = f" [dim]({step.duration_ms:.0f}ms)[/dim]" if step.duration_ms else ""
            label = f"[{style}]{tag}[/{style}] {step.summary}{timing}"
            node = tree.add(label)
            if step.detail:
                detail_style = "red" if step.is_error else "dim"
                node.add(f"[{detail_style}]{step.detail}[/{detail_style}]")
        footer = (
            f"[dim]{self.step_count} steps · "
            f"{self.usage.total_tokens} tokens · "
            f"{self.total_ms:.0f}ms total[/dim]"
        )
        tree.add(footer)
        return tree

    def render(self, console: Console | None = None) -> None:
        """Print the trace tree to the console."""
        (console or Console()).print(self.build_tree())


class timed_step:
    """Context manager that records a step and times its body.

    Usage::

        with timed_step(trace, "tool_call", "calculator(2+2)") as step:
            result = run_tool(...)
            step.detail = result
    """

    def __init__(self, trace: Trace, kind: StepKind, summary: str, detail: str = "") -> None:
        self._trace = trace
        self._step = Step(kind, summary, detail)
        self._start = 0.0

    def __enter__(self) -> Step:
        self._start = time.perf_counter()
        return self._step

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        self._step.duration_ms = (time.perf_counter() - self._start) * 1000.0
        if exc_type is not None:
            self._step.is_error = True
        self._trace.steps.append(self._step)
        return False
