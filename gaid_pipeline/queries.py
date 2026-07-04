"""Query generation: screened observations -> versioned, sampled query set.

v1 covers the full observation grid; all other variants share ONE stratified
subsample so variant contrasts are paired on identical observations. Query
ids hash (obs_id | variant | template_version), so a template edit invalidates
exactly the affected cache entries and nothing else.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pandas as pd
import yaml


def load_prompts(repo_root: Path) -> dict:
    return yaml.safe_load((repo_root / "config" / "prompts.yaml").read_text())


def format_anchor(ground_truth: float) -> str:
    """Human-readable decoy anchor at ground truth x 1.25."""
    anchor = ground_truth * 1.25
    if anchor == 0:
        return "0"
    magnitude = abs(anchor)
    if magnitude >= 1e15 or magnitude < 1e-3:
        return f"{anchor:.2e}"
    if magnitude >= 1000:
        return f"{anchor:,.0f}"
    if magnitude >= 10:
        return f"{anchor:.1f}"
    return f"{anchor:.3g}"


def build_prompt(row: pd.Series, variant: str, templates: dict) -> str:
    spec = templates["variants"][variant]
    template = spec["binary"] if row["binary"] else spec["continuous"]
    fields = {
        "prompt_source": row["prompt_source"],
        "label": row["label"],
        "country": row["Country"],
        "year": int(row["Year"]),
        "region": row["region"] or "its region",
    }
    if variant == "v3_anchored":
        if row["binary"]:
            fields["anchor_binary"] = "had NOT" if row["Value"] >= 0.5 else "had"
        else:
            fields["anchor"] = format_anchor(float(row["Value"]))
    return " ".join(template.format(**fields).split())


def query_id(obs_id: str, variant: str, template_version: int) -> str:
    return hashlib.sha1(f"{obs_id}|{variant}|tv{template_version}".encode()).hexdigest()[:16]


def shared_subsample(obs: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """One stratified subsample reused by every non-v1 variant."""
    frac = cfg["sampling"]["variant_subsample_fraction"]
    seed = cfg["sampling"]["seed"]
    strata = cfg["sampling"]["stratify_by"]
    keys = obs.fillna({"income_tier": "UNCLASSIFIED"})
    picked = (
        keys.groupby(strata, dropna=False, group_keys=False)
        .apply(lambda g: g.sample(n=max(1, math.ceil(len(g) * frac)),
                                  random_state=seed), include_groups=False)
    )
    return obs.loc[picked.index]


def generate(observations_parquet: Path, tag: str, repo_root: Path) -> dict:
    cfg = load_prompts(repo_root)
    tv = cfg["template_version"]
    obs = pd.read_parquet(observations_parquet)
    sub = shared_subsample(obs, cfg)

    records = []
    for variant, spec in cfg["variants"].items():
        frame = obs if spec["coverage"] == "full" else sub
        for _, row in frame.iterrows():
            records.append({
                "query_id": query_id(row["obs_id"], variant, tv),
                "obs_id": row["obs_id"],
                "indicator_id": row["indicator_id"],
                "theme": row["theme"],
                "ISO3": row["ISO3"],
                "country": row["Country"],
                "year": int(row["Year"]),
                "variant": variant,
                "prompt": build_prompt(row, variant, cfg),
                "ground_truth": float(row["Value"]),
                "binary": bool(row["binary"]),
                "income_tier": row["income_tier"],
                "global_north": row["global_north"],
                "region": row["region"],
                "balanced_subset": bool(row["balanced_subset"]),
                "template_version": tv,
            })
    queries = pd.DataFrame(records)

    out = repo_root / "data" / "processed" / tag / "queries.parquet"
    queries.to_parquet(out, index=False)
    by_variant = queries["variant"].value_counts().to_dict()
    return {
        "tag": tag,
        "template_version": tv,
        "total_queries": len(queries),
        "by_variant": by_variant,
        "subsample_observations": int(sub["obs_id"].nunique()),
        "queries_parquet": str(out),
    }
