# ReAct — Interview Questions & Answers

## Conceptual

**1. Explain the Reason-Act-Observe loop. What happens in each phase?**

Reason: the model reads the task plus the full conversation history (all prior observations) and thinks through its next move, emitting either a tool call or a final answer. Act: if a tool call was emitted, the runtime validates the arguments against the tool's schema and dispatches it. Observe: the tool's result is appended to the conversation as an observation, and the loop returns to the Reason phase. The cycle repeats until the model emits an answer or the step bound is hit.

**2. How does the model decide to call a tool versus emit a final answer?**

The model's response is inspected for a `tool_use` block (tool call) versus an `end_turn` stop reason with regular text (final answer). The implementation checks which signal is present and routes control accordingly — no magic, just a branch on the response type.

**3. Why is tool validation performed before dispatch rather than after?**

Pre-dispatch validation catches malformed arguments (wrong types, missing required fields) before they reach the tool implementation, preventing confusing downstream errors. It also lets the runtime return a structured error message to the model ("argument `query` must be a string") that the model can use to self-correct on the next reasoning step.

## Trade-offs

**4. How does ReAct compare to plan-and-execute?**

ReAct replans dynamically on every step — each observation can change the next action. Plan-and-execute commits to a static plan upfront and executes each step independently. ReAct is better when the task is unpredictable and observations frequently change the direction; plan-and-execute is better when subtasks are independent and parallelizable, or when a reliable upfront plan reduces total LLM calls.

**5. How would you tune the step bound for a latency-sensitive application?**

Profile a representative set of tasks and record the step count at which each reached its answer. Set the step bound to the 95th percentile of that distribution — most tasks finish well under it, while genuinely hard tasks get enough steps. For latency-critical paths, add a soft warning at 50% of the bound so the model knows to start wrapping up rather than exploring further.

## Implementation & Failure Modes

**6. What happens when the model enters a reasoning loop — calling the same tool repeatedly with the same arguments?**

The model gets no new information each iteration, so it is stuck. Detect this by hashing each tool call (name + args) and tracking the history within the run; if the same hash appears twice in a row, inject an observation telling the model the tool was already called with those arguments and the result was the same, prompting it to try a different approach or conclude with what it knows.

**7. Describe a scenario where an observation causes the model to abandon its original plan. Is this a bug or a feature?**

A user asks "find the cheapest flight to Paris." The model searches and discovers all flights are sold out. Instead of returning a price, it pivots to notifying the user of no availability and suggesting alternative dates. This is a feature — dynamic replanning is the core value proposition of ReAct over a static pipeline.

## Extension

**8. How would you add persistent memory so observations from a previous session are available at the start of a new one?**

Before the first reasoning step, retrieve relevant memories from a vector store using the current task as the query and prepend them to the system prompt as "prior context." After the session ends, save significant observations (facts learned, user preferences) back to the store. The in-session ReAct loop is unchanged; memory retrieval and storage happen as setup/teardown around it.
