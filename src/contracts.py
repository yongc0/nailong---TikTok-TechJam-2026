"""
Shared data shapes passed between the pipeline modules.

No business logic lives here — these are the structures state.py,
retrieval_filter.py and personalization.py hand to each other.

Field names deliberately mirror docs/agent_api_contract.json's `ask_attribute`
enum and `user_profile` shape, so nothing here needs translation at the
agent.py boundary.
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

    Written by state.py; read by retrieval_filter.py.
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

    # Raw constraint strings the shopper has revealed, verbatim.
    # This is the single strongest retrieval signal we have: measured on the
    # public set, retrieving on category alone puts the target in top-10 for
    # 1.7% of sessions, while retrieving on the full disclosed text reaches
    # 85%. Kept as raw text rather than only parsed slots because the
    # wording itself is drawn from the target product's own listing.
    disclosed_text: list[str] = field(default_factory=list)

    # Turn-by-turn transcript of what the shopper said. Retained for
    # debugging and for showing a full session in the demo; the scored
    # path does not read it back.
    history: list[dict] = field(default_factory=list)


@dataclass
class Candidate:
    """One retrieved product. `parent_asin` is the join key against
    catalog.jsonl. Produced by retrieval_filter.py, consumed by
    personalization.py and agent.py.
    """

    parent_asin: str
    score: float
    source: Literal["filter"] = "filter"
    matched_attributes: list[AttributeName] = field(default_factory=list)


@dataclass
class RankedList:
    """A ranked shortlist: input and output of personalization.py."""

    candidates: list[Candidate]

    def top(self, k: int = 10) -> list[Candidate]:
        return self.candidates[:k]
