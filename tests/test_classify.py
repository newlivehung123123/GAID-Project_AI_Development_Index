"""Unit tests for the scale-aware classifier.

Each case encodes a behaviour the peer review demanded, so a regression here
is a methodology regression, not just a code bug.
"""

import math

from gaid_pipeline.classify import classify, extract_numbers


def cat(resp, gt=100.0, binary=False, year=2019, variant="v1_direct"):
    return classify(resp, gt, binary, year, variant)


# --- number extraction ----------------------------------------------------

def test_plain_and_separators():
    assert extract_numbers("the value was 12,345 publications") == [12345.0]

def test_word_multipliers():
    assert extract_numbers("around 3.5 million") == [3.5e6]

def test_scientific_notation_variants():
    assert extract_numbers("roughly 2.5 x 10^24 FLOP") == [2.5e24]
    assert extract_numbers("about 1.2e23 FLOP") == [1.2e23]

def test_contextual_year_stripped_but_value_year_kept():
    # "in 2019" is a date; a bare "2019" as the asserted count is a value
    assert extract_numbers("in 2019, output rose") == []
    assert 2019.0 in extract_numbers("the country published 2019 papers")

def test_percentages():
    assert extract_numbers("about 45% agreed") == [45.0]


# --- category decisions -----------------------------------------------------

def test_correct_within_threshold():
    r = cat("The value was approximately 104.", gt=100.0)
    assert r["category"] == "correct"
    assert math.isclose(r["rel_error"], 0.04)

def test_fabrication_outside_threshold():
    assert cat("It was 150.", gt=100.0)["category"] == "fabrication"

def test_multi_threshold_columns_disagree():
    # 15% off: fabrication at ±5/±10, correct at ±20/±30 — the reviewer's
    # threshold-sensitivity concern must be visible per response
    r = cat("The value was 115.", gt=100.0)
    assert r["category_at_5"] == "fabrication"
    assert r["category_at_10"] == "fabrication"
    assert r["category_at_20"] == "correct"
    assert r["category_at_30"] == "correct"

def test_scale_awareness_log_ratio():
    # 40 vs 44 and 12,000 vs 13,200 are the SAME error in log space —
    # the exact small-value/large-value asymmetry IEEE R1 flagged
    small = cat("It was 40.", gt=44.0)
    large = cat("It was 12,000.", gt=13200.0)
    assert math.isclose(small["log10_ratio"], large["log10_ratio"], rel_tol=1e-9)

def test_refusal():
    r = cat("I don't know the specific figure for that year.")
    assert r["category"] == "refusal"

def test_refusal_with_guess_flagged_for_review():
    r = cat("I don't know exactly, but perhaps 90 or so.")
    assert r["category"] == "refusal"
    assert r["needs_review"]

def test_hedge():
    r = cat("The country was among the lowest performers, below the regional average.")
    assert r["category"] == "hedge"

def test_misattribution_different_year():
    r = cat("As of 2016, the value was 500.", gt=100.0, year=2019)
    assert r["category"] == "misattribution"

def test_value_with_query_year_not_misattributed():
    r = cat("In 2019 the value was 104.", gt=100.0, year=2019)
    assert r["category"] == "correct"

def test_binary_yes_no():
    assert cat("Yes, it had released one.", gt=1.0, binary=True)["category"] == "correct"
    assert cat("No, it had not.", gt=1.0, binary=True)["category"] == "fabrication"
    assert cat("It is unclear.", gt=1.0, binary=True)["category"] == "hedge"

def test_structured_null_is_refusal():
    r = cat('{"value": null, "confidence": "low"}', variant="v5_structured")
    assert r["category"] == "refusal"

def test_structured_value_scored():
    r = cat('{"value": 104, "confidence": "high"}', gt=100.0, variant="v5_structured")
    assert r["category"] == "correct"
    assert r["structured_confidence"] == "high"

def test_empty_response_is_flagged_fabrication():
    r = cat(None)
    assert r["category"] == "fabrication"
    assert r["needs_review"]
