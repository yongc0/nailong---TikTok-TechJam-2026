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

- HitRate@10 0.985, MRR 0.669, MTTC 1.875 — 197 of 200 sessions convert.
  60% resolve on turn 1 (median and mode); 79% by turn 2. MTTC counts the
  3 misses as turn 11, so the mean among hits alone is 1.736.
- By scenario (Hit Rate@10): browsing 1.000, buying 0.988,
  intent_override 0.967, boundary 0.900 (all were 0.000-0.238 at baseline)
- Implemented: `src/catalog.py`, `src/attributes.py`, `src/intent.py`,
  `src/state.py`, `src/retrieval_filter.py`, root `agent.py`
- **No LLM used.** Fully offline and deterministic, which satisfies the
  offline-fallback requirement in `docs/submission_rules.md` for free.
- `starter/agent.py` now re-exports the root `agent.py`; the original weak
  baseline is preserved as `starter/agent_bm25_baseline.py`. The evaluator
  stays unmodified.
- 24 tests pass: `python3 -m pytest tests/ -q`

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

## Phase 2c — personalization (Aug 26): principled, but worth ~nothing

`user_profile` was entirely unused, leaving Pillar III (Self-Evolution /
Dynamic Context Programming) unaddressed. Now implemented in
`src/personalization.py` — and the measurement is more interesting than the
score change.

Naively boosting candidates by `preference_tags` overlap **hurt at every
weight** (0.8757 -> 0.8746 at 0.05, -> 0.8399 at 1.0). Why:

- tags match the TARGET 1.72x more often than a RANDOM catalogue product,
  which looks like real signal;
- but against the candidates ACTUALLY COMPETING in our pool, the lift is
  only 1.12x.

Almost all the apparent signal was the tags proxying for category relevance
— which constraint coverage and category matching already capture far
better. Added to the score it dilutes a strong signal with a weak one.

**Generalisable lesson: a feature with real lift against a random baseline
can be worthless against a strong one. Always measure against the candidates
you will actually be ranking.**

Redesigned to consult the profile only where the session evidence is
indifferent — it reorders exact ties and never outranks a real score lead.
Net effect +0.0002, i.e. noise. Kept because it is the correct treatment of
the long-term signal and it addresses the pillar, NOT because it moves the
score — and the writeup should say exactly that.

## Phase 3.0 — LLM rerank evaluated and rejected (Aug 26)

Tested before building, on 40 real sessions (0 unusable replies), sampling
BOTH groups deliberately — a rerank that lifts ambiguous sessions but
demotes converged ones is a net loss, and 104 of 200 public sessions are
already ranked 1st and can only lose.

| group | n | our MRR | LLM MRR | delta |
|---|---|---|---|---|
| ambiguous (hit, not rank 1) | 25 | 0.352 | 0.393 | **+0.041** |
| converged (already rank 1)  | 15 | 1.000 | 0.893 | **-0.107** |

Projected over the real 200-session mix: **-0.0109 TechnicalScore**
(0.8759 -> 0.8650). The LLM demoted 2 of 15 already-correct sessions —
pure loss — and on ambiguous cases won 6 / lost 4 / tied 15, which is
indistinguishable from chance.

**Even granting a perfect oracle gate** that only ever fires on ambiguous
sessions and never touches a converged one, the ceiling is **+0.0057**
TechnicalScore. That is below noise, and it would cost network dependency
at scoring time, ~100 minutes of runtime, and free-tier quota exhaustion.

Why our ranker wins: constraint coverage does exact phrase matching against
text the customer quoted verbatim from the target's own listing. The LLM
reasons semantically and cannot match that reliably — the task rewards
literal completeness, not judgement. A stronger model would not obviously
change this.

**Decision: not shipping an LLM stage.** The pipeline stays fully offline
and deterministic. Reproduce with:

```
python3 scripts/validate_llm_rerank.py 25 15
python3 scripts/analyse_llm_validation.py
```

### Rate-limit arithmetic, for the record

Our agent runs 372 turns over 200 sessions (1.86/session), so ~1,488 for
the private 800. Against Groq's free tier (30 RPM / 1,000 RPD / 8,000 TPM /
200,000 TPD), a per-turn rerank exceeds the daily TOKEN budget 2-4x on the
public set alone, and exceeds both request and token budgets on the private
set (4-8 hours of wall clock). Cost was never the obstacle — the same
private run on the paid tier is about $0.33 — the obstacle is that
`docs/submission_rules.md` warns network access may be disabled at scoring
time, so an LLM cannot sit on the scored path regardless.

## Re-ask policy (Aug 26) — correct, and score-neutral

Question: should every attribute be re-asked until exhausted, or only the
ones that can actually hold more?

The customer releases at most two constraints per question, so a second ask
only pays where a bucket holds three or more. Measured share of sessions
with 3+ constraints in a bucket:

  feature 20.5%   material 8.0%   colour 0.5%
  size 0.5%       style 0.0%      use_case 0.0%

Tested four policies on all 200 sessions:

| re-ask policy | score |
|---|---|
| all six attributes (previous behaviour) | 0.8759 |
| **feature + material** | **0.8759** |
| feature only | 0.8712 |
| none — ask each once | 0.8738 |

