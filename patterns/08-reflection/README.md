# 08 · Reflection

> The model critiques its own draft and revises until satisfied.

A single model acts as both author and critic. It generates a draft, then
reviews it for flaws. If it finds any, it revises. The loop continues until the
model says `NO_CHANGES` or `max_iterations` is reached.

```
task → [draft] → [critique] → NO_CHANGES → answer
                     ↓
                [revision] → [critique] → …
```

See [diagram.md](diagram.md) for the control-flow diagram.

## When to use it

- You want **self-improvement without external criteria**: the model decides what's good.
- The task has **soft quality goals** (clarity, tone, completeness) that are hard to enumerate.
- You want a **single-model setup** — no separate evaluator client needed.

Reach for Evaluator-Optimizer (05) when you have explicit, checkable criteria or want
an independent evaluator to reduce self-serving bias.

## Run it

```bash
python patterns/08-reflection/example.py
pytest patterns/08-reflection/
```

## The shape of the code

`run_reflection(task, client, *, max_iterations)` in [pattern.py](pattern.py):

1. Model generates an initial draft.
2. Model critiques the draft; if it says `NO_CHANGES`, stop.
3. Model revises based on the critique; go to step 2.
4. Return the final draft with the full trace.
