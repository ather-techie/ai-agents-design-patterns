# Parallelization — Interview Questions & Answers

## Conceptual

**1. What is the parallelization pattern, and what tasks benefit most from it?**

Parallelization fans out a single query to N worker LLM calls simultaneously, each with a different system prompt (e.g., different expert personas, different analytical lenses), then fans in their outputs to an aggregator LLM that synthesizes a final answer. Tasks benefit most when multiple independent perspectives genuinely add value — risk analysis, multi-criteria evaluation, or comprehensive coverage of a topic.

**2. How does the aggregator LLM differ from the workers in terms of its prompt and role?**

Workers receive only the original query plus their own specialized system prompt; they have no awareness of other workers. The aggregator receives all worker outputs and is specifically prompted to synthesize, reconcile conflicts, and produce a unified answer — it is not solving the original problem itself, only integrating solutions.

**3. What guarantees does this pattern make about worker independence? When would shared state be problematic?**

Each worker call is fully isolated — separate message lists, no shared context. This is a guarantee by construction. Shared state would be problematic if workers need to coordinate (e.g., splitting up a dataset to avoid duplicate analysis), which would require a pre-allocation step before dispatch.

## Trade-offs

**4. How does cost scale with the number of workers, and when would you prefer sequential processing?**

Cost scales linearly with N workers because each makes a full LLM call. Sequential processing is preferable when each step genuinely depends on the result of the previous one (making parallelism incorrect, not just expensive), or when budget is tight and one strong generalist prompt is nearly as good as multiple specialists.

**5. Parallelization reduces latency but not token cost. Under what business constraints would you prefer sequential?**

When cost-per-query is the primary constraint (high-volume consumer product) rather than response time, or when the task is inherently serial — e.g., summarizing the output of a previous summarization step. Also prefer sequential when aggregating multiple opinionated answers introduces hallucinated consensus that a single focused call would avoid.

## Implementation & Failure Modes

**6. If one worker call times out, what should the aggregator do?**

Proceed with the remaining workers' outputs rather than failing the entire request. The aggregator prompt should note which perspectives are missing so it can caveat its synthesis accordingly. Optionally, log the timeout for monitoring so flaky workers can be identified and their prompts or timeouts tuned.

**7. How do you prevent the aggregator from simply repeating the first worker's answer?**

Explicitly instruct the aggregator to identify where workers agree, where they differ, and to synthesize a position that accounts for all views — not just the first. Including a "most important differences" step in the aggregator prompt before the synthesis step forces it to engage with all inputs.

## Extension

**8. How would you combine parallelization with routing?**

Route the query first to determine the relevant domain, then fan out only the specialist workers relevant to that domain rather than all workers every time. This reduces per-query cost while keeping the multi-perspective benefit for queries that warrant it.
