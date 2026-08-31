"""
Long-term profile signal — personalised context, applied as a tie-break.

The `user_profile` handed to `reset()` is the only long-term signal in the
system: it describes what this shopper has cared about across PRIOR
purchases, independent of anything said in this conversation.

Kept deliberately separate from the session's own slots. Short-term
constraints are volatile — an Intent Override retracts them mid-dialogue —
whereas the profile is not invalidated by the shopper changing their mind
about this particular product. Someone whose history emphasises fit and
durability still cares about fit and durability after they switch from boots
to sneakers. Mixing the two would let an override corrupt the long-term
prior, so the boost is applied after ranking rather than folded into the
retrieval slots.

Applied as a SOFT re-ranking prior, never a filter: `preference_tags` are
coarse ("fit", "comfort", "style") and would eliminate valid candidates if
treated as requirements.
"""
from __future__ import annotations

import config
from src.catalog import Catalog, normalise
from src.contracts import RankedList


def profile_affinity(catalog: Catalog, parent_asin: str, tags: list[str]) -> float:
    """Fraction of the shopper's long-term preference tags this product mentions."""
    if not tags:
        return 0.0
    text = catalog.norm_text.get(parent_asin, "")
    return sum(1 for tag in tags if tag in text) / len(tags)


def apply_profile_boost(
    ranked: RankedList,
    user_profile: dict,
    catalog: Catalog,
) -> RankedList:
    """Nudge the ranking toward products matching the shopper's prior interests.

    Returns the list re-sorted in place. A disabled flag (or an empty
    profile) is a no-op, so the caller never needs to branch.
    """
    if not config.PROFILE_TIE_BREAK:
        return ranked

    tags = [
        normalise(str(tag)).strip()
        for tag in (user_profile.get("preference_tags") or [])
    ]
    tags = [tag for tag in tags if tag]
    if not tags:
        return ranked

    # Tie-break only, never additive.
    #
    # Measured: preference_tags match the target 1.72x more often than a
    # random catalogue product, which looks like real signal — but against
    # the candidates actually competing in our pool the lift collapses to
    # 1.12x. Almost all of the apparent value is the tags proxying for
    # category relevance, which constraint coverage and category matching
    # already capture far better. Added into the score it therefore dilutes
    # a strong signal with a weak one, and every non-zero additive weight
    # measured WORSE (0.8757 -> 0.8746 at 0.05, -> 0.8399 at 1.0).
    #
    # So the profile is consulted only where the session evidence is
    # genuinely indifferent: candidates are re-sorted by score first and
    # affinity second, which reorders exact ties and nothing else.
    quantum = config.PROFILE_TIE_QUANTUM
    ranked.candidates.sort(
        key=lambda item: (
            round(item.score / quantum) if quantum else item.score,
            profile_affinity(catalog, item.parent_asin, tags),
        ),
        reverse=True,
    )
    return ranked
