# Evaluator-Optimizer — Interview Questions & Answers

## Conceptual

**1. Describe the evaluator-optimizer loop. What are the two LLM roles, and what does each receive as input?**

The generator produces an initial draft given the original task. The evaluator receives the original task plus the draft and outputs a pass/fail verdict with feedback. If it fails, the generator receives the original task plus the draft plus the evaluator's feedback, and produces a revised draft. This continues until the evaluator passes or the iteration limit is reached.

**2. Why is a separate evaluator LLM often more reliable than asking the generator to self-evaluate?**

A model that just generated an output shares the same reasoning blind spots that produced any flaws in it; self-evaluation tends to rationalize rather than critique. A separate evaluator call — even using the same underlying model — starts fresh from the task specification and the output, without the generative context, making it more likely to catch inconsistencies.

**3. What does the pass/fail status on the final output tell a caller, and how should a caller handle a `fail` result?**

`pass` means the evaluator was satisfied within the iteration budget; `fail` means the loop exhausted its maximum iterations without achieving a passing evaluation. A caller should treat a `fail` result as degraded-quality output: log it, optionally surface it to a human reviewer, and not silently pass it downstream as if it were validated.

## Trade-offs

**4. How does evaluator-optimizer compare to the reflection pattern?**

Both use a critique-revise cycle, but evaluator-optimizer uses a separate LLM call for the evaluator, giving it cleaner separation from the generator's reasoning. Reflection uses the same model for both roles in a single session, which is cheaper but more prone to the model agreeing with its own output. Use evaluator-optimizer when critique quality is critical; use reflection when cost and simplicity matter more.

**5. How would you set the maximum iteration limit appropriately?**

Empirically: run the loop on a representative eval set and plot quality vs. iteration count. Quality typically plateaus after 2–3 iterations for most tasks; diminishing returns set in quickly. Set the limit just past the plateau — often 3–5 — to avoid wasting tokens on iterations that no longer improve quality.

## Implementation & Failure Modes

**6. What is "evaluator bias," and how would you detect it?**

Evaluator bias is when the evaluator systematically passes outputs it should reject (leniency bias) or rejects outputs it should pass (severity bias). Detect it by building a labeled test set of known-good and known-bad outputs and measuring the evaluator's accuracy on each class. If it's lenient, tighten the evaluation rubric; if too strict, add passing examples to the evaluator prompt.

**7. Describe a scenario where the generator and evaluator get stuck in a loop that never converges.**

The evaluator flags "too informal" → the generator revises to "too formal" → the evaluator flags "too formal" → the generator revises to "too informal" — oscillating indefinitely. Beyond capping iterations, detect oscillation by hashing each draft: if a hash repeats, break the loop early and return the highest-quality draft seen so far (tracked by a secondary scoring prompt).

## Extension

**8. How would you make the evaluator output structured feedback targeting specific flaws?**

Use a structured output schema for the evaluator response: `{ "verdict": "fail", "issues": [{"aspect": "clarity", "line": "...", "fix": "..."}] }`. Pass this structured list to the generator prompt with explicit instructions to address each issue in order, rather than a freeform critique the generator might interpret loosely.
