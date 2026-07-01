# Pattern 17: Mixture-of-Experts (MoE)

## When to use

Use Mixture-of-Experts when a query spans multiple domains and no single system prompt handles all facets well. A router selects the best specialists for the question, each answers independently, and a synthesis call merges their perspectives into one coherent reply. This gives you the depth of domain-specific expertise combined with the breadth of generalist synthesis.

Good fits:
- Cross-disciplinary questions ("Can I deduct medical expenses?" → legal + medical)
- Queries where different framing radically changes the answer (technical, legal, business angles)
- Tasks where you want multiple independent opinions before a final summary

## Quick start

```bash
# Offline demo (no API key needed)
python patterns/17-mixture-of-experts/example.py

# Live mode
ANTHROPIC_API_KEY=sk-... python patterns/17-mixture-of-experts/example.py
```

## Code shape

```python
from shared.llm_client import build_client
from shared.config import Config
from pattern import Expert, run_mixture_of_experts

experts = [
    Expert(name="legal",    domain="tax law",         system_prompt="You are a legal expert..."),
    Expert(name="medical",  domain="healthcare",      system_prompt="You are a medical expert..."),
    Expert(name="financial",domain="personal finance", system_prompt="You are a financial advisor..."),
]

config = Config.from_env()
client = build_client(config, mock_planner=make_planner())

result = run_mixture_of_experts(
    query="Can I deduct medical expenses from my taxes?",
    experts=experts,
    client=client,
    top_k=2,
)
print(result.synthesis)
```

## Trace steps

| Step | Meaning |
|------|---------|
| `route` | Router selected these expert names |
| `delegate` | One expert produced an answer |
| `reasoning` | Synthesis LLM merged expert answers |
| `answer` | Final synthesized answer |

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `top_k` | `2` | Number of experts selected by the router |

When `top_k == 1` the synthesis call is skipped and the single expert's answer is returned directly.
