# Mixture-of-Experts — Interview Questions & Answers

## Conceptual

**1. What is the mixture-of-experts pattern, and what makes it different from plain parallelization?**

Both fan out to multiple specialized LLM calls, but parallelization always invokes all workers for every query. Mixture-of-experts adds a router that selects only the top-K most relevant experts before dispatching, so queries pay only for the expertise they actually need rather than running all specialists every time.

**2. How does the router decide which experts to activate, and what does `top_k` control?**

The router receives the query and a description of each registered expert, then selects the top-K expert names by relevance. `top_k` controls how many experts are activated: `top_k=1` dispatches a single best-fit expert and returns its answer directly (no synthesis needed); `top_k>1` dispatches multiple experts and passes all their outputs to a synthesis LLM.

**3. Why does each expert have its own isolated message list?**

Isolation ensures each expert answers from its own specialized perspective without being influenced by what other experts have said. If experts shared a conversation, the first expert's framing would anchor all subsequent ones, collapsing the diversity that makes multi-expert synthesis valuable.

## Trade-offs

**4. How does mixture-of-experts compare to multi-agent with a supervisor?**

Multi-agent dispatches the full task to all selected agents with role-based context; mixture-of-experts dispatches the same query to all selected experts with domain-specific system prompts. The key difference is the routing step: MoE explicitly scores and selects experts before dispatch; multi-agent's supervisor routes as part of a broader task-management role. MoE is lighter (no supervisor synthesis logic); multi-agent supports more complex coordination.

**5. How would you evaluate and improve router accuracy over time?**

Collect cases where users reported unsatisfactory answers and check which experts were routed for each. Build a labeled evaluation set of (query → correct expert set) pairs. Track router precision and recall per expert. Common improvements: add richer expert descriptions in the router prompt, include few-shot routing examples, or fine-tune a lightweight classifier on the labeled data.

## Implementation & Failure Modes

**6. What happens when the router selects two experts with near-identical system prompts?**

The synthesis LLM receives two largely redundant inputs and either produces an overconfident answer (treating the duplicate as independent corroboration) or wastes synthesis capacity averaging near-identical texts. Detect overlap by computing semantic similarity between all expert system prompts at configuration time and merging or differentiating pairs that exceed a similarity threshold.

**7. What prompt strategies prevent the synthesizer from defaulting to the first expert's answer?**

Instruct the synthesizer to explicitly list where experts agree and disagree before producing its synthesis. Add a constraint like "your synthesis must incorporate at least one element from each expert's response that the others did not mention." This forces engagement with all inputs rather than treating the first as authoritative.

## Extension

**8. How would you implement "soft routing" that weights expert contributions rather than selecting a hard top-K?**

Have the router output a relevance score (0–1) for each expert. Dispatch all experts with a non-zero score. Pass each expert's output to the synthesizer along with its score. Instruct the synthesizer to weight each expert's contribution proportionally to its score — lower-confidence experts inform but do not dominate the final answer. This reduces precision loss from hard cutoffs at the cost of higher token spend.
