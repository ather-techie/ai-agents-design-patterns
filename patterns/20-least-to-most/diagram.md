# Least-to-Most — control flow

```mermaid
flowchart LR
    Problem(["Hard Problem"]) --> Decompose["Decompose\nLLM → ordered list"]
    Decompose --> P1["Sub-problem 1\n(easiest)"]
    P1 --> A1[Answer 1]
    A1 --> P2["Sub-problem 2\n(with A1 context)"]
    P2 --> A2[Answer 2]
    A2 --> PN["Sub-problem N\n(hardest)"]
    PN --> AN["Answer N = final"]
    AN --> Final([Final Answer])
```

Each sub-problem's solve prompt includes all prior Q&A pairs. The last sub-problem's answer
is returned as the final answer — it has access to all simpler building blocks.
