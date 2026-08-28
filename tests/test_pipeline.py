"""
Unit checks for the retrieval / intent / state modules.

Run everything:  python3 -m pytest tests/ -q
Run just these:  python3 -m pytest tests/test_pipeline.py -q

The catalog fixture is session-scoped: building the FTS index over 50k
products takes ~2.5s and must not be repeated per test.
"""
from __future__ import annotations

import pytest

from src.catalog import Catalog
from src.contracts import SessionState, Slots
from src.intent import classify_intent, detect_override
from src.retrieval_filter import retrieve
from src.state import choose_attribute_to_ask, update_slots


@pytest.fixture(scope="session")
def catalog() -> Catalog:
    return Catalog("data/catalog.jsonl")


def _state() -> SessionState:
    return SessionState(session_id="t", turn=1, intent="browsing", slots=Slots())


# --- intent ---------------------------------------------------------------

def test_intent_on_harness_phrasing():
    assert classify_intent("I'm looking for shoes, but I'm still exploring.") == "browsing"
    assert classify_intent("I'm looking for boots. A key requirement is: leather.") == "buying"
    assert classify_intent("Actually, ignore my earlier preference. What I need is: cotton.") == "buying"


def test_intent_on_natural_phrasing():
    """Guards against the classifier degenerating into harness-template matching."""
    assert classify_intent("Just browsing for gift ideas") == "browsing"
    assert classify_intent("I need a black leather jacket under $80") == "buying"
    assert classify_intent("not sure what I want yet") == "browsing"


def test_intent_is_sticky_when_signal_is_absent():
    assert classify_intent("ok", prior_intent="buying") == "buying"
    assert classify_intent("ok", prior_intent="browsing") == "browsing"
    assert classify_intent("ok") == "browsing"  # no prior -> wider net


def test_detect_override():
    assert detect_override("Actually, ignore my earlier preference.")
    assert detect_override("changed my mind, show me sneakers")
    assert not detect_override("I need a red dress")


# --- state ----------------------------------------------------------------

def test_opening_line_sets_category_not_a_constraint():
    """Regression: the opening line was once parsed as a feature constraint,
    poisoning every later retrieval with junk keywords."""
    state = update_slots(_state(), "I'm looking for Basketball Men, but I'm still exploring.")
    assert state.slots.category == "Basketball Men"
    assert state.disclosed_text == []
    assert state.slots.feature is None


def test_filler_reply_stores_nothing():
    state = update_slots(_state(), "Those options are not quite right yet. Ask me about one specific attribute.")
    assert state.disclosed_text == []
    assert state.slots.as_dict() == {}


def test_disclosure_accumulates():
    state = _state()
    update_slots(state, "I'm looking for shorts, but I'm still exploring.")
    update_slots(state, "For that, what matters is: Drawstring closure; High quality mesh.")
    assert len(state.disclosed_text) == 2
    assert state.slots.category == "shorts"


def test_boundary_marks_attribute_settled_without_storing_a_value():
    state = _state()
    update_slots(state, "I don't have a preference for material; please use your judgment.")
    assert "material" in state.disclosed_attributes
    assert state.slots.material is None


def test_override_retracts_only_the_opening_preference():
    """An override replaces the preference the shopper opened with; it does
    not invalidate everything learned since. Wiping the whole session threw
    away constraints that were never retracted."""
    state = _state()
    update_slots(state, "I'm looking for boots. A key requirement is: leather.")
    update_slots(state, "For that, what matters is: Lace-up closure; Rubber sole.")
    assert len(state.disclosed_text) == 3

    update_slots(state, "Actually, ignore my earlier preference. What I need is: canvas.")
    joined = " ".join(state.disclosed_text)
    assert state.slots.category == "boots"      # category survives
    assert "leather" not in joined              # the opening preference is dropped
    assert "Lace-up closure" in joined          # later constraints are kept
    assert "canvas" in joined                   # the replacement is recorded


def test_never_asks_a_zero_yield_attribute():
    """budget/brand/category yield nothing in this harness — see config."""
    state = _state()
    asked = []
    for _ in range(20):
        attribute = choose_attribute_to_ask(state)
        if attribute is None:
            break
        asked.append(attribute)
        # Only an explicit refusal settles a bucket.
        state.disclosed_attributes.add(attribute)
    assert "budget" not in asked
    assert "brand" not in asked
    assert "category" not in asked
    assert asked[0] == "feature"  # highest measured yield
    assert choose_attribute_to_ask(state) is None  # terminates


def test_receiving_a_constraint_does_not_exhaust_its_bucket():
    """Regression: marking a bucket settled on first receipt meant a session
    opening with "A key requirement is: Material:alloy" (classified as
    `feature`) never asked `feature` again, and so never learned the
    constraints that identified the product. Worth ~0.17 TechnicalScore."""
    state = _state()
    update_slots(state, "I'm looking for necklaces. A key requirement is: Material:alloy.")
    assert state.disclosed_text == ["Material:alloy"]
    assert state.disclosed_attributes == set()
    assert choose_attribute_to_ask(state) == "feature"


def test_explicit_refusal_does_exhaust_the_bucket():
    state = _state()
    update_slots(state, "I don't have an additional preference for feature.")
    assert "feature" in state.disclosed_attributes
    assert choose_attribute_to_ask(state) != "feature"


# --- retrieval ------------------------------------------------------------

def test_empty_slots_return_nothing_rather_than_crashing(catalog):
    assert retrieve(catalog, Slots()) == []


def test_verified_attributes_rank_above_pure_keyword_hits(catalog):
    results = retrieve(catalog, Slots(category="boots", color="black", material="leather"), top_k=10)
    assert results
    assert all(c.source == "filter" for c in results)
    assert sum(1 for c in results if c.matched_attributes) > 0


def test_disclosed_text_drives_retrieval(catalog):
    """The disclosed wording is the strongest signal we have; it must reach
    the query even when no structured slot is filled."""
    results = retrieve(catalog, Slots(), disclosed_text=["100% Polyester mesh basketball shorts"], top_k=10)
    assert results


def test_missing_price_is_not_penalised(catalog):
    """~79% of the catalog has no price; treating unknown as a budget
    failure would silently demote most of the catalog."""
    unpriced = next(a for a in catalog.products if a not in catalog.price)
    from src.retrieval_filter import _matched_attributes
    assert "budget" not in _matched_attributes(catalog, unpriced, Slots(budget=25.0))
