# Shopping Copilot — Team Plan

Track 4: AI Conversational Search and Recommendations (TikTok TechJam 2026)

## Timeline (all times Asia/Singapore = UTC+8, same as Kuala Lumpur)

| Date | Event |
|---|---|
| Aug 25, 12:00pm | Problem statements released (early bird) |
| Aug 27, 12:00pm | Problem statements public |
| Aug 28, 4:00–4:45pm | Technical workshop + Q&A (Track 4) |
| Aug 29, 12:00pm | Hacking period opens |
| Sep 1, 12:00pm | Hacking period closes (72h window) — submission deadline |
| Sep 1–7 | Judging + public voting |
| Sep 8, 12:00pm | Finalists announced |
| Sep 11 | Grand Final (Singapore, in-person pitch) |
| Sep 15 | Winners announced |

Only 72 hours of official hacking time. Everything before Aug 29 should be
prep: environment setup, architecture design, and skeleton code — not the
scored solution itself (submissions must be "original or significantly
updated" within the hacking window per the Devpost rules).

## What's already done

**Aug 26 — setup**

- Cloned the repo, downloaded `catalog.jsonl.gz` from the participant-kit
  release, verified SHA256, decompressed to `data/catalog.jsonl` (50,000
  rows confirmed)
- Reproduced the baseline: HitRate@10 0.125, MRR 0.068, MTTC 9.81,
  TechnicalScore 0.107 — the floor to beat
- Confirmed Groq `gpt-oss-20b` works (`scripts/test_groq.py`).
  **Gotcha:** it is a reasoning model — the reasoning trace consumes
  `max_completion_tokens` before the answer, so a 20-token cap returns an
  EMPTY string. Budget 200+.

**Aug 26 — working agent, TechnicalScore 0.876 (8.2× baseline)**

- HitRate@10 0.985, MRR 0.669, MTTC 1.875 — 197 of 200 sessions convert,
  typically on the second message
- By scenario (Hit Rate@10): browsing 1.000, buying 0.988,
  intent_override 0.967, boundary 0.900 (all were 0.000-0.238 at baseline)
- Implemented: `src/catalog.py`, `src/attributes.py`, `src/intent.py`,
  `src/state.py`, `src/retrieval_filter.py`, root `agent.py`
- **No LLM used.** Fully offline and deterministic, which satisfies the
  offline-fallback requirement in `docs/submission_rules.md` for free.
- `starter/agent.py` now re-exports the root `agent.py`; the original weak
  baseline is preserved as `starter/agent_bm25_baseline.py`. The evaluator
  stays unmodified.
- 19 tests pass: `python3 -m pytest tests/ -q`

Run it yourself (~18s, writes `results.json`):
```
python3 -m evaluator.local_evaluator
```

### Measurements that shaped the design — read before changing things

1. **Extraction beats ranking.** Retrieving on the opening category alone
   puts the target in top-10 for 1.7% of sessions; retrieving on everything
   the shopper eventually discloses reaches 85%. The game is getting the
   customer to talk, not clever ranking.
2. **Asking is free.** The evaluator scores `recommendations` BEFORE it
   reads `ask_attribute`, so every turn should do both. The real question is
   when to STOP asking, not when to start.
3. **Attribute yield is wildly uneven** (share of sessions where asking
   returns new information): `feature` 96%, `material` 76.5%, `color` 25.5%,
   `style` 9%, `size` 4.5%, `use_case` 2%, and `budget`/`brand`/`category`
   **0%**. We never ask the zero-yield three. This is most of the MTTC win.
4. **Only 21% of the catalog has a price**; material covers 57%, colour 39%.
   Budget is a weak signal, and "no price" must not count as a budget miss.

## System to build

### 1. Intent router (Buying vs Browsing)
Classify each turn's message into a track. Cheap first pass: rule/keyword
classifier (price mentions, size/color/brand nouns, imperative "buy/need"
verbs → Buying; vague adjectives, "browsing/looking around" → Browsing).
Optionally back it with a small LLM call for ambiguous cases. This decides
retrieval strategy weighting, not a hard gate.

### 2. Multi-route retrieval → LLM (or scoring) rerank
- Route A (filter/precision): structured constraint matching over
  `category`, `material`, `color`, `size`, `style`, `brand`, `price` parsed
  from the conversation's accumulated slots.
- Route B (dense/diverse): embedding similarity over title+features+desc
  (build once, offline, over the 50k catalog — sentence-transformers or
  similar, kept in-memory per the "no external vector DB" constraint).
- Fuse candidates (RRF or weighted sum) → rerank top ~30-50 with an LLM
  prompt (or a lightweight cross-encoder/scoring function if avoiding LLM
  cost) that sees the full dialog history and each candidate's key fields.

### 3. Dialog state machine
- Slots: category, material, color, size, style, brand, budget, feature,
  use_case, other — accumulate incrementally.
- Handle **Intent Override**: detect a contradicting/replacing statement
  and wipe conflicting slots rather than merging.
- Handle **Boundary**: user has no preference for the asked attribute — treat
  as an explicit "skip", don't re-ask the same attribute.
- When candidate pool is still huge after a turn (over-generality), do NOT
  return a flat top-10 guess — set `ask_attribute` to the single most
  discriminative missing slot instead of a hit-or-miss guess. This is what
  MTTC rewards: fewer wasted turns.

### 4. Context distillation / personalization
- Use `user_profile` (`purchase_frequency`, `average_prior_rating`,
  `rating_style`, `preference_tags`, `summary`) as a prior on ranking (e.g.
  boost tags that match `preference_tags`), not as a hard filter.
- Maintain short-term session state (this conversation's slots) separately
  from the long-term profile signal so an Intent Override doesn't corrupt
  the profile-level bias.

### 5. Efficiency discipline
- Efficiency = clip((11 - MTTC)/10, 0, 1) is 20% of score and MTTC counts
  every turn including clarifications — an unnecessary question that
  doesn't narrow the candidate set is pure cost. Only ask when the expected
  reduction in candidate-pool entropy justifies a turn.
- Hard cap: 10 turns, forced zero score if exceeded — the agent MUST return
  *something* (even a best-guess top-10) well before turn 10 rather than
  keep clarifying.

## Phase 1 results (Aug 26) — 0.562 → 0.744

Three changes, measured one at a time:

1. **Bucket exhaustion bug: 0.562 → 0.728.** Receiving one constraint from
   an attribute marked that whole attribute settled, so a session opening
   with "A key requirement is: Material:alloy" (classified `feature`) never
   asked `feature` again and never learned what identified the product.
   The customer releases at most two constraints per question and withholds
   the rest — one answer does not empty a bucket. Now only an explicit
   refusal settles one. `buying` went 0.563 → 0.887.
2. **Override retraction: 0.728 → 0.744.** An override retracts the ONE
   preference the shopper opened with, not everything learned since. We now
   drop only the first disclosed constraint and keep the rest.
   `intent_override` Hit Rate went 0.733 → 0.833.
3. **Config sweep: no change — the guesses were already optimal**, but they
   are now measured rather than assumed. Results recorded inline in
   `config.py`. Notable: `POOL_SIZE` has no effect anywhere between 300 and
   3000, and `CONFIDENT_MARGIN` above 0.35 changes nothing, meaning the
   agent effectively always asks — the correct policy when questions cost
   nothing.

### Where the remaining loss was

Of the misses at 0.562, **99% had the target still inside the candidate
pool** — 67% at rank 11-50, 32% at rank 51-800, only 1 absent entirely.
Retrieval was close to saturated; ranking was the remaining problem. Phase 2a
acted on that.

## Phase 2a results (Aug 26) — 0.744 → 0.876

Three ranking features, each measured separately and each weight swept
(results recorded inline in `config.py`):

1. **Constraint coverage: 0.744 → 0.790.** The customer quotes constraints
   verbatim from the target's own listing — 97.1% of them appear literally
   in their target's text — so the product satisfying ALL stated
   requirements is almost always the right one. BM25 rewards term frequency
   and cannot express completeness; coverage can.
2. **Popularity prior: 0.790 → 0.859.** Log review-volume. Bigger than
   expected. Every target is an item real users actually bought, so review
   volume is real evidence of purchase likelihood — but this leans on the
   benchmark's 5-core leave-last-out sampling rather than on the catalogue
   itself. The private set is sampled identically, so it should transfer.
   State this in the writeup rather than leaving it implicit.
3. **Category-path match: 0.859 → 0.876.** Matched against the category
   field alone, so a jersey mentioning shorts is not treated as shorts.

Earlier weights were re-swept afterwards, since the features interact.

**Guard against overfitting:** every optimum is a broad plateau, not a spike
(popularity flat 0.75-2.5, category flat 3.0-10.0). Flat optima survive a
distribution shift; sharp ones are usually fitted noise.

### Remaining headroom

197/200 hits, 104 at rank 1 and 93 at ranks 2-10. Perfect ranking would add
about +0.095 (ceiling ~0.97), so MRR is now the entire remaining gap. A
learned ranker targets exactly that — but with 197/200 already hit and only
200 training sessions, the risk of a fitted model failing to transfer now
rivals the upside. Decide on cross-validated evidence, not train-set gain.

## Revised priorities (after the Aug 26 measurements)

The original build order assumed dense retrieval and LLM reranking were
core. The 1.7%-vs-85% finding says otherwise: dialogue extraction carries
the score, and it is already working without either. Reordered by expected
value:

1. **`intent_override` (0.433, weakest scenario, 30 sessions).** Erasure is
   currently coarse — it wipes all descriptive constraints instead of only
   the contradicted ones.
2. **MRR (0.407).** Targets are often retrieved but not ranked first. This
   is the clearest place an LLM reranker earns its cost, and it is 30% of
   the score.
3. **`buying` (0.563)** underperforms `browsing` (0.838), which is
   counter-intuitive since buying sessions disclose a constraint up front.
   Worth tracing.
4. **Constraint parsing coverage.** Marker-based; a paraphrase outside the
   known set yields nothing. A small LLM extraction call is the obvious fix.
5. **Dense retrieval — now optional.** Only worth it if it lifts Hit Rate
   beyond what keyword retrieval already reaches. Measure before building.

Keep the offline path intact: anything added on the LLM side must degrade
gracefully to the current deterministic behaviour, per
`docs/submission_rules.md`.

## Original build order (kept for reference)

1. **Hour 0-4 (before/at hacking start):** stand up embeddings for the
   catalog offline if using dense retrieval (this is compute you can
   precompute once hacking opens, doesn't need conversation logic).
2. **Hour 4-16:** slot-tracking state machine + rule-based intent router +
   filter-track retrieval. Get a non-LLM baseline beating 0.125 HitRate
   first — this is your fallback if the LLM budget runs out.
3. **Hour 16-30:** add dense retrieval track + fusion + LLM/cross-encoder
   rerank. Re-run local evaluator after every change, track Technical Score.
4. **Hour 30-42:** Intent Override + Boundary handling, clarification
   question generation, over-generality cutoff logic.
5. **Hour 42-54:** context distillation (profile-aware ranking), tune
   fusion weights, ablate on the 4 scenario buckets separately (the
   evaluator already reports per-scenario metrics — use that to find your
   weakest scenario type and target it).
6. **Hour 54-64:** freeze the model/logic. Write the offline-fallback
   documentation required by `submission_rules.md` (does your agent need
   live API/network access? what's the degraded mode?).
7. **Hour 64-72:** README, demo video, Devpost writeup, final evaluator run,
   submit early — don't cut it to the wire.

## Submission checklist (from docs/submission_rules.md)

- [x] `agent.py` exporting `class Agent` with `reset()` / `respond()`
      matching the exact contract (`docs/agent_api_contract.json`)
- [x] `requirements.txt` + exact Python version if non-default
- [x] `README.md`: overview, setup, reproduce steps, limitations, team
      contributions *(names still to fill in)*
- [x] One command to run the agent in the official harness
      (`python3 -m evaluator.local_evaluator`)
- [x] Disclosure: model choice, latency, token usage, estimated cost —
      currently **no model, no tokens, no cost**; ~18s for 200 sessions
- [x] Explicitly state whether it needs network access at inference time,
      and describe the offline fallback — **no network needed**, the scored
      path is fully offline and deterministic
- [x] No API keys / secrets committed (`.env` is git-ignored)
- [x] Does not modify evaluator files, no private data, no undeclared
      external services required for scoring
- [ ] Devpost: written description (approach, dev tools, APIs, libraries,
      datasets/assets used)
- [ ] Public GitHub repo link
- [ ] Demo video on YouTube, public, linked in Devpost (a walkthrough of
      API usage / inference examples is fine — no UI required)

## Resources

- Repo: https://github.com/TechJam2026/techjam-conversational-search
  (cloned into `./repo` in this folder)
- Participant kit release (catalog + checksums):
  https://github.com/TechJam2026/techjam-conversational-search/releases/tag/participant-kit
- Amazon Reviews 2023 source docs: https://amazon-reviews-2023.github.io/
- Track 4 workshop: Aug 28, 4:00-4:45pm SGT — check Devpost/registration
  email for the join link
- Devpost: https://tiktoktechjam2026.devpost.com/
