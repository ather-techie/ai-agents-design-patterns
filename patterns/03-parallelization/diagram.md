# Parallelization — control-flow diagram

```mermaid
flowchart TD
    T([task]) --> FO{fan out}

    FO -->|branch A system prompt| A["LLM call\n[branch A]"]
    FO -->|branch B system prompt| B["LLM call\n[branch B]"]
    FO -->|branch C system prompt| C["LLM call\n[branch C]"]

    A -->|answer A| FI{fan in}
    B -->|answer B| FI
    C -->|answer C| FI

    FI --> AGG["LLM call\n[aggregator]"]
    AGG --> ANS([aggregate answer])

    style T fill:#4a4a8a,color:#fff
    style ANS fill:#2d6a4f,color:#fff
    style FO fill:#555,color:#fff
    style FI fill:#555,color:#fff
    style AGG fill:#6d4c41,color:#fff
```

## Step annotations

| Step kind   | When recorded                                      |
|-------------|----------------------------------------------------|
| `worker`    | Once per branch, after that branch's LLM call returns |
| `reasoning` | Once, after the aggregation LLM call completes     |
| `answer`    | Once, carrying the final synthesised text          |

## Threading model

All branch calls are submitted to a `ThreadPoolExecutor` before any result is
awaited. The executor size equals the number of branches, so every branch is
in-flight simultaneously. `concurrent.futures.as_completed` collects results as
they arrive and records each `worker` step in completion order (which may differ
from submission order). The aggregation call runs only after all branch futures
are resolved.
