# Contributing

Thanks for considering a contribution. This project follows a [Code of Conduct](CODE_OF_CONDUCT.md).

## Adding a new pattern

1. Duplicate `patterns/07-react/` into `patterns/21-new-name/`.
2. Rewrite `pattern.py` — implement one `run_*` function that accepts an `LLMClient` and a `Trace`, records steps, and returns a result dataclass.
3. Update `example.py` with new tools and a matching `mock_planner`.
4. Update `test_pattern.py` — load via `load_pattern_module("21-new-name")` and assert on the result and trace.
5. Write `diagram.md` — a Mermaid `flowchart LR` of the control flow and one paragraph on tradeoffs.
6. Write `interview.md` — 8 Q&A pairs across Conceptual, Trade-offs, Implementation & Failure Modes, and Extension.
7. Add a row to the pattern table in `README.md`, and optionally a row in `bench/compare.py` and a link in `INTERVIEW_PREP.md`.

The shared client, tool registry, tracing, config, and test style carry over unchanged — adding a pattern is typically a ~50-line diff to `pattern.py`.

## Fixing a bug or improving `shared/`

- Keep changes provider-agnostic — code in `shared/` and `patterns/` should not assume live vs. mock mode.
- Run `make test` before opening a PR.
- If you change `shared/llm_client.py`, `shared/tools.py`, `shared/trace.py`, or `shared/config.py`, check that every pattern's `test_pattern.py` still passes (`python -m pytest`), since all 20 patterns depend on the same shared core.

## Opening a PR

- Use the PR template checklist.
- Keep the diff scoped to one pattern or one shared change per PR where possible.
