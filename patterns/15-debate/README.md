# 15 · Debate

> Pit two LLM agents **for and against** a proposition, then let a neutral judge synthesize the verdict.

An affirmative agent argues FOR the proposition; a negative agent argues AGAINST it. With `rounds=2` each side gets a rebuttal. A neutral judge synthesizes the strongest answer from all arguments.

```
[affirmative opening] + [negative opening]
        ↓  (rounds >= 2)
[affirmative rebuttal] + [negative rebuttal]
        ↓
[judge verdict]
```

## When to use it

- You want to **stress-test a decision** by explicitly generating the strongest arguments on both sides.
- You need a **balanced synthesis** for a contentious or nuanced question.
- You want to surface **blind spots** a single-agent answer would miss.
- Useful as a pre-decision review step in autonomous pipelines.

Reach for [Reflection](../08-reflection/) when you only need self-critique of a single draft, or [Constitutional](../16-constitutional/) when you have explicit principles to enforce.

## Run it

No API key required — the demo runs against the deterministic offline mock:

```bash
python patterns/15-debate/example.py     # prints the trace tree + verdict
pytest patterns/15-debate/               # run the tests
```

Set `ANTHROPIC_API_KEY` (and leave `USE_MOCK` unset) to run the *same* pattern code against the live model.

## The shape of the code

`run_debate(proposition, client, *, rounds, trace)` (in [pattern.py](pattern.py)):

1. **Affirmative opening**: LLM call with system prompt arguing FOR → record `"delegate"` step.
2. **Negative opening**: LLM call with system prompt arguing AGAINST → record `"delegate"` step.
3. If `rounds >= 2`:
   - **Affirmative rebuttal** (sees negative opening) → record `"critique"` step.
   - **Negative rebuttal** (sees affirmative opening + rebuttal) → record `"critique"` step.
4. **Judge verdict**: neutral LLM call with full transcript → record `"answer"` step.

Each call has its own independent `Message` list — the agents do not share state.
