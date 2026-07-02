# Code Execution — Interview Questions & Answers

## Conceptual

**1. What does the code-execution pattern add on top of a plain LLM call, and why can't the LLM just simulate execution internally?**

The pattern adds an actual runtime — Python interpreter, shell, etc. — that runs the model's generated code and returns real results. LLMs cannot reliably simulate execution: they hallucinate output for complex arithmetic, file I/O, or library calls because they are predicting plausible tokens, not computing actual values.

**2. Walk through the three phases: generation, execution, and interpretation.**

Generation: the LLM receives the task and writes code. Execution: the code is extracted and run in a sandbox; stdout, stderr, and exit code are captured. Interpretation: the LLM receives the original task plus the execution output and translates raw results into a human-readable answer. These three roles are separated so each call can be focused.

**3. Why is the execution error fed back to the LLM for the next attempt rather than surfacing it directly to the user?**

The LLM often knows how to fix the error — a `NameError` means an import is missing, an `IndexError` means an off-by-one — so re-prompting with the error message triggers a targeted self-correction without requiring human intervention. Surfacing raw tracebacks to users is confusing and unhelpful.

## Trade-offs

**4. What are the security implications of executing LLM-generated code, and what sandboxing strategies would you use?**

LLM-generated code can exfiltrate data, modify the filesystem, or make network calls. Mitigations include running in a container or VM with no network access and a read-only filesystem (except a scratch directory), enforcing a CPU/memory/time limit, and using a restricted execution environment (e.g., RestrictedPython, Pyodide, gVisor) that blocks dangerous syscalls.

**5. How does this pattern compare to ReAct for tasks involving computation?**

ReAct is better when the task requires multiple heterogeneous tool calls with reasoning between them (search, then compute, then summarize). Code execution is better when the task is fundamentally computational — the model can express the entire solution in one self-contained program, making a single generate-run-interpret cycle more efficient than a multi-turn ReAct loop.

## Implementation & Failure Modes

**6. What kinds of errors should trigger a retry versus an immediate abort?**

Retry-worthy: `SyntaxError`, `NameError`, `ImportError`, `IndexError` — the model likely knows how to fix these. Abort immediately: detected dangerous operations (e.g., `os.system`, `subprocess`, file path outside sandbox), infinite loop (timeout exceeded), or memory limit exceeded — retrying would either reproduce the same risk or hit the same resource limit.

**7. After hitting the max retry limit, what should the final interpretation step do if no attempt succeeded?**

Return a best-effort interpretation that honestly reports the failure — what the code was trying to do, what error kept occurring, and any partial result from the last attempt. It should not fabricate an answer. Log the task for offline review so the generation prompt can be improved.

## Extension

**8. How would you extend this pattern to support multi-cell notebook-style execution?**

Maintain a session object (e.g., a persistent IPython kernel) across cells instead of spawning a fresh interpreter per attempt. Each cell's generated code executes in the same namespace, so variables, imports, and data loaded in cell 1 are available in cell 2. The trace records each cell's code, output, and any errors independently, enabling cell-level retry without re-running earlier cells.
