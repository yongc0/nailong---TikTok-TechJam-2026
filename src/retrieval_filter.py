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
from src.catalog import Catalog, tokenize
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
) -> list[Candidate]:
    """Return up to `top_k` candidates ranked by constraint satisfaction.

    Args:
        catalog: the shared in-memory index.
        slots: accumulated structured constraints from the dialog.
        disclosed_text: raw constraint strings the shopper has revealed.
        extra_terms: extra keywords (e.g. tokens from the current message),
            used to widen the pool on turn 1 when little is known.
        top_k: how many candidates to return.
    """
    terms = _query_terms(slots, disclosed_text)
    if extra_terms:
        terms.extend(extra_terms)
    pool = catalog.search(terms, limit=config.POOL_SIZE)
    if not pool:
        return []

    # Normalise BM25 (negative, best-first) into 0..1 so it can be combined
    # with the match count on a comparable scale.
    best = pool[0][1]
    worst = pool[-1][1]
    span = (worst - best) or 1.0

    candidates: list[Candidate] = []
    for parent_asin, bm25_score in pool:
        matched = _matched_attributes(catalog, parent_asin, slots)
        keyword_strength = 1.0 - ((bm25_score - best) / span)
        # Flat bonus per verified match on top of the keyword signal.
        # Deliberately NOT scaled by how many slots are filled: an earlier
        # version scaled the keyword term by the filled-slot count, which
        # perversely shrank the weight of verified matches exactly when we
        # knew most about the shopper.
        score = keyword_strength + config.VERIFIED_MATCH_BONUS * len(matched)
        candidates.append(Candidate(
            parent_asin=parent_asin,
            score=score,
            source="filter",
            matched_attributes=matched,
        ))

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[:top_k]
