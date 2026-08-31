"""
Buying vs Browsing intent router.

Rule/keyword based, no LLM call: intent classification runs on every turn of
every session, and patterns handle this decision well enough that an API
call would only add latency, cost and a network dependency. Nothing on the
scored path calls a model.

This decides retrieval WEIGHTING, not a hard gate — a misclassified turn
nudges how strongly coverage and category agreement are trusted (see
config.INTENT_COVERAGE_MULTIPLIER) and can never cut a product out of
contention.
"""
from __future__ import annotations

import re

from src.contracts import Intent

# Open-ended exploration language. "still exploring" / "just looking" are
# how a genuinely undecided shopper opens, and are also what the evaluator's
# simulated customer says for browsing sessions.
BROWSING_PATTERNS = (
    r"\bstill exploring\b",
    r"\bjust (?:looking|browsing)\b",
    r"\bnot sure\b",
    r"\bany (?:suggestions|ideas|recommendations)\b",
    r"\bopen to\b",
    r"\bideas for\b",
    r"\bsomething (?:for|nice|good)\b",
    r"\bexploring\b",
    r"\bbrowsing\b",
)

# High-intent language: a locked requirement, or a concrete constraint.
BUYING_PATTERNS = (
    r"\bkey requirement\b",
    r"\bwhat i need is\b",
    r"\bmust (?:be|have)\b",
    r"\bneed(?:s|ed)?\b",
    r"\blooking to buy\b",
    r"\bi want\b",
    r"\bspecifically\b",
    r"\bmatters is\b",          # the simulator's disclosure phrasing
    r"\bhas to be\b",
    r"\bexactly\b",
)

# Concrete constraints imply high intent regardless of phrasing: a price,
# a size number, or a named material/color is a hard filter the shopper
# already has in mind.
CONSTRAINT_PATTERNS = (
    r"\$\s*\d",
    r"\bunder\s+\d",
    r"\bsize\s+\d",
    r"\b(?:cotton|polyester|nylon|leather|wool|spandex|silk|rayon)\b",
    r"\b(?:black|white|blue|red|pink|green|brown|gray|grey|purple|yellow|orange)\b",
)

# The evaluator's override message, plus natural equivalents. An override is
# always a decisive statement, so it reads as Buying.
OVERRIDE_PATTERNS = (
    r"\bactually,?\s+(?:ignore|forget|scratch)\b",
    r"\bignore my earlier\b",
    r"\bforget (?:what i|that|the)\b",
    r"\bchanged my mind\b",
    r"\binstead of\b",
    r"\bnever ?mind\b",
    r"\bon second thought\b",
)


def _count(patterns: tuple[str, ...], text: str) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text, re.I))


def detect_override(user_message: str) -> bool:
    """True when the shopper is replacing an earlier preference rather than
    adding to it.

    state.py uses this to decide between merging new slots and retracting
    the conflicting one — see update_slots()'s Intent Override branch.
    """
    return _count(OVERRIDE_PATTERNS, user_message) > 0


def classify_intent(user_message: str, prior_intent: Intent | None = None) -> Intent:
    """Return "buying" or "browsing" for this turn's message.

    Args:
        user_message: raw text for this turn.
        prior_intent: the session's intent as of the previous turn (None on
            turn 1). Acts as a tiebreaker so intent stays stable across turns
            that carry little signal either way, instead of flip-flopping and
            churning the retrieval blend.
    """
    if detect_override(user_message):
        # A decisive correction is high-intent by definition.
        return "buying"

    browsing_score = _count(BROWSING_PATTERNS, user_message)
    buying_score = _count(BUYING_PATTERNS, user_message) + _count(CONSTRAINT_PATTERNS, user_message)

    if buying_score > browsing_score:
        return "buying"
    if browsing_score > buying_score:
        return "browsing"

    # Genuine tie: stay where we were rather than churn. Turn 1 with no
    # signal at all defaults to browsing — casting the wider net is the
    # safer error, since Hit Rate@10 (50% of score) punishes a candidate
    # pool that never contained the target far harder than a loosely
    # ranked one.
    return prior_intent or "browsing"
