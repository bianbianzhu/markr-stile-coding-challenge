# Adversarial QA Fix Postmortem

**Date:** 2026-05-03
**Context:** Follow-up to `lesson-learnt/2026-05-03-adversarial-qa-report.md`.

## What happened

Black-box adversarial QA found two client-triggered `500 internal_error` paths:

1. `summary-marks/@available="2147483648"` passed Python validation, then failed asyncpg/Postgres `INT` binding.
2. `GET /results/x%00/aggregate` passed route validation, then failed when Postgres rejected NUL in a TEXT parameter.

Both were fixed by moving validation to the application boundary:

- `marks_available` / `marks_obtained` must fit Postgres `INT` (`<= 2_147_483_647`).
- aggregate `test_id` cannot contain NUL.

## Why these were real bugs

The brief's recovery workflow depends on bad input returning a clear 4xx. A 500 says "server broke"; a 4xx says "this document/path is invalid". These inputs were client-caused and deterministic, so they belong in the validation layer.

The database rollback behavior was already correct. No partial write occurred. The defect was error classification, not atomicity.

## Why we missed them

Existing tests covered spec-shaped invalid data:

- missing fields
- bad XML
- decimal / negative / impossible scores
- whitespace and length path validation

They did not cover **representation boundary mismatches**:

- Python `int` is arbitrary precision; Postgres `INT` is int32.
- URL percent-decoding can produce characters that normal XML input cannot produce.
- Postgres TEXT has a stricter byte constraint than Python `str` for NUL.

The implementation trusted the database as defense-in-depth, but the API contract required validation before the database. That gap is where both 500s came from.

## What worked

The adversarial report was useful because it tested the running service, not just unit-level assumptions. It also checked atomicity after failure, which prevented over-scoping the fix.

The TDD loop was clean:

1. Add tests proving both 500 paths.
2. Watch them fail against current code.
3. Add narrow validation.
4. Run target tests and full suite.

This kept the patch small and avoided changing adjacent product semantics.

## What not to change yet

Do not bundle lower-severity observations into this fix.

- Duplicate score paradox is current product semantics.
- Permissive `int()` parsing is a strictness choice, not this bug.
- `/docs` exposure is production hardening.
- Optional name length caps are policy.
- `/import/` trailing slash is not a practical body-cap bypass.

Bundling any of these would turn a crisp 500 fix into product behavior drift.

## Future checklist

Add adversarial tests around every boundary where app types differ from backing systems:

- Python numeric type vs DB column range
- Python string vs DB encoding constraints
- URL-decoded path values vs values reachable through ingestion
- framework validation vs repository parameter binding

Rule of thumb: if a value is accepted by Python but rejected by the database driver, the API probably returns the wrong status unless the app validates it first.

## Verification

After the fix:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src/markr`
- `uv run pytest`

All passed; full suite: `92 passed`.
