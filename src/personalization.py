"""
P4 — long-term profile-aware ranking boost (Pillar III: personalized
context distillation) + agent.py integration glue.

STUB ONLY — implement during the hacking window (Aug 29+), not before.
"""
from __future__ import annotations

from src.contracts import RankedList, SessionState


def apply_profile_boost(ranked: RankedList, state: SessionState, user_profile: dict) -> RankedList:
    """Nudge the ranked list using user_profile["preference_tags"] as a
    SOFT prior (never a hard filter) — see config.PROFILE_BOOST_WEIGHT.

    Per PLAN.md system #4: keep this session's short-term slots (state)
    separate from the long-term profile signal (user_profile), so an
    Intent Override wiping slots doesn't also corrupt the profile-level
    bias — e.g. someone who always buys durable, comfortable items is
    still probably style-conscious even after they switch from boots to
    sneakers mid-conversation.
    """
    raise NotImplementedError("P4: implement during the hacking window")
