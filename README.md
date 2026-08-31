# Shopping Copilot — Conversational Search & Recommendations

TikTok TechJam 2026, Track 4. A multi-turn shopping agent that finds a customer's
intended product in a 50,000-item Amazon catalog by asking as few questions as
possible.

**Current score on the 200-session public set: TechnicalScore 0.876** — 8.2× the
provided BM25 baseline (0.107), using **no LLM and no third-party runtime
dependencies**.

| Metric | Weak BM25 baseline | This agent | Change |
|---|---|---|---|
| Hit Rate@10 | 0.125 | **0.985** | +688% |
| MRR | 0.068 | **0.669** | +883% |
| MTTC (turns to conversion) | 9.81 | **1.875** | −7.9 turns |
| Efficiency | 0.119 | **0.913** | — |
| **TechnicalScore** | **0.107** | **0.876** | **8.2×** |

Per-scenario Hit Rate@10: browsing **1.000** · buying **0.988** ·
intent_override **0.967** · boundary **0.900** (baseline 0.000).
197 of 200 sessions find the target. 60% resolve on the shopper's first
message (median and mode = turn 1); MTTC averages 1.875 turns.

## The core insight

The provided baseline never sets `ask_attribute`, so the customer answers
*"Ask me about one specific attribute"* every turn and **discloses nothing**.
It then searches only the current message, discarding everything said earlier.
That is why it needs 9.81 turns to convert.

We measured how much this costs:

```
Retrieving on the opening category alone   →  1.7% of targets in top-10
Retrieving on everything the shopper reveals → 85.0% of targets in top-10
```

**Extraction is the bottleneck, not ranking.** The catalog is reachable by
keyword search — the difficulty is getting the customer to talk, and never
losing what they said. Our architecture follows from that finding.

## Architecture

```
user message
   │
   ├─ state.update_slots ......... accumulate constraints; retract on Intent
   │                               Override; mark Boundary attributes settled
   ├─ intent.classify_intent ..... Buying vs Browsing (rules, no LLM)
   ├─ retrieval_filter.retrieve .. wide keyword pool → rescore on constraint
   │                               coverage, popularity, category, attributes
   ├─ personalization.boost ...... long-term profile, tie-break only
   └─ state.choose_attribute ..... highest-yield unanswered attribute
                │
                ▼
   { recommendations + ask_attribute }   ← always both, never one
```

### Design decisions that drive the score

**1. Every turn recommends *and* asks.** The evaluator scores recommendations
*before* it reads `ask_attribute`, so a question costs nothing when the
recommendation already hits. There is never a reason to ask without also
recommending. The interesting problem is therefore not *when to ask* but
*when to stop* — we go quiet once the top candidate dominates the shortlist
(`config.CONFIDENT_MARGIN`).

Because questions are free, we also **drain the highest-yield attribute before
moving on** rather than asking each once.

Think of the shopper as holding a filing drawer per attribute — feature,
material, colour, size, style, use case — and handing over **at most two items
per question** before closing it. Our largest bug assumed one handover emptied
the drawer, so the agent ticked the attribute off and moved on while half the
information was still inside. A session opening with *"a key requirement is:
Material:alloy"* (which classifies as `feature`) never asked `feature` again,
and so never learned *"Triple Moon Pentagram Symbol"* — the phrase that
actually identifies the product. Only an explicit refusal settles an attribute
now. **Worth +0.166, our single largest fix.**

Only `feature` and `material` are worth returning to: a second ask can only pay
where a drawer holds three or more constraints, true for 20.5% and 8.0% of
sessions respectively and at or below 0.5% for everything else
(`config.REASK_ATTRIBUTES`). That restriction is score-neutral today — sessions
end before the agent reaches the low-yield attributes — but it is provably free
and it is insurance if private-set sessions run longer.

**An Intent Override retracts one preference, not the whole conversation.**
When the shopper says *"actually, ignore my earlier preference — what I need is
canvas"*, they are withdrawing the single thing they opened with. Everything
disclosed since still holds, and the product category has not changed. An
earlier version wiped the entire session and forced the dialogue to restart,
costing both Hit Rate and turns. Dropping only the first disclosed constraint
lifted `intent_override` Hit Rate from 0.733 to 0.833.

**2. Questions are ordered by measured yield, not intuition.** Classifying
every public-set target's disclosable constraints through the evaluator's own
`classify_constraint()` gives the share of sessions where asking each attribute
actually returns new information:

