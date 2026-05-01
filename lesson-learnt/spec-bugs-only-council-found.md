# Why three BLOCKING spec bugs survived brainstorming + Opus audit

**Date**: 2026-05-02
**Context**: Markr take-home spec. Brainstormed for hours with the user. Wrote spec, ran one Opus code-reviewer audit, declared it "ship with fixes." Then ran the multi-model council. Council surfaced 3 BLOCKING bugs that earlier passes missed, all real, all cheap to fix once seen.

This document is a post-mortem on **the review process**, not on the bugs themselves. The bugs are recorded in the spec history; the question here is *why didn't earlier eyes catch them?*

---

## The three bugs in one line each

1. **PG `CREATE TABLE IF NOT EXISTS` race** — claimed safe under multi-worker startup. It is not. Authoritative PG mailing-list reference disproves the claim outright.
2. **Error code unrecoverable from HTTP status** — §9.4 said "infer error code by status." §9.2 mapped 6 codes to status 422 and 2 codes to status 413. Mathematical impossibility, written on the same page.
3. **Health endpoint violates the spec's own envelope contract** — §9.1 said "all non-2xx return `{error, message, details}`." §10.1 raised `HTTPException(detail={"status": "degraded"})` — a dict, not a `message` string. Plus 503 and 500 had no rows in §9.2.

Two of the three are **internal contradictions inside the same document**. One is an **unverified claim about external system behaviour**.

---

## What was missed, by stage

### Stage 1 — Brainstorming

**Process**: Long conversational exploration with the user. Decisions captured turn by turn. Skill-driven.

**What it caught well**: scope decomposition, brief-fidelity, deferred-vs-decided items, trade-off framing.

**What it missed**: anything that requires **stepping back and reading the whole thing as a static document**. Brainstorming is a forward-walking process — each turn adds one decision. Nothing forces a "now read all decisions together and check they're mutually satisfiable" pass.

The error-carrier bug was *born* during brainstorming: §9.1 (envelope) and §9.2 (codes) and §9.4 (handler) were each agreed in different turns, separated by hundreds of lines of conversation. The contradiction only exists when the three are read together.

### Stage 2 — Spec writing

**Process**: Wrote the full spec in one pass, top to bottom, using the brainstormed decisions.

**What it caught well**: section structure, completeness against the agreed item list, README structure.

**What it missed**: cross-section invariants. I wrote §9.1 ("all non-2xx use envelope"), then §9.2 (codes table), then §9.4 (handler design), then later §10.1 (health endpoint). Each section was internally fine. The cumulative contracts were not.

I never did a deliberate "now check that every MUST/ALWAYS claim in section X is honoured by every implementation snippet in sections Y/Z." The pattern that would have surfaced the bugs was: **read the spec backward**, asking *"what claim does this section depend on, and does that claim hold?"*

### Stage 3 — Self-review (brainstorming skill step 7)

**Process**: Quick inline pass: placeholder scan / consistency / scope / ambiguity.

**What it caught**: the empty-batch pipeline gap (a real bug, fixed before audit).

**What it missed**: the three council-found bugs. The self-review checklist was structurally fine but I executed it as a *quick* pass — the equivalent of proofreading your own essay right after writing it. Familiarity blindness applies; you re-read what you intended, not what you wrote.

### Stage 4 — Opus code-reviewer audit (single subagent)

**Process**: Spawned one fresh-context Opus agent with the spec + brief + journal. Asked it to find Tier 1 (ship-blocking), Tier 2 (should fix), Tier 3 (polish).

**What it caught**: the 64-char cap as invented constraint, the body-cap mechanism not being pinned, several wording polish items. Real value.

**What it missed**: **all three of the council's BLOCKING findings**. It did flag the error-carrier issue and the health-envelope shape — but as **Tier 2 ambiguity**, not as **Tier 1 impossibility**. It treated *"this is unclear, please clarify"* and *"this cannot be implemented as written"* as the same severity tier.

Same-architecture bias: the agent and I share priors about what's "fine." Issues that look acceptable to me look acceptable to it.

### Stage 5 — Council (Opus + Gemini + Codex)

**Process**: Three different model lineages, parallel reviews, then synthesis, then surgical debate on contested findings.

**What it caught**: the three BLOCKINGs, with concrete evidence (PG mailing list, table-vs-handler contradiction count, dict-vs-string envelope mismatch).

**Why it caught what others missed**:

- **Codex lineage** (different architectural priors than Claude family) caught the impossibilities that Claude variants treated as ambiguities.
- **Gemini** independently flagged the same PG race condition Codex did — convergence on a single finding is much stronger evidence than one model's hunch.
- **Three reviewers writing reviews in isolation** means each is forced to commit to a verdict. Single-reviewer audits collapse "uncertain" into "advisory" by default. Three independent verdicts make the disagreement visible and force adjudication.

---

## Pattern catalogue: what kept slipping through

### Pattern 1 — Plausible-sounding system claims accepted unverified

> *"`CREATE TABLE IF NOT EXISTS` is idempotent; concurrent worker startup is safe (Postgres serialises via `AccessExclusiveLock`)."*

This sentence sounds correct. It uses the right vocabulary. It cites the right PG mechanism. It is **wrong**: PG checks existence *before* taking the AccessExclusiveLock, leaving a race window.

I wrote this confidently because it sounded like something a senior engineer would write. Neither I nor the Opus auditor checked the PG documentation. The council's Codex linked to a PG mailing-list post from Tom Lane that disproves it directly.

