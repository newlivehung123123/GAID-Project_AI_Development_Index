"""Country reference data: World Bank income tiers and regions.

Income tier is the PRIMARY geographic stratification of the eval (both pilots
flagged the Global North/South binary as too coarse — IEEE limitation 3).
The GN/GS binary is retained for comparability with the pilots, derived as
high-income -> Global North unless overridden.

Fetched once from the World Bank API and cached in data/reference/ (committed,
so runs are reproducible against a pinned snapshot; refresh with --refresh
when the WB updates classifications each July).
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

WB_URL = "https://api.worldbank.org/v2/country"
INCOME_TIERS = {"HIC": "High income", "UMC": "Upper middle income",
                "LMC": "Lower middle income", "LIC": "Low income"}

# Economies the World Bank does not classify but GAID covers.
MANUAL = {
    "TWN": {"income_tier": "HIC", "region": "East Asia & Pacific",
            "note": "not WB-classified; IMF advanced economy"},
}

# Derivation rule for the pilot-comparable binary. Override here if a
# specific economy should not follow the income rule.
GLOBAL_NORTH_OVERRIDES: dict[str, bool] = {}


def reference_path(repo_root: Path) -> Path:
    return repo_root / "data" / "reference" / "wb_countries.json"


def fetch(repo_root: Path, refresh: bool = False) -> dict[str, dict]:
    """ISO3 -> {income_tier, income_label, region, name, global_north}."""
    path = reference_path(repo_root)
    if path.exists() and not refresh:
        return json.loads(path.read_text())

    resp = requests.get(WB_URL, params={"format": "json", "per_page": 400},
                        timeout=60)
    resp.raise_for_status()
    _, rows = resp.json()

    table: dict[str, dict] = {}
    for row in rows:
        iso3 = row.get("id", "")
        # region id "NA" marks World Bank aggregates (e.g. "World"), not economies
        if row.get("region", {}).get("id") == "NA":
            continue
        tier = row.get("incomeLevel", {}).get("id")
        table[iso3] = {
            "name": row.get("name"),
            "income_tier": tier if tier in INCOME_TIERS else None,
            "income_label": INCOME_TIERS.get(tier),
            "region": row.get("region", {}).get("value", "").strip(),
        }
    for iso3, info in MANUAL.items():
        entry = table.setdefault(iso3, {"name": iso3})
        entry.setdefault("income_tier", info["income_tier"])
        entry["income_label"] = INCOME_TIERS[entry["income_tier"]]
        entry.setdefault("region", info["region"])
        entry["note"] = info.get("note")

    for iso3, entry in table.items():
        if iso3 in GLOBAL_NORTH_OVERRIDES:
            entry["global_north"] = GLOBAL_NORTH_OVERRIDES[iso3]
        elif entry.get("income_tier") is None:
            entry["global_north"] = None  # unclassified: excluded from geo strata
        else:
            entry["global_north"] = entry["income_tier"] == "HIC"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(table, indent=2, sort_keys=True) + "\n")
    return table
