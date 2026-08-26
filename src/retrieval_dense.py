"""
P3 — Route B: dense/embedding retrieval ("diverse track") for the Browsing
intent — cross-category, vague-query matching.

STUB ONLY — implement during the hacking window (Aug 29+), not before.

Per PLAN.md system #2, Route B: embedding similarity over
title+features+description, computed and kept fully in-memory (no external
vector DB, per the competition's out-of-scope constraint). Catalog
embeddings should be precomputed once (this is compute you can do the
moment the catalog is available — doesn't depend on any conversation
logic, so it's fair prep work before Aug 29 per PLAN.md's own build order).
"""
from __future__ import annotations

from src.contracts import Candidate, SessionState


def retrieve(state: SessionState, top_k: int = 50) -> list[Candidate]:
    """Embedding similarity search over the catalog given the session's
    accumulated context (slots + recent history), see config.EMBEDDING_MODEL
    and config.DENSE_TOP_K.
    """
    raise NotImplementedError("P3: implement during the hacking window")
