"""Statistical analysis of eval results (Phase 4).

Pure post-processing of results.parquet — re-running any analysis costs $0.

Peer-review traceability (see METHODOLOGY.md):
- multi-threshold headline rates + cross-threshold ranking stability
  (IEEE R1 W1: single ±10% threshold favours small-magnitude indicators)
- logistic regression with cluster-robust SEs by country, plus a
  mixed-effects (country random intercept) robustness fit
  (IEEE R2: descriptive rates presented without inferential uncertainty)
- World Bank income-tier stratification replaces the North/South binary
  (IEEE R1 W3)
- documented-vs-estimated training-cutoff sensitivity (IEEE R1 W4)
- balanced-coverage subset check (IEEE R1 W2)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

THRESHOLDS = (5, 10, 20, 30)
PRIMARY = 10


def load_results(tag: str, repo_root: Path, dry_run: bool = False) -> pd.DataFrame:
    suffix = "_dryrun" if dry_run else ""
    path = repo_root / "data" / "processed" / tag / f"results{suffix}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} — run `classify` first.")
    return pd.read_parquet(path)


def _rates(frame: pd.DataFrame, category_col: str) -> dict:
    n = len(frame)
    counts = frame[category_col].value_counts()
    return {"n": n, **{c: round(counts.get(c, 0) / n, 4) for c in
                       ("correct", "fabrication", "refusal", "hedge",
                        "misattribution")}}


def headline_rates(df: pd.DataFrame) -> dict:
    """Category shares per model at every threshold (numeric-scored rows
    change category with the threshold; refusals/hedges do not)."""
    out = {}
    for model, g in df.groupby("model_id"):
        out[model] = {f"pct_{t}": _rates(g, f"category_at_{t}") for t in THRESHOLDS}
        out[model]["primary"] = out[model][f"pct_{PRIMARY}"]
    return out


def ranking_stability(df: pd.DataFrame) -> dict:
    """Does the fabrication-rate ordering of models survive the threshold
    choice? Kendall's tau between the primary ranking and each other one.
    (Only meaningful with >= 3 models; degenerate values are labelled.)"""
    from scipy.stats import kendalltau
    rank = {}
    for t in THRESHOLDS:
        fab = {m: (g[f"category_at_{t}"] == "fabrication").mean()
               for m, g in df.groupby("model_id")}
        rank[t] = pd.Series(fab).rank()
    models = rank[PRIMARY].index
    out = {}
    for t in THRESHOLDS:
        if t == PRIMARY or len(models) < 2:
            continue
        tau, p = kendalltau(rank[PRIMARY], rank[t].reindex(models))
        out[f"tau_{PRIMARY}_vs_{t}"] = {
            "tau": None if np.isnan(tau) else round(float(tau), 3),
            "p": None if np.isnan(p) else round(float(p), 4)}
    out["n_models"] = len(models)
    return out


def _regression_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Fabrication-vs-correct decisions only (refusal/hedge/misattribution are
    separate behaviours, modelled by the rate tables, not this contrast)."""
    d = df[df["category"].isin(["fabrication", "correct"])].copy()
    d["fabricated"] = (d["category"] == "fabrication").astype(int)
    # magnitude only defined for non-binary indicators with |truth| > 0
    d["log10_magnitude"] = np.where(
        (~d["binary"]) & (d["ground_truth"].abs() > 0),
        np.log10(d["ground_truth"].abs().clip(lower=1e-12)), 0.0)
    d["year_c"] = d["year"] - d["year"].mean()
    d["income_tier"] = d["income_tier"].fillna("UNCLASSIFIED")
    return d


