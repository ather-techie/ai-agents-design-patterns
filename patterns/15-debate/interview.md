# Debate — Interview Questions & Answers

## Conceptual

**1. What is the debate pattern, and why does adversarial structure improve on a single model considering both sides?**

Two agents — Affirmative and Negative — independently argue opposing positions across multiple rounds, then a Judge synthesizes. A single model asked to "consider both sides" typically anchors on its strongest prior and produces a superficial counterargument. Separate agents with explicit mandates to win their position generate more committed, detailed arguments, surfacing real trade-offs the judge can weigh.

**2. How are the Affirmative and Negative agents isolated during the opening round?**

Each agent's message list is initialized separately with its own system prompt (role + position) and the question. Neither can read the other's opening argument until rebuttal rounds begin. This isolation prevents the first responder from anchoring the second and ensures both positions are developed independently before they react to each other.

**3. What information does the Judge receive, and how does its synthesis prompt differ?**

The Judge receives the full debate transcript — all opening statements and rebuttal rounds from both agents, in sequence. Its prompt instructs it to evaluate argument quality (evidence, logical consistency, responsiveness to rebuttals) rather than simply averaging the positions, and to reach a verdict even if the debate was close.

## Trade-offs

**4. How would you decide the optimal number of debate rounds?**

Empirically: run the debate on a benchmark set and score final answers vs. ground truth by round count. Quality typically improves from round 0 (opening only) to round 1–2 (one or two rebuttals) and plateaus or degrades after that as arguments become repetitive. For most tasks, 1–2 rebuttal rounds is optimal; the cost of additional rounds rarely justifies marginal quality gains.

**5. How does debate compare to parallelization with an aggregator?**

Parallelization generates independent answers and aggregates them — there is no back-and-forth. Debate's adversarial rebuttal structure forces each agent to address the other's specific arguments, which surfaces weaknesses that independent generation would miss. Use parallelization for breadth (multiple perspectives on a single question); use debate for depth (testing a claim under adversarial pressure).

## Implementation & Failure Modes

**6. What happens when both agents converge on the same position after round 1?**

If both agents agree, the debate has succeeded quickly — the judge can note the consensus and deliver a verdict with high confidence. This is not a failure. The failure mode is premature convergence caused by one agent being too agreeable rather than genuinely persuaded; detect this by checking whether the Negative agent's later arguments still contain substantive objections or are mostly affirmations.

**7. How would you prevent the judge from simply averaging the two positions?**

Explicitly instruct the judge to identify which arguments were more logically sound and better-evidenced, and to declare a winner (or a specific nuanced position) rather than splitting the difference. Add a constraint: "Do not say 'both sides have merit' as your final verdict — commit to the most defensible position and explain why."

## Extension

**8. How would you extend debate to a multi-party format with three or more agents?**

Assign each agent a distinct position and run one opening round for all simultaneously. For rebuttals, use a round-robin structure where each agent responds to one other agent per round (rotating the target), preventing the combinatorial explosion of all-vs-all responses. The judge receives the full transcript and weights arguments by their total rebuttal exposure — positions attacked and successfully defended carry more credibility.
