# Pattern 20: Least-to-Most

## When to use

Use Least-to-Most when a problem is too complex to solve in one shot but can be scaffolded by first solving simpler sub-problems whose answers feed into harder ones. This mirrors how humans tackle difficult reasoning tasks:

1. Decompose the problem into sub-problems, from easiest to hardest
2. Solve each in sequence, with prior Q&A available as context
3. The final (hardest) sub-problem's answer is the complete solution

Good fits:
- Multi-step math word problems
- Compositional reasoning ("first find X, then use X to find Y")
- Tasks where intermediate results are reused in later steps

## Quick start

```bash
# Offline demo (no API key needed)
python patterns/20-least-to-most/example.py

# Live mode
ANTHROPIC_API_KEY=sk-... python patterns/20-least-to-most/example.py
```

## Code shape

```python
from shared.llm_client import build_client
from shared.config import Config
from pattern import run_least_to_most

config = Config.from_env()
client = build_client(config, mock_planner=make_planner())

result = run_least_to_most(
    problem=(
        "If a train travels at 60 mph for 2.5 hours, then 80 mph for 1.5 hours, "
        "what is the total distance and average speed?"
    ),
    client=client,
    max_sub_problems=5,
)

for sp in result.sub_problems:
    print(f"[{sp.index + 1}] Q: {sp.problem}")
    print(f"    A: {sp.answer}")

print(f"\nFinal answer: {result.answer}")
```

## Trace steps

| Step | Meaning |
|------|---------|
| `plan` | Decomposition produced N sub-problems |
| `reasoning` | One sub-problem solved (with prior context) |
| `answer` | Final answer (last sub-problem's answer) |

Total steps: `1 (plan) + N (reasoning) + 1 (answer)`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_sub_problems` | `5` | Maximum sub-problems to solve (list is truncated if the LLM produces more) |

## Fallback behaviour

If the decomposition LLM response is not valid JSON, the entire response is used as a single sub-problem string. The run completes with one sub-problem solved.
