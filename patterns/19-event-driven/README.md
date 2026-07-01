# Pattern 19: Event-Driven Agent

## When to use

Use the Event-Driven pattern when an agent must react to a stream of incoming events and maintain state across them. Each event triggers a bounded ReAct mini-loop; state persists between events so the agent can correlate information over time — escalating alerts, tracking counts, accumulating context. Useful for:

- Monitoring pipelines (metric → alert → resolve)
- Workflow automation (order placed → inventory check → confirmation)
- Multi-step processes where each step produces an event

## Quick start

```bash
# Offline demo (no API key needed)
python patterns/19-event-driven/example.py

# Live mode
ANTHROPIC_API_KEY=sk-... python patterns/19-event-driven/example.py
```

## Code shape

```python
from shared.llm_client import build_client
from shared.config import Config
from shared.tools import ToolRegistry
from pattern import AgentState, Event, run_event_driven

config = Config.from_env()
client = build_client(config, mock_planner=make_planner())
registry = ToolRegistry()   # add your domain tools here

events = [
    Event(type="metric", payload="cpu_usage=95%"),
    Event(type="metric", payload="cpu_usage=45%"),
    Event(type="report",  payload="generate status"),
]

result = run_event_driven(
    events=events,
    registry=registry,
    client=client,
    max_steps_per_event=4,
)
print(result.final_summary)
print(result.state.snapshot())
```

## Trace steps

| Step | Meaning |
|------|---------|
| `event` | An incoming event is being processed |
| `tool_call` | Agent called a tool during event processing |
| `observation` | Tool result fed back to the agent |
| `answer` | Final summary after all events |

## Built-in tool

A `state_set(key, value)` tool is automatically registered and writes into the shared `AgentState.data` dict. It is available to the agent during every event's mini-loop.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_steps_per_event` | `4` | Maximum ReAct steps per event before moving on |
| `state` | `None` | Pre-populated `AgentState`; created fresh if omitted |
