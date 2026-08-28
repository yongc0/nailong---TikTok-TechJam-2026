# Team Workflow — Shopping Copilot (Track 4)

4-person team. Goal: parallel work that doesn't collide, so the 72-hour
window (Aug 29 12:00pm – Sep 1 12:00pm SGT) is spent building, not
untangling merge conflicts or waiting on each other.

## 1. Role split (mirrors PLAN.md's 5 systems + submission_rules.md's file layout)

The package below exists on `main`. ✅ = implemented and scoring,
⬜ = still a stub raising `NotImplementedError`.

```
agent.py                   ✅ thin glue: wires the pipeline, matches the contract
config.py                  ✅ every tunable threshold and weight — tune here, not in code
src/
  contracts.py             ✅ shared — Slots, SessionState, Candidate, RankedList
  catalog.py               ✅ shared — in-memory FTS5 index + precomputed attributes
  attributes.py            ✅ shared — attribute vocabulary mirrored from the evaluator
  state.py                 ✅ P1 — slots, Intent Override, Boundary, question choice
  intent.py                ✅ P1 — Buying/Browsing router + override detection
  retrieval_filter.py      ✅ P2 — structured/attribute-match retrieval (Route A)
  retrieval_dense.py       ⬜ P3 — embeddings (Route B) — deliberately unbuilt, see below
  fusion_rerank.py         ⬜ P3 — fusion + LLM rerank — deliberately unbuilt, see below
  personalization.py       ✅ P4 — long-term profile prior (tie-break only)
tests/test_pipeline.py     ✅ 21 tests, run with `python3 -m pytest tests/ -q`
starter/agent.py           ✅ re-exports root agent.py so the evaluator runs unmodified
starter/agent_bm25_baseline.py  the original weak baseline, preserved for comparison
```

The two remaining stubs are **not a backlog**. Retrieval is saturated (197/200
sessions hit; the 3 failures are ranking, not coverage), and an LLM reranker was
built, measured and rejected in Phase 3.0 — it projected **-0.011**
TechnicalScore because it demoted already-correct sessions. Do not implement
either without new evidence; see `PLAN.md`.

`contracts.py`, `catalog.py` and `attributes.py` are **shared infrastructure**,
not owned by one person — both retrieval routes need the same 50k-product
index, and loading it twice would double startup and memory for nothing.
Coordinate on a call before changing them.

| Person | Owns | Also responsible for |
|---|---|---|
| **P1 — Dialog & Intent** | `state.py`, `intent.py` | clarification question generation, `ask_attribute` logic, the over-generality cutoff (turn budget discipline) |
| **P2 — Filter Retrieval** | `retrieval_filter.py` | parsing category/material/color/size/style/brand/price out of accumulated slots into catalog filters |
| **P3 — Dense Retrieval & Rerank** | `retrieval_dense.py`, `fusion_rerank.py` | picking + precomputing the embedding model (this is the one piece of prep work defensible *before* the window opens — see §4) |
| **P4 — Personalization & Integration** | `personalization.py`, `agent.py` glue | wiring everyone's modules together, running `local_evaluator` after every merge, tracking per-scenario metrics, owning the submission checklist in PLAN.md |

P4 is the integration point — give that person the least new-feature surface
area so they have slack to review PRs and keep `main` green.

## 2. The internal contract — DONE, now in code

Agreed and implemented as `src/contracts.py`:

- **`Slots`** — the ten attribute fields, mirroring the `ask_attribute` enum
  in `docs/agent_api_contract.json` so nothing needs translating at the
  `agent.py` boundary.
- **`SessionState`** — `slots` plus `disclosed_text`, `disclosed_attributes`,
  `asked_attributes`, `history`, `intent`, `turn`.
  `disclosed_text` (raw constraint strings, verbatim) is the highest-value
  field in the system — see the measurements in `PLAN.md`.
- **`Candidate`** — `parent_asin`, `score`, `source`, `matched_attributes`.
  Both retrieval routes emit these; fusion and personalization consume them.
- **`config.py`** — every tunable threshold and weight. Nothing is hardcoded
  inside a module, so tuning experiments need no code changes.

Change these freely, but change them *together* on a call — every module
depends on them.