| attribute | yields in | | attribute | yields in |
|---|---|---|---|---|
| `feature` | **96.0%** | | `style` | 9.0% |
| `material` | **76.5%** | | `size` | 4.5% |
| `color` | 25.5% | | `use_case` | 2.0% |
| `budget` / `brand` / `category` | **0%** | | | |

`feature` leads because it is the classifier's default bucket. `budget` never
yields (the price hint is appended last and trimmed away), `brand` has no
branch in the classifier at all, and `category` is disclosed for free in turn 1.
We ask `feature` first and **never ask the three zero-yield attributes** — each
wasted question is a turn charged against MTTC. See `config.ATTRIBUTE_PRIORITY`.

**3. Ranking rewards completeness, not term frequency.** The disclosed
constraints are quoted verbatim from the target's own listing — measured, 97.1%
of them appear literally in their target's text. So the product satisfying
*every* stated requirement is almost always the right one, while BM25 would
happily rank a listing that says "mesh" five times above one that quietly meets
all four constraints. `_constraint_coverage` scores the fraction of disclosed
phrases found verbatim in each candidate; it was worth +0.046.

Two further signals refine the ordering:

- **Popularity prior (+0.069).** Every target is an item real users actually
  bought and reviewed, so log review-volume is genuine evidence of purchase
  likelihood. Worth stating plainly: this leans on how the benchmark was
  sampled (Amazon 5-core leave-last-out), not on a property of the catalogue.
  The private set is sampled the same way, so it should transfer.
- **Category-path match (+0.017).** Matched against the product's category
  field alone, so a jersey that mentions shorts in its description does not
  score as a shorts match.

Every weight sits on a broad plateau rather than a sharp peak — popularity is
flat from 0.75 to 2.5, category from 3.0 to 10.0. Flat optima survive a
distribution shift; sharp ones are usually fitted noise. All sweeps are
recorded inline in `config.py`.

**4. Retrieval matches broadly and recovers precision by ranking.** The catalog
has no structured colour/material/size/brand fields, so filtering is really text
matching. A strict `AND` across accumulated constraints returns zero rows often,
and an empty list is a guaranteed miss for that turn. We `OR`-match into a wide
pool (800) and rank by how many constraints each product verifiably satisfies.

**5. The long-term profile breaks ties, and nothing more.** `user_profile`
describes what the shopper valued across *prior* purchases, so it is kept
separate from the session's own slots — an Intent Override retracts what they
said today, but not who they are. The instinct is to add `preference_tags`
into the score; measured, that is wrong. Tags match the target 1.72× more
often than a random product, which looks like signal, but against the
candidates *actually competing in the pool* the lift collapses to 1.12× —
almost all of it was the tags proxying for category relevance, which coverage
and category matching already capture far better. Added into the score it
therefore dilutes a strong signal with a weak one, and every additive weight
we tried scored worse (0.876 → 0.840 at weight 1.0). So the profile is
consulted only where the session evidence is genuinely indifferent: it
reorders exact ties and never outranks a real score lead.

**6. Budget is proximity, not a ceiling.** Budget is disclosed as *"budget
around $X"* where X is the target's own price, so `<= X` would wrongly reward
anything cheap. Products with no price are left unmatched but **not penalised** —
only 21% of the catalog is priced, and treating unknown as failure would demote
four fifths of it.

## Setup

**Python 3.10.12** is what we measured on; any CPython **3.10+** works. The Agent
imports **only the standard library** — retrieval runs on `sqlite3`'s built-in
FTS5 index and stays in memory. There are no runtime dependencies and no
credentials to configure.

```bash
pip install -r requirements.txt          # pytest only, to run the test suite
pip install -r requirements-dev.txt      # OPTIONAL: only for scripts/ ablations
```

`requirements-dev.txt` (`groq`, `python-dotenv`) is needed **only** to re-run the
rejected-LLM-rerank experiment under `scripts/`. It is not needed to reproduce
any reported result. That experiment is the only thing that reads an environment
variable:

| Variable | Required for | Notes |
|---|---|---|
| `GROQ_API_KEY` | `scripts/validate_llm_rerank.py`, `scripts/test_groq.py` only | Copy `.env.example` to `.env` and fill it in; `.env` is git-ignored and no key is committed. Not required by the Agent or the evaluator. |

### Catalog

