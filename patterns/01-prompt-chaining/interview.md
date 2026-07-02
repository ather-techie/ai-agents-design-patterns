# Prompt Chaining — Interview Questions & Answers

## Conceptual

**1. What is the prompt chaining pattern, and what problem does it solve compared to a single large LLM prompt?**

Prompt chaining breaks a complex task into a sequence of focused LLM calls where each step's output becomes the next step's input. It solves the "prompt overload" problem — a single prompt that asks the model to simultaneously extract, transform, evaluate, and format tends to produce lower-quality output at every stage. Focused steps let the model do one thing well at a time.

**2. Why is the pipeline length "fixed" in basic prompt chaining, and when does that become a constraint?**

The number of steps is hard-coded at design time; there is no conditional branching or decision to skip or add steps. This becomes a constraint when the right number of steps depends on input complexity — a simple query is forced through unnecessary steps, while a highly complex one may not get enough processing.

**3. How does each step in a chain know what the previous step produced? What data flows between steps?**

The output text (or a structured field extracted from it) from step N is injected directly into the prompt template of step N+1, typically as a filled variable. Only the relevant output is passed forward — not the full conversation history — keeping each prompt focused and token-efficient.

## Trade-offs

**4. What are the cost and latency implications of adding more steps to a chain versus packing everything into one prompt?**

Each additional step adds one full LLM round-trip, so latency scales linearly with chain length. A single large prompt avoids this overhead but often degrades quality when the task is genuinely multi-stage. The break-even point depends on the task: if decomposition reliably improves output quality and avoids downstream retries, the extra steps are worth the cost.

**5. How does prompt chaining compare to the Evaluator-Optimizer pattern when you need quality control?**

Prompt chaining is strictly forward — there is no loop back for quality checks. Evaluator-Optimizer adds a dedicated critique step that can trigger revision passes, making it better when correctness is critical and higher cost is acceptable. Chaining suits tasks where each step is reliable on its own and low latency matters more than revision cycles.

## Implementation & Failure Modes

**6. If step 3 of a 5-step chain produces malformed output, what happens to the remaining steps? How would you add a validation gate?**

Steps 4 and 5 receive the bad output as input and compound the error, producing a corrupt final result with no indication of where it went wrong. A validation gate runs a lightweight check — schema validation, regex, or a small classifier — after each step, and either retries that step or short-circuits the chain with an explicit error before the damage propagates.

**7. How does error propagation differ in a prompt chain versus a single-call approach?**

In a single call, errors are immediately visible to the caller. In a chain, an error at step K silently corrupts all downstream steps, making the final output appear valid but wrong. Graceful degradation requires per-step output validation and a fallback path — either retry the failed step or return a partial result from the last known-good step.

## Extension

**8. How would you add conditional branching to a prompt chain without turning it into a full ReAct loop?**

Add a lightweight classifier call after the relevant step that returns a branch key (e.g., `"detailed"` vs `"brief"`), then select the next prompt template based on that key. This preserves the deterministic, forward-only nature of chaining while allowing input-dependent routing — without the overhead of a full tool registry and step-bound loop that ReAct requires.
