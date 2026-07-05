"""Dashboard data export (Phase 3): pipeline outputs -> static JSON.

The dashboard at gaid.aiinsocietyhub.com is a static site: no server, no
API — it reads pre-computed JSON generated here at build time.

  site/data/meta.json              countries, pillars, wave info, rankings
  site/data/indices.json           full index panel (all editions)
  site/data/countries/{ISO3}.json  one profile per country: index history +
                                   every analytical metric series

Transactional company-level records (single-row funding events) are excluded
from profiles; analytical country-level metrics (1,331 in w1_v2) are all
included — the dashboard's profile layer exposes the whole dataset, not just
the index-grade subset.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from . import geo


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), allow_nan=False))


def build_site_data(canonical_parquet: Path, indices_parquet: Path, tag: str,
                    repo_root: Path) -> dict:
    cfg = yaml.safe_load((repo_root / "config" / "indices.yaml").read_text())
    out = repo_root / "site" / "data"
    df = pd.read_parquet(canonical_parquet)
    panel = pd.read_parquet(indices_parquet)
    geo_table = geo.fetch(repo_root)

    analytical = df[~df["Metric"].str.contains(r"\[ID:", regex=True, na=False)]
    analytical = analytical[analytical["Value"].notna()]
    names = analytical.drop_duplicates("ISO3").set_index("ISO3")["Country"]

    # --- indices.json: {id: {ISO3: {edition: score}}} -----------------------
    indices_obj: dict = {}
    for (iid, iso3), g in panel.groupby(["id", "ISO3"]):
        indices_obj.setdefault(iid, {})[iso3] = {
            str(int(r["edition"])): r["score"] for _, r in g.iterrows()}
    _write(out / "indices.json", indices_obj)

    # --- meta.json ----------------------------------------------------------
    latest = int(panel["edition"].max())
    overall_id = cfg["overall"]["id"]
    latest_overall = (panel[(panel["edition"] == latest)
                            & (panel["id"] == overall_id)]
                      .sort_values("score", ascending=False).reset_index(drop=True))
    ranks = {r["ISO3"]: i + 1 for i, r in latest_overall.iterrows()}

    manifest = json.loads((repo_root / "data" / "manifest.json").read_text())
    countries_meta = []
    for iso3 in sorted(analytical["ISO3"].unique()):
        info = geo_table.get(iso3, {})
        entry = {"iso3": iso3, "name": str(names.get(iso3, iso3)),
                 "region": info.get("region"),
                 "income": info.get("income_label"),
                 "metrics": int(analytical[analytical["ISO3"] == iso3]["Metric"].nunique())}
        if iso3 in ranks:
            row = latest_overall[latest_overall["ISO3"] == iso3].iloc[0]
            entry["overall"] = {"rank": ranks[iso3], "score": row["score"],
                                "edition": latest}
        countries_meta.append(entry)

    _write(out / "meta.json", {
        "wave": {"tag": tag, "doi": manifest["installed"]["dataset_doi"],
                 "synced_at": manifest["synced_at"]},
        "latest_edition": latest,
        "overall_id": overall_id,
        "pillars": {pid: p["name"] for pid, p in cfg["pillars"].items()},
        "lenses": {lid: l["name"] for lid, l in cfg.get("lenses", {}).items()},
        "n_ranked": len(latest_overall),
        "countries": countries_meta,
    })

    # --- per-country profiles ----------------------------------------------
    panel_by_iso = dict(tuple(panel.groupby("ISO3")))
    for iso3, g in analytical.groupby("ISO3"):
        info = geo_table.get(iso3, {})
        series = {}
        for (metric, source, cat), m in g.groupby(["Metric", "Source",
                                                   "Source_Category"]):
            series[metric] = {
                "source": source, "category": cat,
                "values": {str(int(y)): float(v) for y, v in
                           m.sort_values("Year")[["Year", "Value"]].values}}
        scores = {}
        if iso3 in panel_by_iso:
            for iid, pg in panel_by_iso[iso3].groupby("id"):
                scores[iid] = {str(int(r["edition"])): r["score"]
                               for _, r in pg.iterrows()}
        _write(out / "countries" / f"{iso3}.json", {
            "iso3": iso3, "name": str(names.get(iso3, iso3)),
            "region": info.get("region"), "income": info.get("income_label"),
            "indices": scores, "metrics": series})

    n_files = len(list((out / "countries").glob("*.json")))
    total_kb = sum(p.stat().st_size for p in out.rglob("*.json")) // 1024
    return {"tag": tag, "country_files": n_files,
            "ranked_countries": len(latest_overall),
            "total_size_kb": int(total_kb), "out_dir": str(out)}
