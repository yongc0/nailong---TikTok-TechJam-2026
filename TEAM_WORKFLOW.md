# Team Workflow — Shopping Copilot (Track 4)

4-person team. **This file describes what actually exists**, not the original
plan — several planned components were measured and deliberately dropped, and
crediting anyone with those would be wrong.

## 1. What is built

✅ = implemented and scoring. ⬜ = a stub that raises `NotImplementedError`,
kept only so the import surface is stable — **not a backlog**.

```
agent.py                   ✅ thin glue: wires the pipeline, matches the contract
config.py                  ✅ every tunable threshold and weight — tune here, not in code
src/
  contracts.py             ✅ shared — Slots, SessionState, Candidate, RankedList
  catalog.py               ✅ shared — in-memory FTS5 index + precomputed attributes
  attributes.py            ✅ shared — attribute vocabulary mirrored from the evaluator
  state.py                 ✅ slot accumulation, Intent Override, Boundary, question choice
  intent.py                ✅ Buying/Browsing router + override detection
  retrieval_filter.py      ✅ the retrieval and ranking route (the only one)
  personalization.py       ✅ long-term profile prior, tie-break only
  retrieval_dense.py       ⬜ embeddings — measured as unnecessary, never built
  fusion_rerank.py         ⬜ fusion + LLM rerank — built, measured, rejected
tests/test_pipeline.py     ✅ 24 tests, run with `python3 -m pytest tests/ -q`
starter/agent.py           ✅ re-exports root agent.py so the evaluator runs unmodified
starter/agent_bm25_baseline.py  the original weak baseline, preserved for comparison
```

Why the two stubs stay empty: retrieval is saturated (197/200 sessions hit,
and the 3 failures are ranking misses, not coverage misses), and the LLM
reranker was built, measured at **-0.011**, and cut. Do not implement either
without new evidence — see `PLAN.md`.

`contracts.py`, `catalog.py` and `attributes.py` are **shared infrastructure**
rather than one person's file. Coordinate before changing them.

### Work areas, as they actually turned out

The original P1-P4 split assumed dense retrieval and an LLM reranker were
core. They are not, so the real work divided differently:

| Area | Files | What it covers |
|---|---|---|
| **Dialogue** | `state.py`, `intent.py` | Slot accumulation, Intent Override retraction, Boundary handling, and which attribute to ask next |
| **Retrieval & ranking** | `retrieval_filter.py`, `catalog.py`, `attributes.py` | The in-memory index, attribute extraction, and the scoring that decides the shortlist |
| **Evaluation & experiments** | `scripts/`, `config.py` sweeps | Metric analysis, weight sweeps, the LLM rerank trial, and the robustness testing |
| **Integration & submission** | `agent.py`, `tests/`, docs | API-contract conformance, the test suite, and the submission package |

**Fill in who did what before submitting** — the README's team-contributions
table needs real names against real work. Do not credit anyone with
`retrieval_dense.py` or `fusion_rerank.py`; a judge reading the repo will see
they raise `NotImplementedError`.

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
3. Run `python3 -m pytest tests/ -q` — 24 tests should pass.
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
weight 1.0), title-weighted matching (**-0.022** at weight 3.0), and dense
retrieval (retrieval is saturated). All four are documented with
reproducible measurements in `PLAN.md`.

**Stop tuning against the 200.** We are at the point where further changes
are more likely to be fitting noise than finding signal — `boundary`, with
ten sessions, is the obvious trap. Remaining effort is better spent on
robustness and the deliverables.

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
