# Tests for menu_matcher.py
# Requires: rapidfuzz  (pip install rapidfuzz)

import pandas as pd
import pytest

import menu_matcher


# ---------------------------------------------------------------------------
# Shared fixture: a tiny fake item_profiles DataFrame
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_item_profiles():
    """Small catalog with three well-known beers for fuzzy-match testing."""
    return pd.DataFrame([
        {"beer_id": 1, "beer_name": "Corona Extra",          "brewery_name": "Grupo Modelo"},
        {"beer_id": 2, "beer_name": "Heineken Lager Beer",   "brewery_name": "Heineken N.V."},
        {"beer_id": 3, "beer_name": "Blue Moon Belgian White","brewery_name": "Blue Moon Brewing Co."},
    ])


# ---------------------------------------------------------------------------
# 1. Exact-ish name match (no brewery hint)
# ---------------------------------------------------------------------------

def test_match_menu_beers_exact(fake_item_profiles):
    """'Corona' should fuzzy-match 'Corona Extra' and return beer_id=1."""
    extracted = [{"name": "Corona", "brewery": None}]
    matched_ids, total_extracted = menu_matcher.match_menu_beers(extracted, fake_item_profiles)

    assert total_extracted == 1
    assert 1 in matched_ids, f"Expected beer_id 1 (Corona Extra) in {matched_ids}"


# ---------------------------------------------------------------------------
# 2. Name + brewery hint
# ---------------------------------------------------------------------------

def test_match_menu_beers_with_brewery(fake_item_profiles):
    """'Blue Moon' with brewery hint should resolve to Blue Moon Belgian White (id=3)."""
    extracted = [{"name": "Blue Moon", "brewery": "Blue Moon Brewing"}]
    matched_ids, total_extracted = menu_matcher.match_menu_beers(extracted, fake_item_profiles)

    assert total_extracted == 1
    assert 3 in matched_ids, f"Expected beer_id 3 (Blue Moon Belgian White) in {matched_ids}"


# ---------------------------------------------------------------------------
# 3. No match
# ---------------------------------------------------------------------------

def test_match_menu_beers_no_match(fake_item_profiles):
    """A completely unrelated name should not match any catalog entry."""
    extracted = [{"name": "XYZ NotABeer", "brewery": None}]
    matched_ids, total_extracted = menu_matcher.match_menu_beers(extracted, fake_item_profiles)

    assert total_extracted == 1
    assert matched_ids == [], f"Expected empty match list, got {matched_ids}"


# ---------------------------------------------------------------------------
# 4. Deduplication: two extracted entries that hit the same beer
# ---------------------------------------------------------------------------

def test_match_menu_beers_dedup(fake_item_profiles):
    """Two extracted entries both matching 'Corona Extra' should appear only once."""
    extracted = [
        {"name": "Corona", "brewery": None},
        {"name": "Corona Extra", "brewery": None},
    ]
    matched_ids, total_extracted = menu_matcher.match_menu_beers(extracted, fake_item_profiles)

    assert total_extracted == 2
    # beer_id 1 must appear exactly once
    assert matched_ids.count(1) == 1, (
        f"Corona Extra (beer_id=1) appeared {matched_ids.count(1)} times; expected exactly 1"
    )


# ---------------------------------------------------------------------------
# 5. _normalize helper
# ---------------------------------------------------------------------------

def test_normalize():
    """_normalize should lowercase and strip brewery noise words."""
    result = menu_matcher._normalize("Blue Moon Brewing Co.")
    # Expected: "brewing" and "co" (and trailing punctuation) are stripped,
    # leaving "blue moon"
    assert result == "blue moon", f"_normalize returned {result!r}, expected 'blue moon'"
