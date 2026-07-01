# 04 · Orchestrator-Workers

> A central orchestrator breaks a task into subtasks and delegates each to a specialized worker.

The orchestrator LLM sees the full task and a menu of workers. It produces a
plan (JSON assignments), dispatches subtasks, and synthesizes the results.
Workers are isolated — they only see their own subtask.

```
task → orchestrator → plan
         ├─ worker A (subtask 1)
         ├─ worker B (subtask 2)  → synthesis → answer
         └─ worker C (subtask 3)
```

See [diagram.md](diagram.md) for the control-flow diagram.

## When to use it

- The task **requires different specializations** (research, analysis, writing).
- You want to **isolate concerns**: workers don't see each other's context.
- The number of subtasks is **determined dynamically** by the orchestrator.

## Run it

```bash
python patterns/04-orchestrator-workers/example.py
pytest patterns/04-orchestrator-workers/
```

## The shape of the code

`run_orchestrator_workers(task, orchestrator, workers)` in [pattern.py](pattern.py):

1. Orchestrator call → JSON plan of `{worker, subtask}` assignments.
2. For each assignment, dispatch the subtask to the named worker; record `"delegate"` + `"worker"` steps.
3. Orchestrator synthesis call → final answer.
