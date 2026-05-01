# Plan Review: Execution Layer vs Design Layer

**Date:** 2026-05-02
**Context:** `docs/superpowers/plans/2026-05-02-markr-implementation.md` — initial plan + 4 review rounds + Council of Claudes.

## What happened

I wrote a multi-task implementation plan with embedded Python/TOML/Dockerfile snippets. Reviewed it 4 times. All 4 rounds found real things; none caught the 4 execution-layer bugs that would fail at the very acceptance step of the very task that introduced them.

The Council (Opus + Gemini + Codex in parallel) finally caught them — and only Codex did. Two of three council reviewers (Opus + Gemini) still missed all four.

## The 4 bugs that survived 4 rounds

1. **T1.1 hatch `force-include` ordering.** `pyproject.toml` declared a `force-include` for `src/markr/db/schema.sql` that didn't exist yet. `uv sync` would error with `FileNotFoundError: Forced include not found` before any later task could create the file.
2. **T2.8 spike `JSONResponse(404, {...})` positional.** Signature is `JSONResponse(content, status_code=200, ...)`. Int went to `content`, dict to `status_code` — ASGI server crashes on `http.response.start`.
3. **T6.2 module-scope `app = create_app()`.** `Settings()` requires `DATABASE_URL`; the lifespan test imported `markr.main` *before* setting the env var. Test failed during pytest collection.
4. **T8.2 `debug_select(...) -> list[dict]`.** Bare `dict` violates mypy strict's `disallow_any_generics`. T8.2's own acceptance step ran `mypy` and would exit non-zero.

All 4 are surgical 1–3 line fixes. None touch the design. All 4 fail the *very acceptance step* the plan declares. They are textbook BLOCKING — yet 4 prior reviews and 2 of 3 council reviewers said the plan looked fine.

## Why the prior reviewers missed them

**Every reviewer (and every prompt I gave them) read the plan as a *specification*, not as *code that has to run*.**

The two layers of a code-bearing plan:

| Layer | Question | Lens |
|---|---|---|
| **Design** | Does this match the spec? Is coverage complete? Is the architecture sound? | Architect / Tech Lead |
| **Execution** | Would `uv sync` actually build cleanly? Would this `import` statement resolve at the moment the test runs? Does this kwarg match the library signature? Does mypy strict accept this annotation? | Python interpreter / build tool / type checker |

Reviewers fluent in design lens may be blind to execution lens — and vice versa. They are different cognitive modes.

### Round-by-round breakdown

| Round | Reviewer | Lens | What they caught | What they missed |
|---|---|---|---|---|
| 1 (initial subagent) | Opus general-purpose | Design | Spec coverage gaps, `details` payload shape | All 4 execution bugs |
| 2 (general-purpose) | Opus general-purpose | Design | Behavioral drift in §5.3 ordering, deps install path | All 4 execution bugs |
| 3 (user manual review) | Tianyi | Design + protocol | The §5.3 CT-before-body-cap order, deps drift, matrix IDs, ruff `\|\| true` | All 4 execution bugs |
| 4 (post-fix sanity check) | Opus general-purpose | Design | Cosmetic items (extra files, `pool_pre_ping`) | All 4 execution bugs |
| 5a (Council Opus) | Opus | Design | Confidently READY | All 4 execution bugs |
| 5b (Council Gemini) | Gemini-3.1-pro-preview | Design + framework patterns | TDD atomicity violation | All 4 execution bugs |
| 5c (Council Codex) | Codex CLI | **Execution** | All 4 execution bugs | (caught everything that mattered) |

The council saved us only because **one of three reviewers had a different lens**. Without that diversity, the plan would have entered execution and failed at task 1.

### Why Codex specifically

Codex's persona is closer to a code-execution tool than a design reviewer. Its training/UX makes it ask "what does the actual tool do with this exact byte sequence?" rather than "does this match the architectural intent?". For plan reviews containing code, this is exactly the missing lens.

