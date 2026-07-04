"""Human validation harness for the classifier.

Both pilots were criticised here: the Apart study never validated the
automated classifier against human labels, and the IEEE study's 90.1%
within-run consistency was read as meaningful classification noise. This
module makes validation a standard, repeatable step:

  export : stratified subsample (per category x model, plus every
           `needs_review` case) to a blind-coding CSV for the researcher
  kappa  : Cohen's kappa + confusion matrix from the coded CSV

The researcher codes the CSV personally; nothing here calls any API.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CODING_COLUMNS = ["human_category", "human_notes"]
CATEGORIES = ["correct", "fabrication", "refusal", "hedge", "misattribution"]


def export_sample(results_parquet: Path, out_csv: Path, per_stratum: int = 10,
                  seed: int = 42) -> dict:
    df = pd.read_parquet(results_parquet)
    sampled = (
        df.groupby(["model_id", "category"], group_keys=False)
        .apply(lambda g: g.sample(n=min(per_stratum, len(g)), random_state=seed),
               include_groups=False)
    )
    flagged = df[df["needs_review"]]
    sample = (
        pd.concat([df.loc[sampled.index], flagged])
        .drop_duplicates(subset=["query_id", "model_id"])
    )
    # blind coding: the human sees the prompt, response, and ground truth,
    # but NOT the classifier's category
    cols = ["query_id", "model_id", "prompt", "response", "ground_truth",
            "binary", "year"]
    blind = sample[cols].copy()
    for c in CODING_COLUMNS:
        blind[c] = ""
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    blind.to_csv(out_csv, index=False)
    # the answer key stays alongside for the kappa step
    key = sample[["query_id", "model_id", "category", "needs_review"]]
    key.to_csv(out_csv.with_suffix(".key.csv"), index=False)
    return {"exported": len(blind), "coding_csv": str(out_csv),
            "instructions": f"Fill `human_category` with one of {CATEGORIES}, "
                            "then run `validate-kappa`."}


def cohen_kappa(coded_csv: Path) -> dict:
    coded = pd.read_csv(coded_csv)
    key = pd.read_csv(coded_csv.with_suffix(".key.csv"))
    merged = coded.merge(key, on=["query_id", "model_id"])
    merged = merged[merged["human_category"].isin(CATEGORIES)]
    if merged.empty:
        raise RuntimeError("No coded rows found — fill `human_category` first.")

    a, b = merged["category"], merged["human_category"]
    po = (a == b).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in CATEGORIES)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    confusion = pd.crosstab(a, b, rownames=["classifier"], colnames=["human"])
    return {
        "n_coded": len(merged),
        "observed_agreement": round(float(po), 3),
        "cohen_kappa": round(float(kappa), 3),
        "confusion_matrix": confusion.to_dict(),
    }
