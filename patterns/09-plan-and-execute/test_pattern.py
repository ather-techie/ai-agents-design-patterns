"""Tests for the Plan-and-Execute pattern.

These are self-contained: they build their own tiny tool registry and scripted
mock planners rather than importing the demo, and load ``pattern.py`` by path
so the suite can hold multiple patterns' identically-named modules at once.
"""

from __future__ import annotations

from shared.llm_client import MockClient
from shared.loader import load_pattern_module
from shared.tools import Tool, ToolRegistry
from shared.types import LLMResponse, Message, ToolCall, Usage

pe = load_pattern_module("09-plan-and-execute")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5)


def _echo_tool() -> Tool:
    return Tool(
        name="echo",
        description="Echo a value back.",
        input_schema={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        handler=lambda value: f"echoed:{value}",
    )


def _registry() -> ToolRegistry:
    return ToolRegistry([_echo_tool()])


# ---------------------------------------------------------------------------
# Test 1: Full run — plan parsed, steps executed, synthesis returned
# ---------------------------------------------------------------------------


def test_full_run_trace_structure() -> None:
    """Plan is parsed, each step executes, synthesis is returned; trace has
    'plan', one 'reasoning' per step, and a final 'answer'."""

    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1

        last_content = messages[-1].content if messages else ""

        # Phase 3: synthesis call
        if "Provide a concise final answer" in last_content:
            return LLMResponse(
                text="Tokyo has approximately 14 million people.",
                stop_reason="end_turn",
                usage=_usage(),
            )

        # Phase 1: planning call (first call)
        if call_count == 1:
            return LLMResponse(
                text="1. Research the topic\n2. Analyze findings\n3. Write summary",
                stop_reason="end_turn",
                usage=_usage(),
            )

        # Phase 2: execution calls
        return LLMResponse(
            text=f"Completed step (call {call_count})",
            stop_reason="end_turn",
            usage=_usage(),
        )

    result = pe.run_plan_and_execute(
        "Summarize Tokyo's population",
        _registry(),
        MockClient(planner),
    )

    assert result.answer == "Tokyo has approximately 14 million people."
    assert len(result.plan) == 3
    assert len(result.step_results) == 3

    kinds = [s.kind for s in result.trace.steps]
    assert "plan" in kinds
    assert kinds.count("reasoning") == 3  # one per step
    assert kinds[-1] == "answer"
    assert result.trace.succeeded


# ---------------------------------------------------------------------------
# Test 2: Tool use during execution phase
# ---------------------------------------------------------------------------


def test_tool_use_in_execution_phase() -> None:
    """When a step triggers a tool call the trace includes 'tool_call' and
    'observation' entries for that step."""

    tool_called = False

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal tool_called

        last_content = messages[-1].content if messages else ""

        # Synthesis
        if "Provide a concise final answer" in last_content:
            return LLMResponse(
                text="Final answer after tool use.",
                stop_reason="end_turn",
                usage=_usage(),
            )

        # Planning — single step plan so we have one execution call
        if not any(m.role == "tool" for m in messages) and "Create a step-by-step plan" in last_content:
            return LLMResponse(
                text="1. Look up the value",
                stop_reason="end_turn",
                usage=_usage(),
            )

        # Execution — if tool result already in history, return text answer
        if any(m.role == "tool" for m in messages):
            return LLMResponse(
                text="Got the echoed result.",
                stop_reason="end_turn",
                usage=_usage(),
            )

        # Execution — first call for the step, trigger a tool call
        tool_called = True
        return LLMResponse(
            text="I will echo a value.",
            tool_calls=[ToolCall(id="e1", name="echo", arguments={"value": "hello"})],
            stop_reason="tool_use",
            usage=_usage(),
        )

    result = pe.run_plan_and_execute(
        "Echo hello",
        _registry(),
        MockClient(planner),
    )

    assert tool_called
    kinds = [s.kind for s in result.trace.steps]
    assert "tool_call" in kinds
    assert "observation" in kinds
    assert result.answer == "Final answer after tool use."


# ---------------------------------------------------------------------------
# Test 3: Plan parsing — numbered list parsed correctly
# ---------------------------------------------------------------------------


def test_plan_parsing() -> None:
    """Numbered lines are parsed into PlanStep objects with correct indices
    and descriptions."""

    raw_plan = "1. Research the topic\n2. Analyze findings\n3. Write summary"
    parsed = pe._parse_plan(raw_plan)

    assert len(parsed) == 3
    assert parsed[0].index == 1
    assert parsed[0].description == "Research the topic"
    assert parsed[1].index == 2
    assert parsed[1].description == "Analyze findings"
    assert parsed[2].index == 3
    assert parsed[2].description == "Write summary"


def test_plan_parsing_fallback() -> None:
    """When no numbered lines are found, the whole text becomes a single step."""

    raw_plan = "Just do something useful."
    parsed = pe._parse_plan(raw_plan)

    assert len(parsed) == 1
    assert parsed[0].index == 1
    assert parsed[0].description == "Just do something useful."


# ---------------------------------------------------------------------------
# Test 4: Empty registry (no tools) still works
# ---------------------------------------------------------------------------


def test_empty_registry_works() -> None:
    """Pattern completes successfully with an empty ToolRegistry — execution
    just uses text responses from the model."""

    call_count = 0

    def planner(messages: list[Message], _tools: object) -> LLMResponse:
        nonlocal call_count
        call_count += 1

        last_content = messages[-1].content if messages else ""

        if "Provide a concise final answer" in last_content:
            return LLMResponse(
                text="Done with no tools needed.",
                stop_reason="end_turn",
                usage=_usage(),
            )

        if call_count == 1:
            return LLMResponse(
                text="1. Think about it\n2. Write the answer",
                stop_reason="end_turn",
                usage=_usage(),
            )

        return LLMResponse(
            text=f"Step done ({call_count})",
            stop_reason="end_turn",
            usage=_usage(),
        )

    empty_registry = ToolRegistry()
    result = pe.run_plan_and_execute(
        "Write a haiku",
        empty_registry,
        MockClient(planner),
    )

    assert result.answer == "Done with no tools needed."
    assert len(result.plan) == 2
    assert len(result.step_results) == 2
    # No tool_call or observation steps
    kinds = [s.kind for s in result.trace.steps]
    assert "tool_call" not in kinds
    assert "observation" not in kinds
    assert result.trace.succeeded
