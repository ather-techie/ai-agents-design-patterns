# Self-Ask — Interview Questions & Answers

## Conceptual

**1. What is the self-ask pattern, and what type of question benefits most from it?**

Self-ask decomposes a complex question into an ordered list of simpler sub-questions, answers them sequentially, and synthesizes the final answer from all Q&A pairs. It benefits multi-hop questions most — ones where the answer to question A is required to correctly formulate or answer question B (e.g., "Who was the president when the current CEO of Apple was born?").

**2. How does the pattern thread prior answers into later sub-questions?**

After answering sub-question N, the model receives a prompt containing the original question, all sub-questions seen so far, and all answers so far. Sub-question N+1 is answered in the context of that full Q&A chain, so each answer can reference and build on all prior answers by reading them directly in its prompt.

**3. Why are sub-questions answered sequentially rather than in parallel?**

Because later sub-questions are often logically dependent on earlier answers — you cannot ask "Who succeeded [person X]?" until you know who person X is. Parallelizing would require all sub-questions to be fully specified upfront with no inter-dependencies, which defeats the purpose of sequential decomposition.

## Trade-offs

**4. How does self-ask compare to least-to-most decomposition?**

Self-ask decomposes by logical dependency (question B requires question A's answer); least-to-most decomposes by difficulty (easiest sub-problem first builds context for harder ones). For factual multi-hop chains, self-ask is natural. For abstract reasoning tasks where simpler cases scaffold harder ones, least-to-most is better. The patterns overlap but optimize for different decomposition criteria.

**5. What kinds of questions does this pattern decompose poorly?**

Questions that are holistic rather than compositional — "Is this essay well-written?" — do not break down into sequential sub-questions. Also, questions where the LLM's decomposition is wrong: if sub-question 1 is actually the hardest part, the sequential context chain provides no benefit. The pattern is only as good as the initial decomposition quality.

## Implementation & Failure Modes

**6. If sub-question 2 produces an incorrect answer, how does it propagate?**

Every subsequent sub-question is answered using the wrong fact as context, potentially compounding the error into the final answer. Unlike parallel approaches, there is no independent path to catch the mistake. Detection requires a post-synthesis consistency check that cross-references the final answer against a direct (non-decomposed) LLM call on the original question.

**7. What is the failure mode when the LLM generates too many sub-questions?**

Token cost and latency grow linearly with sub-question count. For a simple two-hop question, 8 sub-questions means 7 unnecessary LLM calls. Cap sub-question count with a schema constraint (e.g., max 5), and add a prompt instruction to use the minimum number of sub-questions necessary to logically derive the answer.

## Extension

**8. How would you ground each sub-question answer with tool calls rather than parametric knowledge?**

Wrap each sub-question answer step in a mini-ReAct loop with a search or database tool. Instead of asking the LLM to answer "Who was the CEO of Apple in 2004?" from memory (potentially hallucinating), it calls a search tool, reads the result, and records it as the verified answer before passing it as context to the next sub-question.
