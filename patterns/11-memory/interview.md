# Memory-Augmented Agent — Interview Questions & Answers

## Conceptual

**1. What problem does adding a MemoryStore to a ReAct agent solve?**

A base ReAct agent forgets everything when the session ends — each new conversation starts from zero. A MemoryStore lets the agent persist facts across sessions (user preferences, prior decisions, domain knowledge it has learned) so it can provide personalized, context-aware responses without the user repeating themselves.

**2. Describe the three memory operations and when an agent would invoke each.**

`remember(key, value)` stores a new fact — used when the agent learns something worth keeping (e.g., "user prefers metric units"). `recall(query)` retrieves stored facts relevant to the current task — used before answering to check for prior context. `forget(key)` removes a fact that is outdated or incorrect — used when the user corrects something the agent previously stored.

**3. How are memory steps distinguished from tool observation steps in the trace?**

Memory operations are recorded as `"memory"` steps; regular tool calls produce `"observation"` steps. This distinction lets you filter the trace to audit what the agent remembered or retrieved during a session, separate from what it computed or looked up, which is critical for debugging unexpected behavior driven by stale memories.

## Trade-offs

**4. How does in-context memory (stuffing prior turns into the prompt) compare to an external MemoryStore?**

In-context memory is simple and always consistent — everything the model needs is right there — but it grows without bound and eventually hits the context window limit. An external MemoryStore is scalable and persistent across sessions, but introduces retrieval latency, potential recall misses, and consistency risks if the store is written concurrently.

**5. What are the consistency risks of a persistent MemoryStore across concurrent sessions?**

Two sessions running simultaneously could write conflicting values for the same key (e.g., one session stores "preferred language: French", another stores "preferred language: Spanish"). Without a locking or versioning strategy, the last write wins silently. Mitigate with optimistic locking (version numbers), per-user namespacing, and eventual-consistency design (the model can handle slight staleness gracefully).

## Implementation & Failure Modes

**6. What happens when recall becomes ambiguous — multiple memories match the query equally well?**

The agent must either return all matching memories (risking an overlong context injection) or rank them by recency, relevance score, or explicit priority. The best design returns the top-K most relevant memories with their metadata (timestamp, confidence) and lets the model reason about which to trust, rather than silently truncating.

**7. How would you build in memory freshness checks?**

Store a `written_at` timestamp alongside every memory. Before using a recalled memory, compute its age and inject a staleness warning into the prompt if it exceeds a threshold (e.g., "this fact is 90 days old — verify before acting on it"). For high-stakes facts (addresses, account numbers), prompt the user to confirm rather than acting directly on a stale value.

## Extension

**8. How would you implement tiered memory without changing the agent's tool interface?**

Keep the `remember/recall/forget` tool signatures unchanged but back them with a tiered store: short-term (Redis, in-memory) for the current session, long-term (vector database) for cross-session persistence. The `recall` implementation queries short-term first (fast, exact), then falls back to long-term semantic search. The agent's prompts and tool calls are identical; only the storage layer changes.
