# 06 · Code Execution

> The model writes code; a sandbox runs it; the output feeds back in.

The LLM generates Python code to solve the task, a caller-supplied executor
runs it, and the output is fed back so the LLM can interpret or correct. If
execution fails, the model retries with patched code — up to `max_attempts`.

```
task → [generate code] → executor → output → [interpret] → answer
                  ↑           ↓ (error)
                  └── [fix code] ◄──────────────────────────┘
```

See [diagram.md](diagram.md) for the control-flow diagram.

## When to use it

- The task requires **exact computation** (math, data transformation, string ops).
- LLM output quality improves with **real feedback** from execution.
- You want **verifiable results**: code output is deterministic.

## Run it

```bash
python patterns/06-code-execution/example.py
pytest patterns/06-code-execution/
```

## The shape of the code

`run_code_execution(task, executor, client, *, max_attempts)` in [pattern.py](pattern.py):

1. Ask the model for Python code; extract it from any markdown fences.
2. Run `executor(code)` — the caller controls the sandbox (subprocess, restricted eval, etc.).
3. On success, ask the model to interpret the output as a final answer.
4. On error, feed the traceback back and ask for a correction; repeat up to `max_attempts`.
