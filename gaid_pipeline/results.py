"""Join cached responses with queries and classify them into results.

Classification is pure post-processing of the response cache: changing the
classifier or thresholds and re-running this stage costs $0 in API spend.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import classify as clf
from . import client


def build_results(queries_parquet: Path, tag: str, repo_root: Path,
                  dry_run: bool = False) -> dict:
    queries = pd.read_parquet(queries_parquet)
    responses = client.load_responses(repo_root, dry_run)
    if responses.empty:
        raise RuntimeError("No responses cached yet. Run `run-eval` first.")

    merged = responses.merge(queries, on="query_id", how="inner")
    records = []
    for _, row in merged.iterrows():
        record = clf.classify(row["response"], row["ground_truth"],
                              row["binary"], row["year"], row["variant"])
        record["extracted"] = ",".join(f"{v:g}" for v in record["extracted"])
        records.append({**row.to_dict(), **record})
    results = pd.DataFrame(records)

    suffix = "_dryrun" if dry_run else ""
    out = repo_root / "data" / "processed" / tag / f"results{suffix}.parquet"
    results.to_parquet(out, index=False)

    dist = (results.groupby(["model_id", "category"]).size()
            .unstack(fill_value=0))
    return {
        "tag": tag, "dry_run": dry_run, "rows": len(results),
        "category_distribution": dist.to_dict(),
        "needs_review": int(results["needs_review"].sum()),
        "results_parquet": str(out),
    }
