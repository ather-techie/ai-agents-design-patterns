# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install the package and dev dependencies in editable mode
make install                  # python -m pip install -e ".[dev]"

# Run all tests
make test                     # python -m pytest

# Run tests for a single pattern
python -m pytest patterns/07-react/ -q

# Run the flagship ReAct demo in offline mock mode (no API key needed)
make demo                     # USE_MOCK=1 python patterns/07-react/example.py

# Run any other pattern's demo offline
make routing-demo             # USE_MOCK=1 python patterns/02-routing/example.py
# ... and equivalents for all 20 patterns (see Makefile for full list)

# Run the cross-pattern comparison benchmark (mock mode, prints a tradeoff table)
make bench                    # python -m bench.compare

# Run against the live Anthropic API (requires .env or env var)
cp .env.example .env          # fill in ANTHROPIC_API_KEY
python patterns/07-react/example.py
```

## Architecture

### Two execution modes

Every pattern runs identically in both modes — the only difference is the `LLMClient` implementation:

- **Mock mode** (default): `USE_MOCK=1` or no `ANTHROPIC_API_KEY` set. A `MockClient` is driven by a deterministic `planner` function that scripts the conversation. No network, no key, fully reproducible.
- **Live mode**: `AnthropicClient` wraps the `anthropic` SDK, targeting `claude-opus-4-8` with adaptive thinking by default.

`shared/config.py` reads the environment; `shared/llm_client.py:build_client()` returns the right client.

### Shared core (`shared/`)

All patterns import from here and stay provider-agnostic:

| File | Purpose |
|------|---------|
| `llm_client.py` | `LLMClient` protocol + `AnthropicClient` + `MockClient` + `build_client()` |
| `tools.py` | `Tool` dataclass + `ToolRegistry` with JSON Schema validation before dispatch |
| `trace.py` | `Trace` / `Step` — records reasoning→tool→observation tree; `timed_step` context manager |
| `config.py` | `Config.from_env()` — resolves mock/live mode and all overrides |
| `types.py` | `Message`, `LLMResponse`, `ToolCall`, `ToolResult`, `Usage` |
| `loader.py` | `load_pattern_module("07-react")` — loads `pattern.py` by file path under a unique synthetic module name (needed because every pattern uses the same filename) |
| `errors.py` | `MaxStepsExceeded`, `ToolValidationError`, `ToolError`, `ConfigError`, `AgentError` |

### Pattern structure (`patterns/NN-name/`)

Each pattern directory contains exactly three files:

- **`pattern.py`** — the implementation (one main `run_*` function, a result dataclass). Imports only from `shared`. No `example.py` code here.
- **`example.py`** — runnable demo: builds tools, writes a deterministic `mock_planner`, calls `Config.from_env()` + `build_client()`, runs the pattern, renders the trace.
- **`test_pattern.py`** — pytest tests: uses `load_pattern_module("NN-name")` to import `pattern.py`; builds a `MockClient` inline; asserts on the result and trace.

Pattern directories have a leading digit and hyphens (`07-react`), so they are **not importable as Python packages**. Only `shared` and `bench` are installed packages.

### Benchmark harness (`bench/compare.py`)

Loads all 20 patterns via `load_pattern_module`, runs the same 4 customer-support tasks through each in mock mode, aggregates `Trace` metrics (steps, tokens, latency, success rate), and prints a Rich table. Invoke with `make bench` or `python -m bench.compare`.

### Trace system

`Trace` is threaded through every pattern run. `trace.add(kind, summary)` records each step. `trace.render(console)` prints the color-coded Rich tree. `trace.succeeded` is `True` when the run ended with a non-error `answer` step. `timed_step` is a context manager that times a step's body and appends it to the trace automatically.

## Adding a new pattern

1. Duplicate `patterns/07-react/` into `patterns/21-new-name/`.
2. Rewrite `pattern.py` — implement one `run_*` function that accepts an `LLMClient` and a `Trace`, records steps, and returns a result dataclass.
3. Update `example.py` with new tools and a matching `mock_planner`.
4. Update `test_pattern.py` — tests load via `load_pattern_module("21-new-name")`.
5. Optionally add an entry to `bench/compare.py`.

## Environment variables

| Variable | Default | Effect |
|----------|---------|--------|
| `ANTHROPIC_API_KEY` | unset | Set to enable live mode |
| `USE_MOCK` | unset | `1/true/yes/on` forces mock mode even with a key |
| `AGENT_MODEL` | `claude-opus-4-8` | Model for live calls |
| `AGENT_MAX_STEPS` | `6` | Loop bound passed to patterns |
| `AGENT_TIMEOUT` | `60` | HTTP timeout in seconds |
| `AGENT_MAX_TOKENS` | `1024` | Max tokens per completion |
| `AGENT_LOG` | unset | Set to `info`/`debug` for structured JSON logs |
