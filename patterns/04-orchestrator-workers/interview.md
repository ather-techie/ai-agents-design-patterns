# Orchestrator-Workers — Interview Questions & Answers

## Conceptual

**1. What role does the orchestrator play, and why do workers receive only their subtask?**

The orchestrator makes two LLM calls: one to decompose the original request into subtasks and assign each to a worker, and one to synthesize all worker results into a final answer. Workers receive only their subtask — not the full original request or other workers' tasks — to minimize context size, reduce distraction, and keep worker calls cheap and focused regardless of how many workers there are.

**2. Why are there exactly two orchestrator calls rather than one combined plan-and-synthesize call?**

Separating planning from synthesis lets each call specialize. The planning call can reason about task decomposition without being distracted by partial results; the synthesis call can focus entirely on integrating outputs without the clutter of the original planning logic. Combining them tends to produce lower quality on both dimensions.

**3. How does keeping each worker's context minimal benefit memory usage as the number of workers grows?**

Because each worker prompt is proportional to its single subtask rather than the full problem, total token consumption grows linearly (one subtask per worker) rather than quadratically (full context × N workers). The orchestrator holds the big picture; workers are intentionally narrow.

## Trade-offs

**4. How does orchestrator-workers compare to plan-and-execute?**

Orchestrator-workers treats workers as parallel-capable specialists that each receive one isolated subtask — no inner tool loop, no shared state. Plan-and-execute runs each plan step sequentially through its own inner ReAct loop, so later steps can use results from earlier ones. Use orchestrator-workers when subtasks are independent; use plan-and-execute when steps must build on each other.

**5. The orchestrator is a single point of failure — a bad decomposition poisons all workers. How do you guard against this?**

Validate the orchestrator's task list before dispatching workers: check that subtasks are non-overlapping, cover the full scope of the original request, and are actionable by the available worker types. A lightweight LLM checker or structured output schema (requiring each task to have an owner and a clear deliverable) can catch decomposition failures before they propagate.

## Implementation & Failure Modes

**6. What happens when two workers produce contradictory conclusions?**

The synthesizer receives conflicting inputs and must resolve them. The synthesis prompt should explicitly instruct the model to identify contradictions, reason about which worker's subtask scope is authoritative for each conflict, and surface unresolved disagreements in the final answer rather than silently picking one.

**7. How would you handle a subtask that a worker cannot complete?**

The worker should return a structured failure response (reason + partial result if any) rather than an empty string or an error exception. The orchestrator's synthesis step then notes the gap in its final answer and, if possible, compensates with information from other workers that partially overlaps the failed subtask.

## Extension

**8. How would you allow workers to request additional subtasks mid-execution without full replanning?**

Give workers a special `request_subtask(description)` tool call. The orchestrator intercepts these requests, creates new minimal worker calls on the fly, and injects their results back to the requesting worker before it finalizes its output. This preserves the orchestrator-as-coordinator model without requiring a full second planning pass.
