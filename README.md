# AI Agents Design Patterns

> **The only agent-patterns repo that benchmarks and visualizes each pattern — runnable in one command, no API key required.**

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](#)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

<!-- Drop your hero GIF here: record `make demo` and the trace tree it prints. -->
<!-- ![ReAct trace](docs/react-trace.gif) -->

Production-oriented reference implementations of LLM agent design patterns.
Each pattern is **runnable, tested, traced, and benchmarked** — not toy snippets.

## Why this exists

Most "agent pattern" repos give you 12 disconnected tutorials. This one answers
the question you actually have — *which pattern, and why* — by running the same
task through each pattern and showing the cost, latency, and reliability
tradeoffs side by side. And every run is **traced**, so you can watch the agent
think.

## 30-second demo (no API key)

\```bash
make install
make demo     # runs ReAct in mock mode and prints a live trace tree
make bench    # runs the comparison harness and prints the tradeoff table
\```

Add a real key in `.env` (`ANTHROPIC_API_KEY=...`) to run against a live model.

## What's inside

- **Trace visualizer** — every run prints a reasoning → tool → observation tree
  with per-step timings.
- **Comparison harness** (`bench/`) — same tasks, multiple patterns, one table.
- **Shared core** (`shared/`) — provider-agnostic client, validated tool
  registry, retries/timeouts, structured logging. Adding a pattern is a ~50-line
  diff.
- **Offline mock mode** — deterministic client so demos and tests run with no
  network and no key.

## Patterns

| # | Pattern | Status | One-liner |
|---|---------|--------|-----------|
| 01 | [Prompt Chaining](patterns/01-prompt-chaining/) | ✅ | Sequential pipeline of LLM calls; each output feeds the next. |
| 02 | [Routing](patterns/02-routing/) | ✅ | Classify input, dispatch to a specialized handler. |
| 03 | [Parallelization](patterns/03-parallelization/) | ✅ | Fan out to N independent branches, fan in to one aggregate. |
| 04 | [Orchestrator-Workers](patterns/04-orchestrator-workers/) | ✅ | Orchestrator plans subtasks; workers execute; orchestrator synthesizes. |
| 05 | [Evaluator-Optimizer](patterns/05-evaluator-optimizer/) | ✅ | Generate a draft, evaluate against criteria, refine until passing. |
| 06 | [Code Execution](patterns/06-code-execution/) | ✅ | LLM writes code; a sandbox runs it; result feeds back in a loop. |
| 07 | [ReAct](patterns/07-react/) | ✅ | Interleave reasoning and acting in a bounded loop. |
| 08 | [Reflection](patterns/08-reflection/) | ✅ | Single model critiques its own draft and revises until satisfied. |
| 09 | [Plan-and-Execute](patterns/09-plan-and-execute/) | ✅ | Model builds a full plan upfront, then executes each step. |
| 10 | [Multi-Agent](patterns/10-multi-agent/) | ✅ | Supervisor selects specialized agents by role and synthesizes results. |
| 11 | [Memory](patterns/11-memory/) | ✅ | ReAct loop augmented with episodic remember / recall / forget tools. |
| 12 | [Self-Ask](patterns/12-self-ask/) | ✅ | Decompose a question into sub-questions, answer each, then synthesize. |
| 13 | [Human-in-the-Loop](patterns/13-human-in-the-loop/) | ✅ | Pause for human approval before executing checkpointed tools. |
| 14 | [State Machine](patterns/14-state-machine/) | ✅ | Route an agent through an explicit FSM; LLM picks transitions. |
| 15 | [Debate](patterns/15-debate/) | ✅ | Two agents argue for and against; a neutral judge synthesizes. |
| 16 | [Constitutional](patterns/16-constitutional/) | ✅ | Generate a draft, critique it against principles, revise until compliant. |
| 17 | [Mixture-of-Experts](patterns/17-mixture-of-experts/) | ✅ | Router selects the best specialist experts; their answers are synthesized. |
| 18 | [Speculative](patterns/18-speculative/) | ✅ | Generate N candidate answers, score each, pick the best. |
| 19 | [Event-Driven](patterns/19-event-driven/) | ✅ | Stateful reactive agent processes a stream of events. |
| 20 | [Least-to-Most](patterns/20-least-to-most/) | ✅ | Decompose a hard problem into sub-problems ordered easy to hard. |

## Adding a pattern

Duplicate `patterns/07-react/`, rename, and rewrite `pattern.py`. The shared
client, tool registry, tracing, config, and test style carry over unchanged.

## License

MIT.