def logistic_models(df: pd.DataFrame) -> dict:
    """Per-model and pooled logistic regressions of fabrication on magnitude,
    year, income tier, variant and binary-indicator status, with
    cluster-robust standard errors by country (ISO3)."""
    import statsmodels.formula.api as smf

    def formula_for(frame: pd.DataFrame, pooled: bool) -> str:
        """Only include predictors that actually vary in this frame —
        constant columns make the design matrix singular."""
        terms = [t for t, col in [("log10_magnitude", "log10_magnitude"),
                                  ("year_c", "year_c"),
                                  ("C(income_tier)", "income_tier"),
                                  ("C(variant)", "variant"),
                                  ("binary", "binary")]
                 if frame[col].nunique() > 1]
        if pooled:
            terms.append("C(model_id)")
        return "fabricated ~ " + " + ".join(terms)

    def fit(frame: pd.DataFrame, pooled: bool = False) -> dict | None:
        if frame["fabricated"].nunique() < 2 or len(frame) < 50:
            return {"skipped": f"insufficient variation (n={len(frame)})"}
        try:
            import warnings as w
            with w.catch_warnings():
                w.simplefilter("ignore")
                model = smf.logit(formula_for(frame, pooled), data=frame).fit(
                    disp=False, cov_type="cluster",
                    cov_kwds={"groups": frame["ISO3"]})
        except Exception as exc:  # separation, singular matrix, ...
            return {"skipped": f"fit failed: {type(exc).__name__}: {exc}"}
        if not getattr(model, "mle_retvals", {}).get("converged", True):
            return {"skipped": "MLE did not converge (quasi-separation "
                               f"likely; n={len(frame)}) — coefficients "
                               "unreliable, not reported"}
        odds = np.exp(model.params)
        return {
            "n": int(model.nobs),
            "terms": {
                name: {"coef": round(float(model.params[name]), 4),
                       "se_cluster": round(float(model.bse[name]), 4),
                       "odds_ratio": round(float(odds[name]), 4),
                       "p": round(float(model.pvalues[name]), 4)}
                for name in model.params.index},
        }

    d = _regression_frame(df)
    per_model = {m: fit(g) for m, g in d.groupby("model_id")}
    pooled = fit(d, pooled=True) if d["model_id"].nunique() > 1 \
        else {"skipped": "single model; pooled = per-model"}
    return {"per_model": per_model, "pooled": pooled,
            "outcome": "fabrication vs correct (other categories excluded)",
            "cluster": "ISO3"}


def mixed_effects(df: pd.DataFrame) -> dict:
    """Robustness: Bayesian binomial GLMM with a country random intercept.
    Slow; run with --mixed. Confirms the cluster-robust results do not
    hinge on the independence approximation."""
    from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

    d = _regression_frame(df)
    out = {}
    for m, g in d.groupby("model_id"):
        if g["fabricated"].nunique() < 2 or len(g) < 100:
            out[m] = {"skipped": f"insufficient variation (n={len(g)})"}
            continue
        try:
            fit = BinomialBayesMixedGLM.from_formula(
                "fabricated ~ log10_magnitude + year_c + binary",
                {"country": "0 + C(ISO3)"}, g).fit_vb()
            names = list(fit.model.exog_names)
            out[m] = {"n": len(g),
                      "fixed_effects": {
                          n: {"mean": round(float(fit.fe_mean[i]), 4),
                              "sd": round(float(fit.fe_sd[i]), 4)}
                          for i, n in enumerate(names)},
                      "country_re_sd": round(float(np.exp(fit.vcp_mean[0])), 4)}
        except Exception as exc:
            out[m] = {"skipped": f"fit failed: {type(exc).__name__}"}
    return out


def income_stratification(df: pd.DataFrame) -> dict:
    """Category rates by World Bank income tier, per model, with a
    chi-square test of independence (fabrication vs correct only)."""
    from scipy.stats import chi2_contingency
    out = {}
    d = df.copy()
    d["income_tier"] = d["income_tier"].fillna("UNCLASSIFIED")
    for m, g in d.groupby("model_id"):
        tiers = {}
        for tier, tg in g.groupby("income_tier"):
            tiers[tier] = _rates(tg, "category")
        sub = g[g["category"].isin(["fabrication", "correct"])]
        table = pd.crosstab(sub["income_tier"], sub["category"])
        if table.shape[0] >= 2 and table.shape[1] == 2 and (table > 0).all().all():
            chi2, p, dof, _ = chi2_contingency(table)
            test = {"chi2": round(float(chi2), 3), "p": round(float(p), 4),
                    "dof": int(dof)}
        else:
            test = {"skipped": "sparse contingency table"}
        out[m] = {"by_tier": tiers, "chi2_fab_vs_correct": test}
    return out


