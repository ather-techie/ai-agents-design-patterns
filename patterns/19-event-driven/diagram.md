# Event-Driven Agent — control flow

```mermaid
flowchart TD
    Events(["Event stream"]) --> Loop{"For each event"}
    Loop --> Prompt["Build event prompt\n+ state snapshot"]
    Prompt --> MiniLoop["Bounded ReAct\nmini-loop"]
    MiniLoop --> StateSet["state_set → AgentState"]
    StateSet --> MiniLoop
    MiniLoop --> Loop
    Loop --> Summary["Final summary call"]
    Summary --> Result(["EventResult + state"])
```

The `state_set` tool is auto-registered alongside any caller-supplied tools. State persists
across all events in the run so the agent can correlate information between them.
