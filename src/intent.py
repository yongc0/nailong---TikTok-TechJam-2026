"""
P1 — Buying vs Browsing intent router.

STUB ONLY — implement during the hacking window (Aug 29+), not before.

Per PLAN.md: cheap first pass is a rule/keyword classifier (price mentions,
size/color/brand nouns, imperative "buy/need" verbs -> buying; vague
adjectives, "browsing/looking around" -> browsing). Optionally back it with
a Groq call (see config.GROQ_MODEL) for ambiguous cases only, to protect the
free-tier request budget. This decides retrieval strategy WEIGHTING, not a
hard gate — see PLAN.md system #1.
"""
from __future__ import annotations

from src.contracts import Intent


def classify_intent(user_message: str, prior_intent: Intent | None) -> Intent:
    """Return "buying" or "browsing" for this turn's message.

    Args:
        user_message: the raw text for this turn.
        prior_intent: the session's intent as of the previous turn (None on
            turn 1). Compare against this to help detect an Intent Override.
    """
    raise NotImplementedError("P1: implement during the hacking window")
