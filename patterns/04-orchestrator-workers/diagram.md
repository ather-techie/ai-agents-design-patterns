# Orchestrator-Workers — control flow

```mermaid
flowchart TD
    Task([Task]) --> Orch[Orchestrator LLM\nplan prompt]
    Orch --> Plan[JSON Plan\nassignments]

    Plan --> D1[delegate: worker A\nsubtask 1]
    Plan --> D2[delegate: worker B\nsubtask 2]
    Plan --> D3[delegate: worker C\nsubtask 3]

    D1 --> WA[Worker A LLM]
    D2 --> WB[Worker B LLM]
    D3 --> WC[Worker C LLM]

    WA --> R1[result A]
    WB --> R2[result B]
    WC --> R3[result C]

    R1 --> Synth[Orchestrator LLM\nsynthesis prompt]
    R2 --> Synth
    R3 --> Synth

    Synth --> Answer([Final Answer])
```

The orchestrator makes two LLM calls: one to produce the plan, one to
synthesize results. Each worker makes exactly one call and sees only its own
subtask — context remains small regardless of how many workers participate.

Unknown worker names in the plan are recorded as error trace steps and skipped;
the remaining assignments still execute normally.