`data/catalog.jsonl` is git-ignored, so **every teammate must fetch it locally** —
it does not arrive with `git clone`. Download `catalog.jsonl.gz` from the
[participant-kit release](https://github.com/TechJam2026/techjam-conversational-search/releases/tag/participant-kit)
into the repository root, then:

```bash
# SHA256SUMS covers the COMPRESSED download, so verify before decompressing.
shasum -a 256 -c SHA256SUMS          # expects catalog.jsonl.gz in the repo root
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
```

Verify the decompressed file directly (this is the exact copy our results were
produced from):

```bash
sha256sum data/catalog.jsonl
# da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67
wc -l data/catalog.jsonl        # 50000
```

| Artifact | SHA-256 | Size |
|---|---|---|
| `catalog.jsonl.gz` (as downloaded) | `07fd142631fd6b03e2b4d09988c3eb7d53720e9d57010c79db48eeaada50a8f8` | — |
| `data/catalog.jsonl` (decompressed) | `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67` | 60,546,327 bytes / 50,000 rows |

## Reproduce our results

```bash
python3 -m evaluator.local_evaluator      # writes results.json
python3 -m pytest tests/ -q               # 25 tests
```

The printed `recommended_technical_score` must read **`0.875866`**.

`docs/final_evaluation_faq.md` §1 requires teams to retain `results.json`
together with the submitted commit hash and environment details, so record them
in the same step:

```bash
git rev-parse HEAD > results_commit.txt
python3 -m evaluator.local_evaluator
python3 -VV >> results_commit.txt
```

All numbers below were produced by the unmodified official evaluator at commit
[`93530be`](https://github.com/yongc0/nailong---TikTok-TechJam-2026/commit/93530bec47a4020af05a7d241d84d3ea19be2d25)
on a clean working tree.

### Exact environment these numbers came from

| | |
|---|---|
| CPU | AMD Ryzen AI 7 350 (2 vCPU visible to the runner) |
| RAM | 3.8 GiB available |
| OS | Ubuntu 22.04.5 LTS, Linux 6.8.0-136 x86_64 |
| Python | 3.10.12 (GCC 11.4.0), CPython |
| Third-party packages on the scored path | none |

| Measurement | Value | How it was measured |
|---|---|---|
| Wall clock, all 200 sessions | **18.0 s** | `time python3 -m evaluator.local_evaluator`, warm page cache |
| One-off catalog index build | **6.2 s** | `time.perf_counter()` around `Catalog("data/catalog.jsonl")` |
| Session work (18.0 s − index build) | **11.8 s** | derived |
| Per session | **59 ms** | 11.8 s ÷ 200 sessions |
| Per turn | **32 ms** | 11.8 s ÷ 372 turns actually executed |
| Peak RSS, whole run | **638 MiB (0.62 GB)** | `/usr/bin/time -v`, "Maximum resident set size" |
| RSS after index build alone | **410 MiB (0.40 GB)** | `resource.getrusage(RUSAGE_SELF).ru_maxrss` |
| Prompt / completion tokens | **0 / 0** | no model is called |
| Estimated model cost | **$0.00** | no model is called |

Timings are hardware-dependent; the catalog index build dominates start-up and
the per-turn cost is what scales with session count. Per
`docs/final_evaluation_faq.md` §3 there is no organizer-imposed CPU, RAM or
per-response limit, since teams run the final evaluation in their own
environments.

## Repository layout

```text
agent.py                     submission entry point — wires the pipeline
config.py                    every tunable threshold and weight
src/
  contracts.py               shared dataclasses (Slots, SessionState, Candidate)
  catalog.py                 in-memory FTS5 index + precomputed attributes
  attributes.py              attribute vocabulary mirrored from the evaluator
  intent.py                  Buying/Browsing router + override detection
  state.py                   slot accumulation, override, boundary, question choice
  retrieval_filter.py        attribute-match retrieval and ranking
  personalization.py         long-term profile prior, used as a tie-break
tests/test_pipeline.py       unit tests for the pipeline
tests/test_evaluator.py      contract tests against the official evaluator
scripts/validate_llm_rerank.py    the LLM-rerank experiment we ran and rejected
scripts/analyse_llm_validation.py scores that experiment
scripts/test_groq.py              Groq connectivity smoke test
starter/agent_bm25_baseline.py    the original weak baseline, preserved
docs/                             the organizer's participant kit, unmodified
```

Every module listed under `src/` is on the scored path — there are no
placeholder or unimplemented files in this tree. Earlier revisions carried
`retrieval_dense.py` and `fusion_rerank.py` as stubs for a second retrieval
route and an LLM reranker; both were measured, found unnecessary (see
Limitations), and removed rather than shipped as dead scaffolding.

`starter/agent.py` re-exports the root `agent.py` so
`evaluator/local_evaluator.py` runs **unmodified** — modifying evaluator files is
disallowed by `docs/submission_rules.md`.

`docs/` is a verbatim copy of the organizer's participant kit, synced from
[`TechJam2026/techjam-conversational-search`](https://github.com/TechJam2026/techjam-conversational-search)
at upstream commit `9c9e7c9` (Track 4 final evaluation FAQ). The authoritative
copies are the ones in that repository:
[competition specification](https://github.com/TechJam2026/techjam-conversational-search/blob/main/docs/competition_specification.md) ·
[agent API contract](https://github.com/TechJam2026/techjam-conversational-search/blob/main/docs/agent_api_contract.json) ·
[submission rules](https://github.com/TechJam2026/techjam-conversational-search/blob/main/docs/submission_rules.md) ·
[**final evaluation FAQ**](https://github.com/TechJam2026/techjam-conversational-search/blob/main/docs/final_evaluation_faq.md)

### Development history

`PLAN.md` and `TEAM_WORKFLOW.md` were internal planning documents used during
the build. They went stale as the design changed and are not part of the
submitted tree, but they are **not** erased: the full history, including every
measurement we recorded as we went, is in git.

```bash
git log --all --oneline -- PLAN.md TEAM_WORKFLOW.md
git show <commit>:PLAN.md
```

## Network access, models, and cost

**The scored pipeline is fully offline and deterministic.** It makes no network
calls, uses no external services, imports no third-party package, and needs no
API key or credential of any kind. Reported token usage is `0 / 0` and estimated
model cost is `$0.00`, because no model is ever called.

To be clear about *why*: `docs/final_evaluation_faq.md` §2 allows network access
and external APIs, and does **not** require an offline fallback. Running offline
is therefore a deliberate engineering choice, not compliance with a restriction.
We chose it because we measured the alternative and it lost — an LLM reranking
stage scored **worse** than our ranker (see Limitations) — and because a
submission with no credentials, no rate limits and no service dependency is one
that reproduces identically for anyone who runs it, today or after the deadline.

The only external dependency anywhere in this repository is the Groq API used by
`scripts/validate_llm_rerank.py`, the experiment that produced that negative
result. It is isolated in `requirements-dev.txt`, needs `GROQ_API_KEY`, and is
never imported by `agent.py` or anything under `src/`. Deleting it entirely would
not change a single reported number.

Full latency, memory and cost measurements, with the method used for each, are
in [Reproduce our results](#reproduce-our-results).

## Robustness on data we cannot see

The 200 public sessions are for development; scoring happens on 800 private
sessions with different users and different target products. So we spent time
on failure modes the public set never exercises.

**A latent zero-results bug.** The raw user message reached the search engine
untokenised, becoming a single quoted phrase that matched nothing (0 hits raw
against 20 tokenised). Worse, a message containing a double quote made the
query malformed, and the error handler turned that into **zero candidates for
the entire turn**. The public set never triggers it; 800 unseen sessions might.
It is now a last-resort fallback, tokenised, used only when nothing parses —
score unchanged, and every degenerate input returns a full shortlist.

**No crashes across malformed input**: empty, `None` and wrongly-typed
profiles; empty and whitespace-only messages; unicode and emoji; FTS and SQL
syntax characters; a 54,000-character message.

**Sensitivity of our biggest assumption.** The popularity prior is the one
place our ranking leans on how the benchmark was built. Swept for
mis-tuning: weight 0.75 scores 0.8697, 1.5 (ours) 0.8759, 3.5 scores 0.8742 —
a spread of 0.006 across a wide band. Being somewhat wrong costs little; only
popularity carrying no signal at all in the private set would hurt (-0.066).

**Every weight sits on a plateau, not a peak** — deliberately. Flat optima
survive a distribution shift; sharp ones are usually fitted noise.

## Limitations and what we would improve

- **An LLM reranking stage was tested and rejected on evidence.** On 40 real
  sessions it lifted ambiguous cases (+0.041 MRR) but demoted already-correct
  ones (-0.107 MRR), projecting to **-0.011 TechnicalScore**; even a perfect
  invocation gate caps the gain at +0.006, below noise. Our ranker wins
  because constraint coverage matches text the customer quoted verbatim from
  the target's listing — the task rewards literal completeness over semantic
  judgement. Reproduce with `scripts/validate_llm_rerank.py`. This is why the
  pipeline is deliberately, not incidentally, offline.
- **Dense (embedding) retrieval is not implemented.** It was planned as core,
  but the 1.7%-vs-85% measurement showed dialogue extraction mattered far more.
  Retrieval is now close to saturated — 197 of 200 sessions find the target, and
  the 3 that fail are ranking failures, not coverage failures — so a second
  retrieval route has almost nothing left to add. The `retrieval_dense.py` and
  `fusion_rerank.py` stubs have been deleted rather than shipped as dead
  scaffolding; the decision and its evidence live here instead.
- **Title-weighted matching was tested and rejected.** Rewarding a constraint
  found in the product title above one found anywhere in its text is
  principled — a requirement in the title is what the product *is* — but it
  hurt at every weight (0.876 → 0.854 at weight 3.0), because constraints are
  drawn from the features and details fields rather than titles.
- **A learned ranker (LTR) was scoped but not built.** The remaining +0.095 of
  headroom is all in MRR, which is what it would target. We stopped because
  with 197/200 sessions already hit and only 200 training sessions available,
  the risk of a fitted model failing to transfer to the private set now rivals
  the upside. It is the right next experiment, but it must be judged on
  cross-validated evidence (GroupKFold by session), never on train-set gain.
- **`intent.py` now weights retrieval, and it is honestly close to
  load-bearing too.** Buying leans harder on verified coverage/category
  agreement than Browsing (`config.INTENT_COVERAGE_MULTIPLIER` /
  `INTENT_CATEGORY_MULTIPLIER`). Swept the same way as every other knob
  here: it changes individual candidate scores (see
  `test_intent_measurably_changes_retrieval_ranking`) but not the public-set
  TechnicalScore (0.875866, unchanged) -- both Buying and Browsing were
  already at or near ceiling on the un-weighted formula, so there was
  nothing left for this axis to win. We would rather report the honest null
  than claim a lift we didn't measure; see `config.py` for the full sweep.
- **Personalization is principled but worth almost nothing here (+0.0002,
  i.e. noise).** The profile is too coarse to separate candidates that
  already match the session constraints. It earns its place as correct
  handling of the long-term signal, not as a score contributor, and we would
  rather say so than overclaim it.
- **`boundary` remains our weakest scenario (0.900 Hit Rate, MTTC 3.00).** The
  customer refuses to narrow one attribute and we have no special handling
  beyond marking it settled. With only 10 such sessions the estimate is noisy.
- **`intent_override` MTTC (3.97) stays high by construction** — the evaluator
  ignores hits before the override turn, so those sessions cannot converge
  before turn 3-4 however good the agent is. Its Hit Rate is 0.967 and its MRR
  (0.815) is our best of any scenario.
- **Constraint parsing is marker-based.** It handles the disclosure phrasings we
  observed plus common natural equivalents, but a paraphrase outside that set
  yields nothing. A small LLM extraction call is the obvious upgrade.
- **`ATTRIBUTE_PRIORITY` is tuned on public-set yield.** The private set uses the
  same simulator, so it should transfer — but this is an assumption, and a
  meaningfully different constraint distribution would degrade MTTC.
- **Attribute extraction is vocabulary-bound.** Materials and colours are matched
  against the evaluator's fixed word lists; anything outside them is invisible to
  verified matching and falls back to keyword relevance.

## Team contributions

| Team member | Contribution |
|---|---|
| Yong Chuan Onn | Software development and solution ideation |
| Chew Qiao Enn | Software development and solution ideation |
| Balon Alexandre Stephane Daniel | Solution ideation, product direction, and project review; demo video editing and scriptwriting |
| Stella Teo Boon Yim | Solution ideation, product direction, and project review; demo video editing and scriptwriting |

Module ownership during the build: dialog state & intent (`state.py`,
`intent.py`), retrieval & ranking (`catalog.py`, `retrieval_filter.py`,
`attributes.py`), personalization & integration (`personalization.py`,
`agent.py`, evaluation harness).

## Data source

Catalog and sessions derive from Amazon Reviews 2023 (McAuley Lab, UCSD). See
`DATA_ATTRIBUTION.md`. The catalog is read-only and unmodified.
