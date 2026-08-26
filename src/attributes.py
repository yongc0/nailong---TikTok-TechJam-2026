"""
Shared vocabulary + extraction helpers for mapping catalog text onto the
fixed attribute vocabulary the evaluator's simulated customer uses.

This intentionally MIRRORS evaluator/local_evaluator.py's MATERIALS,
MATERIAL_RE, COLOR_RE, searchable_text(), and classify_constraint() — not
an approximation of them, the same vocabulary and logic. The reason: our
retrieval/clarification code needs to detect the same attributes the
simulated customer will actually reveal. If our vocabulary diverges (e.g.
we detect "beige" as a color but the simulator's COLOR_RE doesn't), we'll
filter on signals the simulator never sends, and miss the ones it does.

Do NOT edit evaluator/local_evaluator.py to "fix" this instead — per
PLAN.md's submission checklist, evaluator files must not be modified. This
module is our own hand-kept mirror; if the evaluator's vocabulary ever
changes, update both.
"""
from __future__ import annotations

import re
from typing import Optional

from src.contracts import AttributeName

# Mirrors evaluator/local_evaluator.py exactly (MATERIALS / MATERIAL_RE / COLOR_RE).
MATERIALS = ("cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon", "fabric")
COLORS = ("black", "white", "blue", "red", "pink", "green", "brown", "gray", "grey", "purple", "yellow", "orange")

MATERIAL_RE = re.compile(r"\b(" + "|".join(MATERIALS) + r")\b", re.I)
COLOR_RE = re.compile(r"\b(" + "|".join(COLORS) + r")\b", re.I)

# Mirrors evaluator/local_evaluator.py's SEARCH_FIELDS exactly — the real
# catalog schema confirmed locally: parent_asin, title, features (list),
# description (list), price, categories (list), details (dict),
# average_rating, rating_number, store. No dedicated color/material/size/
# brand fields exist — everything below extracts from free text.
SEARCH_FIELDS = ("title", "features", "details", "description", "categories", "store")


def searchable_text(product: dict) -> str:
    """Flatten a catalog record's text fields into one searchable string.
    Mirrors evaluator/local_evaluator.py's searchable_text()."""
    parts: list[str] = []
    for field in SEARCH_FIELDS:
        value = product.get(field)
        if isinstance(value, dict):
            parts.extend(f"{key} {item}" for key, item in value.items())
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).strip()


def extract_material(product: dict) -> Optional[str]:
    match = MATERIAL_RE.search(searchable_text(product))
    return match.group(1).lower() if match else None


def extract_color(product: dict) -> Optional[str]:
    match = COLOR_RE.search(searchable_text(product))
    return match.group(1).lower() if match else None


def classify_constraint(value: str) -> AttributeName:
    """Given a free-text constraint string (e.g. "leather", "under $60"),
    return which attribute bucket the evaluator's simulated customer would
    file it under.

    Mirrors evaluator/local_evaluator.py's classify_constraint() EXACTLY,
    including its real gaps — this is deliberate, not an oversight:
      - Nothing ever classifies as "brand" (no branch checks for it).
      - "category" never appears here either, since the evaluator always
        discloses category for free in turn 1 (see initial_message()).
    Both facts matter for choose_attribute_to_ask() in state.py: asking
    about "brand" or "category" is very likely a wasted turn against MTTC,
    because the simulator has no mechanism to reward either question with
    new information.
    """
    lowered = value.lower()
    if "budget" in lowered or re.search(r"(?:\$|<=|under)\s*\d", lowered):
        return "budget"
    if any(material in lowered for material in MATERIALS):
        return "material"
    if any(word in lowered for word in ("color", "black", "white", "blue", "red", "pink", "green")):
        return "color"
    if any(word in lowered for word in ("size", "sizing", "width", "wide", "narrow")):
        return "size"
    if any(word in lowered for word in ("department", "style", "fit", "sleeve", "neck")):
        return "style"
    if any(word in lowered for word in ("hiking", "running", "gym", "winter", "outdoor", "work")):
        return "use_case"
    return "feature"
