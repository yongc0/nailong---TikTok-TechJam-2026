# Team Workflow — Shopping Copilot (Track 4)

4-person team. Goal: parallel work that doesn't collide, so the 72-hour
window (Aug 29 12:00pm – Sep 1 12:00pm SGT) is spent building, not
untangling merge conflicts or waiting on each other.

## 1. Role split (mirrors PLAN.md's 5 systems + submission_rules.md's file layout)

Restructure `starter/agent.py` into a package so each person owns files
nobody else touches:

```
agent.py                  # thin glue: imports + wires the 4 modules below
src/
  state.py                # P1 — slots, Intent Override, Boundary handling
  intent.py                # P1 — Buying/Browsing router
  retrieval_filter.py      # P2 — structured/attribute-match retrieval (Route A)
  retrieval_dense.py       # P3 — embeddings + candidate retrieval (Route B)
  fusion_rerank.py         # P3 — RRF fusion + LLM/cross-encoder rerank
  personalization.py       # P4 — user_profile-based ranking boost
requirements.txt           # P4 owns, everyone can append via PR
README.md                  # P4 owns final pass, everyone drafts their section
```

| Person | Owns | Also responsible for |
|---|---|---|
| **P1 — Dialog & Intent** | `state.py`, `intent.py` | clarification question generation, `ask_attribute` logic, the over-generality cutoff (turn budget discipline) |
| **P2 — Filter Retrieval** | `retrieval_filter.py` | parsing category/material/color/size/style/brand/price out of accumulated slots into catalog filters |
| **P3 — Dense Retrieval & Rerank** | `retrieval_dense.py`, `fusion_rerank.py` | picking + precomputing the embedding model (this is the one piece of prep work defensible *before* the window opens — see §4) |
| **P4 — Personalization & Integration** | `personalization.py`, `agent.py` glue | wiring everyone's modules together, running `local_evaluator` after every merge, tracking per-scenario metrics, owning the submission checklist in PLAN.md |

P4 is the integration point — give that person the least new-feature surface
area so they have slack to review PRs and keep `main` green.

## 2. The one thing to agree on *before* Aug 29: the internal contract

The org's `docs/agent_api_contract.json` is what lets your team not depend
on the organizer's harness internals. Do the same thing internally, on a
call, before hacking opens — write down the exact function signatures /
dict shapes each module passes to the next:

- What shape are "slots" (`state.py` → `retrieval_filter.py`,
  `retrieval_dense.py`)?
- What does a "candidate" look like coming out of each retrieval route,
  before fusion (`parent_asin`, `score`, any metadata `fusion_rerank.py`
  needs)?
- What does `personalization.py` take as input (ranked list + `user_profile`
  dict) and return (re-ranked list)?

Once this is written down, all 4 people can build against the *contract*
in parallel using stub/fake data — nobody blocks on anybody else's module
actually being finished.

## 3. Git workflow

- `main` stays green — always runnable, always passes `local_evaluator`.
- One feature branch per module: `feature/dialog-state`, `feature/filter-retrieval`,
  `feature/dense-retrieval`, `feature/personalization-glue`.
- Small, frequent PRs (every 3–6 hours during the sprint, not one PR at
  hour 70) — at least one teammate reviews before merging to `main`.
- After every merge to `main`, re-run `python3 -m evaluator.local_evaluator`
  and post the TechnicalScore in the team channel — catches regressions
  immediately instead of at submission time.

## 4. Sync cadence (only 72 scored hours — keep this light)

- Standup ~2x/day (e.g. 9am / 9pm SGT), 10 min, async-friendly: what merged,
  what's blocked, current TechnicalScore.
- One shared channel (Discord/WhatsApp) for blockers as they happen.
- Task board: GitHub Projects on this repo, one column per module +
  "integration" — low overhead, lives next to the code.

## 5. What to do right now (Aug 26 – Aug 29 12:00pm SGT, before the window opens)

Nothing here is scored work — Devpost rules require the submission to be
original/substantially updated *within* the hacking window, so treat all of
this as setup, not solution-building.

1. **Tonight:** confirm the 4 names against the roles in §1, post it in the
   team channel.
2. **Everyone, by tomorrow:** clone the repo, download+verify the catalog
   (steps already in `README.md`), run `python3 -m evaluator.local_evaluator`
   and confirm you reproduce the baseline (HitRate@10 0.125 / MRR 0.068 /
   MTTC 9.81) locally — this is just an environment sanity check, catches
   "it doesn't work on my machine" before it costs you sprint hours.
3. **Group call before Aug 28:** walk through `PLAN.md` and
   `docs/agent_api_contract.json` together, agree the internal contract from
   §2, write it into this file's §2 section or a shared doc.
4. **P3 specifically:** pick the embedding model/library now (e.g. a local
   `sentence-transformers` model — no external vector DB per the kit's
   constraints) so there's no research time lost on day 1. Writing the
   embedding-build *script* now is fine; whether you're allowed to run it
   and commit the resulting vectors before the window opens is worth a
   direct question to the organizers at the workshop (see #5) rather than
   assuming.
5. **Aug 28, 4:00–4:45pm SGT:** attend the Track 4 workshop. Bring specific
   questions — network access at official scoring time, and whether
   pre-computing embeddings on the frozen catalog before Aug 29 is allowed.
6. **Before Aug 29 morning:** create the 4 empty feature branches and the
   file skeleton from §1 so day 1 starts with `git pull` + write code, not
   repo setup.

## 6. Submission ownership (from `docs/submission_rules.md`, tracked in PLAN.md)

P4 owns final submission assembly but everyone contributes their module's
piece: latency/token-usage disclosure for anything you added, and a
one-paragraph "how my part works" for the README's team-contributions
section.
