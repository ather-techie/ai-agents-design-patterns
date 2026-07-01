# State Machine Agent — control flow

```mermaid
flowchart LR
    Input([Input]) --> S0["State: initial\nhandler(input, ctx)"]
    S0 --> LLM0["LLM picks\nnext state"]
    LLM0 --> S1["State: next\nhandler(input, ctx)"]
    S1 --> LLM1["LLM picks\nnext state"]
    LLM1 --> Term["Terminal state\nhandler(input, ctx)"]
    Term --> Answer([Final answer])
```

Each non-terminal state's output is appended to `accumulated_context`; the LLM selects the
next transition from the state's `transitions` list. A terminal state (or empty transitions) ends the loop.
