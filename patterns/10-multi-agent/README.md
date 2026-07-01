# 10 · Multi-Agent

> A supervisor routes a task to specialized agents and synthesizes their outputs.

Each agent has a defined role. The supervisor examines the task and selects
which agents to invoke. Each selected agent runs independently on the full
task (filtered through their role), and the supervisor synthesizes the results.

```
                 ┌─[researcher]─┐
task → supervisor├─[critic    ]─┤ → synthesis → answer
  (selects roles)└─[writer    ]─┘
```

See [diagram.md](diagram.md) for the control-flow diagram.

## When to use it

- Different **role perspectives** are needed on the same problem.
- You want **dynamic selection**: the supervisor decides which experts are relevant.
- Agents are **reusable** across tasks — add them to a pool, supervisor picks at runtime.

## Run it

```bash
python patterns/10-multi-agent/example.py
pytest patterns/10-multi-agent/
```

## The shape of the code

`run_multi_agent(task, agents, supervisor)` in [pattern.py](pattern.py):

1. Supervisor selects relevant agents from the pool (JSON routing decision).
2. Each selected agent processes the task through their role lens.
3. Supervisor synthesizes all outputs into a final answer.
