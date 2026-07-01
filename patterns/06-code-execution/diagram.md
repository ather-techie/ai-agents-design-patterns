# Code Execution — control flow

```mermaid
flowchart TD
    Task([Task]) --> GenCode[LLM: generate code\nreasoning step]
    GenCode --> Extract[extract code\nstrip markdown fences]
    Extract --> Exec{executor\ncode}

    Exec -->|success| Output[output / stdout]
    Exec -->|raises| Error[error message\nobservation is_error=true]

    Error --> Retry{attempts < max?}
    Retry -->|yes| RetryPrompt[LLM: fix code\nwith error context\nreasoning step]
    RetryPrompt --> Extract
    Retry -->|no| Fail([MaxStepsExceeded])

    Output --> Interp[LLM: interpret output\nanswer step]
    Interp --> Result([CodeExecutionResult\ncode · output · answer · attempts])
```

Each code-generation call appends a `"reasoning"` step to the `Trace`.
Each executor result appends an `"observation"` step (with `is_error=True` on failure).
The final interpretation appends an `"answer"` step.
