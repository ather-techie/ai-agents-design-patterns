# Least-to-Most — Interview Questions & Answers

## Conceptual

**1. What is the least-to-most decomposition principle? How does ordering by difficulty differ from self-ask?**

Least-to-most orders sub-problems from simplest to most complex, so each solution builds foundational knowledge that makes the next harder problem solvable. Self-ask orders sub-questions by logical dependency — question B requires question A's answer to even be formulated. Least-to-most is better for abstract reasoning tasks (math, logic) where simpler cases scaffold harder ones; self-ask is better for multi-hop factual chains.

**2. How does each sub-problem receive context from prior answers?**

Before the model answers sub-problem N, its prompt includes the original problem, then sub-problem 1 and its answer, sub-problem 2 and its answer, ... sub-problem N-1 and its answer, then sub-problem N. Each answer is a permanent, growing context that all subsequent sub-problems can read directly — the "easiest-first" ordering ensures early answers are always available to inform later ones.

**3. Why is the final sub-problem's answer treated as the final result rather than running a synthesis step?**

Because the final sub-problem is the original hard question, answered with all the scaffolding already in context. A separate synthesis step would duplicate effort — it would just re-read the same context and re-state the final answer. The design assumes the last sub-problem is the target and the earlier ones exist solely to build up to it.

## Trade-offs

**4. How does least-to-most compare to self-ask?**

Least-to-most focuses on difficulty ordering to build cognitive scaffolding; self-ask focuses on logical dependency ordering to build factual scaffolding. For a math problem, least-to-most is natural (prove lemma A, then use it to prove theorem B). For "who is the current CEO of the company that acquired X in 2021?", self-ask is more natural. Many real problems benefit from both, and the patterns can be combined.

**5. What types of problems decompose cleanly from easy to hard, and which do not?**

Clean decomposition: mathematical proofs, multi-step reasoning chains, coding problems with helper functions. Poor decomposition: holistic creative tasks (writing a poem), problems that require all information simultaneously before any part can be solved (constraint satisfaction), and ill-defined problems where "difficulty" has no clear ordering. Forcing a least-to-most decomposition onto an ill-suited problem produces arbitrary sub-problems that add noise rather than scaffolding.

## Implementation & Failure Modes

**6. How is cascading error propagation worse in least-to-most than in parallel approaches?**

In a parallel approach (e.g., speculative execution), each candidate is generated independently — one wrong candidate does not affect others. In least-to-most, a wrong sub-problem answer is injected into every subsequent sub-problem's prompt as ground truth, compounding errors all the way to the final answer. There is no independent path that could produce a correct result despite the early error.

**7. What is the failure mode when the model cannot correctly order sub-problems by difficulty?**

A hard sub-problem placed early gets no scaffolding from easier ones, so the model must solve the hardest part first with no foundation — this typically produces a wrong answer that then misleads all downstream sub-problems. Since the decomposition step's quality determines everything, add a validation pass that checks whether the proposed ordering makes sense: does sub-problem 1 require any knowledge that would only come from solving sub-problem 3?

## Extension

**8. How would you augment least-to-most with tool calls at each sub-problem step?**

Wrap each sub-problem answer step in a mini-ReAct loop with a retrieval or computation tool. The easiest sub-problem is answered first using a search tool to ground it in facts rather than parametric knowledge. That grounded answer becomes context for the next sub-problem, which can call tools to verify or extend it. This hybrid builds factual scaffolding (verified by tools) rather than relying on the model's potentially hallucinated knowledge at each step.
