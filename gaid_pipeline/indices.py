"""Composite index computation (Phase 3), with built-in validation.

Six pillars -> overall index + lenses, per annual edition. Alongside the
headline scores, every run produces:
  - dimensionality audit: Cronbach's alpha per pillar, cross-pillar
    correlations, eigenvalue structure (re-validates the pillar design
    against every new wave)
  - sensitivity variants: z-score and percentile normalisation
  - weighting check: PCA(PC1)-weighted vs equal-weighted pillar scores
  - convergent validity vs held-out external indices (Tortoise, GIRAI)

Outputs:
  data/processed/{tag}/indices.parquet    long panel of scores
  reports/{tag}/index_report.md           audit + sensitivity + validity
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def load_config(repo_root: Path) -> dict:
    return yaml.safe_load((repo_root / "config" / "indices.yaml").read_text())


# --- component extraction --------------------------------------------------

def component_rows(df: pd.DataFrame, spec: dict) -> pd.DataFrame:
    if "metric" in spec:
        rows = df[df["Metric"] == spec["metric"]]
    else:
        rows = df[df["Metric"].str.match(spec["metric_regex"], na=False)]
    out = rows.groupby(["ISO3", "Year"])["Value"].mean().reset_index()
    if spec.get("log"):
        out["Value"] = np.log1p(out["Value"].clip(lower=0))
    return out


def edition_values(rows: pd.DataFrame, edition: int, lookback: int) -> pd.Series:
    """Latest value per country within (edition - lookback, edition]."""
    window = rows[(rows["Year"] > edition - lookback) & (rows["Year"] <= edition)]
    if window.empty:
        return pd.Series(dtype=float)
    latest = window.sort_values("Year").groupby("ISO3").tail(1)
    return latest.set_index("ISO3")["Value"]


def normalise(s: pd.Series, direction: int, winsor: list[float],
              method: str = "minmax") -> pd.Series:
    if len(s) < 3:
        return pd.Series(dtype=float)
    lo, hi = s.quantile(winsor)
    s = s.clip(lo, hi)
    if method == "minmax":
        rng = s.max() - s.min()
        out = (s - s.min()) / rng * 100 if rng > 0 else pd.Series(50.0, index=s.index)
    elif method == "zscore":
        sd = s.std()
        out = (s - s.mean()) / sd * 15 + 50 if sd > 0 else pd.Series(50.0, index=s.index)
    elif method == "percentile":
        out = s.rank(pct=True) * 100
    else:
        raise ValueError(method)
    return 100 - out if direction == -1 else out


# --- pillar & index assembly -------------------------------------------------

def pillar_scores(comp_scores: dict[str, pd.Series], specs: list[dict],
                  min_share: float) -> tuple[pd.Series, pd.Series]:
    """Nested equal weights: mean within group, mean across groups.
    Returns (scores, n_components_used)."""
    groups: dict[str, list[pd.Series]] = {}
    for spec in specs:
        s = comp_scores.get(spec["id"])
        if s is not None and len(s):
            groups.setdefault(spec["group"], []).append(s)
    if not groups:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    group_means = pd.DataFrame({g: pd.concat(ss, axis=1).mean(axis=1)
                                for g, ss in groups.items()})
    n_comp = pd.concat(
        [s.notna().astype(int) for ss in groups.values() for s in ss], axis=1
    ).sum(axis=1)
    need = int(np.ceil(min_share * len(specs)))
    score = group_means.mean(axis=1)[n_comp >= need]
    return score, n_comp[score.index]


def compute_edition(df: pd.DataFrame, cfg: dict, edition: int,
                    method: str = "minmax") -> dict[str, dict]:
    """All pillar scores for one edition year. Returns
    {pillar_id: {score, n_components, components (normalised, for audits)}}."""
    ed_cfg = cfg["editions"]
    winsor = cfg["normalisation"]["winsorise"]
    out = {}
    for pid, pcfg in cfg["pillars"].items():
        comp_scores, comp_raw = {}, {}
        for spec in pcfg["components"]:
            vals = edition_values(component_rows(df, spec), edition,
                                  ed_cfg["max_lookback_years"])
            if len(vals) >= 3:
                comp_scores[spec["id"]] = normalise(
                    vals, spec["direction"], winsor, method)
        score, n_comp = pillar_scores(comp_scores, pcfg["components"],
                                      ed_cfg["min_component_share"])
        out[pid] = {"score": score, "n_components": n_comp,
                    "components": comp_scores}
    return out


def aggregate_indices(pillars: dict[str, dict], cfg: dict) -> dict[str, pd.Series]:
    frame = pd.DataFrame({pid: p["score"] for pid, p in pillars.items()})
    out = {}
    min_p = cfg["editions"]["min_pillars_for_overall"]
    enough = frame.notna().sum(axis=1) >= min_p
    out[cfg["overall"]["id"]] = frame.mean(axis=1)[enough]
    for lens_id, lens in cfg.get("lenses", {}).items():
        sub = frame[lens["pillars"]]
        ok = sub.notna().sum(axis=1) >= lens["min_pillars"]
        out[lens_id] = sub.mean(axis=1)[ok]
    return out


# --- validation battery -------------------------------------------------------

def cronbach(frame: pd.DataFrame) -> tuple[float | None, int]:
    sub = frame.dropna()
    k = sub.shape[1]
    if k < 2 or len(sub) < 10:
        return None, len(sub)
    denom = sub.sum(axis=1).var()
    if denom == 0:
        return None, len(sub)
    return float(k / (k - 1) * (1 - sub.var().sum() / denom)), len(sub)


def pca_weight_check(frame: pd.DataFrame) -> tuple[float | None, int]:
    """Spearman rho between equal-weighted and PC1-weighted pillar score."""
    sub = frame.dropna()
    if sub.shape[1] < 2 or len(sub) < 10:
        return None, len(sub)
    z = (sub - sub.mean()) / sub.std().replace(0, np.nan)
    z = z.dropna(axis=1)
    if z.shape[1] < 2:
        return None, len(sub)
    _, _, vt = np.linalg.svd(z.values, full_matrices=False)
    w = np.abs(vt[0]); w = w / w.sum()
    pca_score = (z * w).sum(axis=1)
    rho = sub.mean(axis=1).corr(pca_score, method="spearman")
    return float(rho), len(sub)


def _audit_edition(pillars: dict[str, dict], cfg: dict) -> dict:
    """Alpha at the right level: pillars are FORMATIVE composites (OECD/JRC
    handbook), so internal consistency is required only within reflective
    groups; pillar-level alpha is reported for information."""
    audit = {}
    for pid, p in pillars.items():
        comp = pd.DataFrame(p["components"])
        a, n = cronbach(comp)
        rho_pca, _ = pca_weight_check(comp)
        group_alphas = {}
        for spec in cfg["pillars"][pid]["components"]:
            g = spec["group"]
            ids = [s["id"] for s in cfg["pillars"][pid]["components"]
                   if s["group"] == g and s["id"] in comp.columns]
            if g not in group_alphas and len(ids) >= 2:
                ga, gn = cronbach(comp[ids])
                group_alphas[g] = (None if ga is None else round(ga, 2), gn)
        audit[pid] = {"alpha_pillar": a, "n_complete": n,
                      "k_active": comp.shape[1],
                      "group_alphas": group_alphas,
                      "rho_equal_vs_pca": rho_pca}
    return audit


def run_validation(pillars: dict[str, dict], cfg: dict, df: pd.DataFrame,
                   indices: dict[str, pd.Series], edition: int) -> dict:
    sens = {}
    audit = _audit_edition(pillars, cfg)
    # historical benchmark edition: audits pillars in their fullest form
    # (e.g. P1 with publications + FWCI + patents all populated)
    audit_2019 = _audit_edition(compute_edition(df, cfg, 2019), cfg)
    frame = pd.DataFrame({pid: p["score"] for pid, p in pillars.items()})
    cross = frame.corr(method="spearman", min_periods=15)

    for method in ["zscore", "percentile"]:
        alt = compute_edition(df, cfg, edition, method)
        sens[method] = {
            pid: float(frame[pid].corr(alt[pid]["score"], method="spearman"))
            if len(alt[pid]["score"]) else None
            for pid in pillars}

    convergent = []
    scores_all = {**{pid: p["score"] for pid, p in pillars.items()}, **indices,
                  "overall": indices[cfg["overall"]["id"]]}
    for v in cfg["validation"]["convergent"]:
        theirs_rows = df[df["Metric"] == v["theirs"]]
        if theirs_rows.empty:
            continue
        theirs = (theirs_rows[theirs_rows["Year"] == theirs_rows["Year"].max()]
                  .groupby("ISO3")["Value"].mean())
        ours = scores_all.get(v["ours"], pd.Series(dtype=float))
        joined = pd.concat([ours, theirs], axis=1, keys=["ours", "theirs"]).dropna()
        convergent.append({
            "ours": v["ours"], "theirs": v["theirs"], "n": len(joined),
            "rho": float(joined["ours"].corr(joined["theirs"], method="spearman"))
            if len(joined) >= 10 else None,
            "note": v.get("note", "")})
    return {"audit": audit, "audit_2019": audit_2019, "cross_pillar": cross,
            "sensitivity": sens, "convergent": convergent}


# --- top-level ---------------------------------------------------------------

def build_indices(canonical_parquet: Path, tag: str, repo_root: Path,
                  editions: list[int] | None = None) -> dict:
    cfg = load_config(repo_root)
    df = pd.read_parquet(canonical_parquet)
    df = df[df["Value"].notna()]
    editions = editions or list(range(2000, int(df["Year"].max()) + 1))
    latest = max(editions)

    records = []
    latest_pillars = None
    for ed in editions:
        pillars = compute_edition(df, cfg, ed)
        indices = aggregate_indices(pillars, cfg)
        if ed == latest:
            latest_pillars, latest_indices = pillars, indices
        for pid, p in pillars.items():
            for iso3, score in p["score"].items():
                records.append({"ISO3": iso3, "edition": ed, "level": "pillar",
                                "id": pid, "score": round(float(score), 2),
                                "n_components": int(p["n_components"][iso3])})
        for iid, s in indices.items():
            for iso3, score in s.items():
                records.append({"ISO3": iso3, "edition": ed, "level": "index",
                                "id": iid, "score": round(float(score), 2),
                                "n_components": None})
    panel = pd.DataFrame(records)

    validation = run_validation(latest_pillars, cfg, df, latest_indices, latest)

    out_dir = repo_root / "data" / "processed" / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(out_dir / "indices.parquet", index=False)
    report = write_report(panel, validation, cfg, tag, latest, repo_root)
    return {
        "tag": tag, "editions": f"{min(editions)}-{latest}",
        "panel_rows": len(panel),
        "countries_scored_latest": int(
            panel[(panel["edition"] == latest)
                  & (panel["id"] == cfg["overall"]["id"])]["ISO3"].nunique()),
        "indices_parquet": str(out_dir / "indices.parquet"),
        "report": report,
    }


def write_report(panel: pd.DataFrame, val: dict, cfg: dict, tag: str,
                 latest: int, repo_root: Path) -> str:
    rep_dir = repo_root / "reports" / tag
    rep_dir.mkdir(parents=True, exist_ok=True)
    ov = cfg["overall"]["id"]
    latest_p = panel[panel["edition"] == latest]
    cov = (latest_p.groupby("id")["ISO3"].nunique()
           .rename("countries").to_frame())
    top = (latest_p[latest_p["id"] == ov]
           .nlargest(15, "score")[["ISO3", "score"]])

    def audit_rows(audit: dict) -> list[dict]:
        return [
            {"pillar": pid, "name": cfg["pillars"][pid]["name"],
             "k_active": a["k_active"],
             "alpha_pillar(info)": None if a["alpha_pillar"] is None
             else round(a["alpha_pillar"], 2),
             "n": a["n_complete"],
             "group_alphas(test)": ", ".join(
                 f"{g}={v[0]} (n={v[1]})" for g, v in a["group_alphas"].items())
             or "single-component groups",
             "rho_equal_vs_pca": None if a["rho_equal_vs_pca"] is None
             else round(a["rho_equal_vs_pca"], 3)}
            for pid, a in audit.items()]

    lines = [
        f"# GAID composite index report — {tag}, edition {latest}", "",
        f"Normalisation: log1p (flagged) -> winsorise {cfg['normalisation']['winsorise']} "
        f"-> min-max within edition. Weights: nested equal. "
        f"Lookback: {cfg['editions']['max_lookback_years']} years.", "",
        "## Coverage (latest edition)", "",
        cov.to_markdown(), "",
        f"## Top 15 — {ov} (edition {latest})", "",
        top.to_markdown(index=False), "",
        f"## Dimensionality audit — edition {latest}", "",
        pd.DataFrame(audit_rows(val["audit"])).to_markdown(index=False), "",
        "## Dimensionality audit — benchmark edition 2019 (fullest P1 form)", "",
        pd.DataFrame(audit_rows(val["audit_2019"])).to_markdown(index=False), "",
        "Interpretation: pillars are FORMATIVE composites (OECD/JRC handbook) —"
        " internal consistency (alpha >= 0.7) is required within reflective"
        " groups, shown in group_alphas; pillar-level alpha is informational"
        " only. rho_equal_vs_pca near 1 means equal and PCA weighting produce"
        " the same ordering (equal weights defensible).", "",
        "## Cross-pillar correlations (Spearman)", "",
        val["cross_pillar"].round(2).to_markdown(), "",
        "## Normalisation sensitivity (Spearman vs headline min-max)", "",
        pd.DataFrame(val["sensitivity"]).round(3).to_markdown(), "",
        "## Convergent validity vs held-out external indices", "",
        pd.DataFrame(val["convergent"]).to_markdown(index=False), "",
    ]
    path = rep_dir / "index_report.md"
    path.write_text("\n".join(lines))
    return str(path)
