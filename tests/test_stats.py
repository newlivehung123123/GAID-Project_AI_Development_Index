"""Unit tests for the stats module (peer-review-driven analyses)."""

import numpy as np
import pandas as pd
import pytest

from gaid_pipeline import stats


def frame(n=400, seed=7):
    """Synthetic results frame with a planted magnitude effect."""
    rng = np.random.default_rng(seed)
    truth = 10 ** rng.uniform(0, 6, n)
    fab_p = 0.2 + 0.4 * (np.log10(truth) / 6)          # more fabrication at scale
    cat = np.where(rng.random(n) < fab_p, "fabrication", "correct")
    df = pd.DataFrame({
        "model_id": rng.choice(["m1", "m2"], n),
        "category": cat,
        "ground_truth": truth,
        "binary": False,
        "year": rng.integers(2015, 2025, n),
        "ISO3": rng.choice(["USA", "GBR", "KEN", "BRA", "IND", "VNM"], n),
        "income_tier": rng.choice(["HIC", "UMC", "LMC", "LIC"], n),
        "variant": rng.choice(["v1_direct", "v5_structured"], n),
        "balanced_subset": rng.random(n) < 0.5,
        "log10_ratio": rng.normal(0, 0.3, n),
    })
    for t in stats.THRESHOLDS:
        df[f"category_at_{t}"] = df["category"]
    return df


def test_headline_rates_sum_to_one():
    rates = stats.headline_rates(frame())
    for r in rates.values():
        p = r["primary"]
        total = sum(p[c] for c in ("correct", "fabrication", "refusal",
                                   "hedge", "misattribution"))
        assert total == pytest.approx(1.0, abs=0.01)


def test_regression_frame_excludes_non_decisions():
    df = frame()
    df.loc[df.index[:50], "category"] = "refusal"
    d = stats._regression_frame(df)
    assert set(d["category"]) == {"fabrication", "correct"}
    assert len(d) == len(df) - 50


def test_logistic_recovers_planted_magnitude_effect():
    fit = stats.logistic_models(frame(n=2000))
    for m, res in fit["per_model"].items():
        assert "terms" in res, res
        term = res["terms"]["log10_magnitude"]
        assert term["odds_ratio"] > 1.0          # planted: fabrication rises with scale
        assert term["p"] < 0.05


def test_income_stratification_has_all_tiers():
    out = stats.income_stratification(frame())
    for res in out.values():
        assert set(res["by_tier"]) == {"HIC", "UMC", "LMC", "LIC"}


def test_continuous_error_scale_invariant():
    out = stats.continuous_error(frame())
    for r in out.values():
        assert 0 <= r["within_one_order_of_magnitude"] <= 1
        assert r["median_abs_log10_ratio"] >= 0


def test_cutoff_sensitivity_documented_subset():
    panel = [
        {"id": "m1", "training_cutoff": {"date": "2020-01", "status": "documented"}},
        {"id": "m2", "training_cutoff": {"date": "2020-01", "status": "estimated"}},
    ]
    out = stats.cutoff_sensitivity(frame(), panel)
    assert set(out["all_models"]) == {"m1", "m2"}
    assert set(out["documented_cutoffs_only"]) == {"m1"}
    pre = out["all_models"]["m1"]["pre"]
    post = out["all_models"]["m1"]["post"]
    assert pre["n"] + post["n"] == len(frame()[frame()["model_id"] == "m1"])
