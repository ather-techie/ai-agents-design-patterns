# 05 · Evaluator-Optimizer

> Generate a draft, evaluate it against criteria, and refine until it passes.

A generator LLM produces a draft; an evaluator LLM checks it against explicit
criteria. If the evaluator returns `FAIL`, a revision is requested. The loop
runs until the evaluator returns `PASS` or `max_iterations` is reached.

```
task → [generate] → draft → [evaluate] → PASS → answer
                       ↑         ↓
                       └── FAIL: reason ──┘
```

See [diagram.md](diagram.md) for the control-flow diagram.

## When to use it

- You have **explicit, checkable criteria** for a good output.
- The task benefits from **iterative refinement** rather than one-shot generation.
- Using **separate generator and evaluator** models reduces self-serving bias.

## Run it

```bash
python patterns/05-evaluator-optimizer/example.py
pytest patterns/05-evaluator-optimizer/
```

## The shape of the code

`run_evaluator_optimizer(task, criteria, generator, evaluator, *, max_iterations)` in [pattern.py](pattern.py):

1. Generator produces the first draft.
2. Evaluator checks all criteria; responds `PASS` or `FAIL: <reason>`.
3. On `FAIL`, generator revises with the feedback; repeat.
4. On `PASS` or exhausting iterations, return the last draft with the trace.