## Concrete takeaways

### Takeaway 1: A code-bearing plan is two artifacts

Treat it explicitly as such. Always run two passes:
- Pass A: design conformance (spec coverage, behavioral correctness, architecture)
- Pass B: execution correctness (would each line run, given the configured tooling?)

Different prompts. Different acceptance criteria. Don't mix them.

### Takeaway 2: Add execution-layer questions to plan-review briefings

Whenever I draft a plan-review briefing, it must include explicit questions like:

- "Trace every `import` in every test block — does each symbol exist in a strictly earlier task at the moment the test would import it?"
- "For every library call (FastAPI, SQLAlchemy, Pydantic, hatchling, uv), check positional vs keyword args against the actual library signature."
- "For every config (mypy strict, ruff strict), would the code in the plan satisfy that config? Run the mental type-checker."
- "For every file referenced by a build tool (hatch `force-include`, `package-data`, importlib resources), does the file exist when the build tool reads the config?"
- "For every module-scope side effect (e.g. `app = create_app()`), what fires at import time, and is anything in the test that imports it set up first?"

### Takeaway 3: Don't trust a unanimous "READY" from a single reviewer family

Opus said READY in rounds 1, 4, and council 5a. Three independent invocations, same blind spot. **Same model, same lens — independence is illusory.**

The council's value isn't "three reviewers" — it's "three different lenses". A council of three Opuses would have agreed on READY just as confidently. The Codex slot is the variance.

If running a plan review without a council, **explicitly run an execution-lens pass yourself**: open a temp project, paste the `pyproject.toml`, run `uv sync`, eyeball every library kwarg call, mentally run mypy.

### Takeaway 4: Severity calibration in council protocol

The council protocol's BLOCKING/ADVISORY binary is too coarse. "Acceptance step fails" is BLOCKING. So is "production data corruption". Same label, very different blast radius. The council report read dramatically because it didn't distinguish.

Future briefings: ask reviewers to add a "blast radius" line to each finding (e.g. "fails T1.1 acceptance, no production impact, 1-line fix" vs "production data loss"). Helps prioritize fixes.

### Takeaway 5: Reproduce, don't just inspect

Tianyi's confirmation step ("I reproduced #1 with a temp project: `uv sync` fails with `FileNotFoundError: Forced include not found`") is what closed the loop. Without that, it's still just a claim from one reviewer.

For plan reviews, **the highest-leverage validation is**: take the first task's `pyproject.toml`, drop it in a temp dir, and run the literal commands. 30 seconds; catches every execution-layer bug that could possibly fire at task 1.

This is exactly what the plan's own "spike-before-integrate" rule was supposed to enforce — but the rule applied to runtime APIs, not to the plan's own bootstrap code. The plan didn't have a spike for *itself*.

## Action items going forward

1. **Add an "execution-lens self-review" section to `PROMPTS/generate-impl-plan-extra.md`** — explicit list of "would this run?" checks the plan author should answer before declaring done.
2. **In `/council` invocations for plan reviews, explicitly include the Codex slot** (or equivalent execution-lens reviewer). Never run with only design-lens models.
3. **Before any plan review's "READY" verdict**, run the first task's bootstrap commands in a temp project. If `uv sync` / `npm install` / `cargo build` fails, the verdict is auto-NOT_READY regardless of what reviewers say.
4. **Treat "single reviewer caught a BLOCKER everyone else missed" as a strong signal** — the lens that caught it is the lens the others lacked. Don't downgrade just because it's a minority view.

## File references

- Plan: `docs/superpowers/plans/2026-05-02-markr-implementation.md`
- Council session artefacts: `/tmp/council-ElzPiK/` (ephemeral)
- Council report: `/tmp/council-ElzPiK/COUNCIL_REPORT.md`
- Prior lesson: `lesson-learnt/spec-bugs-only-council-found.md` (sister file — same pattern, different round)
