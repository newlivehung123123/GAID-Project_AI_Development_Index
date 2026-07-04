"""Indicator screening as code: thematic mapping -> coverage -> redundancy.

Re-run against every new GAID wave. Candidates and rules live in
config/indicators.yaml; what is retained is decided by the data. Everything
that was a manual judgement call in the pilots is either automated or made
an explicit, printed override so the screening is auditable end to end.

Outputs per wave:
  data/processed/{tag}/observations.parquet   screened obs + geo strata
  reports/{tag}/screening_report.md           decisions with reasons
  reports/{tag}/indicator_coverage.csv        coverage incl. per income tier
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pandas as pd
import yaml

from . import geo


def load_config(repo_root: Path) -> dict:
    return yaml.safe_load((repo_root / "config" / "indicators.yaml").read_text())


def build_indicator_frame(df: pd.DataFrame, ind: dict, eval_years: list[int]) -> pd.DataFrame:
    years = ind.get("years_override") or eval_years
    sub = df[
        (df["Metric"] == ind["metric"])
        & (df["Source"] == ind["source"])
        & (df["Year"].isin(years))
        & df["Value"].notna()
    ].copy()
    sub["indicator_id"] = ind["id"]
    sub["theme"] = ind["theme"]
    sub["binary"] = ind["binary"]
    sub["label"] = ind["label"]
    sub["prompt_source"] = ind["prompt_source"]
    return sub


def coverage_table(obs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ind_id, g in obs.groupby("indicator_id"):
        by_year_max = g.groupby("Year")["ISO3"].nunique().max()
        tiers = g.drop_duplicates("ISO3")["income_tier"].value_counts()
        rows.append({
            "indicator_id": ind_id,
            "theme": g["theme"].iloc[0],
            "n_obs": len(g),
            "n_countries": g["ISO3"].nunique(),
            "max_countries_single_year": int(by_year_max),
            "years": ",".join(str(y) for y in sorted(g["Year"].unique())),
            "n_HIC": int(tiers.get("HIC", 0)),
            "n_UMC": int(tiers.get("UMC", 0)),
            "n_LMC": int(tiers.get("LMC", 0)),
            "n_LIC": int(tiers.get("LIC", 0)),
        })
    return pd.DataFrame(rows).sort_values("indicator_id")


def redundancy_pairs(obs: pd.DataFrame, cfg: dict) -> list[dict]:
    """|Spearman r| between indicator pairs on a shared cross-section."""
    threshold = cfg["screening"]["redundancy_threshold"]
    preferred_year = cfg["screening"]["redundancy_year"]
    flagged = []
    for a, b in combinations(sorted(obs["indicator_id"].unique()), 2):
        ga, gb = obs[obs["indicator_id"] == a], obs[obs["indicator_id"] == b]
        shared_years = sorted(set(ga["Year"]) & set(gb["Year"]), reverse=True)
        if not shared_years:
            continue
        year = preferred_year if preferred_year in shared_years else shared_years[0]
        wide = pd.merge(
            ga[ga["Year"] == year][["ISO3", "Value"]],
            gb[gb["Year"] == year][["ISO3", "Value"]],
            on="ISO3", suffixes=("_a", "_b"),
        )
        if len(wide) < 5:  # too few overlapping countries for a stable rho
            continue
        if wide["Value_a"].nunique() < 2 or wide["Value_b"].nunique() < 2:
            continue  # constant series (e.g. binary all-1s): rho undefined
        rho = wide["Value_a"].corr(wide["Value_b"], method="spearman")
        if pd.notna(rho) and abs(rho) > threshold:
            flagged.append({"pair": (a, b), "rho": round(float(rho), 3),
                            "year": int(year), "n": len(wide)})
    return flagged


def resolve_redundancy(flagged: list[dict], coverage: pd.DataFrame,
                       cfg: dict) -> tuple[set[str], list[str]]:
    """Return (indicator ids to drop, log lines). Overrides keep pairs with a
    printed conceptual justification; otherwise the lower-coverage side drops."""
    overrides = {frozenset(o["pair"]): o for o in cfg.get("redundancy_overrides", [])}
    n_countries = coverage.set_index("indicator_id")["n_countries"]
    drop, log = set(), []
    for f in flagged:
        a, b = f["pair"]
        key = frozenset((a, b))
        if key in overrides and overrides[key].get("keep") == "both":
            log.append(f"- KEPT both `{a}` and `{b}` despite rho={f['rho']} "
                       f"({f['year']}, n={f['n']}): "
                       f"{overrides[key]['justification'].strip()}")
            continue
        loser = a if n_countries.get(a, 0) <= n_countries.get(b, 0) else b
        winner = b if loser == a else a
        drop.add(loser)
        log.append(f"- DROPPED `{loser}` (rho={f['rho']} with `{winner}`, "
                   f"{f['year']}, n={f['n']}; lower country coverage)")
    return drop, log


def screen(canonical_parquet: Path, tag: str, repo_root: Path) -> dict:
    cfg = load_config(repo_root)
    eval_years = cfg["eval_years"]
    df = pd.read_parquet(canonical_parquet)
    geo_table = geo.fetch(repo_root)

    # Stage 1: thematic mapping (config) + observation extraction
    frames, missing = [], []
    for ind in cfg["indicators"]:
        sub = build_indicator_frame(df, ind, eval_years)
        (frames if len(sub) else missing).append(sub if len(sub) else ind["id"])
    obs = pd.concat(frames, ignore_index=True)

    # attach geo strata
    obs["income_tier"] = obs["ISO3"].map(lambda i: (geo_table.get(i) or {}).get("income_tier"))
    obs["region"] = obs["ISO3"].map(lambda i: (geo_table.get(i) or {}).get("region"))
    obs["global_north"] = obs["ISO3"].map(lambda i: (geo_table.get(i) or {}).get("global_north"))
    unclassified = sorted(obs[obs["income_tier"].isna()]["ISO3"].unique())

    # Stage 2: coverage
    coverage = coverage_table(obs)
    min_c = cfg["screening"]["min_countries"]
    thin = coverage[coverage["max_countries_single_year"] < min_c]["indicator_id"].tolist()

    # balanced-coverage subset (IEEE R1 weakness 2): enough countries per tier
    min_tier = cfg["analysis_gates"]["balanced_subset_min_per_tier"]
    balanced = coverage[
        (coverage[["n_HIC", "n_UMC", "n_LMC", "n_LIC"]] >= min_tier).all(axis=1)
    ]["indicator_id"].tolist()

    # Stage 3: redundancy
    kept_after_cov = obs[~obs["indicator_id"].isin(thin)]
    flagged = redundancy_pairs(kept_after_cov, cfg)
    dropped_red, red_log = resolve_redundancy(flagged, coverage, cfg)

    retained = kept_after_cov[~kept_after_cov["indicator_id"].isin(dropped_red)].copy()
    retained["balanced_subset"] = retained["indicator_id"].isin(balanced)
    retained["obs_id"] = (retained["indicator_id"] + "|" + retained["ISO3"]
                          + "|" + retained["Year"].astype(str))

    out_dir = repo_root / "data" / "processed" / tag
    rep_dir = repo_root / "reports" / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)
    obs_path = out_dir / "observations.parquet"
    retained.to_parquet(obs_path, index=False)
    coverage.to_csv(rep_dir / "indicator_coverage.csv", index=False)

    lines = [
        f"# Indicator screening report — {tag}", "",
        f"Candidates: {len(cfg['indicators'])} | retained: "
        f"{retained['indicator_id'].nunique()} | observations: {len(retained):,}",
        f"Eval years: {eval_years}", "",
        "## Stage 1 — thematic mapping",
        f"- Candidates with zero matching rows in this wave: {missing or 'none'}",
        f"- ISO3 codes without World Bank income classification "
        f"(kept, excluded from income-tier strata): {unclassified or 'none'}", "",
        "## Stage 2 — coverage",
        f"- Rule: >= {min_c} countries in at least one eval year",
        f"- Excluded as thin: {thin or 'none'}",
        f"- Balanced-coverage subset (>= {min_tier} countries in every income "
        f"tier): {balanced or 'none'}", "",
        "## Stage 3 — redundancy",
        f"- Rule: |Spearman rho| > {cfg['screening']['redundancy_threshold']} "
        f"on the {cfg['screening']['redundancy_year']} cross-section "
        "(fallback: latest shared year)",
        *(red_log or ["- no pairs flagged"]), "",
        "## Retained indicators", "",
        coverage[~coverage["indicator_id"].isin(set(thin) | dropped_red)]
        .to_markdown(index=False), "",
        "## Observations by income tier x theme", "",
        retained.pivot_table(index="theme", columns="income_tier",
                             values="obs_id", aggfunc="count", fill_value=0)
        .to_markdown(), "",
    ]
    (rep_dir / "screening_report.md").write_text("\n".join(lines))

    return {
        "tag": tag,
        "retained_indicators": int(retained["indicator_id"].nunique()),
        "observations": len(retained),
        "excluded_thin": thin,
        "dropped_redundant": sorted(dropped_red),
        "balanced_subset": balanced,
        "observations_parquet": str(obs_path),
        "report": str(rep_dir / "screening_report.md"),
    }
