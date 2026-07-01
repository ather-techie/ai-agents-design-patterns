# Speculative Execution — control flow

```mermaid
flowchart TD
    Task([Task]) --> Gen["Generate N candidates"]
    Gen --> C1[Candidate 1]
    Gen --> C2[Candidate 2]
    Gen --> CN[Candidate N]
    C1 & C2 & CN --> Eval["Evaluate each\n(SCORE: 0.0 – 10.0)"]
    Eval --> Winner["Pick max score"]
    Winner --> Answer([Best candidate])
```

With `n_candidates=1` the evaluation step is skipped; the single candidate scores 10.0.
Each candidate is generated independently (no shared context between generation calls).
