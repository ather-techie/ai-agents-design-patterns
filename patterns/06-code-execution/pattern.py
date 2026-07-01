"""Code Execution: the LLM writes Python code; a sandbox runs it; the output feeds back in.

The model generates Python code to solve a task, a caller-supplied executor
runs it (subprocess, restricted eval, etc.), and the output is returned to the
model for interpretation. If the code raises an exception the error is fed back
and the model can retry — up to ``max_attempts`` times — before
:class:`~shared.errors.MaxStepsExceeded` is raised.

The function depends only on the :class:`~shared.llm_client.LLMClient` protocol,
so it runs unchanged against the live Anthropic client or the offline mock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from shared.errors import MaxStepsExceeded
from shared.llm_client import LLMClient
from shared.trace import Trace
from shared.types import Message

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_CODE_PROMPT = (
    "Write Python code to solve this task. "
    "Output ONLY the code, no explanation, no markdown.\n\n"
    "Task: {task}"
)

_RETRY_PROMPT = (
    "The previous code produced an error: {error}\n\n"
    "Write corrected Python code. Output ONLY the code, no explanation, no markdown.\n\n"
    "Task: {task}"
)

_INTERPRET_PROMPT = (
    "The code produced this output: {output}\n\n"
    "Answer the original task concisely based on this output.\n\n"
    "Task: {task}"
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CodeExecutionResult:
    """The outcome of a code-execution run."""

    code: str      # the final code that succeeded (or last attempt)
    output: str    # the execution output
    answer: str    # the LLM's interpretation of the output
    attempts: int
    trace: Trace


# ---------------------------------------------------------------------------
# Code-fence extraction helper
# ---------------------------------------------------------------------------

def _extract_code(text: str) -> str:
    """Strip markdown code fences if present, returning bare source."""
    for fence in ("```python", "```"):
        if fence in text:
            start = text.index(fence) + len(fence)
            end = text.index("```", start)
            return text[start:end].strip()
    return text.strip()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_code_execution(
    task: str,
    executor: Callable[[str], str],
    client: LLMClient,
    *,
    max_attempts: int = 3,
    trace: Trace | None = None,
) -> CodeExecutionResult:
    """Generate, execute, and interpret Python code to solve *task*.

    Parameters
    ----------
    task:
        Natural-language description of what the code should compute.
    executor:
        Caller-supplied sandbox.  It receives a code string and must return
        the stdout/result as a string, or raise an exception on failure.
    client:
        Any :class:`~shared.llm_client.LLMClient` (live or mock).
    max_attempts:
        Maximum number of code-generation/execution cycles before giving up.
    trace:
        Optional pre-existing :class:`~shared.trace.Trace`; a fresh one is
        created when not supplied.

    Returns
    -------
    :class:`CodeExecutionResult`

    Raises
    ------
    :class:`~shared.errors.MaxStepsExceeded`
        When every attempt fails.
    """
    trace = trace or Trace(title=f"Code Execution · {task[:60]}")

    messages: list[Message] = []
    last_code = ""
    last_output = ""

    for attempt in range(1, max_attempts + 1):
        # ------------------------------------------------------------------
        # Step 1: ask the model to (re-)generate code
        # ------------------------------------------------------------------
        if attempt == 1:
            prompt = _CODE_PROMPT.format(task=task)
        else:
            # Include the error from the previous attempt.
            error_text = last_output  # set below on failure
            prompt = _RETRY_PROMPT.format(error=error_text, task=task)

        messages.append(Message(role="user", content=prompt))

        start = time.perf_counter()
        response = client.complete(messages)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        trace.record_usage(response.usage)
        code = _extract_code(response.text)
        last_code = code

        trace.add(
            "reasoning",
            f"generated code ({len(code)} chars)",
            detail=code[:120],
            duration_ms=elapsed_ms,
        )

        # Append the assistant turn so subsequent user messages are coherent.
        messages.append(Message(role="assistant", content=response.text))

        # ------------------------------------------------------------------
        # Step 2: execute
        # ------------------------------------------------------------------
        start = time.perf_counter()
        try:
            output = executor(code)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            last_output = output

            trace.add(
                "observation",
                f"output: {output[:80]}",
                duration_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            err_str = str(exc)
            last_output = err_str  # used as error context on retry

            trace.add(
                "observation",
                f"error: {err_str}",
                is_error=True,
            )
            # Continue to next attempt (the retry prompt will include the error).
            continue

        # ------------------------------------------------------------------
        # Step 3: interpret the output
        # ------------------------------------------------------------------
        interpret_prompt = _INTERPRET_PROMPT.format(output=output, task=task)
        messages.append(Message(role="user", content=interpret_prompt))

        start = time.perf_counter()
        interpret_response = client.complete(messages)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        trace.record_usage(interpret_response.usage)
        answer = interpret_response.text.strip()

        trace.add("answer", answer, duration_ms=elapsed_ms)

        return CodeExecutionResult(
            code=last_code,
            output=last_output,
            answer=answer,
            attempts=attempt,
            trace=trace,
        )

    # All attempts exhausted.
    raise MaxStepsExceeded(max_attempts)
