# Human-in-the-Loop — Interview Questions & Answers

## Conceptual

**1. What is the human-in-the-loop pattern, and what distinguishes a checkpointed tool?**

The pattern is a ReAct loop where certain tools — marked as "checkpointed" — pause execution and request explicit human approval before they are dispatched. Non-checkpointed tools execute freely. The distinction is a configuration flag (or a set of tool names) that the runtime checks before each dispatch. It gives humans a veto over high-stakes or irreversible actions while keeping low-risk tool calls automated.

**2. How does the agent know which tools require human approval?**

The set of checkpointed tool names is defined in configuration at startup — separate from the tools' own definitions — and injected into the runtime's dispatch logic. This keeps authorization policy decoupled from tool implementation; a tool does not know whether it is checkpointed, and the policy can be changed without modifying tool code.

**3. What happens when a human rejects a checkpointed tool call?**

The implementation raises a `HumanAborted` exception immediately, which unwinds the current ReAct step. In the simplest design, this terminates the run with a "rejected by human" status. A more sophisticated design catches the rejection, appends it as an observation ("Human rejected: [reason]"), and lets the model try a different approach.

## Trade-offs

**4. How would you decide which tools to checkpoint in a real deployment?**

Checkpoint tools whose effects are irreversible (send email, delete record, charge payment), highly visible (post to social media, create ticket), or outside the agent's verified authority (access another user's data). Tools that only read or compute (search, calculate, summarize) generally do not need checkpointing. A simple heuristic: checkpoint anything that writes, deletes, or sends.

**5. How does unbounded human approval latency interact with the step bound?**

If the human takes hours to approve, the step bound timer — if one exists — may expire before approval arrives. The system must either pause the timer during approval windows or set the step bound to wall-clock time rather than number of iterations. The safest design suspends the run entirely at the checkpoint and resumes it only when the human responds, with no timeout.

## Implementation & Failure Modes

**6. What is the "rubber stamp" risk, and how do you design against it?**

A rubber stamp approver approves every request without reading it, providing the appearance of oversight without the reality. Design against it by: surfacing a clear plain-language summary of what the tool will do (not just raw arguments), requiring the approver to select from "approve / reject / ask for clarification" rather than a single confirm button, and logging all approvals for periodic audit.

**7. If the human approves a tool call but the tool then fails, does the agent retry? Should it request re-approval?**

The agent should retry transient failures (network timeout, rate limit) without re-approval — the human already authorized the intent, and the failure was mechanical. For substantive failures (the tool returns an error that changes what the retry would do), the agent should seek re-approval with the new context rather than re-using the prior authorization.

## Extension

**8. How would you implement asynchronous human approval — agent pauses and resumes on response?**

Serialize the agent's full state (conversation history, trace, pending tool call) and store it in a durable queue. Send the human a notification with an approval link. When the human responds, retrieve the serialized state, inject the approval/rejection as an observation, and resume the ReAct loop from exactly where it paused. This requires idempotent tool dispatch and a run-ID-based state store.
