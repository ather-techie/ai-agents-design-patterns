# Evaluator-Optimizer — Control-Flow Diagram

```mermaid
flowchart TD
    A([Task]) --> B[Generator:\nProduce initial draft]
    B --> C{Evaluator:\nCheck all criteria}
    C -- "PASS" --> D([Return final draft\npassed=True])
    C -- "FAIL: reason" --> E{Max iterations\nreached?}
    E -- "No" --> F[Generator:\nRevise with feedback]
    F --> C
    E -- "Yes" --> G([Return last draft\npassed=False])

    style D fill:#22c55e,color:#fff
    style G fill:#ef4444,color:#fff
    style C fill:#f59e0b,color:#fff
    style E fill:#f59e0b,color:#fff
```

## Step legend

| Trace kind  | Description                                          |
|-------------|------------------------------------------------------|
| `reasoning` | Initial draft produced by the generator              |
| `critique`  | Evaluator verdict (`PASS` or `FAIL: <reason>`)       |
| `revision`  | Revised draft produced by the generator after a FAIL |
| `answer`    | Final output returned to the caller                  |
