# Event-Driven — Interview Questions & Answers

## Conceptual

**1. What is the event-driven agent pattern, and how does it differ from a single ReAct run?**

The event-driven pattern processes a stream of discrete events, running a bounded mini-ReAct loop for each event and maintaining persistent state across all of them. A single ReAct run handles one task from start to finish. Here, the "task" is ongoing — the agent continuously reacts to new inputs over time, updating shared state with each event rather than concluding after one answer.

**2. How does state persist across events?**

A `state_set(key, value)` tool writes key-value pairs to a persistent StateStore. At the start of each event's mini-loop, the current snapshot of that store is injected into the prompt as "current state." The model reads prior state to understand context (e.g., a running total, a user's escalation level) before deciding how to handle the new event.

**3. Why does each event trigger its own bounded mini-ReAct loop rather than one continuous loop?**

One continuous loop would accumulate all event history in a single growing context window, eventually hitting token limits and conflating the reasoning for different events. Per-event loops keep context proportional to the current event plus the compact state snapshot. Each loop's step bound also prevents runaway processing on a single event from blocking the queue.

## Trade-offs

**4. How does the event-driven pattern compare to a stateful ReAct agent with memory?**

Both persist state across interactions. The key difference is structure: event-driven makes the "stream of inputs" and "per-event loop" model explicit — each input is a discrete event with a defined processing cycle. A memory-augmented ReAct agent is better for conversational sessions where the user drives the interaction. Event-driven is better for automated pipelines where events arrive from external systems (queues, webhooks, sensors).

**5. How does the state prompt scale as state grows large?**

Injecting the full state snapshot into every event's prompt is cheap when state is small (a dozen keys), but becomes expensive as state grows to hundreds of keys with large values. Beyond a certain threshold, switch to selective state injection: retrieve only the state keys relevant to the current event type (via a keyword lookup or small classifier), keeping the prompt lean regardless of total state size.

## Implementation & Failure Modes

**6. What happens when two events arrive out of order?**

If event B arrives before event A and B's state update assumes A's state already exists, the agent operates on an inconsistent view. Guard against this with sequence numbers on events and a buffer that holds out-of-order events until their predecessors arrive. For truly unordered event streams (e.g., sensor readings), design state updates to be commutative — order-independent — so out-of-order processing does not corrupt state.

**7. If `state_set` writes a logically wrong value mid-loop, how would you detect and correct it before the next event?**

Add a state-validation step after the mini-loop completes: run a lightweight LLM or rule-based check against the updated state snapshot (e.g., "balance must be non-negative", "status must be a valid enum value"). If validation fails, rollback the state to the pre-event snapshot and log the event for manual review rather than poisoning subsequent events.

## Extension

**8. How would you adapt this pattern to high-frequency events where per-event mini-ReAct loops are too slow?**

Batch events: accumulate N events (or events within a time window), inject them all into a single mini-loop prompt as a list, and process the batch in one pass with a single set of state updates. The model reasons over the batch collectively, then calls `state_set` once with the net result. This reduces LLM call frequency by N× at the cost of some per-event reasoning granularity.
