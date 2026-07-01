# Pattern 18: Speculative Execution

## When to use

Use Speculative Execution when a single attempt at a solution may miss important cases and you want to trade latency for quality. The pattern generates `n_candidates` independent solutions, scores each against a rubric, and returns the highest scorer. Effective when:

- The solution space is large (algorithms, code, essays)
- You want self-consistency checking without a human in the loop
- Quality variance across attempts is high and you can afford more LLM calls

## Quick start

```bash
# Offline demo (no API key needed)
python patterns/18-speculative/example.py

# Live mode
ANTHROPIC_API_KEY=sk-... python patterns/18-speculative/example.py
```

## Code shape

```python
from shared.llm_client import build_client
from shared.config import Config
from pattern import run_speculative

config = Config.from_env()
client = build_client(config, mock_planner=make_planner())

result = run_speculative(
    task="Write a Python function to check if a number is prime.",
    client=client,
    n_candidates=3,
)
print(f"Winner (score {result.winner.score}):")
print(result.winner.content)
```

## Trace steps

| Step | Meaning |
|------|---------|
| `candidate` | One generated solution (n_candidates total) |
| `critique` | Evaluator scored one candidate |
| `answer` | Winning candidate selected |

Total steps for `n > 1`: `2 * n_candidates + 1`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_candidates` | `3` | Number of independent solutions to generate |

When `n_candidates == 1` the scoring step is skipped and the single candidate receives a score of 10.0 automatically.

## Scoring format

The evaluator LLM is prompted to respond with:

```
SCORE: X.X
RATIONALE: ...
```

Scores are parsed with a regex; malformed responses default to `0.0`.