**Lesson**: when writing "X is safe because library Y does Z", **either cite a source for Z or mark the claim as `TODO: verify`**. Plausibility is not correctness. The cost of looking up one PG behaviour is 60 seconds; the cost of being wrong about it in a spec is real.

### Pattern 2 — Cross-section contracts written piecewise, never reconciled

The `{error, message, details}` envelope was a "nice-to-have" I added in §9.1 because it's good API hygiene. Then in §9.2 I listed all the codes. Then in §9.4 I wrote a handler that "infers code from status." Then in §10.1 I wrote `detail={"status": "degraded"}` as a quick health example.

Each was internally fine. Together they are mutually unsatisfiable. The §9.4 handler cannot honour the §9.2 table given the status-to-code multiplicity. The §10.1 example cannot honour the §9.1 envelope.

**Lesson**: every time the spec says **"all"**, **"every"**, **"MUST"**, that's a universal contract. After writing such a contract, do a deliberate sweep: enumerate every code path that could break it. If the sweep finds a path you forgot, either fix the path or relax the contract — don't leave both standing.

### Pattern 3 — "Best practice" contracts introduced without enforcement

The uniform envelope (§9.1) wasn't required by the brief. I added it because it felt professional. Then the rest of the spec didn't actually enforce it — FastAPI's auto-405, Starlette's path-422, and my own `/health` example all violated it.

This is a specific case of pattern 2 but worth naming. Adding a "best practice" contract creates an invariant. If you don't enumerate every place that invariant could leak, you've added a self-sabotaging clause.

**Lesson**: don't add contracts the brief doesn't require unless you're willing to enforce them everywhere. "Less spec, faithfully kept" beats "more spec, partially honoured."

### Pattern 4 — Single-perspective audit collapses severity tiers

The Opus auditor saw the §9.4-vs-§9.2 contradiction (it literally said "infer code from status, but multiple codes share status"). It tagged it Tier 2.

The council's Codex saw the same thing and called it BLOCKING with this reasoning: *"two implementations can emit different `error` values for the same failure, or collapse all 422s/413s to one code. This breaks the API contract."*

Same observation, different severity. The Opus auditor was structurally biased toward "let me note this for the engineer to consider." The council's Codex was structurally biased toward "if the spec is ambiguous about X, two engineers will produce two implementations and one will fail hidden tests."

The latter framing is the correct one for **spec-before-implementation**. The former is correct for **post-implementation code review**.

**Lesson**: when reviewing a spec, ask **"can this be implemented unambiguously by two strangers without coordination?"** — not "is this clear enough to start coding?" The bar for the former is higher.

### Pattern 5 — Same-model audit shares the original's blind spots

The Opus auditor and the spec author (me) are the same model lineage with the same priors. We share opinions about what's "obvious." If I think "infer from status" is fine because the codes "obviously" map back, the auditor is likely to think the same.

The council fixed this by including Codex (OpenAI lineage) and Gemini (Google lineage). Different priors, different blind spots, low overlap.

**Lesson**: for high-stakes specs, **multi-model review is not a luxury, it's a debug technique**. One model's audit is one perspective. Three models' independent audits triangulate. The cost is ~5 minutes of orchestration; the value is bugs that no single model would catch alone.

---

## Process changes for next time

Concrete, in priority order:

1. **Add an "implementability sweep" between spec writing and audit.** For every `MUST` / `ALWAYS` / `all X` claim, enumerate every section that implements it and verify each one matches. Treat "this section depends on a claim made elsewhere — is the claim still true?" as an explicit checklist item.

2. **Mark every external-behaviour claim with a citation or `TODO: verify`.** Specifically: any sentence of the form "X is safe because library Y does Z" must either link a source or carry a verify marker. The few seconds it takes to add the marker forces the writer to acknowledge the claim is unverified.

3. **For specs that will drive implementation, default to multi-model review.** A single-subagent audit catches structural and brief-fidelity issues; a council catches impossibility-as-ambiguity issues. The two are complementary, not redundant.

4. **Frame the audit prompt around implementability, not clarity.** "Can two engineers implement this from this document and produce the same behaviour?" surfaces different bugs than "is this document clear?".

5. **Don't add contracts the brief doesn't require unless willing to enforce them everywhere.** Each `MUST` in the spec is a debt the implementation must repay. Self-imposed `MUST`s without complete enforcement are how spec contradictions are born.

6. **For each "good practice" idea added during writing, ask "does this leak through any other section I've already written?"** — and check, don't assume.

---

## What worked, worth keeping

- **Brainstorming process** as a decision-gathering tool: excellent. The three bugs are not failures of brainstorming. They're failures of the review steps that come after.
- **Journal as decision-history** alongside spec: invaluable for the audit and council agents. Without it, they'd have flagged many decisions as "unjustified" instead of being able to trace back to "this was decided in Round 7.5 because of X."
- **Spec-as-standalone document** (separate from journal): right call. Each artefact has one job.
- **Council skill** itself: did exactly what it was designed to do, including catching what the single-pass audit missed. Worth running for any spec that will drive multi-day implementation.
- **Spec-review-standards rubric (MVP mode)**: gave the reviewers consistent guardrails. The G-numbered findings were easy to consolidate.

---

## TL;DR

Three BLOCKING bugs slipped through brainstorming, self-review, and a single-Opus audit. All three were obvious in hindsight: one was a wrong-about-PG factual error, two were spec-self-contradictions visible on a slow second read.

Single-pass review with same-architecture bias treats impossibilities as ambiguities. Multi-model council with different priors does not.

For specs that will drive real implementation, **the council is not optional**. Add an implementability sweep before spawning it; cite or mark every external-system claim; and don't introduce universal contracts you can't enforce everywhere.