## 3. Git workflow

**Current reality (updated Aug 26):** one person holds the Claude Code
account and is generating most of the code, so the per-module feature-branch
model in the original plan added ceremony without solving a real collision
problem. We are committing **straight to `main`**, pulling before each push,
and reviewing after the fact via the commit diff on GitHub.

- `main` stays green — always runnable, always passes `local_evaluator`.
- Pull before you push. Small, frequent commits with real messages.
- After every push, re-run `python3 -m evaluator.local_evaluator` and post
  the TechnicalScore in the team channel — catches regressions immediately
  instead of at submission time.
- **Anyone can tune without touching logic:** edit a value in `config.py`,
  re-run the evaluator, report the score delta. That is the highest-value
  contribution for anyone not writing modules.
- Reach for a feature branch only when two people really are editing the
  same file at the same time.

## 4. Sync cadence (only 72 scored hours — keep this light)

- Standup ~2x/day (e.g. 9am / 9pm SGT), 10 min, async-friendly: what merged,
  what's blocked, current TechnicalScore.
- One shared channel (Discord/WhatsApp) for blockers as they happen.
- Task board: GitHub Projects on this repo, one column per module +
  "integration" — low overhead, lives next to the code.

## 5. Where we are and what's next

**Status: working agent on `main`, TechnicalScore 0.876 vs 0.107 baseline.**
Full detail and the measurements behind the design are in `PLAN.md`.

### Everyone, before you write any code

1. `git pull` — then download and verify the catalog locally if you have not
   already (`README.md` has the commands). `data/catalog.jsonl` is
   git-ignored, so it does **not** arrive with `git clone`.
2. Run `python3 -m evaluator.local_evaluator` and confirm you get
   `0.875866`. If you get something else, say so before changing anything.
3. Run `python3 -m pytest tests/ -q` — 21 tests should pass.
4. **Read the measurements in `PLAN.md`** before proposing changes. Several
   are counter-intuitive and were expensive to discover: asking questions is
   free; `budget` and `brand` yield nothing; an LLM reranker makes things
   worse; and boosting on `preference_tags` hurts despite looking like real
   signal.

### Highest-value work now, in order

**1. Deliverables — the only urgent work left.** Devpost writeup, demo video,
README team names. None are started, and they carry real judging weight
(Presentation 10%, and the writeup shapes Innovation 20%). An unfinished
submission costs far more than any remaining tenth of a point. **Whoever is
free should start here, not on the model.**

**2. A learned ranker — the last score lever, and a genuine gamble.** All
+0.095 of remaining headroom is in MRR. But with 197/200 already hit and only
200 training sessions, the risk of a fitted model failing on the private set
now rivals the upside. If attempted: GroupKFold **by session**, judge on
cross-validated gain only, ship behind a fallback, and drop it if CV gain is
under ~0.02.

**3. `boundary`** — weakest scenario (0.900 Hit@10, MTTC 3.00) but only 10
sessions, so tuning against it risks fitting noise.

**Ruled out, with evidence — please read before proposing these again:**
LLM reranking (projected **-0.011**), additive personalization (**-0.036** at
weight 1.0), and dense retrieval (retrieval is saturated). All three are
documented with reproducible measurements in `PLAN.md`.

**Config tuning is done** for every live knob; sweep results are recorded
inline in `config.py`. The unswept knobs belong to the two stubs.

### Still worth asking at the Aug 28 workshop (4:00–4:45pm SGT)

- Is network access available at official scoring time? *(Now low-stakes: our
  scored path is offline, and Phase 3.0 measured an LLM stage as net-negative
  anyway, so the answer changes nothing we plan to ship.)*
- Anything to know about how the private 800 sessions were sampled? Our
  popularity prior assumes the same 5-core leave-last-out construction as the
  public set — that assumption is worth confirming, since it is the one place
  our ranking leans on the benchmark's design.

## 6. Submission ownership (from `docs/submission_rules.md`, tracked in PLAN.md)

P4 owns final submission assembly but everyone contributes their module's
piece: latency/token-usage disclosure for anything you added, and a
one-paragraph "how my part works" for the README's team-contributions
section.
