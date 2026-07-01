# 07 · ReAct

> Interleave **rea**soning and **act**ing in a bounded loop.

ReAct alternates between *thinking* (the model reasons about what to do next) and
*acting* (it calls a tool), feeding each tool's *observation* back into the
context. It repeats until the model produces a final answer — or until it hits a
hard step bound, which guarantees the loop terminates even if the model never
stops calling tools.

```
reason → act → observe → reason → act → observe → … → answer
```

See [diagram.md](diagram.md) for the control-flow diagram.

## When to use it

- The task needs **external information or computation** the model doesn't have
  (search, a calculator, an API, a database).
- The number of steps isn't known up front — the model decides when it has
  enough to answer.
- You want the agent's intermediate reasoning and tool use to be **inspectable**
  (this implementation traces every step).

Reach for a simpler pattern (a single call, or [Routing](../02-routing/)) when
the task is one-shot and needs no tools.

## Run it

No API key required — the demo runs against the deterministic offline mock:

```bash
python patterns/07-react/example.py     # prints the trace tree + answer
pytest patterns/07-react/               # run the tests
```

Set `ANTHROPIC_API_KEY` (and leave `USE_MOCK` unset) to run the *same* pattern
code against the live model (`claude-opus-4-8`, adaptive thinking).

## The shape of the code

`run_react(task, registry, client, *, max_steps)` (in [pattern.py](pattern.py))
depends only on the shared `LLMClient` protocol and a `ToolRegistry`:

1. Send the task + tool definitions to the model.
2. If the model returns tool calls → validate args, execute each tool, append the
   observations, and loop.
3. If the model returns a final answer → return it with the trace.
4. If `max_steps` is exhausted → raise `MaxStepsExceeded`.

This is the template the other patterns copy: swap the loop body in `pattern.py`,
keep the shared client, tools, tracing, config, and test style.
