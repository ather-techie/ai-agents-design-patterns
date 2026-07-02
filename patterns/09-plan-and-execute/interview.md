# Plan-and-Execute — Interview Questions & Answers

## Conceptual

**1. Describe the three phases of plan-and-execute. What LLM call happens in each?**

Phase 1 — Plan: one LLM call receives the full task and returns an ordered list of numbered steps. Phase 2 — Execute: each step gets its own inner ReAct loop (one or more LLM calls per step) that uses available tools to complete just that step. Phase 3 — Synthesize: one final LLM call receives the original task plus all step results and produces the final answer.

**2. Why does each execution step run its own inner ReAct loop rather than a single tool call?**

Some steps are complex enough to require multiple tool interactions — searching, then filtering, then reformatting. A full inner ReAct loop gives each step the dynamic tool-use flexibility of a standalone agent, while the plan keeps their overall purpose narrowly scoped so they do not drift into adjacent work.

**3. How does each step's context stay isolated?**

Each step's inner ReAct loop is initialized with only that step's description and the tools it needs — not the full original task or other steps' results. This prevents step N's loop from being distracted by step N-1's intermediate findings and keeps each loop's token cost proportional to its subtask, not the whole problem.

## Trade-offs

**4. How does plan-and-execute compare to ReAct?**

Plan-and-execute commits to a full task decomposition before any execution begins, making it predictable and parallelizable (steps could run concurrently if independent). ReAct adapts step-by-step based on each observation. Plan-and-execute wins when the task is well-structured and steps can be defined in advance; ReAct wins when discoveries during execution should change the approach.

**5. What happens when executing step 2 reveals that the plan from step 1 is wrong?**

In the basic implementation, the plan is fixed — steps 3–N will still execute with the wrong foundation. To handle this, add a replanning check after each step: if the step result contradicts a plan assumption, trigger a new planning call with the current findings, replacing the remaining steps. This adds cost but significantly improves robustness.

## Implementation & Failure Modes

**6. If a single execution step fails, should synthesis proceed with partial results or abort?**

Proceed with partial results if the failed step's output is non-critical to the final answer; abort if the downstream steps depend on it. The synthesis prompt should explicitly receive a structured step-status list (pass/fail per step) and be instructed to caveat the final answer based on which steps failed.

**7. How would you evaluate plan quality before committing to execution?**

Run a lightweight plan-validation LLM call that checks: are steps non-overlapping? Do they collectively cover the full task? Is each step actionable with the available tools? You can also use structured output (require steps to name which tool they will use) to catch "steps" that have no executable path.

## Extension

**8. How would you support dynamic plan revision mid-execution?**

After each step completes, compare the step's result to what the plan assumed it would produce. If they diverge significantly (detected via a brief LLM classifier call), trigger a replan: pass the original task, all completed steps and their results, and the remaining planned steps to the planner, which returns a revised list of remaining steps. Execution continues with the updated plan.
