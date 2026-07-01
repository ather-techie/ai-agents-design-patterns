# Memory-Augmented Agent — control flow

```mermaid
flowchart TD
    Start(["Task + Memory Snapshot"]) --> Reason[Reason]
    Reason --> Decide{"Tool call\nor answer?"}
    Decide -->|memory tool| MemTool["remember / recall / forget"]
    MemTool --> Store[("MemoryStore")]
    Store --> MemStep["[memory] step"]
    MemStep --> Reason
    Decide -->|other tool| Act[Execute tool]
    Act --> Obs["[observation] step"]
    Obs --> Reason
    Decide -->|end_turn| Answer([Final answer])
```

Memory tool results are recorded as `"memory"` steps; ordinary tools as `"observation"` steps.
Both paths go through the same ReAct loop — the memory store persists across the run.
