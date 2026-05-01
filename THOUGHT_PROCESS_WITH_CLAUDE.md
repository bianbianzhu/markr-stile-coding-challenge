# Thought Process — Markr Take-Home

> This is **not** a design spec. The design spec lives elsewhere.
>
> This file is a journal of how I went from "I have a vague feeling about this problem" to "I actually understand what the brief is asking for." It's intentionally messy — it preserves wrong turns, gut reactions, and the moments where I had to walk back something I confidently said five minutes earlier.
>
> I worked through this with Claude as a thinking partner. Setup honesty: my Round 0 design was deliberately over-engineered — I knew it, the plan was to lean on the model to cut it down. Rounds 1–3 the model was **Haiku** (left over from a previous task, didn't notice). Instead of cutting, it agreed and padded. After Round 3 the behaviour felt off — checked settings, found Haiku, switched to **Opus 4.7, reasoning effort high** from Round 4 onward. Pushback quality changed immediately, and Round 4's "re-read the brief slowly" prompt is what surfaced the constraints buried in the prose. Early rounds left as-is; the contrast is part of the story.
>
> Brief quoted verbatim throughout so a reviewer can sanity-check every interpretation. Round labels matter — a few "obvious" conclusions only became obvious after arguing through three other ideas first.
>
> If you're a reviewer looking for the final architecture, skip to the end. If you want to see why it ended up that way, read in order.

---

## Table of contents

1. [Round 0 — Setting up the subtraction exercise](#round-0)
2. [Round 1 — First pass at the brief](#round-1)
3. [Round 2 — Is this an AI feature?](#round-2)
4. [Round 3 — Is the model actually thinking?](#round-3)
5. [Round 4 — Re-reading the brief, slowly this time](#round-4)
6. [Round 5 — What's the best practice for parsing XML?](#round-5)
7. [Round 5.5 — Requirements clarification: what _is_ one POST?](#round-5-5)
8. [Round 5.6 — With those numbers, does Round 0 still hold up?](#round-5-6)
9. [Round 6 — Pub-sub is dead. But is decoupling?](#round-6)
10. [Round 7 — L1 vs L2: not pure deployment, but close](#round-7)
11. [Round 7.5 — Pinning data contracts: required fields & aggregate shape](#round-7-5)
12. [Round 7.6 — HTTP error code policy](#round-7-6)
13. [Round 8 — "What if the server crashes mid-batch?"](#round-8)
14. [Final position](#final-position)
15. [Round-4 deferrals closed in 7.5](#deferred)
16. [Assumptions, inclusions, exclusions, trade-offs, future work](#assumptions)

---

<a id="round-0"></a>
## Round 0 — Setting up the subtraction exercise

**TL;DR — Round 0 is a deliberately inflated straw man. The strategy is _front-load context, then subtract together_, and the cuts (with justifications) are the deliverable.**

Skim-read shape: HTTP ingest, "real-time dashboard" hint, persistent storage, instances might die. Reflex muscle-memory design:

```
[Scanner] → [Ingestion API, stateless] → [Redis Streams]
                                              │
                                              ▼
                                    [Processing Service]
                                       ├─ writes to Postgres
                                       ├─ updates Redis hot cache
                                       └─ pushes SSE to dashboard
```

Obvious over-engineering for a 2-3 hour take-home. I knew that before reading carefully — staging it anyway is the point.

**Why stage it.** Recent Claude models are lazy: they do the smallest work that lets them declare success. Against crisp specs that's a virtue. Against an under-specified brief — exactly what a from-scratch project is on day one — it lands at PoC when stakeholders wanted SLC (simple, lovable, complete). Constraints buried in prose ("the _entire_ document," "other kinds of XML," "extra fields … shouldn't concern you") only become load-bearing once teased out. Hand the model too little and it'll happily skip them.

**Counter-strategy.** Pile it on, then cull together with brief and sample in hand, justifying every cut. Subtraction needs something to bite into. The cuts and their justifications are the actual output of this document; the "big idea then walked back" framing is just scaffolding. The journey is performed, not lived.

---

<a id="round-1"></a>
## Round 1 — First pass at the brief

_Model: **Haiku** (unnoticed)._

Skim-read summary:

1. `POST /import` — accepts XML, persists results
2. `GET /results/:test-id/aggregate` — mean, count, p25/p50/p75 as percentages
3. Dedup: same student + test → keep highest score
4. Reject malformed documents wholesale

Plus meta: docker-compose, tests, README, Git.

**Correct but shallow** — misses the constraints buried in prose. I didn't realise yet.

---

<a id="round-2"></a>
## Round 2 — Is this an AI feature?

_Model: **Haiku**._

> "Do we need to build any AI features into this?"

No. Zero mention of ML, prediction, or anomaly detection in the brief — it's ingestion + aggregation. Worth asking out loud so scope doesn't drift.

---

<a id="round-3"></a>
## Round 3 — Is the model actually thinking?

_Model: **Haiku**. I pitched the Round 0 design hoping for "you don't need any of this." Got "yes and here's how to build it." No pushback._

**TL;DR — leading prompt, sycophantic trajectory. Smelled it here, checked settings, found Haiku from a previous task, switched to Opus before Round 4. Rule locked in: don't trust a model answer that arrives after you've signalled your conclusion.**

Leading prompt:

> "This is probably over-engineering — what do you think?"

Trajectory: agreed immediately → hedged ("but for an interview this shows production thinking") → spent the bulk _expanding_ the design, sketching layer responsibilities → looped back to a simplified recommendation as a dutiful afterthought.

The simplified recommendation matched where I ended up — content was right. The **shape** was telling: praise first, expand second, walk-back third. Counterfactual: flip the prompt to "this looks clean to me, anything missing?" and the same model would have praised the same design and recommended _additions_. Needle was tracking my framing, not the brief.

Round 3 as design reasoning, weight near zero. The rounds I trust later are the ones with open questions ("how does the database actually get written to?", "what happens if the server crashes mid-batch?") and quoted brief text.

Fact-checks kept (held up later under Opus):

- **Postgres**: `PERCENTILE_CONT` for percentiles, `INSERT ... ON CONFLICT` for dedup UPSERT, ACID for the all-or-nothing requirement, durability for "instances might die." SQLite needs a mounted volume; Supabase is heavy.
- Redis Streams IDs are `<ms-timestamp>-<sequence>`, monotonic. Filed under "interesting, won't use."

---

<a id="round-4"></a>
## Round 4 — Re-reading the brief, slowly this time

_Model: **Opus 4.7, high reasoning** — switched after the Round 3 smell test. The findings below are why the switch was worth it; Haiku wouldn't have surfaced them from the same prompt._

**TL;DR — most valuable round. Things buried in the prose that the first-pass summary missed.**

Prompt:

> "The brief contains deliberate ambiguity. Distinguish firm requirements, soft hints about future direction, and details you can safely ignore."

### 4.1 — "Trust summary-marks" is scope reduction, not an edge case

> "your boss told you to go with what's in there … you can safely ignore the `<answer>` elements."

Not "summary-marks might be wrong, handle that." It's "don't even look at answers." Sample confirms: 100 records, sum of per-question marks always equals `summary-marks/@obtained`. Take the gift.

### 4.2 — "Extra fields" → lenient parser

> "extra fields … shouldn't concern you - probably some gunk the reporting team needs"

No XSD, no strict schema. Validation checks required fields are _present_, not that nothing else is.

### 4.3 — "Other kinds of XML" → real rejection condition

> "other kinds of XML documents … try not to get your wires crossed"

Multiple formats exist. Check root element is `<mcq-test-results>`, reject otherwise.

### 4.4 — "Reject the entire document" → transaction boundary

> "If you've already accepted part of the document, that'll cause some confusion"

Not just "return 400" — every record commits or none do. Rules out fire-and-forget queues that ack before processing.

### 4.5 — Sample data findings

- 100 records, all `test-id=9863`
- 19 duplicate `(student, test)` pairs; `obtained` differs (e.g. 11 vs 13), `available` never differs
- `summary-marks/@obtained` always equals sum of answer marks
- All well-formed — no malformed examples

Sample is "happy path + duplicates"; malformed cases must be imagined. Brief still says `MAX(available)` across duplicates — implement defensively even though sample doesn't exercise it.

### 4.6 — Element order is not fixed

Brief example places `<summary-marks>` near the top; sample places it at the bottom. Use DOM `.find()`, not an order-dependent streaming parser.

### 4.7 — "Important fields" deliberately undefined

> "the machines … post you a document missing some important bits."

Brief never names them. Tentative: `student-number`, `test-id`, `summary-marks/@available`, `summary-marks/@obtained` required; names and `scanned-on` optional. Pin down in design spec.

### 4.8 — Response shape: prose vs example mismatch

Bullet list says 5 fields (`mean, count, p25, p50, p75`); example shows 8 (adds `stddev, min, max`):

```json
{
  "mean": 65.0,
  "stddev": 0.0,
  "min": 65.0,
  "max": 65.0,
  "p25": 65.0,
  "p50": 65.0,
  "p75": 65.0,
  "count": 1
}
```

Contradiction. Defer to design spec.

### 4.9 — Duplicates cross requests

> "duplicate documents may come in a single request or in multiple requests."

Dedup can't live only in request-processing logic — must be enforced at the persistence layer. UPSERT with `GREATEST` is the natural fit.

### 4.10 — Percentage math

`obtained / available * 100`. Example confirms (13/20 = 65).

### 4.11 — "Aggregate fetching doesn't need to be fast" → explicit permission to not optimise

> "the aggregate fetching doesn't need to be fast"

No aggregate cache, no materialised view, no precomputed snapshot table — query Postgres directly per request and ship it. Justifies several later cuts.

### 4.12 — Real-time dashboards are an explicit "write things down" ask, not a passing hint

> "it's probably worth having a think about that & writing a few things down even if the prototype implementation you build is a bit slow."

Not "future feature, ignore." The brief literally asks for written design thinking on it. README must show how the design evolves into real-time dashboards, even though we don't build them.

### 4.13 — `student-number` formatting is heterogeneous in the sample

First record: `<student-number>002299</student-number>`. Second: `2300`. Both unquoted decimals; the first has leading zeros. Storing as integer silently strips them — breaks dedup if `002300` and `2300` are meant to be different students, and loses the original value either way. **Store as TEXT, not BIGINT.**

---

After Round 4, the simple "POST and GET" task had structure and constraints I hadn't seen on first read.

---

<a id="round-5"></a>
## Round 5 — What's the best practice for parsing XML?

_Model: **Opus 4.7, high reasoning** from here on. Pushback quality changed immediately._

**TL;DR — final answer is a three-piece package: DOM + `defusedxml` + explicit input caps. First pass landed on DOM + `defusedxml` (hardening > throughput). Hooks-triggered Codex review caught the missing third piece — without an input bound, `defusedxml` still leaves DOM as an OOM surface.**

> "What's a good pattern or best practice for parsing XML in this project?"

### The three options

| Pattern                                                                              | What it does                                                                                              | When it's right                                    |
| ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| **DOM** (`ElementTree.fromstring`, `lxml.etree.fromstring`)                          | Whole tree in memory; `.find()` / XPath.                                                                  | Small/medium docs (<~10 MB). Order-independent.    |
| **iterparse / pull parsing — i.e. _streaming_** (`ET.iterparse` + `element.clear()`) | Walk elements incrementally, free memory as you go. This is what "streaming XML parsing" means in Python. | Large docs (100s of MB+) or unknown-size streams.  |
| **SAX**                                                                              | Pure event stream, callback-driven.                                                                       | Almost never now — `iterparse` strictly dominates. |

Streaming is best practice for _big_ XML, not XML in general.

### First pass: DOM + hardening

Our docs are sub-megabyte (one exam?). DOM wins on simplicity and order-independence (Round 4.6).

Real concern is **hardening, not throughput**. XML parsing has a long security footgun surface: entity expansion, DTD/external-entity behaviour depending on parser, and hostile payloads. `defusedxml` is a drop-in guardrail — one-line import swap. Brief waves off security but `/import` accepts arbitrary XML; using it is free.

Meta: "best practice" prompts pull instincts toward throughput; for an open ingest endpoint, hardening comes first.

So: **DOM + `defusedxml`.**

### Codex adversarial review (hooks-triggered)

A Claude Code hook auto-fired a Codex adversarial review. `[high]` finding:

> "Round 5 says streaming offers no benefit because all-or-nothing rejection forces every record to be held in memory before UPSERT. That inference is not defensible: all-or-nothing can be implemented with streaming validation into a bounded dedup map or transactional staging table, committing only after the full document validates. The current recommendation makes DOM parsing safe only if a concrete body/record cap is enforced before parsing; otherwise an open XML endpoint can still be driven into high memory use despite `defusedxml` hardening."

Two corrections:

1. **All-or-nothing is a _commit_ boundary, not a _parsing_ boundary.** Stream into a staging table, commit at the end — works fine. The "DOM is forced by all-or-nothing" leg doesn't hold.
2. `defusedxml` blocks entity expansion, not large-but-legal bodies. A 500MB valid XML still pins the process. DOM is safe *only* on bounded input — `defusedxml` does not provide that bound.

So "DOM is fine" is actually **DOM + bounded input**. The body-size bound must come from the HTTP layer, before the parser sees the body.

### Decision

Three-piece package — remove any one, the argument breaks:

- **Parser**: `defusedxml.ElementTree.fromstring(body)`
- **Access**: DOM, `.find()` / `.findall()`, no order assumptions
- **Caps**: reject an oversize body at the HTTP layer with `413` _before_ parsing; reject too many records after safe parse, before validation/DB work. Numbers and enforcement layer left open here.
- **Fallback**: if real bodies hit tens of MB, switch to `lxml.etree.iterparse` + `element.clear()` (still hardened — `resolve_entities=False`, no DTD load)

### Open question

Cap values + exact enforcement split left open here.

---

<a id="round-5-5"></a>
## Round 5.5 — Requirements clarification: what _is_ one POST?

**TL;DR — Round 5 said "some cap must exist" without numbers. The number depends on what one POST physically is. Brief + sample give a strong-enough answer: one POST = one fully-scanned stack. Cap is a defensive backstop (~10× realistic max), not a workflow bound.**

Four human-asked clarification questions before settling cap values:

1. Could input actually get big?
2. Could a scanner emit 100k records in one giant XML?
3. **Per-paper POST or per-batch POST?** _(load-bearing — the answer changes the architecture, not just the numbers)_
4. How many concurrent scanners?

### Evidence

- Brief: _"formats **an** XML document containing **a set of** results"_; _"at the end of a test"_; _"reject the **entire** document … work-experience kid enters the whole thing manually."_
- Sample: 100 records in one file; `scanned-on` spans **99 min** at exactly 1 record/min; **167 KB / ~1.7 KB per record**.

### Answers

| Q       | Answer                                                                                       | Why                                                                                                                                                                                                                                   |
| ------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q3      | One POST per fully-scanned stack                                                             | Three independent signals: singular "**an** XML document / **a set of** results"; sample bundles 100 records in one file across 99 min (per-paper would be 100 files); the manual re-entry loop only makes sense at batch granularity |
| Q1 / Q2 | Realistic per-POST: tens–hundreds of records, hundreds of KB. 100k is fiction                | At 1 paper/min, 100k = 70 days continuous; modern 60 ppm scanners still need ~28 hr                                                                                                                                                   |
| Q4      | Inferred, not brief-stated. Per-scanner ≈ 0.01 QPS; aggregate ≈ 1–2 QPS even at 10k scanners | Each scanner emits ~one POST per 100 min                                                                                                                                                                                              |

Wire-level assumption: the scanner sends a completed XML file as the request body, not an hour-long HTTP chunked-transfer stream. That keeps the DOM + body-cap decision coherent.

### Cap numbers

Defensive backstop:

- Body size: **10 MB**, enforced before `defusedxml` sees the body
- Record count: **10,000**, enforced after safe parse and before validation/DB work
- Either exceeded → **413 Payload Too Large**

These are independent backstops; whichever trips first wins. For sample-shaped XML with full `<answer>` elements, the 10 MB body cap is tighter than 10,000 records.

Documented assumptions, easy to retune if real traffic disagrees.

---

<a id="round-5-6"></a>
## Round 5.6 — With those numbers, does Round 0 still hold up?

**TL;DR — Round 0 was an admitted strawman, but it deserves a proper post-mortem now that 5.5 has nailed down the workload. Two independent arguments kill pub-sub: contract mismatch (can't reject after ack) and zero benefit (no producer pressure to absorb). Not over-engineering — _wrong design_.**

### [1] Contract mismatch — pub-sub can't honour "reject the entire document"

The reject contract (Round 4.4): the HTTP caller must learn whether the **entire** batch was accepted _before_ the response is sent — 4.4 explicitly _"rules out fire-and-forget queue designs where you ack the HTTP request before processing."_ Pub-sub's contract: producer ack happens when the message hits the queue, before any consumer touches it. **Incompatible by construction.**

Three ways you might try to bridge them — each fails:

| Partition                         | Why it fails                                                                                                                                                                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Whole batch as one event          | Producer ack races consumer write. Either ack-then-reject (violates contract) or block waiting for consumer (degenerates to sync RPC — pub-sub adds nothing)                                                              |
| One event per `<mcq-test-result>` | Reject granularity becomes per-record — directly violates "the **entire** document". Recovering batch boundaries needs `batch_id` + `total_count` + consumer-side reassembly = reinventing a transaction                  |
| Validate fully, then pub          | All parsing/validation already done synchronously in the producer. Consumer only does the DB write. Splitting that across a queue is one extra hop, one extra failure mode, zero architectural gain |

### [2] Zero benefit — solving a problem we don't have

Pub-sub's classical value is **buffering producer load when consumers are slower**. 5.5's numbers say there's nothing to buffer:

- Per-scanner: ~0.01 QPS (one POST per ~100 min)
- Aggregate even at 10k scanners: ~1–2 QPS
- Per-POST budget: parse + validate + multi-VALUES UPSERT, well under 1s

Producer is not under pressure. A queue between producer and DB just inserts latency and an extra failure surface.

### Conclusion

**Two independent arguments, either one sufficient.** [1] is _categorical_ — pub-sub fundamentally cannot satisfy the reject contract, regardless of payload size or queue choice. [2] is _empirical_ — even if it could, there'd be nothing to gain. Together: not "over-engineered but defensible", but **wrong tool for the contract**.

Round 0's pub-sub diagram is officially struck. The next round picks up the surviving question: with Level 3 dead, do we still need decoupling at all?

---

<a id="round-6"></a>
## Round 6 — Pub-sub is dead. But is decoupling?

**TL;DR — Two-step round.**

**(1) User stopped me mid-response: before asking "what level of decoupling?", first verify the upstream question — is the ingestion / aggregation split itself necessary, or is that an inherited Round-0 assumption? Derive it from earlier findings: yes, two layers are _forced_ by the brief's read/write asymmetry, not chosen.**

**(2) Given two layers must exist, Level 1 becomes a floor, not a trade-off. Stateless ingestion falls out for free. Level 1 vs Level 2 deferred to interview-context judgement.**

> "Pub-sub is dead. Do we still need decoupling?"

Was about to launch into Level 1/2/3. User cut in:

> "Hold on — let's double-check first. Splitting ingestion and aggregation into two layers: is that even necessary? I think it is, less mental burden, clearner architecture and data ingestion should be stateless (scale up)"

Fair. Round 0 drew them as separate boxes; Round 0 was an admitted strawman (5.6). Time to derive instead of assume.

### Step 1 — Are there really two layers?

**Ingestion side (write path)** — three things forced into one synchronous execution path inside the POST handler:

- Parse XML (Round 5 — DOM + `defusedxml` + cap)
- Validate the whole batch synchronously, before the HTTP response (Round 4.4: _"rules out fire-and-forget queue designs where you ack the HTTP request before processing"_ — once you ack, you can no longer reject)
- Persist atomically (Round 4.4: _"never partially commit a batch"_; 5.6 already showed they cannot be split across a queue)

So **ingestion = parse + validate + UPSERT, as a unit, inside the request handler**. Not a design choice — a derivation. There is nowhere else for them to live.

**Aggregation side (read path)** — what GET `/results/:test-id/aggregate` does:

- Read persisted state
- Compute mean / stddev / percentiles (Round 4.10, 4.8)
- Return JSON

Brief: _"the aggregate fetching doesn't need to be fast"_ (Round 4.11) — explicit permission to query Postgres on demand, no precomputation, no cache.

**Different on every dimension that matters:**

| Dimension      | Ingestion (write)             | Aggregation (read)           |
| -------------- | ----------------------------- | ---------------------------- |
| Trigger        | POST from scanner             | GET from visualisation team  |
| Latency budget | Tight (synchronous reject)    | Loose (4.11, brief explicit) |
| Failure mode   | Malformed XML, missing fields | Test-id not found, empty set |
| Consistency    | Transactional, all-or-nothing | Snapshot read                |
| Test fixtures  | Sample / malformed XML        | Pre-populated rows in DB     |

Two layers exist not because we _chose_ them — they are forced by the brief's read/write asymmetry. Round 0's instinct was right; pub-sub was the wrong vehicle for it.

### Step 2 — Given two layers, what level of decoupling?

Now the original question is well-posed. "Decoupling" hides three options:

| Level       | What                                                                              | What it solves                        |
| ----------- | --------------------------------------------------------------------------------- | ------------------------------------- |
| 1 — Logical | One process, ingestion + aggregation as separate modules over a shared Repository | Code maintainability + testability    |
| 2 — Process | Two services, separate containers, shared Postgres                                | Independent deploy + horizontal scale |
| 3 — Event   | Queue between producer and consumer                                               | (Ruled out in 5.6)                    |

Same `[component] → arrow → [component]` shape as Round 0, so the contrast is direct:

**Level 1 — one process, two modules:**

```
[Scanner]   → [POST /import]          ┐
                                      │
[Viz team]  → [GET /:id/aggregate]    ┤
                                      ▼
                       [FastAPI process (1 replica)]
                          ├─ Ingestion module (parse + validate + upsert)
                          ├─ Aggregation module (read + percentile math)
                          └─ Repository → [Postgres]
```

**Level 2 — two services, shared DB:**

```
[Scanner]   → [POST /import]    → [Ingestion service (N replicas)]    ┐
                                                                       │
[Viz team]  → [GET /:id]        → [Aggregation service (M replicas)]  ┤
                                                                       ▼
                                                                  [Postgres]
                                                                   (shared)
```

Difference is one line of topology: in Level 1 the two modules share a process; in Level 2 they don't. Repository abstraction keeps the core data-access surface reusable, but the exact service-split cost is still unresolved here.

**Level 1 is the floor, not a choice.** Step 1 established the two responsibility shapes are different on every dimension. Wedging both behind one fat handler trades ~30 LOC of boundary plumbing for a multiplier on every future change. There's no trade-off to evaluate — Level 1 is just default Python project hygiene once two distinct concerns exist.

### Stateless ingestion — falls out for free

Brief: _"be ready for your instances to turn off at any time"_

Strict reading: a single instance that gracefully restarts and re-reads its state from Postgres satisfies the literal requirement — the phrase doesn't _literally_ demand multi-replica scaling.

Important distinction: "instances might die" forces per-request statelessness; it does **not** by itself require horizontal scaling across replicas. Multi-replica scaling rests on the inferred multi-scanner assumption from Round 5.5 Q4.

But the cheapest way to satisfy "instance might die at any time" is **statelessness**:

- No in-process queue or buffer surviving the request
- No on-disk state on the container
- All durability lives in Postgres, full stop

Crucially, statelessness isn't a separate engineering decision — it's a **consequence** of the Step-1 request lifecycle (validate → tx → respond, no shared mutable state across requests). Free.

**Bonus**: stateless ingestion is also the precondition for Level 2 (multi-replica behind a load balancer). We earn the option without exercising it now.

### Level 1 vs Level 2 — deferred

Level 1 satisfies the brief literally, including the "instances might die" line via statelessness. Level 2 buys operational independence + the ability to scale ingestion and aggregation read-load separately. Whether that's worth the extra docker-compose / connection-pool / config overhead in a 2–3h take-home is a _judgement call_ grounded in interview context, not in the brief itself.

Decision left open at this point.

---

<a id="round-7"></a>
## Round 7 — L1 vs L2: not pure deployment, but close

**TL;DR — Spawned adversarial Opus subagent to break "L1 vs L2 = purely deployment diff." Verdict MOSTLY RIGHT, six concrete code deltas at first; Codex review then forced 7.3's "two engines in one L1 process" insight, which retroactively collapsed two of those deltas (pool tuning and DB-role split aren't L2-only after all). Net L2-only: 4 hard + 1 partial + independent deploy lifecycle. Concurrency questions (multi-scanner, read-during-write): visibility identical L1/L2 (Postgres MVCC), resource isolation differs unless you do the two-engine trick. Decision: L1 with two engines.**

### 7.1 — Is "L1 vs L2 = pure deployment" really true?

Adversarial Opus subagent, prompt: try to break it, concrete code paths only, no platitudes.

Conceded up front: router code byte-identical via `Depends(Repository)`. Schema, models, `PERCENTILE_CONT` query — all reused as-is.

Six deltas it found (initial list — two later collapsed, see note below):

| Delta                                  | What changes                                                                                                                                                                                                       |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| App factory + lifespan                 | L1: 1 `create_app()`, 1 `lifespan`. L2: 2 factories (or one parameterised), 2 lifespans                                                                                                                            |
| ~~Pool tuning~~ (collapsed)            | ~~Shared pool can't tune ingest and aggregate separately~~ → see note below                                                                                                                                        |
| Migration ownership                    | L2 first-boot race. Both run `alembic upgrade head` → advisory lock saves alembic, doesn't save `create_all`. Single owner → other service can boot against empty DB                                               |
| Config + DB roles (partial)            | L2 forces config split across two `.env` / two services. DB role split (`markr_ingest` vs `markr_reader`) **also achievable in L1** with two engines + two URLs — only the _config-file-split_ half is L2-specific |
| Test harness                           | L1: one `AsyncClient(app=app)`. L2: two apps or compose-driven; "POST then GET" becomes real cross-process                                                                                                         |
| Version skew (L2-only failure mode)    | New ingest writes column old aggregate doesn't `SELECT`. L1 impossible by construction                                                                                                                             |
| Independent deploy lifecycle (L2-only) | L1 restart of either module = whole process restart = both endpoints down briefly. L2 can rolling-restart one side without touching the other                                                                      |

**Post-Codex correction**: the original list had "Pool tuning" as a real L2 delta, but 7.3's resource-isolation caveat resolved that by introducing **two `AsyncEngine` objects in one L1 process** (7.4 item 7). Once you accept that pattern, pool tuning is no longer L2-only — both L1 (with two engines) and L2 (with per-service engines) can tune ingest and aggregate pools separately. So pool tuning _moves out_ of the L2-delta list. Same logic shrinks "Config + DB roles" — DB role split is achievable in L1; only the literal two-`.env` split survives. **Net result: 4 hard L2-only deltas + 1 partial + "independent deploy lifecycle" added** (which the subagent missed and is arguably the strongest L2 case).

Verdict, verbatim:

> "MOSTLY RIGHT. The router code is genuinely shared. But 'purely deployment-time' overstates it: app factory, lifespan, pool config, migration ownership, settings split, and test harness are all real code diffs. For a 2-3h take-home, ship Level 1 and call out these as the Level-2 delta — don't claim the delta is zero."

Subagent also flagged misleading-but-true bits in the original claim: read-after-write consistency identical L1/L2 (same MVCC); hot-reload one module is theatre at this scope; rolling-deploy mid-batch drops in-flight requests in both, unless graceful drain coded — also code, not free.

### 7.2 — Concurrent scanners: FastAPI or Postgres handles it?

Postgres handles DB contention. FastAPI handles request concurrency until CPU-bound parsing or DB locks become the boundary.

- 1 uvicorn worker = 1 event loop. `async def` handlers cooperatively yield at `await` (DB I/O). Two POSTs interleave during await — not threads.
- True parallelism: `--workers N` multi-process. Round 5.5 numbers (1–2 QPS aggregate even at 10k scanners) → **2 workers** is a reasonable default. 1 would technically clear the QPS, but XML parse is CPU-sync (no `await` until DB I/O) — a 100-record batch can block the loop ~100 ms; second worker keeps a concurrent GET responsive. 4+ is hard to justify for this prototype.
- **Actual same-key boundary: Postgres row lock.** Two POSTs hitting same `(test_id, student_number)` → row-level lock serialises UPSERT, `GREATEST` resolves. Different keys can proceed independently at the row-lock level.
- L2 does not improve same-key contention (still serialised by row lock). For independent-key traffic L2 could in principle parallelise parse/validate/request-handling across replicas — but Round 5.5's 1–2 QPS aggregate even at 10k scanners leaves L1 (uvicorn `--workers 2`) huge headroom. Operational isolation, not throughput, would be the real reason to split.

Mental-model fix: "FastAPI does threads smartly" is wrong framing. FastAPI multiplexes async handlers onto an event loop; Postgres handles actual contention. Sync `def` handlers go to a thread pool, but our handlers are `async def`.

### 7.3 — Read during write: what does the viz team see?

MVCC + READ COMMITTED. **Visibility** identical L1/L2; **resource isolation** is not (see caveat below).

| POST phase                       | GET sees                                          |
| -------------------------------- | ------------------------------------------------- |
| Parsing / validating, no tx open | Pre-POST state                                    |
| Inside tx, before COMMIT         | Pre-POST state (READ COMMITTED skips uncommitted) |
| After COMMIT                     | Post-POST state, immediately                      |

Round 6 already killed any in-memory-not-yet-DB state — validate→tx→respond is one synchronous unit inside the handler. Nothing in flight is queryable. Same in L1 and L2 because both lean on the same Postgres MVCC, not on intra-process synchronisation.

Error handling on `/aggregate/:test-id`:

- Zero rows → **404 Not Found**. Don't return `{count: 0, ...}` empty shell — that lies about an aggregate that doesn't exist.
- ≥1 row → 200 + computed stats.

Same code, same behaviour, both levels.

**Resource-isolation caveat.** Vanilla L1 (one shared `AsyncEngine`) lets bursty bulk import saturate connections/CPU → concurrent GET queues _before_ it ever reaches MVCC. L2 with per-service pools (Round 7.1 delta #2) isolates aggregate read latency from ingest pressure. **L1 vs L2 is defined by process count, not engine count** — so we can mitigate inside L1 by building **two `AsyncEngine` objects in one process**: write engine for ingest, read engine for aggregate, separate `pool_size` budgets, same `DATABASE_URL`. Same deploy shape, just two `create_async_engine(...)` calls. Buys most of L2's isolation at near-zero cost.

### 7.4 — Decision + DB hard constraints

Decision: **L1 with two engines in one process**. README will list 7.1's post-correction L2-only deltas (4 hard + 1 partial config + independent deploy lifecycle) as "what shipping L2 would actually change" — awareness documented, cost not paid. (Solution README not yet written; the file currently in the repo is Markr's brief.)

DB hard constraints, ordered by "skip this and you corrupt data":

1. **Types**: `student_number TEXT` (Round 4.13: `002299` ≠ `2299`), `test_id TEXT`, `marks_* INT` with `CHECK (marks_obtained >= 0 AND marks_available > 0 AND marks_obtained <= marks_available)`, `scanned_on TIMESTAMPTZ NULL`. `available > 0` because aggregate divides by it.
2. **PK = `(test_id, student_number)`** — dedup uniqueness + leftmost-prefix covers `WHERE test_id = $1` for aggregate. No extra index needed.
3. **UPSERT atomic, never SELECT-then-UPDATE** (concurrent-request safety):

```sql
 INSERT INTO test_results (...)
 VALUES (...), (...), ...
 ON CONFLICT (test_id, student_number) DO UPDATE SET
   marks_obtained  = GREATEST(test_results.marks_obtained,  EXCLUDED.marks_obtained),
   marks_available = GREATEST(test_results.marks_available, EXCLUDED.marks_available);
```

4. **Intra-request dedup in app code, not SQL.** Postgres `ON CONFLICT DO UPDATE` rejects multiple rows with same conflict key in one INSERT → Python pre-aggregates `(test_id, student_number) → (max(obtained), max(available))` first. Cross-request dedup stays in DB via `GREATEST`.
5. **One tx per request, COMMIT before HTTP 200.** Validate whole batch first, then open tx, then write — don't validate-and-write in a loop, wastes DB work on requests that'll fail anyway.
6. **Multi-VALUES chunked** ~1000 rows / SQL, well under Postgres' 65,535 param ceiling. Per-row async writes do not help here — round-trip count is the bottleneck, not blocking; batching is what reduces it. `COPY` + staging is reserved for future million-row batches (see future work).
7. **Two engines in one process** (still L1 — process count, not engine count, defines L1 vs L2). Same `DATABASE_URL`, separate pools so bursty ingest can't starve aggregate GETs. From 7.3 caveat:

```python
 write_engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20, pool_pre_ping=True)
 read_engine  = create_async_engine(DATABASE_URL, pool_size=5,  max_overflow=10, pool_pre_ping=True)
```

Ingest module uses `write_engine`; aggregate module uses `read_engine`. Two `create_async_engine(...)` calls, zero L2 cost.

8. **Schema bootstrap**: `CREATE TABLE IF NOT EXISTS` in lifespan startup. Alembic deferred — README documents the upgrade path.

### L1 final shape

```
              ┌──────────┐                              ┌──────────┐
              │ Scanner  │                              │ Viz team │
              └─────┬────┘                              └─────┬────┘
                    │ POST /import                            │ GET /results/:id/aggregate
                    │ Content-Type: text/xml+markr            │
                    ▼                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ FastAPI process  ·  uvicorn --workers 2                                 │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Body-size middleware:  body ≤ 10 MB                  → 413        │  │
│  └──────────────────────────┬────────────────────────────────────────┘  │
│                             │                                           │
│  ┌──────────────────────────▼──────────┐  ┌──────────────────────────┐  │
│  │ Ingestion module                    │  │ Aggregation module       │  │
│  │                                     │  │                          │  │
│  │ ① defusedxml parse         → 400    │  │ ① SELECT PERCENTILE_CONT │  │
│  │ ② root = mcq-test-results? → 422    │  │     FROM test_results    │  │
│  │ ③ record count ≤ 10k?      → 413    │  │     WHERE test_id = $1   │  │
│  │ ④ required fields present? → 422    │  │ ② 0 rows   → 404         │  │
│  │ ⑤ obtained ≤ available?    → 422    │  │ ③ → percentages          │  │
│  │ ⑥ Python dedup:                     │  │ ④ → JSON 200             │  │
│  │    max(obt), max(avail) per         │  │                          │  │
│  │    (test_id, student_number)        │  │                          │  │
│  │  ─── BEGIN TX ───                   │  │                          │  │
│  │ ⑦ multi-VALUES UPSERT, ~1000/SQL    │  │                          │  │
│  │    ON CONFLICT (test_id,            │  │                          │  │
│  │      student_number) DO UPDATE      │  │                          │  │
│  │      SET marks_* = GREATEST(...)    │  │                          │  │
│  │  ─── COMMIT ───   → 200             │  │                          │  │
│  └──────────────┬──────────────────────┘  └────────┬─────────────────┘  │
│                 │                                  │                    │
│        ┌────────▼─────────┐               ┌────────▼─────────┐          │
│        │ write_engine     │               │ read_engine      │          │
│        │ pool_size=10     │               │ pool_size=5      │          │
│        │ max_overflow=20  │               │ max_overflow=10  │          │
│        └────────┬─────────┘               └────────┬─────────┘          │
└─────────────────┼──────────────────────────────────┼────────────────────┘
                  │                                  │
                  └────────────────┬─────────────────┘
                                   ▼
                ┌─────────────────────────────────────┐
                │ Postgres                            │
                │                                     │
                │  test_results                       │
                │  ─────────────                      │
                │   test_id         TEXT  ┐ PK        │
                │   student_number  TEXT  ┘           │
                │   marks_obtained   INT              │
                │   marks_available  INT              │
                │   scanned_on       TIMESTAMPTZ NULL │
                │                                     │
                │   CHECK marks_obtained  ≥ 0,        │
                │         marks_available > 0,        │
                │         marks_obtained ≤ available  │
                └─────────────────────────────────────┘

  Concurrency: FastAPI async event loop multiplexes; row lock in
  Postgres serialises same-key UPSERTs (GREATEST resolves). Different
  keys can proceed independently at the row-lock level.

  Read/write isolation: write_engine vs read_engine = same Postgres,
  separate app-side pools → bursty ingest can't consume aggregate's pool.

  Crash safety: COMMIT before HTTP 200; UPSERT is idempotent (re-POSTing
  the same XML is safe — GREATEST converges to the same row).

  Rejection contract: validate-all-then-write. Any failure before COMMIT
  → ROLLBACK + 4xx. Partial commit impossible by construction.
```

---

<a id="round-7-5"></a>
## Round 7.5 — Pinning data contracts: required fields & aggregate shape

**TL;DR — Two open items from Round 4 (4.7 required-fields, 4.8 response shape) deferred to "design spec." Schema work in 7.4 makes them load-bearing now, so close here. _Required fields is genuinely DB-adjacent_ — drives `NOT NULL` + `CHECK` + the pre-UPSERT validator. _Response shape is not_ — same schema, different `SELECT` projection. Decisions: required = the 4 fields the system actually uses (`student-number`, `test-id`, `summary-marks/@available` > 0, `summary-marks/@obtained`); response = the 8 fields from the example, in the example's order, all stats as JSON floats with `count` as int, using `STDDEV_POP` for the n=1 case.**

"4.7 required-fields + 4.8 response shape. let's close here**.** _In case I forget."_

| Question                              | DB coupling | Why                                             |
| ------------------------------------- | ----------- | ----------------------------------------------- |
| What fields make a record valid?      | **Tight**   | `NOT NULL` + `CHECK` + validator gating UPSERT  |
| What fields go in aggregate response? | **Loose**   | `SELECT` projection + JSON; schema is invariant |

All 8 aggregate stats derive from `marks_obtained` and `marks_available`. Returning 5 vs 8 fields doesn't change the table. Pinning both here because 7.4's schema can't finalise without the first one — atomic close of the 4.x debt.

### Required fields

Brief evidence — deliberately undefined (Round 4.7):

> "the machines … post you a document missing some important bits."

Sample evidence: all 6 of `scanned-on` / `first-name` / `last-name` / `student-number` / `test-id` / `summary-marks` present in 100/100 records.

Two competing principles in the brief:

- **Leniency**: _"extra fields … shouldn't concern you"_
- **Rejection cost**: _"work-experience kid types in all 100 by hand"_

What the system actually consumes, end-to-end:

| Field                      | Ingest validation                   | UPSERT     | Aggregate |
| -------------------------- | ----------------------------------- | ---------- | --------- |
| `student-number`           | dedup key                           | PK         | —         |
| `test-id`                  | dedup key                           | PK         | `WHERE`   |
| `summary-marks/@available` | `available > 0`; `obtained ≤ avail` | yes        | denom     |
| `summary-marks/@obtained`  | yes                                 | yes        | num       |
| `first-name`, `last-name`  | —                                   | if present | —         |
| `scanned-on`               | —                                   | if present | —         |

**Decision**: required = the 4 fields the system uses, with `available > 0`. Names + `scanned-on` _tolerated_ (stored if present and parseable, ignored otherwise).

Justification: rejection is expensive — reject only on data the system cannot function without. Names never read by either endpoint; demanding them expands the rejection surface for zero functional gain. Sample-data presence ≠ brief-level requirement.

Why `available > 0` (not `>= 0`): aggregate divides `obtained / available`. A record with `available="0"` would pass a non-negative check, persist, then crash the read query with division-by-zero. Catch at the validator (and mirror in the DB CHECK) so the system can't reach an unservable state.

`scanned-on` malformed-but-present: best-effort parse → `NULL` on failure (no rejection). It's never read by either endpoint; matches the "tolerated" spirit and avoids reject-the-batch pain over a field the system doesn't use.

Schema reflection (updates 7.4 item 1):

```sql
test_id          TEXT NOT NULL,
student_number   TEXT NOT NULL,           -- TEXT, not BIGINT (4.13)
marks_available  INT  NOT NULL CHECK (marks_available > 0),
marks_obtained   INT  NOT NULL CHECK (marks_obtained  >= 0
                                  AND marks_obtained <= marks_available),
first_name       TEXT,
last_name        TEXT,
scanned_on       TIMESTAMPTZ,                       -- best-effort, NULL on parse failure
PRIMARY KEY (test_id, student_number)
```

Python validator runs _before_ the UPSERT — any record failing required-presence, `available > 0`, or `obtained ≤ available` rejects the entire batch (Round 4.4). Storage never sees a half-valid row.

### Aggregate response shape

Brief contradiction (Round 4.8):

- Prose: 5 fields — `mean, count, p25, p50, p75`
- Example: 8 fields, with literal formatting:

```json
{
  "mean": 65.0,
  "stddev": 0.0,
  "min": 65.0,
  "max": 65.0,
  "p25": 65.0,
  "p50": 65.0,
  "p75": 65.0,
  "count": 1
}
```

My heuristic: when prose and a concrete example contradict, hidden test suites tend to follow the example. **Decision: 8 fields.**

Three sub-decisions baked into the example, all easy to miss:

1. **All stats as floats** — `mean: 65.0`, not `65`. Only `count` is `int`.
2. **Field order** — `mean, stddev, min, max, p25, p50, p75, count`. JSON unordered in spec, but string-matching test suites care. Lock order in the Pydantic response model.
3. **`stddev=0.0` when `count=1`** — Postgres `STDDEV_SAMP` returns `NULL` for n=1 (sample stddev undefined); `STDDEV_POP` returns `0.0`. Use `STDDEV_POP` to match the example.

Empty test_id (zero rows): **404** (Round 7.3). Never serve a `count: 0` shell.

Read query:

```sql
SELECT
  AVG(pct)                                          AS mean,
  COALESCE(STDDEV_POP(pct), 0)                      AS stddev,
  MIN(pct)                                          AS min,
  MAX(pct)                                          AS max,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY pct) AS p25,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY pct) AS p50,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY pct) AS p75,
  COUNT(*)                                          AS count
FROM (
  SELECT marks_obtained::float / marks_available * 100 AS pct
  FROM test_results
  WHERE test_id = $1
) t;
```

`COUNT(*) = 0` in handler → 404. Otherwise serialise via Pydantic (field order locked).

### Resolves

- 4.7 (required-fields list) → 4 required, 3 tolerated
- 4.8 (response shape) → 8 fields, example order, stats as JSON floats / `count` as int, `STDDEV_POP` for n=1 (float-rounding deferred until tests demand it)
- 7.4 item 1 (schema) → updated with optional columns + concrete `CHECK`s above

---

<a id="round-7-6"></a>
## Round 7.6 — HTTP error code policy

R7.4 put status codes into the L1 diagram before arguing them. Pin them down here so the implementation spec does not invent its own taxonomy.

Policy:

| Failure                                     | Status | Why                                                                                         |
| ------------------------------------------- | ------ | ------------------------------------------------------------------------------------------- |
| `Content-Type` is not `text/xml+markr`      | 415    | Endpoint only supports Markr XML payloads                                                    |
| Body over 10 MB                             | 413    | Raw request entity is too large; reject before parser sees it                               |
| Malformed XML                               | 400    | Request body is syntactically invalid                                                       |
| XML root is not `<mcq-test-results>`        | 422    | XML is well-formed, but not the document type this endpoint can process                     |
| More than 10,000 `<mcq-test-result>` rows   | 413    | Valid XML, but the submitted request entity exceeds this service's accepted batch size      |
| Required field missing                      | 422    | Correct document type, semantically unprocessable record                                    |
| `available <= 0` or `obtained > available`  | 422    | Correct document type, invalid score semantics                                              |
| Aggregate `test-id` has no persisted rows   | 404    | The requested aggregate does not exist                                                      |

`413` for the record-count cap is a deliberate operational-cap choice, not a claim that the raw byte body was too large. `422` would also be defensible; using `413` keeps both hard input-size backstops in the same family.

---

<a id="round-8"></a>
## Round 8 — "What if the server crashes mid-batch?"

I poked at the next worry:

> "If a chunk of 1,000 records is sitting in memory waiting to be UPSERTed — or a request at the 10,000-record upper bound is being processed — and the server crashes, what happens?"

Claude walked through it carefully and the answer is reassuring once laid out:

| When the crash happens               | Committed state                         | HTTP caller sees          | Integrity preserved?                         |
| ------------------------------------ | --------------------------------------- | ------------------------- | -------------------------------------------- |
| During parse                         | no DB call yet                          | connection drop           | Yes — nothing accepted                       |
| During validate                      | no transaction opened                   | connection drop           | Yes — nothing accepted                       |
| During UPSERT, before commit         | unchanged after rollback                | connection drop           | Yes — no partial commit                      |
| **During COMMIT**                    | **committed or rolled back atomically** | connection drop / timeout | Yes — replay is safe if the caller resubmits |
| **After commit, before sending 200** | **batch committed**                     | connection drop           | Yes — replay is safe if the caller resubmits |
| After 200 sent                       | batch committed                         | 200 OK                    | Yes — normal accepted path                   |

Two correctness guarantees, plus one operational implication:

1. **Atomicity**: one transaction wraps the whole request. Chunking only changes how many SQL statements we send; it does not weaken the commit boundary. If chunk 7/10 fails before we issue `COMMIT` — for example because the connection drops, the query times out, Postgres restarts, or the DB rejects the statement — chunks 1-6 are rolled back with it. Until `COMMIT` finishes, the batch is not accepted.
2. **Ambiguous commit + idempotent write**: HTTP cannot prove the caller received the 200 after commit, and a dropped connection during `COMMIT` leaves the caller unable to tell whether Postgres committed or rolled back. The brief specifies print-and-manual recovery for rejected documents, not automatic scanner retry. If the same document is submitted again after an ambiguous failure, `GREATEST` makes that replay safe: same XML twice converges to the same row.
3. **Operational recovery implication**: if commit succeeds but the 200 is lost, the service cannot force the caller to know that. Server-side correctness comes from idempotent replay if the caller or operator submits the document again through the same `/import` path. If manual recovery writes to some other system, that is outside this service's guarantees.

The in-memory batch worry is real for memory-pressure reasons; Round 5.5's 10 MB / 10,000-record caps are the answer to that. This round is only about crash recovery: transaction boundary + idempotent replay keep the database from landing in a half-accepted state.

The useful little surprise: the brief chose "highest score wins" for business reasons (folded paper, re-scan the sheet), but that same rule gives crash safety for free. If the same XML comes through twice after an ambiguous failure, `GREATEST` converges instead of double-counting.

---

<a id="final-position"></a>
## Final position

Single FastAPI service, Postgres, Docker Compose. Two endpoints. Internally:

```
┌─────────────────────────────────────────┐
│        FastAPI Application             │
│                                         │
│  ┌────────────┐    ┌──────────────┐    │
│  │ POST       │    │ GET          │    │
│  │ /import    │    │ /results/... │    │
│  └─────┬──────┘    └──────┬───────┘    │
│        │                  │            │
│  ┌─────▼─────┐    ┌───────▼───────┐    │
│  │ Ingestion │    │ Aggregation   │    │
│  │  module   │    │   module      │    │
│  │           │    │               │    │
│  │ parse →   │    │ query stats   │    │
│  │ validate →│    │ from DB       │    │
│  │ dedup →   │    │               │    │
│  │ upsert    │    │               │    │
│  └─────┬─────┘    └───────┬───────┘    │
│        │                  │            │
│        └────────┬─────────┘            │
│                 ▼                      │
│        ┌────────────────┐              │
│        │  Repository    │              │
│        │ (DB access)    │              │
│        └────────┬───────┘              │
└─────────────────┼──────────────────────┘
                  ▼
            ┌──────────┐
            │ Postgres │
            └──────────┘
```

The diagram is intentionally compressed. The load-bearing R7.4 details still stand:

- `uvicorn --workers 2`
- body-size middleware rejects bodies over 10 MB before XML parse
- ingestion and aggregation use separate `write_engine` / `read_engine` pools inside the same FastAPI process

Key decisions and where they were settled:

| Decision                          | Choice                                         | Round                     |
| --------------------------------- | ---------------------------------------------- | ------------------------- |
| Service topology                  | Single service, Level 1 (logical decoupling)   | 7.4                       |
| Read/write DB pools               | Two engines in one process                     | 7.3, 7.4                  |
| Language / framework              | Python + FastAPI                               | (default chosen up front) |
| Database                          | Postgres                                       | 3                         |
| XML parsing                       | DOM + `defusedxml`, order-independent          | 4.6, 5                    |
| Validation                        | All-or-nothing, before any DB write            | 4.4, 6, 7.4, 8            |
| Transaction boundary              | One per HTTP request                           | 4.4, 6, 7.4, 8            |
| Dedup within a request            | Application-layer, max() per `(student, test)` | 7.4 item 4                |
| Dedup across requests             | DB UPSERT with `GREATEST(...)`                 | 4.9, 7.4 item 3           |
| Bulk write strategy               | Multi-VALUES UPSERT, chunked (~1000 rows)      | 7.4 item 6                |
| Async                             | FastAPI async I/O, `uvicorn --workers 2`       | 7.2, 7.4                  |
| Crash safety                      | Tx + idempotent UPSERT for ambiguous failure   | 8                         |
| Content type                      | Require `text/xml+markr`; otherwise 415        | 7.6                       |
| Reject malformed XML              | 400, no partial commit                         | 4.4, 7.6, 8               |
| Reject wrong document type        | Check root element; otherwise 422              | 4.3, 7.6                  |
| Lenient parsing of unknown fields | Yes — ignore extras                            | 4.2                       |
| `<answer>` elements               | Ignore entirely; trust `<summary-marks>`       | 4.1                       |
| Body / record-count limits        | 10 MB body + 10k records; 413 if exceeded      | 5, 5.5, 7.6               |
| Aggregate computation             | Postgres `PERCENTILE_CONT`, percentages        | 3, 4.10                   |

---

<a id="deferred"></a>
## Round-4 deferrals closed in 7.5

Both 4.x deferrals **closed in Round 7.5**:

- ~~Aggregate response shape.~~ → 8 fields in the example's order, stats as JSON floats / `count` as int, `STDDEV_POP` for n=1.
- ~~"Important fields" list.~~ → 4 required (`student-number`, `test-id`, `summary-marks/@available`, `summary-marks/@obtained`), names + `scanned-on` tolerated.

---

<a id="assumptions"></a>
## Assumptions, inclusions, exclusions, trade-offs, future work

The brief asks the README to cover: assumptions and why; what's included and what's left out; trade-offs; how I'd extend the solution given more time. That belongs in the README of the actual deliverable, but here's the list as it stands at the end of this thinking exercise — the README will draw from this.

### Assumptions

- **One POST = one complete XML batch.** Scanner sends a request only after the body is fully assembled. (Round 5.5.)
- **Realistic batch sizes are tens to low hundreds of records.** Five-figure batches are not the normal workflow. (Round 5.5.)
- **Multi-scanner concurrency exists.** Inferred from "every school system in Europe & North America," not stated. (Round 5.5.)
- **Required fields are `student-number`, `test-id`, `summary-marks/@available` (>0), `summary-marks/@obtained`.** Other fields (names, `scanned-on`) are tolerated when present, ignored when absent or unparseable. (Closed in Round 7.5.)
- **`summary-marks` is trusted; `<answer>` elements are ignored.** Per the brief.
- **Unknown XML elements are ignored without error.** Per the brief.
- **Documents whose root element is not `<mcq-test-results>` are rejected.** Per the brief's "other kinds of XML."
- **`available > 0` and `obtained ≤ available` enforced as validation rules, not just trusted.** `available > 0` prevents division-by-zero in aggregate; `obtained ≤ available` is defensive — the sample data is well-behaved, but the brief warns about malformed inputs.

### Included

- `POST /import` accepting `text/xml+markr`
- `GET /results/:test-id/aggregate` returning JSON percentages
- All-or-nothing batch semantics
- Cross-request deduplication via UPSERT + `GREATEST`
- Persistent storage in Postgres
- Docker Compose setup
- Automated tests around the basics: parsing, validation, dedup, aggregation math, the all-or-nothing contract

### Excluded (deliberately)

- **Redis Streams or any event queue.** Considered (Round 3); ruled out as wrong design in Round 5.6.
- **A second service.** Considered (Round 6, 7); single service with module boundaries chosen instead.
- **A hot aggregate cache.** The brief explicitly says aggregation doesn't need to be fast.
- **SSE / push notifications.** Future-dashboard concern, not a current requirement.
- **Authentication / TLS.** Brief explicitly waves these off.
- **Use of `<answer>` elements.** Brief explicitly says to ignore them.
- **100% test coverage.** Brief explicitly says not to aim for it.
- **Streaming XML parser.** Avoided in favour of DOM parsing because the 10 MB body cap makes full-tree parsing safe enough, and DOM sidesteps the element-order question.

### Trade-offs

- **Single service vs. two services.** Chose simpler now, documented the future split path. Costs visible "enterprise architecture" points; gains time to do the actual job well.
- **Synchronous request handling vs. async fire-and-forget.** Chose synchronous because "reject the entire document" requires it. Costs longer per-request latency for very large batches; gains correctness guarantees and simpler reasoning.
- **In-memory full batch vs. streaming parse.** Chose in-memory because realistic batch sizes don't justify the complexity of streaming. Costs theoretical scalability ceiling; mitigated by hard-capping request size.
- **Trusting `<summary-marks>` vs. recomputing from `<answer>`.** Chose to trust, per the brief. Costs the ability to detect machine-level miscounts; gains time and matches what the boss asked for.
- **Application-layer intra-request dedup vs. database-only dedup.** Forced by Postgres' `ON CONFLICT` constraint; both happen, in their respective layers.

### How I would extend with more time

These are intentionally separated by trigger — what would have to be true to justify each step:

- **If real-time dashboards become a requirement** (currently a hint, not a need): introduce an event publisher _after_ the database commit (so the database remains the source of truth), have a separate consumer maintain a Redis hash of pre-aggregated stats per `test-id`, and serve those over SSE. The existing `GET /results/.../aggregate` endpoint stays unchanged as the canonical answer.
- **If ingestion volume grows to many scanners with real bursts**: split ingestion and aggregation into separate services. The existing module/Repository boundary keeps the code changes local, but R7.1's service-level deltas still apply. Aggregation can scale read replicas independently.
- **If batch sizes grow into the millions**: switch the write path from multi-VALUES UPSERT to `COPY` into a staging table, then a single set-based MERGE into the main table. This is faster and uses much less memory. The application code changes are localised to the Repository.
- **If observability matters**: add structured logging, request IDs, OpenTelemetry tracing on the parse/validate/upsert phases, and Prometheus metrics on rejection rate, batch size distribution, and end-to-end latency.
- **If test-id metadata becomes useful** (test name, subject, max possible score historically): a separate `tests` table referenced by foreign key, populated from the test-id space we observe.
- **If schema changes become frequent**: introduce Alembic migrations rather than a single bootstrap SQL file.

---

## A small footnote

A couple of things in the brief that don't influence architecture but did influence my mood while reading:

> "At least it's not SOAP"

Same energy. Whoever wrote this brief has been around the block.

> "The poor work experience kid"

I've thought about this kid a lot. Every "reject the entire document" decision means more typing for them. The `GREATEST` clause in our UPSERT means _they don't have to retype anything when a paper jam causes a re-scan_. A small kindness, embedded in the SQL.
