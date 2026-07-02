# Reflection — Interview Questions & Answers

## Conceptual

**1. What is the reflection pattern, and how does it differ from the evaluator-optimizer pattern?**

Reflection uses the same model to generate a draft and then critique it in a single session: the model first produces output, then is re-prompted to find flaws, then revises. Evaluator-optimizer uses a separate LLM call for the evaluator, starting fresh from the task specification. Reflection is cheaper and simpler; evaluator-optimizer provides stronger critic independence at higher cost.

**2. What is the role of the `NO_CHANGES` signal, and why is an early-exit condition important?**

When the model finds no meaningful issues during critique, it emits `NO_CHANGES` to signal the output is already good. Without this early exit, the loop would always run to the maximum iteration limit even for high-quality first drafts, wasting tokens and adding latency on the simplest cases.

**3. How is the trace structured in reflection — what steps are recorded and in what order?**

A typical trace records: `reasoning` (initial generation), `critique` (the reflection step), `revision` (the revised draft), then back to `critique` — alternating until `NO_CHANGES` or max iterations, at which point an `answer` step is recorded. Each step captures its wall-clock duration for latency analysis.

## Trade-offs

**4. What types of errors is a model least likely to catch in its own output during self-critique?**

Factual errors the model confidently believes are correct (hallucinations), logical errors it made consistently throughout generation, and stylistic blind spots baked into its training (e.g., a tendency toward verbose hedging). A separate evaluator with a different system prompt or a factual grounding tool is more effective against these than self-reflection.

**5. When would you use reflection over evaluator-optimizer?**

When the task involves stylistic improvements, tone adjustments, or structural clarity — areas where the same model can meaningfully critique its own phrasing — and when you need to minimize cost and latency. Reflection is well-suited to writing polish; evaluator-optimizer is better for factual accuracy or correctness-critical outputs.

## Implementation & Failure Modes

**6. Describe the oscillation failure mode and how to fix it.**

The model alternates between two versions — "too formal" → "too casual" → "too formal" — never converging. Detect it by hashing each revision; if a hash repeats, break the loop and return the best version seen so far (scored by a single evaluation call). Adding a `max_identical_revisions=2` guard is a simple implementation.

**7. How do you prevent the critique step from over-critiquing a good answer?**

Frame the critique prompt to require the model to justify each change it proposes and to compare it against the original task requirements, not abstract quality ideals. If no proposed change makes the output more correct, more relevant, or clearer for the user's goal, the critique must emit `NO_CHANGES`. This anchors critique to utility rather than perfectionism.

## Extension

**8. How would you incorporate external ground-truth checks into the reflection critique step?**

Alongside the LLM critique, run automated checks — unit tests, schema validation, API calls to a knowledge base — and inject their pass/fail results into the critique prompt. The model then treats these as hard constraints (not just suggestions), ensuring revisions never regress on measurable correctness even while improving other qualities.
