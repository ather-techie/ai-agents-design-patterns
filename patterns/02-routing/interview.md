# Routing — Interview Questions & Answers

## Conceptual

**1. Describe the routing pattern. What distinguishes it from a plain if-else dispatch in code?**

A routing agent uses an LLM as the classifier — it reads the user's natural-language query and selects the appropriate handler from a set of named routes. Unlike a hard-coded if-else, the LLM generalizes to paraphrases, ambiguous phrasing, and novel intents that no regex or keyword match could cover.

**2. Why is routing described as "the cheapest useful agent baseline"? What does it optimize for?**

The entire agentic behavior fits in a single LLM call (the classifier); after that, a simple function dispatch runs with no further model calls. It optimizes for latency and cost: you get intelligent, language-aware dispatch without paying for a reasoning loop or tool calls.

**3. In this implementation, how many LLM calls does a single query require, and why is that significant?**

Exactly one — the classifier call. The handler that executes after routing is pure code. This makes routing trivially cheap to scale and easy to reason about; there are no emergent multi-turn behaviors to debug.

## Trade-offs

**4. What are the risks when the classifier mislabels a query? How do you measure and improve accuracy?**

A mislabeled query reaches the wrong handler, which may produce a confidently wrong answer with no indication of the error. You measure accuracy with a labeled eval set covering common and edge-case queries per route. Improvements include better route descriptions in the system prompt, few-shot examples for ambiguous categories, and adding a confidence threshold below which the query falls back to a general handler.

**5. How does routing compare to parallelization for a query that spans multiple categories?**

Routing dispatches to exactly one handler, so a cross-category query (e.g., a billing question that is also technical) either gets misrouted or hits a catch-all. Parallelization fans out to multiple handlers simultaneously and merges answers, which is better for multi-faceted queries at the cost of higher latency and token spend.

## Implementation & Failure Modes

**6. How would you handle a query that scores equally across two routes, or falls below a confidence threshold?**

Route the query to a general-purpose fallback handler that can address any topic without deep specialization. Optionally, log the ambiguous query for offline analysis to decide whether to add a new route or improve the classifier prompt.

**7. What happens to routing accuracy as the number of routes grows?**

Inter-route confusion increases because category boundaries overlap more as the taxonomy becomes finer-grained. Past roughly 10–15 routes, a single classifier often needs richer descriptions, few-shot examples, or a hierarchical two-level classifier (coarse category → fine-grained sub-route) to maintain accuracy.

## Extension

**8. How would you extend this pattern to support hierarchical routing while keeping latency acceptable?**

Use two sequential LLM calls: a first-level classifier maps the query to a broad category (e.g., "billing"), then a second-level classifier within that category picks the specific handler (e.g., "refund" vs. "invoice"). Because both calls are cheap classifier prompts with no tool loops, total latency stays well under a second for most deployments.