def _cutoff_year(model_cfg: dict) -> int | None:
    date = str(model_cfg.get("training_cutoff", {}).get("date", ""))
    return int(date[:4]) if date[:4].isdigit() else None


def cutoff_sensitivity(df: pd.DataFrame, panel: list[dict]) -> dict:
    """Pre- vs post-training-cutoff fabrication rates per model, run twice:
    all models, then only models with DOCUMENTED cutoffs (IEEE R1 W4)."""
    cfg = {m["id"]: m for m in panel}

    def one(model_ids: list[str]) -> dict:
        res = {}
        for m in model_ids:
            g = df[df["model_id"] == m]
            year = _cutoff_year(cfg.get(m, {}))
            if year is None or g.empty:
                continue
            pre, post = g[g["year"] <= year], g[g["year"] > year]
            res[m] = {
                "cutoff_year": year,
                "cutoff_status": cfg[m]["training_cutoff"]["status"],
                "pre": _rates(pre, "category") if len(pre) else None,
                "post": _rates(post, "category") if len(post) else None,
            }
        return res

    models = [m for m in df["model_id"].unique() if m in cfg]
    documented = [m for m in models
                  if cfg[m]["training_cutoff"]["status"] == "documented"]
    return {"all_models": one(models),
            "documented_cutoffs_only": one(documented),
            "note": "post-cutoff queries can only be answered from retrieval "
                    "or fabrication; documented-only run excludes estimated "
                    "cutoffs as a sensitivity check"}


def balanced_subset_check(df: pd.DataFrame) -> dict:
    """Headline rates recomputed on the balanced-coverage indicator subset
    (equalised country coverage), per model (IEEE R1 W2)."""
    sub = df[df["balanced_subset"]]
    return {m: {"full": _rates(g, "category"),
                "balanced_subset": _rates(sub[sub["model_id"] == m], "category")}
            for m, g in df.groupby("model_id")}


def continuous_error(df: pd.DataFrame) -> dict:
    """Threshold-free error summary: |log10 ratio| for numeric answers.
    Scale-invariant — the IEEE 'multiplicative bias' complaint."""
    d = df.dropna(subset=["log10_ratio"])
    out = {}
    for m, g in d.groupby("model_id"):
        a = g["log10_ratio"].abs()
        out[m] = {"n_numeric": len(g),
                  "median_abs_log10_ratio": round(float(a.median()), 4),
                  "p90_abs_log10_ratio": round(float(a.quantile(0.9)), 4),
                  "within_half_order_of_magnitude":
                      round(float((a <= 0.176).mean()), 4),  # x/÷1.5
                  "within_one_order_of_magnitude":
                      round(float((a <= 1.0).mean()), 4)}
    return out


