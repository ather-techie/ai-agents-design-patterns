# AI Agents Design Patterns — common tasks.
# Override the interpreter with `make PYTHON=python3 ...` if needed.

PYTHON ?= python

.PHONY: help install demo bench test routing-demo \
        memory-demo self-ask-demo human-loop-demo state-machine-demo \
        debate-demo constitutional-demo moe-demo speculative-demo \
        event-driven-demo least-to-most-demo

help:
	@echo "Targets:"
	@echo "  make install              Install the package + dev deps (editable)"
	@echo "  make demo                 Run the ReAct demo in mock mode (prints a trace tree)"
	@echo "  make bench                Run the comparison harness (prints the tradeoff table)"
	@echo "  make test                 Run the test suite"
	@echo "  make routing-demo         Run the Routing demo"
	@echo "  make memory-demo          Run the Memory-Augmented demo"
	@echo "  make self-ask-demo        Run the Self-Ask demo"
	@echo "  make human-loop-demo      Run the Human-in-the-Loop demo"
	@echo "  make state-machine-demo   Run the State Machine demo"
	@echo "  make debate-demo          Run the Debate demo"
	@echo "  make constitutional-demo  Run the Constitutional demo"
	@echo "  make moe-demo             Run the Mixture-of-Experts demo"
	@echo "  make speculative-demo     Run the Speculative Execution demo"
	@echo "  make event-driven-demo    Run the Event-Driven demo"
	@echo "  make least-to-most-demo   Run the Least-to-Most demo"

install:
	$(PYTHON) -m pip install -e ".[dev]"

# Force mock mode so the demo always runs offline, with or without a key set.
demo:
	USE_MOCK=1 $(PYTHON) patterns/07-react/example.py

routing-demo:
	USE_MOCK=1 $(PYTHON) patterns/02-routing/example.py

memory-demo:
	USE_MOCK=1 $(PYTHON) patterns/11-memory/example.py

self-ask-demo:
	USE_MOCK=1 $(PYTHON) patterns/12-self-ask/example.py

human-loop-demo:
	USE_MOCK=1 $(PYTHON) patterns/13-human-in-the-loop/example.py

state-machine-demo:
	USE_MOCK=1 $(PYTHON) patterns/14-state-machine/example.py

debate-demo:
	USE_MOCK=1 $(PYTHON) patterns/15-debate/example.py

constitutional-demo:
	USE_MOCK=1 $(PYTHON) patterns/16-constitutional/example.py

moe-demo:
	USE_MOCK=1 $(PYTHON) patterns/17-mixture-of-experts/example.py

speculative-demo:
	USE_MOCK=1 $(PYTHON) patterns/18-speculative/example.py

event-driven-demo:
	USE_MOCK=1 $(PYTHON) patterns/19-event-driven/example.py

least-to-most-demo:
	USE_MOCK=1 $(PYTHON) patterns/20-least-to-most/example.py

bench:
	$(PYTHON) -m bench.compare

test:
	$(PYTHON) -m pytest
