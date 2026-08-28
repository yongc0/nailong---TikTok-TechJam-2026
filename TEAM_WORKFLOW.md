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
  retrieval_dense.py       ⬜ P3 — embeddings + candidate retrieval (Route B)
  fusion_rerank.py         ⬜ P3 — RRF fusion + LLM/cross-encoder rerank
  personalization.py       ⬜ P4 — user_profile-based ranking boost
tests/test_pipeline.py     ✅ 19 tests, run with `python3 -m pytest tests/ -q`
starter/agent.py           ✅ re-exports root agent.py so the evaluator runs unmodified
starter/agent_bm25_baseline.py  the original weak baseline, preserved for comparison
```

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

**Status: working agent on `main`, TechnicalScore 0.744 vs 0.107 baseline.**
Full detail and the measurements behind the design are in `PLAN.md`.

### Everyone, before you write any code

1. `git pull` — then download and verify the catalog locally if you have not
   already (`README.md` has the commands). `data/catalog.jsonl` is
   git-ignored, so it does **not** arrive with `git clone`.
2. Run `python3 -m evaluator.local_evaluator` and confirm you get
   `0.743549`. If you get something else, say so before changing anything.
3. Run `python3 -m pytest tests/ -q` — 19 tests should pass.
4. **Read the four measurements in `PLAN.md`** before proposing changes.
   Two of them are counter-intuitive (asking questions is free; `budget`
   and `brand` are worth zero) and both were expensive to discover.

### Highest-value work now, in order

Priorities changed after the measurements — dense retrieval and LLM
reranking are no longer core. See "Revised priorities" in `PLAN.md`:

1. **A learned ranker.** When we miss, the target is still in the candidate
   pool 99% of the time — just ranked too low. Pointwise learning-to-rank
   over the existing pool is the biggest remaining win, and unlike an LLM it
   keeps the pipeline offline. Validate with GroupKFold **by session**: 200
   queries is thin, and public/private use different products.
2. **Richer ranking features first** — token overlap with the title,
   `average_rating`, `rating_number`, category-path depth. Often captures
   most of the gain before any model is trained.
3. **`boundary` (0.700, 10 sessions)** — weakest scenario now, though the
   sample is small enough that the estimate is noisy.
4. **Config tuning** is done for the three live knobs (results recorded in
   `config.py`); the remaining knobs belong to modules that are still stubs.

### Still worth asking at the Aug 28 workshop (4:00–4:45pm SGT)

- Is network access available at official scoring time? *(Our scored path is
  offline either way, so this is now a question about whether adding an LLM
  stage is safe — not a risk to what already works.)*
- Any constraint on precomputing embeddings over the frozen catalog?

## 6. Submission ownership (from `docs/submission_rules.md`, tracked in PLAN.md)

P4 owns final submission assembly but everyone contributes their module's
piece: latency/token-usage disclosure for anything you added, and a
one-paragraph "how my part works" for the README's team-contributions
section.
