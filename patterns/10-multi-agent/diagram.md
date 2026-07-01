# Multi-Agent — control flow

```mermaid
flowchart TD
    Task([Task]) --> Sup1[Supervisor LLM\nrouting prompt]
    Sup1 --> Route["JSON routing decision\n{selected: [agent1, agent2, ...]}"]

    Route --> D1[delegate: researcher\nfull task + role]
    Route --> D2[delegate: critic\nfull task + role]
    Route --> D3[delegate: writer\nfull task + role]

    D1 --> A1[Researcher LLM]
    D2 --> A2[Critic LLM]
    D3 --> A3[Writer LLM]

    A1 --> O1[researcher output]
    A2 --> O2[critic output]
    A3 --> O3[writer output]

    O1 --> Sup2[Supervisor LLM\nsynthesis prompt]
    O2 --> Sup2
    O3 --> Sup2

    Sup2 --> Answer([Final Answer])
```

The supervisor makes two LLM calls: one to produce the routing decision, one to
synthesize results. Each agent makes exactly one call and receives the full
task prefixed by their role description — every agent sees the whole problem
from their own perspective, not a fragment.

Unknown agent names in the routing decision are recorded as error trace steps
and skipped; the remaining selected agents still execute normally.
