"""Comparison harness: run one task-set through every pattern, print the table.

This is the README's headline feature — *which pattern, and why*. It runs the
same support-style task-set through all 20 patterns in offline mock mode and
prints a single table of the tradeoffs: steps, tokens, latency, and success
rate per pattern. Reading metrics straight off each run's `Trace` means the
patterns are benchmarked exactly as they ship — no instrumentation bolted on.

    python -m bench.compare      # or: make bench
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Render the comparison table as UTF-8 where the terminal allows it.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:  # pragma: no cover - older interpreters / odd streams
    pass

from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

from shared.llm_client import MockClient  # noqa: E402
from shared.loader import load_pattern_module  # noqa: E402
from shared.tools import Tool, ToolRegistry  # noqa: E402
from shared.trace import Trace  # noqa: E402
from shared.types import LLMResponse, Message, ToolCall, Usage  # noqa: E402

react = load_pattern_module("07-react")
routing = load_pattern_module("02-routing")
chain = load_pattern_module("01-prompt-chaining")
para = load_pattern_module("03-parallelization")
ow = load_pattern_module("04-orchestrator-workers")
eo = load_pattern_module("05-evaluator-optimizer")
ce = load_pattern_module("06-code-execution")
ref = load_pattern_module("08-reflection")
pe = load_pattern_module("09-plan-and-execute")
ma = load_pattern_module("10-multi-agent")
mem = load_pattern_module("11-memory")
sa = load_pattern_module("12-self-ask")
human = load_pattern_module("13-human-in-the-loop")
sm = load_pattern_module("14-state-machine")
debate = load_pattern_module("15-debate")
const = load_pattern_module("16-constitutional")
moe = load_pattern_module("17-mixture-of-experts")
spec = load_pattern_module("18-speculative")
ed = load_pattern_module("19-event-driven")
ltm = load_pattern_module("20-least-to-most")

# Shared task-set — the same requests run through every pattern.
TASKS = [
    "I was double charged, can I get a refund?",
    "The dashboard throws a 500 error on login.",
    "What plans do you offer?",
    "My invoice total looks wrong.",
]


@dataclass
class PatternStats:
    """Aggregated metrics for one pattern across the whole task-set."""

    name: str
    runs: int
    successes: int
    total_steps: int
    total_tokens: int
    total_ms: float

    @property
    def avg_steps(self) -> float:
        return self.total_steps / self.runs if self.runs else 0.0

    @property
    def avg_tokens(self) -> float:
        return self.total_tokens / self.runs if self.runs else 0.0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.runs if self.runs else 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / self.runs if self.runs else 0.0


def _aggregate(name: str, traces: list[Trace]) -> PatternStats:
    return PatternStats(
        name=name,
        runs=len(traces),
        successes=sum(1 for t in traces if t.succeeded),
        total_steps=sum(t.step_count for t in traces),
        total_tokens=sum(t.usage.total_tokens for t in traces),
        total_ms=sum(t.total_ms for t in traces),
    )


# --- ReAct (07) -------------------------------------------------------------


def _react_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            Tool(
                name="lookup",
                description="Look up account or product info.",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                handler=lambda query: f"(info about: {query})",
            )
        ]
    )


def _react_planner(messages: list[Message], _tools: Any) -> LLMResponse:
    usage = Usage(input_tokens=140, output_tokens=40)
    if any(m.role == "tool" for m in messages):
        return LLMResponse(text="Here's what I found and recommend.", stop_reason="end_turn", usage=usage)
    return LLMResponse(
        text="Let me look that up first.",
        tool_calls=[ToolCall(id="r1", name="lookup", arguments={"query": "account"})],
        stop_reason="tool_use",
        usage=usage,
    )


def _run_react() -> list[Trace]:
    registry = _react_registry()
    traces: list[Trace] = []
    for task in TASKS:
        client = MockClient(_react_planner)
        result = react.run_react(task, registry, client, max_steps=6)
        traces.append(result.trace)
    return traces


# --- Routing (02) -----------------------------------------------------------


def _routes() -> list:
    Route = routing.Route
    return [
        Route("billing", "invoices, refunds, charges", lambda q: "Billing will assist you."),
        Route("technical", "errors, bugs, outages", lambda q: "Technical support will assist you."),
        Route("general", "anything else", lambda q: "Here's some general guidance."),
    ]


def _routing_planner(messages: list[Message], _tools: Any) -> LLMResponse:
    # Match only the user's request, not the route descriptions in the prompt.
    prompt = messages[-1].content
    text = prompt.split("Request:")[-1].split("Category:")[0].lower()
    if any(w in text for w in ("refund", "invoice", "charge")):
        label = "billing"
    elif any(w in text for w in ("error", "500", "bug", "login")):
        label = "technical"
    else:
        label = "general"
    return LLMResponse(text=label, usage=Usage(input_tokens=70, output_tokens=2))


def _run_routing() -> list[Trace]:
    routes = _routes()
    traces: list[Trace] = []
    for task in TASKS:
        client = MockClient(_routing_planner)
        result = routing.run_routing(task, routes, client, fallback="general")
        traces.append(result.trace)
    return traces


# --- Prompt Chaining (01) ---------------------------------------------------


def _run_prompt_chaining() -> list[Trace]:
    steps = [
        chain.ChainStep("analyze", "Identify the key issue in: {input}"),
        chain.ChainStep("respond", "Write a helpful response to: {input}"),
    ]

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        return LLMResponse(text="Processed output.", usage=Usage(input_tokens=60, output_tokens=20))

    traces: list[Trace] = []
    for task in TASKS:
        result = chain.run_prompt_chain(task, steps, MockClient(planner))
        traces.append(result.trace)
    return traces


# --- Parallelization (03) ---------------------------------------------------


def _run_parallelization() -> list[Trace]:
    branches = [
        para.Branch("analyst", "You are a support analyst. Analyze the issue."),
        para.Branch("advisor", "You are a customer advisor. Draft a response."),
    ]

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        return LLMResponse(text="Branch output.", usage=Usage(input_tokens=80, output_tokens=25))

    traces: list[Trace] = []
    for task in TASKS:
        result = para.run_parallelization(task, branches, MockClient(planner))
        traces.append(result.trace)
    return traces


# --- Orchestrator-Workers (04) ----------------------------------------------


def _run_orchestrator_workers() -> list[Trace]:
    def make_orch_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            calls[0] += 1
            usage = Usage(input_tokens=100, output_tokens=30)
            if calls[0] == 1:
                return LLMResponse(
                    text='{"assignments": [{"worker": "support", "subtask": "handle this customer request"}]}',
                    usage=usage,
                )
            return LLMResponse(text="Here is the synthesized answer.", usage=usage)

        return planner

    def worker_planner(messages: list[Message], _tools: Any) -> LLMResponse:
        return LLMResponse(text="I have handled this request.", usage=Usage(input_tokens=70, output_tokens=20))

    traces: list[Trace] = []
    for task in TASKS:
        workers = [ow.Worker("support", "customer support specialist", MockClient(worker_planner))]
        result = ow.run_orchestrator_workers(task, MockClient(make_orch_planner()), workers)
        traces.append(result.trace)
    return traces


# --- Evaluator-Optimizer (05) -----------------------------------------------


def _run_evaluator_optimizer() -> list[Trace]:
    criteria = [eo.Criterion("Response is helpful and professional")]

    def gen_planner(messages: list[Message], _tools: Any) -> LLMResponse:
        return LLMResponse(text="Here is a helpful response.", usage=Usage(input_tokens=70, output_tokens=25))

    def eval_planner(messages: list[Message], _tools: Any) -> LLMResponse:
        return LLMResponse(text="PASS", usage=Usage(input_tokens=90, output_tokens=5))

    traces: list[Trace] = []
    for task in TASKS:
        result = eo.run_evaluator_optimizer(
            task, criteria, MockClient(gen_planner), MockClient(eval_planner)
        )
        traces.append(result.trace)
    return traces


# --- Code Execution (06) ----------------------------------------------------


def _run_code_execution() -> list[Trace]:
    def executor(code: str) -> str:
        return "42"

    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            calls[0] += 1
            usage = Usage(input_tokens=80, output_tokens=30)
            if calls[0] == 1:
                return LLMResponse(text="print(42)", usage=usage)
            return LLMResponse(text="The computed result is 42.", usage=usage)

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        result = ce.run_code_execution(task, executor, MockClient(make_planner()), max_attempts=3)
        traces.append(result.trace)
    return traces


# --- Reflection (08) --------------------------------------------------------


def _run_reflection() -> list[Trace]:
    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            calls[0] += 1
            usage = Usage(input_tokens=80, output_tokens=25)
            if calls[0] == 1:
                return LLMResponse(text="Here is my helpful response.", usage=usage)
            return LLMResponse(text="NO_CHANGES", usage=usage)

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        result = ref.run_reflection(task, MockClient(make_planner()), max_iterations=3)
        traces.append(result.trace)
    return traces


# --- Plan-and-Execute (09) --------------------------------------------------


def _run_plan_and_execute() -> list[Trace]:
    _registry = ToolRegistry(
        [
            Tool(
                name="lookup",
                description="Look up account or product info.",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                handler=lambda query: f"(info about: {query})",
            )
        ]
    )

    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            calls[0] += 1
            usage = Usage(input_tokens=100, output_tokens=35)
            if calls[0] == 1:
                return LLMResponse(
                    text="1. Identify the issue\n2. Find a resolution\n3. Provide a recommendation",
                    usage=usage,
                )
            if calls[0] <= 4:
                return LLMResponse(text=f"Completed step {calls[0] - 1}.", usage=usage)
            return LLMResponse(text="Based on the analysis, here is the final answer.", usage=usage)

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        result = pe.run_plan_and_execute(task, _registry, MockClient(make_planner()), max_plan_steps=3)
        traces.append(result.trace)
    return traces


# --- Multi-Agent (10) -------------------------------------------------------


def _run_multi_agent() -> list[Trace]:
    def make_supervisor_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            calls[0] += 1
            usage = Usage(input_tokens=90, output_tokens=20)
            if calls[0] == 1:
                return LLMResponse(text='{"selected": ["support"]}', usage=usage)
            return LLMResponse(text="Here is the synthesized response.", usage=usage)

        return planner

    def agent_planner(messages: list[Message], _tools: Any) -> LLMResponse:
        return LLMResponse(text="I can help with this request.", usage=Usage(input_tokens=70, output_tokens=20))

    traces: list[Trace] = []
    for task in TASKS:
        supervisor = MockClient(make_supervisor_planner())
        agents = [ma.Agent("support", "You are a customer support specialist.", MockClient(agent_planner))]
        result = ma.run_multi_agent(task, agents, supervisor)
        traces.append(result.trace)
    return traces


# --- Memory (11) ------------------------------------------------------------


def _run_memory() -> list[Trace]:
    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            n = calls[0]
            calls[0] += 1
            usage = Usage(input_tokens=100, output_tokens=25)
            if n == 0:
                return LLMResponse(
                    text="Storing the request in memory.",
                    tool_calls=[
                        ToolCall(
                            id="m1",
                            name="remember",
                            arguments={"key": "request", "content": "customer issue"},
                        )
                    ],
                    stop_reason="tool_use",
                    usage=usage,
                )
            return LLMResponse(
                text="Based on memory, here is the answer.", stop_reason="end_turn", usage=usage
            )

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        store = mem.MemoryStore()
        registry = ToolRegistry()
        result = mem.run_memory_agent(task, registry, MockClient(make_planner()), store, max_steps=4)
        traces.append(result.trace)
    return traces


# --- Self-Ask (12) ----------------------------------------------------------


def _run_self_ask() -> list[Trace]:
    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            n = calls[0]
            calls[0] += 1
            usage = Usage(input_tokens=80, output_tokens=20)
            if n == 0:
                return LLMResponse(
                    text='["What is the core issue?", "What is the resolution?"]',
                    stop_reason="end_turn",
                    usage=usage,
                )
            if n <= 2:
                return LLMResponse(
                    text="Sub-question answered.", stop_reason="end_turn", usage=usage
                )
            return LLMResponse(
                text="Based on the analysis, here is the complete answer.",
                stop_reason="end_turn",
                usage=usage,
            )

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        result = sa.run_self_ask(task, MockClient(make_planner()), max_sub_questions=2)
        traces.append(result.trace)
    return traces


# --- Human-in-the-Loop (13) -------------------------------------------------


def _run_human_in_loop() -> list[Trace]:
    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            n = calls[0]
            calls[0] += 1
            usage = Usage(input_tokens=100, output_tokens=25)
            if n == 0:
                return LLMResponse(
                    text="Looking up account info.",
                    tool_calls=[ToolCall(id="h1", name="lookup", arguments={"query": "account"})],
                    stop_reason="tool_use",
                    usage=usage,
                )
            return LLMResponse(
                text="Here is the information.", stop_reason="end_turn", usage=usage
            )

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        registry = ToolRegistry(
            [
                Tool(
                    name="lookup",
                    description="Look up account or product info.",
                    input_schema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                    handler=lambda query: f"(info about: {query})",
                )
            ]
        )
        result = human.run_human_in_loop(
            task,
            registry,
            MockClient(make_planner()),
            human.MockHumanIO(["yes"]),
            checkpoints=set(),
            max_steps=4,
        )
        traces.append(result.trace)
    return traces


# --- State Machine (14) -----------------------------------------------------


def _run_state_machine() -> list[Trace]:
    State = sm.State

    def planner(messages: list[Message], _tools: Any) -> LLMResponse:
        return LLMResponse(
            text="respond", stop_reason="end_turn", usage=Usage(input_tokens=60, output_tokens=5)
        )

    traces: list[Trace] = []
    for task in TASKS:
        states = [
            State(
                "analyze",
                "Analyze the request",
                lambda inp, ctx: f"Analysis: {inp[:30]}",
                transitions=["respond"],
            ),
            State(
                "respond",
                "Generate response",
                lambda inp, ctx: f"Response to: {inp[:30]}",
                transitions=[],
                terminal=True,
            ),
        ]
        result = sm.run_state_machine(
            task, states, MockClient(planner), initial_state="analyze", max_transitions=5
        )
        traces.append(result.trace)
    return traces


# --- Debate (15) ------------------------------------------------------------


def _run_debate() -> list[Trace]:
    _responses = [
        "I strongly argue in favor of this.",
        "I strongly argue against this.",
        "My rebuttal addresses the opposing argument.",
        "I counter the affirmative rebuttal.",
        "After both sides, the balanced answer is: both have merit.",
    ]

    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            n = calls[0]
            calls[0] += 1
            return LLMResponse(
                text=_responses[min(n, len(_responses) - 1)],
                stop_reason="end_turn",
                usage=Usage(input_tokens=90, output_tokens=25),
            )

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        result = debate.run_debate(task, MockClient(make_planner()), rounds=2)
        traces.append(result.trace)
    return traces


# --- Constitutional (16) ----------------------------------------------------


def _run_constitutional() -> list[Trace]:
    principles = [
        const.Principle("helpful", "Response must be helpful."),
        const.Principle("clear", "Response must be clear and concise."),
    ]

    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            n = calls[0]
            calls[0] += 1
            usage = Usage(input_tokens=80, output_tokens=20)
            if n == 0:
                return LLMResponse(
                    text="Here is the initial draft.", stop_reason="end_turn", usage=usage
                )
            if n <= 2:
                return LLMResponse(
                    text="The draft satisfies this principle.", stop_reason="end_turn", usage=usage
                )
            return LLMResponse(
                text="Here is the improved response.", stop_reason="end_turn", usage=usage
            )

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        result = const.run_constitutional(
            task, principles, MockClient(make_planner()), max_revisions=1
        )
        traces.append(result.trace)
    return traces


# --- Mixture-of-Experts (17) ------------------------------------------------


def _run_moe() -> list[Trace]:
    experts = [
        moe.Expert("billing", "billing, refunds, invoices", "You are a billing specialist."),
        moe.Expert(
            "technical",
            "errors, bugs, troubleshooting",
            "You are a technical support specialist.",
        ),
        moe.Expert(
            "general", "general inquiries, plans", "You are a general support agent."
        ),
    ]

    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            n = calls[0]
            calls[0] += 1
            usage = Usage(input_tokens=90, output_tokens=20)
            if n == 0:
                return LLMResponse(
                    text='["billing", "general"]', stop_reason="end_turn", usage=usage
                )
            if n <= 2:
                return LLMResponse(
                    text="Expert answer for this query.", stop_reason="end_turn", usage=usage
                )
            return LLMResponse(
                text="Synthesized answer from experts.", stop_reason="end_turn", usage=usage
            )

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        result = moe.run_mixture_of_experts(task, experts, MockClient(make_planner()), top_k=2)
        traces.append(result.trace)
    return traces


# --- Speculative (18) -------------------------------------------------------


def _run_speculative() -> list[Trace]:
    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            n = calls[0]
            calls[0] += 1
            usage = Usage(input_tokens=80, output_tokens=25)
            if n < 3:
                return LLMResponse(
                    text=f"Candidate solution {n + 1}.", stop_reason="end_turn", usage=usage
                )
            scores = [9.0, 7.5, 6.0]
            score = scores[n - 3]
            return LLMResponse(
                text=f"SCORE: {score}\nRATIONALE: Solid candidate.",
                stop_reason="end_turn",
                usage=usage,
            )

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        result = spec.run_speculative(task, MockClient(make_planner()), n_candidates=3)
        traces.append(result.trace)
    return traces


# --- Event-Driven (19) ------------------------------------------------------


def _run_event_driven() -> list[Trace]:
    def make_planner() -> Any:
        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            usage = Usage(input_tokens=80, output_tokens=20)
            for m in messages:
                if m.role == "user" and "Summarize what happened" in m.content:
                    return LLMResponse(
                        text="All events processed successfully.",
                        stop_reason="end_turn",
                        usage=usage,
                    )
            return LLMResponse(text="Event processed.", stop_reason="end_turn", usage=usage)

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        events = [
            ed.Event("request", task),
            ed.Event("followup", "Please confirm resolution."),
        ]
        state = ed.AgentState()
        result = ed.run_event_driven(
            events,
            ToolRegistry(),
            MockClient(make_planner()),
            state=state,
            max_steps_per_event=2,
        )
        traces.append(result.trace)
    return traces


# --- Least-to-Most (20) -----------------------------------------------------


def _run_least_to_most() -> list[Trace]:
    def make_planner() -> Any:
        calls = [0]

        def planner(messages: list[Message], _tools: Any) -> LLMResponse:
            n = calls[0]
            calls[0] += 1
            usage = Usage(input_tokens=80, output_tokens=20)
            if n == 0:
                return LLMResponse(
                    text='["Identify the core issue", "Find the resolution", "Recommend next steps"]',
                    stop_reason="end_turn",
                    usage=usage,
                )
            return LLMResponse(
                text=f"Answer to sub-problem {n}.", stop_reason="end_turn", usage=usage
            )

        return planner

    traces: list[Trace] = []
    for task in TASKS:
        result = ltm.run_least_to_most(task, MockClient(make_planner()), max_sub_problems=3)
        traces.append(result.trace)
    return traces


# --- Scenario registry -------------------------------------------------------

SCENARIOS: dict[str, Callable[[], list[Trace]]] = {
    "Prompt Chain (01)": _run_prompt_chaining,
    "Routing (02)": _run_routing,
    "Parallel (03)": _run_parallelization,
    "Orch-Workers (04)": _run_orchestrator_workers,
    "Eval-Optim (05)": _run_evaluator_optimizer,
    "Code Exec (06)": _run_code_execution,
    "ReAct (07)": _run_react,
    "Reflection (08)": _run_reflection,
    "Plan-Execute (09)": _run_plan_and_execute,
    "Multi-Agent (10)": _run_multi_agent,
    "Memory (11)": _run_memory,
    "Self-Ask (12)": _run_self_ask,
    "Human-Loop (13)": _run_human_in_loop,
    "State-Mach (14)": _run_state_machine,
    "Debate (15)": _run_debate,
    "Constitut. (16)": _run_constitutional,
    "Mix-Expert (17)": _run_moe,
    "Speculative (18)": _run_speculative,
    "Event-Drive (19)": _run_event_driven,
    "Least-Most (20)": _run_least_to_most,
}


def main() -> None:
    console = Console()
    stats = [_aggregate(name, runner()) for name, runner in SCENARIOS.items()]

    table = Table(title=f"Pattern comparison · {len(TASKS)} tasks · mock mode")
    table.add_column("Pattern", style="bold")
    table.add_column("Avg steps", justify="right")
    table.add_column("Avg tokens", justify="right")
    table.add_column("Avg latency", justify="right")
    table.add_column("Success", justify="right")

    for s in stats:
        table.add_row(
            s.name,
            f"{s.avg_steps:.1f}",
            f"{s.avg_tokens:.0f}",
            f"{s.avg_ms:.1f}ms",
            f"{s.success_rate:.0%}",
        )

    console.print()
    console.print(table)
    console.print(
        "\n[dim]Same tasks, all 20 patterns. Simpler patterns (Routing, Prompt Chain, Self-Ask) "
        "spend fewer steps and tokens; richer patterns (ReAct, Plan-Execute, Debate, Speculative) "
        "trade cost for capability — pick the simplest pattern that solves the task.[/dim]\n"
    )


if __name__ == "__main__":
    main()
