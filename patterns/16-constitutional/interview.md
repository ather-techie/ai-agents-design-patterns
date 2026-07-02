# Constitutional AI — Interview Questions & Answers

## Conceptual

**1. What is the constitutional AI pattern, and how does encoding explicit principles differ from relying on general instruction-following?**

The pattern runs a generate → critique-against-principles → revise loop, where each critique call checks the draft against a named, explicit list of rules (e.g., "do not make claims without evidence", "never share PII"). General instruction-following asks the model to behave well in the abstract; constitutional AI makes the rules inspectable, testable per principle, and auditable in the trace — you can see exactly which principle triggered a revision.

**2. Walk through the critique-revision loop. What does the critic receive on the second iteration that it did not have on the first?**

Iteration 1: critic receives the original task + initial draft + the full principle list. It outputs identified violations and suggestions. Iteration 2: critic receives the same task + the revised draft (not the original) + the same principle list. The key difference is that the draft has already been partially corrected, so the critic only needs to catch residual violations rather than re-citing ones that were already fixed.

**3. Why does the pattern return the draft immediately when no principles are provided?**

With no principles, there is nothing to critique against — running the loop would produce a critique of nothing, wasting tokens and potentially introducing spurious revisions. The short-circuit makes the principle list a required driver of the loop rather than an optional accessory, signaling that the pattern is meaningless without a constitutional document.

## Trade-offs

**4. How does constitutional AI compare to the reflection pattern?**

Both use a critique-revise cycle. Constitutional AI critiques against an external, fixed principle list — violations are objective relative to the rules. Reflection uses the model's own judgment about what makes a good answer — critique is subjective and task-dependent. Constitutional AI is better for compliance and safety requirements; reflection is better for quality improvements where the criteria are implicit.

**5. How should the critique step handle conflicting principles?**

Flag both principles and the conflict explicitly in the critique output (e.g., "Principle 3 requires brevity, but satisfying Principle 7 requires full disclosure — they conflict here"). The revision step must then make a judgment call. For production systems, principles should be ordered by priority, and the critique prompt should instruct the model to resolve conflicts in favor of higher-priority principles.

## Implementation & Failure Modes

**6. What is "principle wash," and how would you detect it?**

Principle wash is when the critique acknowledges a violation but the revision does not actually fix it — it paraphrases the offending sentence without removing the problem. Detect it by running the evaluator on the revision with the same principle list and checking that previously flagged violations are no longer flagged. Automated principle-by-principle regression testing on a held-out eval set catches systematic principle wash.

**7. How would you prevent the model from satisfying all principles by producing a vacuous, heavily hedged response?**

Add a utility principle that is always present: "The response must be helpful and directly address the user's question." Include it first in the principle list so it has the highest priority. This prevents the model from optimizing for compliance by adding infinite caveats at the expense of answering the question.

## Extension

**8. How would you move from a static principle list to a dynamic one retrieved per query?**

Store principles in a tagged knowledge base (e.g., "privacy", "financial", "medical"). At the start of each run, classify the query's domain (a single cheap LLM or keyword classifier call), retrieve the relevant principle subset, and pass it to the critique step as usual. The core loop is unchanged; only the principle-retrieval step is added before it.
