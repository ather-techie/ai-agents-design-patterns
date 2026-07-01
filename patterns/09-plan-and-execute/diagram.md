# Plan-and-Execute — control flow

```mermaid
flowchart TD
    Start([Task]) --> Plan["Phase 1: Plan\nAsk model for numbered steps"]
    Plan --> Parse["Parse numbered list\ninto PlanStep objects"]
    Parse --> Inspect{Plan\ninspectable here}
    Inspect --> ExecLoop

    subgraph ExecLoop ["Phase 2: Execute (for each step)"]
        NextStep["Take next PlanStep"] --> CallModel["Call model with\nstep + tools"]
        CallModel --> Decide{Tool call\nor result?}
        Decide -->|tool_use| RunTool["Validate + run tool"]
        RunTool --> Observe["Append observation\nto step context"]
        Observe --> CallModel
        Decide -->|end_turn| StepDone["Record step result"]
        StepDone --> MoreSteps{More\nsteps?}
        MoreSteps -->|yes| NextStep
    end

    MoreSteps -->|no| Synth

    subgraph Synth ["Phase 3: Synthesize"]
        BuildPrompt["Build prompt with\nall step results"] --> SynthCall["Call model"]
        SynthCall --> Answer([Final answer])
    end
```

Each step in the execution phase runs its own inner tool loop, identical to
ReAct's loop but scoped to one plan step. Tool calls and observations are
recorded as `Step` entries in the run's `Trace`. The plan itself is recorded
as a single `"plan"` step before execution begins.
