# Routing — control flow

```mermaid
flowchart LR
    Input([Query]) --> C[Classifier\nLLM Call]
    C --> D{Route?}
    D -->|billing| H1[Billing Handler]
    D -->|technical| H2[Technical Handler]
    D -->|general| H3[General Handler]
    D -->|no match| F[Fallback Handler]
    H1 --> Answer([Answer])
    H2 --> Answer
    H3 --> Answer
    F --> Answer
```

The classifier makes a single LLM call and returns a route name. Dispatch is
deterministic — no further model calls. The cheapest useful agent shape and a
good baseline to benchmark richer patterns against.
