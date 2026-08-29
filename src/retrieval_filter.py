"""
P2 — Route A: structured/attribute-match retrieval ("filter track").

Retrieves a wide keyword pool from everything the shopper has disclosed, then
rescores so products satisfying MORE of their stated constraints float up.

Design note — why rescoring instead of hard filtering:
the catalog has no structured color/material/size/brand fields (confirmed
against the real schema), so a "filter" here is really text matching. A
strict AND across several accumulated slots returns zero rows surprisingly
often, and an empty list is a guaranteed Hit Rate@10 miss for that turn. So
we match broadly (OR) and recover precision by ranking on constraint
satisfaction — relaxation is built into scoring rather than a retry loop.
"""
from __future__ import annotations

import config
from src.catalog import Catalog, normalise, tokenize
from src.contracts import AttributeName, Candidate, Slots


def _matched_attributes(catalog: Catalog, parent_asin: str, slots: Slots) -> list[AttributeName]:
    """Which of the shopper's stated constraints this product verifiably satisfies.

    Only attributes backed by a precomputed catalog signal appear here.
    Everything else (style, use_case, feature...) is unverifiable against
    structured data and is credited through the keyword signal instead — we
    never claim a confirmed match we cannot actually check.
    """
    matched: list[AttributeName] = []

    if slots.material:
        wanted = slots.material.lower()
        have = catalog.material.get(parent_asin) or set()
        if any(wanted in value or value in wanted for value in have):
            matched.append("material")

    if slots.color:
        wanted = slots.color.lower()
        have = catalog.color.get(parent_asin) or set()
        if any(wanted in value or value in wanted for value in have):
            matched.append("color")

    if slots.brand:
        have_brand = catalog.brand.get(parent_asin)
        if have_brand and slots.brand.lower() in have_brand:
            matched.append("brand")

    if slots.budget is not None:
        price = catalog.price.get(parent_asin)
        # Budget is a PROXIMITY target, not a ceiling: the evaluator's
        # customer discloses it as "budget around $X" where X is the target
        # product's own price (see intent_card()), so "<= X" would wrongly
        # reward anything cheap.
        # Products with no price are left UNMATCHED but not penalised
        # elsewhere — only ~21% of the catalog has a price at all, so
        # treating "unknown" as "fails the budget" would silently demote
        # four fifths of the catalog, target included.
        if price is not None and abs(price - slots.budget) <= slots.budget * config.BUDGET_TOLERANCE:
            matched.append("budget")

    return matched


def _constraint_coverage(catalog: Catalog, parent_asin: str, normalised: list[str]) -> float:
    """Fraction of the shopper's disclosed constraints present verbatim in
    this product's text.

    This is the strongest ranking signal available, and it exists because of
    how the constraints are produced: the simulated customer quotes them from
    the target product's own listing, so the target contains all of them
    (97.1% of constraints are literally present in their target's text) while
    a distractor typically matches only one or two.

    Keyword scoring alone cannot express this — BM25 rewards term frequency,
    so a product mentioning "mesh" five times can outrank one that satisfies
    every stated requirement once. Coverage rewards completeness instead.
    """
    if not normalised:
        return 0.0
    text = catalog.norm_text.get(parent_asin, "")
    return sum(1 for phrase in normalised if phrase in text) / len(normalised)


def _category_match(catalog: Catalog, parent_asin: str, category_tokens: list[str]) -> float:
    """Fraction of the shopper's stated category words in this product's own
    category path.

    Matched against the category field alone rather than the whole listing:
    a basketball jersey whose description mentions shorts should not score
    as a shorts match.
    """
    if not category_tokens:
        return 0.0
    path = catalog.norm_categories.get(parent_asin, "")
    return sum(1 for token in category_tokens if f" {token} " in path) / len(category_tokens)


def _query_terms(slots: Slots, disclosed_text: list[str] | None) -> list[str]:
    """Keyword terms from every populated text slot plus raw disclosed text.

    `disclosed_text` matters more than the parsed slots: the constraints the
    simulated customer reveals are drawn verbatim from the target product's
    own features/details, so feeding that text back as keywords is the
    single strongest retrieval signal available.
    """
    terms: list[str] = []
    for name, value in slots.as_dict().items():
        if name == "budget":
            continue  # numeric, matched by proximity not keywords
        terms.extend(tokenize(str(value)))
    for text in disclosed_text or []:
        terms.extend(tokenize(text))
    return terms


