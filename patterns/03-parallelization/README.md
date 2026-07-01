# 03 · Parallelization

> Fan out to N independent branches, fan in to one aggregate.

All branches receive the same task but with different system prompts, so they
approach it from different angles simultaneously. A final aggregation call
synthesizes the branch outputs into one answer.

```
             ┌─[branch A]─┐
task ──────► ├─[branch B]─┤ ──► aggregate ──► answer
             └─[branch C]─┘
```

See [diagram.md](diagram.md) for the control-flow diagram.

## When to use it

- You want **diverse perspectives** on one question (critic, optimist, analyst).
- Independent **verification**: run the same task N times and check for agreement.
- **Throughput**: embarrassingly parallel sub-tasks that can run simultaneously.

The wall-clock time is the slowest branch, not the sum — cost scales with N
but latency does not.

## Run it

```bash
python patterns/03-parallelization/example.py
pytest patterns/03-parallelization/
```

## The shape of the code

`run_parallelization(task, branches, client, *, aggregator_prompt)` in [pattern.py](pattern.py):

1. Dispatch all branches to a `ThreadPoolExecutor`; each calls the model with its system prompt prepended.
2. Collect branch answers; record a `"worker"` step per branch.
3. Build an aggregation prompt and call the model once more; record `"reasoning"`.
4. Return the aggregate with the full trace.
