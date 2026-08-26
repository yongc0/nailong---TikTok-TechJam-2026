"""
Shared data shapes between pipeline modules.

SCAFFOLDING ONLY — no business logic lives here. This exists so all 4 people
can build state.py, intent.py, retrieval_filter.py, retrieval_dense.py,
fusion_rerank.py, and personalization.py in parallel against a stable
interface, per TEAM_WORKFLOW.md's file layout.

Field names deliberately mirror docs/agent_api_contract.json's `ask_attribute`
enum and `user_profile` shape, so nothing here should require translation at
the agent.py boundary.

NOTE: per TEAM_WORKFLOW.md §2, this is a *proposal* to react to on the
pre-hacking group call, not a locked spec. Change freely before Aug 29.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

AttributeName = Literal[
    "category", "material", "color", "size", "style",
    "brand", "budget", "feature", "use_case", "other",
]

Intent = Literal["buying", "browsing"]


@dataclass
class Slots:
    """Accumulated structured constraints extracted from the dialog so far.

    Owned/mutated by state.py (P1). Read by retrieval_filter.py (P2),
    retrieval_dense.py (P3), and personalization.py (P4).
    """

    category: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    style: Optional[str] = None
    brand: Optional[str] = None
    budget: Optional[float] = None
    feature: Optional[str] = None
    use_case: Optional[str] = None
    other: Optional[str] = None

    def as_dict(self) -> dict:
        """Only the slots that have actually been filled in."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class SessionState:
    """One shopper's session, threaded through every turn. Owned by state.py (P1)."""

    session_id: str
    turn: int
    intent: Intent
    slots: Slots

    # Attributes the user has explicitly answered or explicitly declined
    # ("Boundary" case) — never re-ask something already in here.
    disclosed_attributes: set[AttributeName] = field(default_factory=set)

    # Attributes we've asked about, whether or not they got an answer —
    # used together with disclosed_attributes to avoid repeat questions.
    asked_attributes: set[AttributeName] = field(default_factory=set)

    # parent_asins already shown and rejected/ignored by the user.
    rejected_candidates: set[str] = field(default_factory=set)

    # Raw turn-by-turn log (role, message) for LLM prompt context in
    # fusion_rerank.py's reranking step.
    history: list[dict] = field(default_factory=list)


@dataclass
class Candidate:
    """One retrieved product, pre- or post-fusion. `parent_asin` is the join
    key against catalog.jsonl. Produced by retrieval_filter.py /
    retrieval_dense.py, consumed by fusion_rerank.py / personalization.py.
    """

    parent_asin: str
    score: float
    source: Literal["filter", "dense"]
    matched_attributes: list[AttributeName] = field(default_factory=list)


@dataclass
class RankedList:
    """Output of fusion_rerank.py; input+output of personalization.py."""

    candidates: list[Candidate]

    def top(self, k: int = 10) -> list[Candidate]:
        return self.candidates[:k]
