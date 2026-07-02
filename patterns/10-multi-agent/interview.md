# Multi-Agent — Interview Questions & Answers

## Conceptual

**1. What is the supervisor's role, and how does its two-call structure differ from single orchestration?**

The supervisor first makes a routing call to select which agents to dispatch (based on the query's nature), then makes a synthesis call after all agents respond. Splitting these responsibilities means the routing call can reason about agent capabilities without being distracted by partial results, and the synthesis call can focus entirely on integrating outputs without replaying routing logic.

**2. Why does each agent receive the full task prefixed with its role rather than a narrowed subtask?**

Giving each agent the full original task lets it apply its specialized perspective to the whole problem — a billing agent might notice a technical constraint relevant to the billing answer that a subtask-only prompt would have omitted. The role prefix steers its lens; the full task gives it complete context to work from.

**3. How does agent isolation work, and why is it by design?**

Each agent gets its own message list and system prompt; it cannot see what other agents are writing. This isolation ensures each agent provides a genuinely independent perspective — if agents could read each other mid-execution, the first responder would anchor all others, defeating the purpose of multi-agent breadth.

## Trade-offs

**4. How does multi-agent compare to orchestrator-workers?**

Multi-agent routes the full task to role-based agents and synthesizes their independent views — best when you want diverse expert perspectives on the same problem. Orchestrator-workers decomposes the task into subtasks where each worker addresses a non-overlapping piece — best when the problem has distinct parts that can be solved independently and combined. Use multi-agent for analysis; use orchestrator-workers for production tasks.

**5. At what point does a larger agent pool start hurting output quality?**

When agent roles overlap significantly (near-duplicate outputs) or when the synthesis LLM exceeds its effective context for integrating many responses coherently. In practice, 3–6 well-differentiated agents is the sweet spot; beyond that, synthesis quality plateaus or degrades as the model struggles to reconcile too many voices.

## Implementation & Failure Modes

**6. What happens when two agents produce directly contradictory conclusions?**

The synthesis prompt should explicitly instruct the model to identify contradictions, explain the reasoning behind each agent's position, and either resolve the conflict (if one is clearly better supported) or surface both positions as a nuanced answer that acknowledges the disagreement. Silent averaging — picking neither — is the failure mode to guard against.

**7. How would you prevent agents with overlapping roles from producing redundant outputs?**

Design agent role descriptions to be mutually exclusive in scope. Before deploying, run a test query through all agents and compute semantic similarity between outputs; if two agents consistently produce high-similarity responses, merge their roles or sharpen the distinction in their system prompts.

## Extension

**8. How would you implement inter-agent communication while preserving isolation?**

Use a message-passing pattern: after each agent's first response, allow it to post one structured "question" to a named other agent via a special tool call. The runtime collects these cross-agent questions, resolves them in a second round of targeted agent calls, and injects the answers back before final synthesis. This adds one extra round-trip but enables grounded cross-referencing without agents reading each other's full output.
