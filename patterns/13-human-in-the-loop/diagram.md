# Human-in-the-Loop — control flow

```mermaid
flowchart TD
    Start([Task]) --> Reason[Reason]
    Reason --> Decide{"Tool call\nor answer?"}
    Decide -->|tool_use| Check{"Tool in\ncheckpoints?"}
    Check -->|yes| Gate["Human approval\nrequest"]
    Gate --> Approved{Approved?}
    Approved -->|no| Abort([HumanAborted])
    Approved -->|yes| Run[Execute tool]
    Check -->|no| Run
    Run --> Obs[Observation]
    Obs --> Reason
    Decide -->|end_turn| Answer([Final answer])
```

Non-checkpointed tools bypass the gate entirely; only tools whose names appear in `checkpoints`
pause for `HumanIO.request`. A rejection raises `HumanAborted` immediately.
