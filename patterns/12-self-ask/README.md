# 12 · Self-Ask

> Decompose a complex question into **sub-questions**, answer each, then synthesize.

Self-Ask is a pure-LLM strategy — no tools required. The model is asked to break
a hard question into simpler ones, each answered individually with prior answers
as context, and then the answers are combined into a final response. It trades
multiple LLM calls for improved accuracy on multi-hop reasoning tasks.

```
question → [decompose] → sub-q₁ → [answer] → sub-q₂ → [answer] → … → [synthesize] → answer
```

## When to use it

- Questions that require **chaining facts** (e.g. "What is the population of
  the capital of the country that hosted the 2012 Olympics?").
- You want the reasoning chain to be **inspectable** — every sub-question and
  its answer are recorded in the trace.
- Tasks where a single-pass response is likely to miss intermediate steps.

Reach for [ReAct](../07-react/) when the agent also needs external tools (search,
calculators, APIs). Use a single call when the question is genuinely one-hop.

## Run it

No API key required — the demo runs against the deterministic offline mock:

```bash
python patterns/12-self-ask/example.py     # prints the trace tree + answer
pytest patterns/12-self-ask/               # run the tests
```

Set `ANTHROPIC_API_KEY` (and leave `USE_MOCK` unset) to run the *same* pattern
code against the live model (`claude-opus-4-8`, adaptive thinking).

## The shape of the code

`run_self_ask(question, client, *, max_sub_questions)` (in [pattern.py](pattern.py)):

1. **Decompose** — ask the model for a JSON array of sub-questions (capped at
   `max_sub_questions`). Falls back to treating the raw response as a single
   sub-question if JSON parsing fails.
2. **Answer each sub-question** — one LLM call per sub-question, with prior
   Q&A pairs injected as context. Recorded as `"sub_question"` trace steps.
3. **Synthesize** — one final LLM call combining every sub-question and answer.
   Recorded as the `"answer"` trace step.
