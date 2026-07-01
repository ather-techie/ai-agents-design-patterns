# 11 · Memory-Augmented Agent

> Give the agent **episodic memory** via first-class remember / recall / forget tools.

A standard ReAct loop gains a persistent :class:`MemoryStore` that the model
controls. Before each run the current memory snapshot is injected into the
prompt, so the model always starts with full context. Memory tool calls are
traced with the dedicated `"memory"` step kind, visually distinct from ordinary
tool observations.

```
reason → remember → [memory] → recall → [memory] → reason → answer
```

## When to use it

- The agent needs to **persist facts between turns** within a session (user
  preferences, partial results, entity relationships).
- You want the model to decide **what is worth storing** rather than recording
  everything automatically.
- Tasks span multiple questions where earlier answers inform later ones.

Reach for a vector-store or database-backed memory when the number of entries
grows large enough that keyword search becomes unreliable.

## Run it

No API key required — the demo runs against the deterministic offline mock:

```bash
python patterns/11-memory/example.py     # prints the trace tree + answer
pytest patterns/11-memory/               # run the tests
```

Set `ANTHROPIC_API_KEY` (and leave `USE_MOCK` unset) to run the *same* pattern
code against the live model (`claude-opus-4-8`, adaptive thinking).

## The shape of the code

`run_memory_agent(task, registry, client, store, *, max_steps)` (in
[pattern.py](pattern.py)):

1. Auto-register `remember`, `recall`, `forget` tools from `store` into
   `registry`.
2. Prepend a memory snapshot to the task prompt.
3. Run a standard ReAct loop — but record memory-tool results as `"memory"`
   steps instead of `"observation"`.
4. Return `MemoryResult(answer, trace, store)` so callers can inspect or
   persist the store after the run.
