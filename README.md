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

Python 3.10+. The agent itself needs **no third-party packages** — retrieval runs
on the standard library (`sqlite3` FTS5) and stays entirely in memory.

```bash
pip install -r requirements.txt
```

Download `catalog.jsonl.gz` from the participant-kit release, verify it, and
place it:

```bash
shasum -a 256 -c SHA256SUMS
gzip -dk catalog.jsonl.gz && mv catalog.jsonl data/catalog.jsonl
```

`data/catalog.jsonl` is git-ignored, so **every teammate must do this locally** —
it does not arrive with `git clone`.

## Reproduce our results

```bash
python3 -m evaluator.local_evaluator
```

Runs all 200 public sessions in ~18s on a laptop and writes `results.json`.
The printed `recommended_technical_score` should read `0.875866`.

Run the tests:

```bash
python3 -m pytest tests/ -q
```

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
  retrieval_filter.py        Route A — attribute-match retrieval
  retrieval_dense.py         Route B — embedding retrieval (stub; see Limitations)
  fusion_rerank.py           route fusion + LLM rerank (stub; see Limitations)
  personalization.py         long-term profile prior, used as a tie-break
tests/test_pipeline.py       24 unit tests for the above
scripts/test_groq.py         Groq connectivity smoke test
scripts/validate_llm_rerank.py    Phase 3.0 experiment: LLM rerank vs ours
scripts/analyse_llm_validation.py scores that experiment
starter/agent_bm25_baseline.py    the original weak baseline, preserved
```

`starter/agent.py` re-exports the root `agent.py` so
`evaluator/local_evaluator.py` runs **unmodified** — modifying evaluator files is
disallowed by `docs/submission_rules.md`.

## Network access and offline fallback

**The scored pipeline is fully offline and deterministic.** It makes no network
calls, uses no external services, and needs no API key. If organizer policy
disables network access at scoring time, the agent runs unchanged with identical
results.

`groq` and `python-dotenv` appear in `requirements.txt` only for the offline
experiment in `scripts/validate_llm_rerank.py`, which measured an LLM reranker
and found it net-negative (see Limitations). Nothing in the scored path imports
them, and the agent runs unchanged if they are absent.

Token usage reported to the evaluator is `0`, and model cost is `$0`, because
no model is called. Latency is ~18s for all 200 sessions end to end (~90ms per
session), including a one-off 4.7s index build; peak memory is 0.41 GB.

This is a measured decision, not an omission: we tested the LLM stage and it
made the ranking worse.

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
  retrieval route has almost nothing left to add. `retrieval_dense.py` and
  `fusion_rerank.py` remain stubs, deliberately.
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

For the module-level breakdown used during parallel development, see
`TEAM_WORKFLOW.md` (dialog state & intent, filter retrieval, dense
retrieval & rerank, personalization & integration).

## Data source

Catalog and sessions derive from Amazon Reviews 2023 (McAuley Lab, UCSD). See
`DATA_ATTRIBUTION.md`. The catalog is read-only and unmodified.
