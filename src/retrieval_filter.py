"""
P2 — Route A: structured/attribute-match retrieval ("filter track").

STUB ONLY — implement during the hacking window (Aug 29+), not before.

High-precision retrieval for the Buying intent: hard-filter the catalog on
whatever slots are populated (category, material, color, size, style,
brand, budget/price) — see PLAN.md system #2, Route A.
"""
from __future__ import annotations

from src.contracts import Candidate, Slots


def retrieve(slots: Slots, top_k: int = 50) -> list[Candidate]:
    """Return candidates matching as many populated slots as possible,
    most-constrained-first.

    Should degrade gracefully: if filtering on every populated slot returns
    zero results, relax the least-important constraint(s) rather than
    returning an empty list — an empty list here guarantees a miss on
    Hit Rate@10 for this turn.
    """
    raise NotImplementedError("P2: implement during the hacking window")
