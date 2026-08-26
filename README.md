# Shopping Copilot — Conversational Search & Recommendations

TikTok TechJam 2026, Track 4. A multi-turn shopping agent that finds a customer's
intended product in a 50,000-item Amazon catalog by asking as few questions as
possible.

**Current score on the 200-session public set: TechnicalScore 0.562** — 5.3× the
provided BM25 baseline (0.107), using **no LLM and no third-party runtime
dependencies**.

| Metric | Weak BM25 baseline | This agent | Change |
|---|---|---|---|
| Hit Rate@10 | 0.125 | **0.655** | +424% |
| MRR | 0.068 | **0.407** | +499% |
| MTTC (turns to conversion) | 9.81 | **5.385** | −4.4 turns |
| Efficiency | 0.119 | **0.562** | — |
| **TechnicalScore** | **0.107** | **0.562** | **5.3×** |

Per scenario: browsing **0.838** · boundary **0.600** (baseline 0.000) ·
buying **0.563** · intent_override **0.433**.

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
   ├─ state.update_slots ......... accumulate constraints; erase on Intent
   │                               Override; mark Boundary attributes settled
   ├─ intent.classify_intent ..... Buying vs Browsing (rules, no LLM)
   ├─ retrieval_filter.retrieve .. wide keyword pool → rescore by verified
   │                               attribute matches
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

**3. Retrieval matches broadly and recovers precision by ranking.** The catalog
has no structured colour/material/size/brand fields, so filtering is really text
matching. A strict `AND` across accumulated constraints returns zero rows often,
and an empty list is a guaranteed miss for that turn. We `OR`-match into a wide
pool (800) and rank by how many constraints each product verifiably satisfies.

**4. Budget is proximity, not a ceiling.** Budget is disclosed as *"budget
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
The printed `recommended_technical_score` should read `0.561976`.

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
  retrieval_dense.py         Route B — embedding retrieval (not yet implemented)
  fusion_rerank.py           route fusion + LLM rerank (not yet implemented)
  personalization.py         profile-aware reranking (not yet implemented)
tests/test_pipeline.py       unit tests for the above
scripts/test_groq.py         Groq connectivity smoke test
starter/agent_bm25_baseline.py   the original weak baseline, preserved
```

`starter/agent.py` re-exports the root `agent.py` so
`evaluator/local_evaluator.py` runs **unmodified** — modifying evaluator files is
disallowed by `docs/submission_rules.md`.

## Network access and offline fallback

**The scored pipeline is fully offline and deterministic.** It makes no network
calls, uses no external services, and needs no API key. If organizer policy
disables network access at scoring time, the agent runs unchanged with identical
results.

`groq` and `python-dotenv` appear in `requirements.txt` only for the optional LLM
reranking stage under development; it is not on the scoring path, and the agent
degrades to the current behaviour if it is unavailable.

Token usage reported to the evaluator is currently `0` for the same reason.

## Limitations and what we would improve

- **Dense retrieval and LLM reranking are not implemented yet.** They were
  planned as core, but the 85%-with-full-disclosure measurement showed dialogue
  extraction mattered far more, so they were deprioritised. The remaining
  headroom in MRR (0.407 — targets are often found but not ranked first) is the
  clearest use for a reranker.
- **`intent.py` is built but barely load-bearing.** Intent is classified and
  tracked, but does not yet change retrieval weighting between routes.
- **`intent_override` is our weakest scenario (0.433).** Partly structural — the
  evaluator ignores hits before the override turn, so MTTC there cannot fall
  below ~3 — but our erasure heuristic is also coarse: it wipes all descriptive
  constraints rather than only the contradicted ones.
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

| Person | Ownership |
|---|---|
| P1 | Dialog state & intent — `state.py`, `intent.py` |
| P2 | Filter retrieval — `retrieval_filter.py` |
| P3 | Dense retrieval & rerank — `retrieval_dense.py`, `fusion_rerank.py` |
| P4 | Personalization & integration — `personalization.py`, `agent.py`, evaluation |

*To be completed with names and per-person detail before submission.*

## Data source

Catalog and sessions derive from Amazon Reviews 2023 (McAuley Lab, UCSD). See
`DATA_ATTRIBUTION.md`. The catalog is read-only and unmodified.
