# 16 · Constitutional

> Iteratively **critique and revise** a draft against a set of explicit principles.

Inspired by Constitutional AI, this pattern first generates an initial draft, then applies each `Principle` as a critic lens to produce targeted critiques, and finally asks the model to revise the draft in light of all critiques. The critique-revision loop repeats up to `max_revisions` times.

```
[initial draft]
      ↓  (for each principle)
[critique-clarity] [critique-brevity] ...
      ↓
[revision 1]
      ↓  (repeat up to max_revisions)
[answer]
```

## When to use it

- You have **explicit quality criteria** (safety, clarity, brevity, tone) the output must satisfy.
- You want **traceable, auditable** improvements with one critique step per principle.
- The task benefits from **multiple revision passes** rather than a single generation.
- Useful for regulated content (compliance text, customer communications, policies).

Reach for [Reflection](../08-reflection/) when you want open-ended self-critique rather than principle-driven critique, or [Debate](../15-debate/) when you need adversarial perspectives.

## Run it

No API key required — the demo runs against the deterministic offline mock:

```bash
python patterns/16-constitutional/example.py     # prints the trace tree + final draft
pytest patterns/16-constitutional/               # run the tests
```

Set `ANTHROPIC_API_KEY` (and leave `USE_MOCK` unset) to run the *same* pattern code against the live model.

## The shape of the code

`run_constitutional(task, principles, client, *, max_revisions, trace)` (in [pattern.py](pattern.py)):

1. **Initial draft**: LLM call → record `"reasoning"` step.
2. If `principles` is empty → record `"answer"` and return draft as-is.
3. For each revision pass (up to `max_revisions`):
   - For each principle: LLM critique call → record `"critique"` step.
   - LLM revision call with all critiques → record `"revision"` step.
4. Record `"answer"` step with the final draft.

Critiques are stored as `(principle_name, critique_text)` tuples on `ConstitutionalResult.critiques`.
