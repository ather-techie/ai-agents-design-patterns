# 14 · State Machine Agent

> Route an agent through an **explicit finite-state machine** where an LLM picks the next transition.

Each node in the graph is a `State` with a handler function and a list of allowed next states. After a handler runs, an LLM is asked to choose the next state from the allowed transitions. The loop terminates when a terminal state is reached or `max_transitions` is exceeded.

```
[triage] --LLM picks--> [diagnose] --LLM picks--> [resolve*]
```

(`*` = terminal)

## When to use it

- The task has **well-defined phases** that must execute in a controlled order (e.g., triage → diagnose → resolve).
- You want to **constrain** the agent to a known set of actions rather than letting it choose freely.
- The business process has **compliance or audit requirements** that demand a fixed workflow.
- Different states need **different prompts or tools** without the overhead of a full multi-agent system.

Reach for [ReAct](../07-react/) when the step sequence is unpredictable, or [Routing](../02-routing/) when you only need a single routing decision.

## Run it

No API key required — the demo runs against the deterministic offline mock:

```bash
python patterns/14-state-machine/example.py     # prints the trace tree + answer
pytest patterns/14-state-machine/               # run the tests
```

Set `ANTHROPIC_API_KEY` (and leave `USE_MOCK` unset) to run the *same* pattern code against the live model.

## The shape of the code

`run_state_machine(input, states, client, *, initial_state, max_transitions)` (in [pattern.py](pattern.py)):

1. Look up `initial_state` in the state map (raise `StateError` if missing).
2. Call `state.handler(input, accumulated_context)` → `output`.
3. Record a `"transition"` step.
4. If `state.terminal` or no transitions → record `"answer"` and return.
5. Ask the LLM to pick the next state from `state.transitions`.
6. Match the LLM's reply (case-insensitive) → raise `StateError` if no match.
7. Record a `"reasoning"` step and accumulate output into context.
8. If `max_transitions` exhausted → raise `MaxStepsExceeded`.