def retrieve(
    catalog: Catalog,
    slots: Slots,
    disclosed_text: list[str] | None = None,
    extra_terms: list[str] | None = None,
    top_k: int = 50,
    intent: str | None = None,
) -> list[Candidate]:
    """Return up to `top_k` candidates ranked by constraint satisfaction.

    Args:
        catalog: the shared in-memory index.
        slots: accumulated structured constraints from the dialog.
        disclosed_text: raw constraint strings the shopper has revealed.
        extra_terms: free text (e.g. the raw current message) used ONLY when
            nothing could be parsed from the dialogue, so a turn never
            returns an empty list. Tokenised here, so callers may pass whole
            sentences safely.
        top_k: how many candidates to return.
        intent: "buying" or "browsing" (or None). Nudges how hard coverage
            and category agreement are trusted -- see
            config.INTENT_COVERAGE_MULTIPLIER / INTENT_CATEGORY_MULTIPLIER.
            A weighting adjustment only, never a hard gate: an unrecognised
            or missing intent falls back to a neutral 1.0 multiplier, i.e.
            today's behaviour.
    """
    terms = _query_terms(slots, disclosed_text)
    if not terms and extra_terms:
        # LAST-RESORT fallback only, when nothing could be parsed from the
        # message. Used unconditionally it measurably hurts: filler words
        # ("still exploring") widen the pool and blur the ranking, costing
        # MRR for no gain (0.8759 -> 0.8743). Used as a fallback it costs
        # nothing and stops a turn returning an empty list.
        #
        # Tokenised, never passed through raw: an untokenised sentence
        # becomes a single FTS phrase that matches nothing, and one
        # containing a double quote makes the whole query malformed, which
        # the error handler turns into zero candidates for that turn.
        for text in extra_terms:
            terms.extend(tokenize(str(text)))
    pool = catalog.search(terms, limit=config.POOL_SIZE)
    if not pool:
        return []

    # Normalise BM25 (negative, best-first) into 0..1 so it can be combined
    # with the match count on a comparable scale.
    best = pool[0][1]
    worst = pool[-1][1]
    span = (worst - best) or 1.0

    # Normalise the disclosed phrases once, not per candidate.
    normalised = [normalise(text).strip() for text in (disclosed_text or [])]
    normalised = [phrase for phrase in normalised if phrase]
    category_tokens = tokenize(slots.category) if slots.category else []

    # Intent nudges how hard we trust coverage/category agreement -- see
    # config.py for the measured multipliers and the ablation that set them.
    # .get(intent, 1.0) means an unknown or missing intent is a no-op.
    coverage_weight = config.COVERAGE_WEIGHT * config.INTENT_COVERAGE_MULTIPLIER.get(intent, 1.0)
    category_weight = config.CATEGORY_WEIGHT * config.INTENT_CATEGORY_MULTIPLIER.get(intent, 1.0)

    candidates: list[Candidate] = []
    for parent_asin, bm25_score in pool:
        matched = _matched_attributes(catalog, parent_asin, slots)
        keyword_strength = 1.0 - ((bm25_score - best) / span)
        coverage = _constraint_coverage(catalog, parent_asin, normalised)
        # Flat bonus per verified match on top of the keyword signal.
        # Deliberately NOT scaled by how many slots are filled: an earlier
        # version scaled the keyword term by the filled-slot count, which
        # perversely shrank the weight of verified matches exactly when we
        # knew most about the shopper.
        score = (
            keyword_strength
            + config.VERIFIED_MATCH_BONUS * len(matched)
            + coverage_weight * coverage
            + config.POPULARITY_WEIGHT * catalog.popularity.get(parent_asin, 0.0)
            + category_weight * _category_match(catalog, parent_asin, category_tokens)
        )
        candidates.append(Candidate(
            parent_asin=parent_asin,
            score=score,
            source="filter",
            matched_attributes=matched,
        ))

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[:top_k]
