"""
P1 — dialog state machine: slot accumulation, Intent Override, Boundary
handling, and the over-generality clarification trigger.

STUB ONLY — implement during the hacking window (Aug 29+), not before.
"""
from __future__ import annotations

from src.contracts import AttributeName, SessionState


def update_slots(state: SessionState, user_message: str) -> SessionState:
    """Merge new information from `user_message` into `state.slots`.

    Must handle:
      - Incremental accumulation: a new slot value is added, existing ones
        are kept.
      - Intent Override: a contradicting statement (e.g. "actually, forget
        boots, show me sneakers") must ERASE the now-conflicting slots
        rather than merging on top of them.
      - Boundary: "I don't have a preference for X" should add X to
        state.disclosed_attributes WITHOUT setting a slot value, so it is
        never re-asked (see docs/agent_api_contract.json's ask_attribute
        enum for the fixed set of attribute names).
    """
    raise NotImplementedError("P1: implement during the hacking window")


def should_ask_clarifying_question(state: SessionState, candidate_pool_size: int) -> bool:
    """Over-generality trigger.

    True when candidate_pool_size exceeds config.CANDIDATE_POOL_TOO_LARGE
    AND state hasn't already spent config.MAX_CLARIFYING_TURNS turns asking
    — MTTC punishes every wasted turn, and the 10-turn hard cap means the
    agent MUST fall back to returning its best-guess top-10 well before
    turn 10 rather than keep clarifying indefinitely.
    """
    raise NotImplementedError("P1: implement during the hacking window")


def choose_attribute_to_ask(state: SessionState) -> AttributeName:
    """Pick the single most discriminative missing slot to ask about next.

    Must not repeat anything already in state.disclosed_attributes or
    state.asked_attributes. See config.ATTRIBUTE_PRIORITY for a starting
    default order — ideally this becomes pool-size-aware (ask about
    whichever unknown attribute would split the current candidate pool
    the most) rather than a fixed priority list.
    """
    raise NotImplementedError("P1: implement during the hacking window")
