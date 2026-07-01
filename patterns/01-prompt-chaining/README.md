# 01 · Prompt Chaining

> Decompose a task into a sequential pipeline of LLM calls.

Each step's output is injected into the next step's prompt via `{input}`.
The pipeline is fixed at construction time — unlike ReAct, there is no
dynamic branching.

```
input → [step 1] → output₁ → [step 2] → output₂ → … → final output
```

See [diagram.md](diagram.md) for the control-flow diagram.

## When to use it

- The task has **clear sequential sub-goals** (extract → transform → format).
- Each step produces output that a subsequent step must refine or extend.
- You want **predictable structure**: the pipeline shape is known up front.

Reach for ReAct when the number of steps is unknown, or for Routing when a
single classification call is all that's needed.

## Run it

```bash
python patterns/01-prompt-chaining/example.py
pytest patterns/01-prompt-chaining/
```

## The shape of the code

`run_prompt_chain(initial_input, steps, client)` in [pattern.py](pattern.py):

1. For each `ChainStep`, format its `prompt_template` with the current output.
2. Call the model; record a `"reasoning"` step with timing.
3. The model's text becomes the input for the next step.
4. Return the final output with the full trace.
