# 09 · Plan-and-Execute

> The model builds a complete plan upfront, then executes each step.

Unlike ReAct, planning and execution are **separated**. The model first produces
a numbered list of steps (the plan), then executes them one by one, optionally
using tools. Finally, it synthesizes all step results into a final answer.

```
task → [plan] → step 1 → step 2 → … → step N → [synthesize] → answer
                  ↓         ↓             ↓
               (tools)   (tools)       (tools)
```

See [diagram.md](diagram.md) for the control-flow diagram.

## When to use it

- You want to **inspect or validate the plan** before committing to execution.
- The task has **predictable sub-steps** that can be enumerated upfront.
- Execution is expensive — the plan acts as a **checkpoint** before committing.

Use ReAct (07) when the number of steps is unknown or depends on intermediate
results.

## Run it

```bash
python patterns/09-plan-and-execute/example.py
pytest patterns/09-plan-and-execute/
```

## The shape of the code

`run_plan_and_execute(task, registry, client, *, max_plan_steps)` in [pattern.py](pattern.py):

1. **Plan**: ask the model for a numbered step list; parse into `PlanStep` objects.
2. **Execute**: for each step, call the model (with tools); record result.
3. **Synthesize**: ask the model to combine all step results into a final answer.