def _md_report(stats: dict, tag: str, dry_run: bool) -> str:
    lines = [f"# GAID eval statistics — {tag}"
             + (" (DRY RUN — synthetic responses)" if dry_run else ""), ""]
    if stats.get("partial_models_excluded"):
        lines += ["> **Excluded as incomplete** (coverage-biased; finish the "
                  "run or drop the model): "
                  + ", ".join(f"{m} ({n})" for m, n in
                              stats["partial_models_excluded"].items()), ""]
    lines += ["## Headline category rates (primary threshold ±10%)", "",
              "| model | n | correct | fabrication | refusal | hedge | misattr. |",
              "|---|---|---|---|---|---|---|"]
    for m, r in stats["headline_rates"].items():
        p = r["primary"]
        lines.append(f"| {m} | {p['n']} | {p['correct']:.1%} | "
                     f"{p['fabrication']:.1%} | {p['refusal']:.1%} | "
                     f"{p['hedge']:.1%} | {p['misattribution']:.1%} |")
    lines += ["", "## Threshold sensitivity (fabrication share)", "",
              "| model | ±5% | ±10% | ±20% | ±30% |", "|---|---|---|---|---|"]
    for m, r in stats["headline_rates"].items():
        row = " | ".join(f"{r[f'pct_{t}']['fabrication']:.1%}" for t in THRESHOLDS)
        lines.append(f"| {m} | {row} |")
    lines += ["", "## Logistic regression (fabrication ~ magnitude + year + "
                  "income tier + variant + binary; cluster-robust SEs by ISO3)", ""]
    for m, fit in stats["logistic"]["per_model"].items():
        if "skipped" in fit:
            lines.append(f"- **{m}**: {fit['skipped']}")
            continue
        lines.append(f"- **{m}** (n={fit['n']}):")
        for term, v in fit["terms"].items():
            if term == "Intercept":
                continue
            stars = "***" if v["p"] < 0.001 else "**" if v["p"] < 0.01 \
                else "*" if v["p"] < 0.05 else ""
            lines.append(f"  - `{term}` OR={v['odds_ratio']} "
                         f"(p={v['p']}){stars}")
    lines += ["", "## Scale-invariant error (|log10 model/truth|)", ""]
    for m, r in stats["continuous_error"].items():
        lines.append(f"- **{m}**: median {r['median_abs_log10_ratio']}, "
                     f"within half an order of magnitude "
                     f"{r['within_half_order_of_magnitude']:.1%} "
                     f"(n={r['n_numeric']})")
    lines += ["", "*Full machine-readable output: `stats.json` alongside "
                  "this file.*", ""]
    return "\n".join(lines)


def run_stats(tag: str, repo_root: Path, *, dry_run: bool = False,
              mixed: bool = False) -> dict:
    df = load_results(tag, repo_root, dry_run)
    panel = yaml.safe_load(
        (repo_root / "config" / "models.yaml").read_text())["panel"]

    # A model with incomplete coverage has a coverage-BIASED sample (queries
    # run in fixed order), which also tends to break the regressions via
    # quasi-separation. Only complete models enter the inferential analyses.
    n_queries = len(pd.read_parquet(
        repo_root / "data" / "processed" / tag / "queries.parquet"))
    counts = df.groupby("model_id").size()
    complete = sorted(counts[counts >= n_queries].index)
    partial = {m: f"{int(n)}/{n_queries}" for m, n in counts.items()
               if n < n_queries}
    dfc = df[df["model_id"].isin(complete)]

    stats = {
        "tag": tag, "dry_run": dry_run,
        "n_results": len(df), "models": sorted(df["model_id"].unique()),
        "complete_models": complete,
        "partial_models_excluded": partial,
        "headline_rates": headline_rates(dfc),
        "ranking_stability": ranking_stability(dfc),
        "logistic": logistic_models(dfc),
        "income_stratification": income_stratification(dfc),
        "cutoff_sensitivity": cutoff_sensitivity(dfc, panel),
        "balanced_subset_check": balanced_subset_check(dfc),
        "continuous_error": continuous_error(dfc),
    }
    if mixed:
        stats["mixed_effects"] = mixed_effects(dfc)

    out_dir = repo_root / "reports" / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_dryrun" if dry_run else ""
    (out_dir / f"stats{suffix}.json").write_text(json.dumps(stats, indent=2))
    (out_dir / f"stats_report{suffix}.md").write_text(
        _md_report(stats, tag, dry_run))
    return {"tag": tag, "dry_run": dry_run, "models": stats["models"],
            "complete_models": complete,
            "partial_models_excluded": partial,
            "n_results": len(df),
            "report": str(out_dir / f"stats_report{suffix}.md"),
            "json": str(out_dir / f"stats{suffix}.json")}
