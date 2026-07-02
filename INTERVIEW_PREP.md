# AI Agent Design Patterns — Interview Prep Guide

Each pattern directory contains an `interview.md` with 7–8 questions spanning four categories:
**Conceptual** → **Trade-offs** → **Implementation & Failure Modes** → **Extension**

Questions are ordered from definition-level to system-design depth, mirroring how interviewers typically probe a topic.

---

## Study Path (simple → complex)

### Foundational Patterns
These establish the vocabulary. Learn these first.

| # | Pattern | Core idea | Interview file |
|---|---------|-----------|----------------|
| 02 | Routing | Single-classifier dispatch to specialized handlers | [patterns/02-routing/interview.md](patterns/02-routing/interview.md) |
| 01 | Prompt Chaining | Fixed sequential LLM pipeline | [patterns/01-prompt-chaining/interview.md](patterns/01-prompt-chaining/interview.md) |
| 03 | Parallelization | Fan-out to N workers, fan-in to aggregator | [patterns/03-parallelization/interview.md](patterns/03-parallelization/interview.md) |
| 06 | Code Execution | Generate → execute → retry with error feedback | [patterns/06-code-execution/interview.md](patterns/06-code-execution/interview.md) |

### Iterative Loop Patterns
These introduce cycles and self-improvement.

| # | Pattern | Core idea | Interview file |
|---|---------|-----------|----------------|
| 07 | ReAct | Reason-Act-Observe loop with tool calls | [patterns/07-react/interview.md](patterns/07-react/interview.md) |
| 08 | Reflection | Generate → self-critique → revise until stable | [patterns/08-reflection/interview.md](patterns/08-reflection/interview.md) |
| 05 | Evaluator-Optimizer | Separate generator and evaluator in a revision loop | [patterns/05-evaluator-optimizer/interview.md](patterns/05-evaluator-optimizer/interview.md) |
| 16 | Constitutional AI | Critique-revision loop guided by explicit principles | [patterns/16-constitutional/interview.md](patterns/16-constitutional/interview.md) |

### Planning & Decomposition Patterns
These split hard problems into manageable parts.

| # | Pattern | Core idea | Interview file |
|---|---------|-----------|----------------|
| 12 | Self-Ask | Decompose into sub-questions, answer sequentially | [patterns/12-self-ask/interview.md](patterns/12-self-ask/interview.md) |
| 20 | Least-to-Most | Order sub-problems easiest-first, build up context | [patterns/20-least-to-most/interview.md](patterns/20-least-to-most/interview.md) |
| 09 | Plan-and-Execute | Static plan → per-step inner ReAct → synthesize | [patterns/09-plan-and-execute/interview.md](patterns/09-plan-and-execute/interview.md) |
| 18 | Speculative Execution | Generate N independent candidates, evaluate, pick best | [patterns/18-speculative/interview.md](patterns/18-speculative/interview.md) |

### Multi-Agent & Coordination Patterns
These involve multiple models or structured control flow.

| # | Pattern | Core idea | Interview file |
|---|---------|-----------|----------------|
| 04 | Orchestrator-Workers | Plan + isolated workers + synthesis | [patterns/04-orchestrator-workers/interview.md](patterns/04-orchestrator-workers/interview.md) |
| 10 | Multi-Agent | Supervisor routes to role-based agents, synthesizes | [patterns/10-multi-agent/interview.md](patterns/10-multi-agent/interview.md) |
| 17 | Mixture-of-Experts | Router selects top-k expert agents to answer | [patterns/17-mixture-of-experts/interview.md](patterns/17-mixture-of-experts/interview.md) |
| 15 | Debate | Affirmative vs. Negative agents, judge synthesizes | [patterns/15-debate/interview.md](patterns/15-debate/interview.md) |

### Stateful & Constrained Patterns
These add persistent state, explicit structure, or human oversight.

| # | Pattern | Core idea | Interview file |
|---|---------|-----------|----------------|
| 11 | Memory-Augmented Agent | ReAct + persistent MemoryStore (remember/recall/forget) | [patterns/11-memory/interview.md](patterns/11-memory/interview.md) |
| 14 | State Machine | Explicit state graph; LLM selects transitions | [patterns/14-state-machine/interview.md](patterns/14-state-machine/interview.md) |
| 19 | Event-Driven | Per-event mini-ReAct loop with persistent state | [patterns/19-event-driven/interview.md](patterns/19-event-driven/interview.md) |
| 13 | Human-in-the-Loop | ReAct with checkpointed tools requiring human approval | [patterns/13-human-in-the-loop/interview.md](patterns/13-human-in-the-loop/interview.md) |

---

## Cross-Pattern Comparison Questions

These are high-signal interview questions that span multiple patterns:

1. **ReAct vs. Plan-and-Execute**: When does dynamic replanning (ReAct) outperform a static upfront plan, and vice versa?
2. **Reflection vs. Evaluator-Optimizer**: Both use a critique step — what does using a *separate* evaluator model add, and at what cost?
3. **Routing vs. Mixture-of-Experts**: Both dispatch to specialists — how do they differ in how many specialists answer, and when does each model fit better?
4. **Orchestrator-Workers vs. Multi-Agent**: Both decompose work across agents — what determines which pattern to use for a given task?
5. **Self-Ask vs. Least-to-Most**: Both decompose into sub-questions — what does ordering by difficulty add, and when does it not matter?
6. **Parallelization vs. Debate**: Both generate multiple answers — how does the adversarial rebuttal structure in Debate add value that parallel independent answers do not?
7. **State Machine vs. ReAct**: Both loop until a terminal condition — what does making the control flow graph explicit gain you, and what does it cost?
8. **Speculative Execution vs. Evaluator-Optimizer**: Both try multiple approaches and select the best — what is the fundamental difference in how they improve quality?
