# Speculative Execution — Interview Questions & Answers

## Conceptual

**1. What is speculative execution in the context of LLM agents, and what problem does it solve?**

Speculative execution generates N independent candidate answers in parallel, evaluates each with a scoring LLM call, and returns the highest-scoring candidate. It solves the "single-shot lottery" problem: a single LLM call may produce a suboptimal answer due to stochastic sampling, but running N independent attempts makes it statistically much more likely that at least one is high quality.

**2. Why do candidates share no context with each other?**

Isolation ensures genuine diversity in the candidate pool. If candidates could read each other, earlier ones would anchor later ones toward the same reasoning path, producing near-identical outputs that a scorer cannot meaningfully differentiate. Independence is what makes the max-over-N quality improvement non-trivial.

**3. How does the `N=1` fast path work, and why is it correct?**

With a single candidate, the evaluator has nothing to compare against — it would always assign that candidate a score of 10.0 and return it. The implementation skips the evaluation step entirely and returns the single candidate directly. This is correct: speculative execution adds value only when there is a selection to make.

## Trade-offs

**4. How would you empirically determine the right value of N?**

Run the pattern on a benchmark task set and plot best-candidate quality (evaluated by human or reference answer) vs. N. Quality typically improves fast from N=1 to N=3, then flattens. The inflection point — where each added candidate yields diminishing quality improvement relative to its cost — is the right N for your cost/quality target. Most tasks saturate by N=3–5.

**5. How does speculative execution compare to the evaluator-optimizer pattern?**

Both try to improve output quality through evaluation. Evaluator-optimizer is iterative — each revision is informed by the previous one's critique, so it can climb toward quality from any starting point. Speculative execution is one-shot — all candidates are generated in parallel without feedback, then the best is selected. Use evaluator-optimizer when revision from feedback is possible; use speculative execution when you want one-shot quality improvement with no iteration.

## Implementation & Failure Modes

**6. What happens when all N candidates receive identical or near-identical scores?**

The evaluator cannot differentiate, and candidate selection becomes arbitrary — you pay for N generations without getting N-times-better selection. This means your candidates lack diversity. Inject variation by using different temperatures, different system prompt framings, or explicit role-priming ("answer as a cautious expert", "answer as a decisive practitioner") to drive diverse generation.

**7. How would you validate that the evaluator consistently picks the best candidate?**

Build a labeled test set where human experts rank N candidates for a variety of tasks. Compute the evaluator's rank correlation with human rankings (Kendall's τ or Spearman's ρ). If the correlation is low, the evaluator is miscalibrated — revise the scoring rubric, add anchor examples to the evaluator prompt, or switch to a pairwise comparison approach (which model consistently outperforms head-to-head) rather than absolute scoring.

## Extension

**8. How would you combine speculative execution with prompt chaining for multi-step tasks?**

For each step in the chain, generate N candidate outputs instead of one, evaluate all N, and carry only the best forward to the next step. This "speculative chain" applies quality filtering at every step rather than only at the final output. Cost is N × step count, but early-stage quality improvements compound through the chain, reducing error accumulation.
