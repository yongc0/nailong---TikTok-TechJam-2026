"""
P3 — fuse Route A (filter) + Route B (dense) candidates, then LLM rerank.

STUB ONLY — implement during the hacking window (Aug 29+), not before.
"""
from __future__ import annotations

from src.contracts import Candidate, RankedList, SessionState


def fuse(filter_candidates: list[Candidate], dense_candidates: list[Candidate]) -> list[Candidate]:
    """Combine both retrieval routes — RRF or weighted sum, see
    config.FUSION_METHOD / config.FILTER_ROUTE_WEIGHT / config.DENSE_ROUTE_WEIGHT.
    Dedup on parent_asin, keeping the higher-confidence source's match info.
    """
    raise NotImplementedError("P3: implement during the hacking window")


def rerank(candidates: list[Candidate], state: SessionState) -> RankedList:
    """LLM semantic rerank of the top config.RERANK_CANDIDATE_POOL fused
    candidates using the full dialog history in `state`.

    This is what drives MRR (30% of TechnicalScore) — the goal is pushing
    the true target product as close to rank 1 as possible, not just
    getting it into the top 10.

    Use config.GROQ_MODEL with config.RERANK_REASONING_EFFORT and
    config.RERANK_MAX_COMPLETION_TOKENS. Reminder confirmed empirically on
    this model: gpt-oss's reasoning trace consumes completion tokens before
    the final answer — 200+ tokens minimum or you get an empty response.
    """
    raise NotImplementedError("P3: implement during the hacking window")
