# 13 · Human-in-the-Loop

> Pause execution and ask a human for **approval** before running sensitive tools.

A standard ReAct loop gains approval gates: any tool whose name appears in
``checkpoints`` is paused before execution. The human's response is recorded as
a ``"human_input"`` trace step. Rejection raises :class:`HumanAborted`
immediately, giving callers a clean exception to handle. Non-checkpointed tools
run without interruption.

```
reason → tool_call → [human approves?] → observe → reason → answer
                          ↓ no
                     HumanAborted
```

## When to use it

- Tools have **irreversible side-effects** (sending emails, deleting records,
  making purchases) that should not execute without explicit sign-off.
- You need a **compliance or audit trail** — every human decision is recorded
  in the trace.
- Gradual autonomy: start with many checkpoints and remove them as you gain
  confidence in the agent's judgment.

Reach for a standard [ReAct](../07-react/) loop when no tool requires human
oversight.

## Run it

No API key required — the demo runs against the deterministic offline mock:

```bash
python patterns/13-human-in-the-loop/example.py     # prints the trace tree + answer
pytest patterns/13-human-in-the-loop/               # run the tests
```

Set `ANTHROPIC_API_KEY` (and leave `USE_MOCK` unset) to run the *same* pattern
code against the live model (`claude-opus-4-8`, adaptive thinking).

## The shape of the code

`run_human_in_loop(task, registry, client, human_io, *, checkpoints, max_steps)`
(in [pattern.py](pattern.py)):

1. Run a ReAct step — get the model's next response.
2. For each tool call: if the tool name is in ``checkpoints``, call
   `human_io.request(...)`. Record the response as a `"human_input"` step.
   Raise `HumanAborted` on rejection.
3. Execute the tool, record an `"observation"` step, and loop.
4. Return `HumanLoopResult(answer, trace, human_turns)`.

Swap `ConsoleHumanIO` for a custom `HumanIO` implementation (e.g. a Slack bot
or a web approval widget) to integrate with any approval workflow.
