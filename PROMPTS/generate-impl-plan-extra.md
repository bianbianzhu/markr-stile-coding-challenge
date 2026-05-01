# Prompt: Generate Implementation Plan

## Inputs

Read and ground the plan in these sources:

- **Authoritative spec** — `specs/2026-05-02-markr-design.md` (primary source of truth)
- **Original brief** — `README.md` (core requirements as stated by the customer)
- **Sample data** — `sample_results.xml` (concrete shape of real-world input)
- **Decision history** — `THOUGHT_PROCESS_WITH_CLAUDE.md` (rationale; may contain noise / superseded ideas — when it conflicts with the spec, the spec wins)

## Goal

Produce a sequenced implementation plan that an engineer (or AI agent) can execute end-to-end without further clarification.

## Hard requirements

1. **Full coverage** — every requirement and acceptance criterion in the spec maps to at least one task in the plan. Cross-reference each task to the spec section(s) it satisfies.
2. **Acceptance criteria per task** — every task must declare concrete, verifiable acceptance criteria (commands that pass, outputs that match, files that exist, tests that go green). No "looks good" / "works correctly" hand-waving.
3. **Topological ordering** — no task may depend on the output of a later task. If task B reads a file that task A produces, A comes first.
4. **Self-contained tasks** — each task must contain enough detail (file paths, function signatures, expected behavior, exact commands) that the executor never has to guess. If a decision is needed, name the decision and the answer.
5. **No scope creep** — do not introduce requirements, features, libraries, or architectural decisions that are not present in the spec. If you find a gap, flag it as an open question rather than silently filling it.

## Backpressure design (critical — DO NOT SKIP)

You will sometimes feel a backpressure step is "obviously unnecessary." You are usually wrong about this. The steps below **cannot be skipped on your own initiative.**

### Spike Check Protocol (mandatory before integrating any new API)

**Every spike is a committed file under `spikes/`. Never `/tmp/`, never `python -c` one-liners — replays must be possible later, and disposable scratch is a bad habit.**

For every external library / API the implementation will touch (FastAPI middleware shape, defusedxml return type, SQLAlchemy async engine API, asyncpg quirks, pydantic v2 serialization order, testcontainers lifecycle, etc.), the plan must include explicit spike tasks **before** the task that integrates that API:

- **Signature check** — `spikes/sig_<feature>.py`. Print `inspect.signature(...)` and any quick `dir()` / `__doc__` output you needed. Tiny, but committed.
- **Runtime-behavior check** — `spikes/spike_<feature>.py`. Smallest script that calls the function with minimal real args. Confirms: imports resolve, signature matches, return type matches, no deprecation warnings.
- **Complex spike** — add a sibling `spikes/<feature>.md` describing **what is being verified, how, and the conclusion**, so a future reader can replay.

Run spikes via `uv run python spikes/<file>.py`. **The spike is the single source of truth.** If docs (including this spec) and the spike disagree, trust the spike.

> Why: the spec contains worked examples and code snippets for several dependencies. Some are paraphrased, some are based on training-data knowledge that may be stale. Do not trust them. Do not trust your own recall either. Run the spike — code that executes is unambiguous.

The plan MUST list a spike step as a prerequisite for any task that uses an API non-trivially. Trivial usage (e.g. `dict.get`, stdlib `re`) does not need a spike.

### End-to-end test gating (mandatory)

Use real `curl` for true E2E tests. Claude (and any executing agent) can run bash + curl directly; Docker Desktop is running; the database lifecycle is yours to manage.

- The plan MUST identify the **earliest minimum E2E-testable slice** (e.g. "POST /import accepts a one-record fixture and returns 200") and schedule a `curl`-driven E2E task immediately at that point — not deferred to the end.
- Subsequent E2E tasks must fire as each new endpoint or contract becomes minimally exercisable.
- E2E tests are non-skippable. "Unit tests pass" is not a substitute. Do not invent reasons to defer.
