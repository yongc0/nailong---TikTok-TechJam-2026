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

## What's already done (this session, Aug 26)

- Cloned `techjam-conversational-search` repo into this folder (`./repo`)
- Downloaded `catalog.jsonl.gz` from the participant-kit release, verified
  SHA256 against `SHA256SUMS`, decompressed to `data/catalog.jsonl` (50,000
  rows confirmed)
- Ran the local evaluator end-to-end on a 10-sample slice — pipeline works.
  Full 200-sample public set takes ~45-60s locally (build FTS index + run
  200 simulated sessions); run it yourself with:
  ```
  cd repo
  python3 -m evaluator.local_evaluator
  ```
  (writes `results.json`, prints the summary)
- Baseline (weak BM25 starter) reference score: HitRate@10 0.125, MRR 0.068,
  MTTC 9.81, TechnicalScore 0.107 — this is the floor to beat.

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

## Suggested build order (fits a 72h sprint)

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

- [ ] `agent.py` exporting `class Agent` with `reset()` / `respond()`
      matching the exact contract (`docs/agent_api_contract.json`)
- [ ] `requirements.txt` + exact Python version if non-default
- [ ] `README.md`: overview, setup, reproduce steps, limitations, team
      contributions
- [ ] One command to run the agent in the official harness
- [ ] Disclosure: model choice, latency, token usage, estimated cost
- [ ] Explicitly state whether it needs network access at inference time,
      and describe the offline fallback if organizer disables network for
      official scoring
- [ ] No API keys / secrets committed
- [ ] Does not modify evaluator files, no private data, no undeclared
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
