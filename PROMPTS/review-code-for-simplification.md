Review code for simplifications. READ-ONLY all stages. No edits until I
say "go fix".

## Stage 1: /simplify

Run /simplify. 3 review agents will run in parallel. Stop after findings aggregated, skip Phase 3 (fixes).
Output: dedup list, each item = file:line, issue, fix, severity.

## Stage 2: superpowers code review

Invoke superpowers:requesting-code-review, dispatch
superpowers:code-reviewer.
Pass: same files + Stage 1 list verbatim.
Reviewer must read source, mark each finding: - valid+do / valid-skip / invalid - flag behavior or perf risks if done naively
Push back when existing code is intentional (KISS, defense-in-depth,
readability).

## Stage 3: codex:rescue cross-check

Invoke codex:rescue. Pass Stage 1 list + Stage 2 verdicts.
Tasks: - independently verify disputed findings from source - flag where Stage 1+2 both wrong - flag where Stage 2 over-rejected - flag missed behavior/perf risks
No edits.

## Stage 4: synthesis (main agent)

Table per finding: # | finding | S1 sev | S2 verdict | S3 verdict | final
Final = DO / SKIP / NEEDS-CARE.

Then:

### To fix

Items with DO/NEEDS-CARE. Each: file:line, concrete change, caveats from
S2/S3,
acceptance criteria (tests/commands, behavior must stay byte-identical).

### Explicitly not fixing

Items with SKIP. One-line reason each. Prevents re-raising later.

## Rules

- READ-ONLY. No edits, commits, worktrees.
- Stages independent. S2/S3 don't see each other until S4.
- 3 stages flag = high confidence. 1 stage = low. Weight accordingly.
- Disagreement: reviewer cites source, not defender.
- Final output: tables + bullets, no prose.
- English.
