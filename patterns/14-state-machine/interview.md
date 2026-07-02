# State Machine — Interview Questions & Answers

## Conceptual

**1. How does the state-machine pattern structure an LLM workflow differently from a free-form ReAct loop?**

A state machine encodes the control flow as an explicit graph of named states and allowed transitions defined upfront. The LLM can only move between states that are connected by an edge — it cannot invent new states or skip to an arbitrary state. This makes the agent's behavior auditable, testable, and constrained by design, unlike a ReAct loop where the model freely chooses any tool or answer at any step.

**2. How does the agent decide which state to transition to next?**

At each non-terminal state, the model receives the current state name, the accumulated context from all prior states, and the list of valid outgoing transitions for that state. It selects one transition label. The runtime looks up the target state in the graph and moves there — the model never directly names a state, only a transition from the current one.

**3. What defines a terminal state, and how does the loop know it has reached one?**

A terminal state has no outgoing transitions — its edges list is empty. The loop checks after each transition whether the new state has any available transitions; if not, it collects the final accumulated context and calls the synthesis step to produce the final answer.

## Trade-offs

**4. How does the state-machine pattern compare to plan-and-execute?**

Plan-and-execute generates a dynamic plan at runtime — the planner decides steps based on the specific input. A state machine's structure is fixed at design time — the same graph applies to every input. State machines are better for well-understood, repeatable workflows (customer onboarding, structured triage); plan-and-execute is better for open-ended tasks where the right approach depends on the problem.

**5. What are the costs of getting the state graph wrong?**

Too few states: insufficient granularity means the agent cannot differentiate between importantly different situations. Too many states: the graph becomes unmaintainable and the LLM struggles to select among too many transition options. Missing a transition: the agent gets trapped in a state that should be able to reach another one but cannot, hitting the step bound instead of completing naturally.

## Implementation & Failure Modes

**6. What should happen if the LLM selects a transition that does not exist for the current state?**

Treat it as a validation error: do not execute the invalid transition, log the invalid selection, and re-prompt the model with an explicit reminder of valid transitions for the current state. If the model repeatedly selects invalid transitions, it is a signal that the current state's context or transition descriptions are ambiguous and need to be clarified.

**7. How would you detect a liveness failure (a state that can be entered but never exited) during graph design?**

Run a static graph analysis before deployment: perform a reachability check from every non-terminal state to at least one terminal state. Any state with no path to a terminal is a liveness failure. Automated tooling (a simple DFS over the transition graph) can catch these at configuration time before the graph is ever invoked at runtime.

## Extension

**8. How would you allow the state machine to add new states dynamically mid-execution?**

Reserve a special "expand" transition available from any state. When the LLM emits this transition, it also emits a structured description of the new state(s) and their connections. The runtime validates these against a schema (allowed tools, max new states), adds them to the in-memory graph, and continues. This preserves the graph's formal structure while allowing bounded runtime extension for unanticipated intents.