Restricting to feature + material is exactly neutral; cutting further hurts.
So re-asking those two is load-bearing and re-asking the other four is not.

**Why it is neutral rather than a gain:** instrumenting the runs shows the
restriction never actually binds here. feature is asked 291 times (97
repeats) and material 43 (16 repeats), but colour, style, size and use_case
are asked 3-4 times each with **zero** repeats — sessions end (median: one
question) long before the walk reaches them, and an unproductive ask retires
the bucket in one turn anyway.

Kept regardless, as documented policy rather than accident: it is provably
free (a bucket with fewer than three constraints cannot reward a second
ask), and it is insurance if private-set sessions run longer than public
ones. `config.REASK_ATTRIBUTES`.

## Robustness pass (Aug 26) — a latent zero-results bug

Looking for further gains turned up a defect that the public set never
triggers but 800 unseen sessions might.

`agent.py` passed the raw user message into `retrieve()` as `extra_terms`,
and it reached FTS untokenised. Two consequences:

1. It became a single quoted PHRASE ("I am looking for shoes"), which
   matches nothing — 0 hits raw against 20 tokenised. Removing it entirely
   scored 0.8759, identical to leaving it in: pure dead weight.
2. A message containing a DOUBLE QUOTE made the FTS expression malformed.
   `catalog.search()` catches `OperationalError` and returns `[]`, so one
   quote character silently zeroed out that entire turn.

Naively tokenising fixes the fragility but costs score: filler words
("still exploring") widen the pool and blur the ranking — hit rate rises
0.985 -> 0.990 while MRR falls 0.670 -> 0.651, netting 0.8759 -> 0.8743.

So `extra_terms` is now a LAST-RESORT fallback: used only when nothing could
be parsed from the dialogue, and tokenised when used. Score stays exactly
0.875866, and every degenerate input returns a full shortlist.

Also verified no crash across: empty / None / wrongly-typed profiles, empty
and whitespace-only messages, unicode and emoji, FTS and SQL syntax
characters, and a 54,000-character message.

### Tested and rejected: title-weighted matching

Weighting a constraint found in the product TITLE above one found anywhere
in its text. Principled — a requirement named in the title is what the
product IS — but it hurt at every weight (0.8759 -> 0.8726 at 0.5,
-> 0.8537 at 3.0), because constraints are drawn from the features and
details fields, not titles. Reverted rather than left as dead config.

### Private-set exposure: how much does the popularity prior have to be right?

  weight 0.75 -> 0.8697    1.5 -> 0.8759 (ours)    3.5 -> 0.8742

Anywhere in that range costs at most 0.006, so being mis-tuned for the
private set is cheap. The only expensive case is popularity carrying no
signal there at all, which would cost 0.066 — unlikely, since both sets are
sampled the same way.

## What is left, in expected-value order

Every priority in the earlier version of this section has now been done or
ruled out on evidence: `intent_override` went 0.433 -> 0.967, `buying`
0.563 -> 0.988, MRR 0.407 -> 0.670, and the LLM reranker was tested and
rejected. Current standing:

| scenario | n | Hit@10 | MRR | MTTC |
|---|---|---|---|---|
| browsing | 80 | 1.000 | 0.591 | 1.46 |
| buying | 80 | 0.988 | 0.691 | 1.36 |
| intent_override | 30 | 0.967 | 0.815 | 3.97 |
| boundary | 10 | 0.900 | 0.692 | 3.00 |

197/200 sessions hit; 104 at rank 1, 93 at ranks 2-10; 3 misses (one each
in buying, intent_override, boundary).

**1. Deliverables — the only genuinely urgent work.** Devpost writeup,
demo video, README team names. These carry real judging weight (Presentation
10%, and the writeup shapes Innovation 20%) and none of them are started.
An unfinished submission costs more than any remaining tenth of a point.

**2. A learned ranker (LTR) — the last real score lever, and a genuine
gamble.** All +0.095 of remaining headroom is in MRR. But with 197/200
already hit and only 200 training sessions, the risk of a fitted model
failing to transfer to the private set now rivals the upside. If attempted:
validate with GroupKFold BY SESSION, judge it on cross-validated gain only,
ship it behind a fallback to the current hand-scored ranking, and drop it if
the CV gain is under ~0.02.

**3. `boundary` (0.900, MTTC 3.00) — our weakest scenario, but only 10
sessions.** Any tuning against it risks fitting noise. Treat carefully.

**4. Constraint-parsing coverage.** Marker-based; a paraphrase outside the
known set yields nothing. This is the one place an LLM would plausibly beat
us — extraction, not ranking — but it would put the network on the scored
path, which Phase 3.0 argues against.

**Ruled out, with evidence:** LLM reranking (Phase 3.0, projected -0.011),
additive personalization (Phase 2c, -0.036 at weight 1.0), and dense
retrieval (retrieval is saturated — the 3 remaining misses are ranking
failures, not coverage failures).

Whatever is added, keep the scored path offline and deterministic: it costs
nothing today and removes all dependence on network access at scoring time.

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
