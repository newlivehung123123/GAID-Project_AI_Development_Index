"""Harmonisation layer: raw GAID wave -> canonical, validated dataset.

Each annual wave may grow or change shape. This layer maps whatever the wave
contains onto one canonical schema, validates it, and fails loudly with a
diff report if an assumption breaks — a wrong benchmark silently built from
a changed schema is worse than no benchmark.

Outputs:
  data/processed/{tag}/gaid_canonical.parquet   canonical long-format panel
  reports/{tag}/wave_report.md                  human-readable wave summary
  reports/{tag}/metric_coverage.csv             per-metric coverage (screening input)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# The canonical long-format schema. REQUIRED columns must exist in every
# wave; OPTIONAL ones are carried through when present.
REQUIRED = ["Year", "Country", "ISO3", "Metric", "Value", "Source"]
OPTIONAL = ["Dataset", "Source_Category", "Source_File", "Source_Type", "Source_Year"]

YEAR_RANGE = (1990, 2035)


class SchemaError(RuntimeError):
    """Raised when a wave does not match the canonical schema."""


def find_ground_truth_csv(wave_dir: Path) -> Path:
    """Locate the main long-format CSV inside an extracted wave.

    Identified by schema (has the required columns), not by filename, so a
    renamed file in a future wave still resolves. Largest match wins.
    """
    candidates = []
    for csv in sorted(wave_dir.rglob("*.csv")):
        try:
            header = pd.read_csv(csv, nrows=0)
        except Exception:
            continue
        if set(REQUIRED).issubset(header.columns):
            candidates.append(csv)
    if not candidates:
        seen = {c.name: list(pd.read_csv(c, nrows=0).columns)
                for c in wave_dir.rglob("*.csv")}
        raise SchemaError(
            f"No CSV in {wave_dir} has the required columns {REQUIRED}.\n"
            f"CSVs found (name -> columns): {json.dumps(seen, indent=2, default=str)}"
        )
    return max(candidates, key=lambda p: p.stat().st_size)


def load_canonical(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, low_memory=False)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SchemaError(
            f"{csv_path.name} is missing required columns {missing}; "
            f"has {list(df.columns)}"
        )

    keep = REQUIRED + [c for c in OPTIONAL if c in df.columns]
    df = df[keep].copy()

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    bad_years = df[(df["Year"] < YEAR_RANGE[0]) | (df["Year"] > YEAR_RANGE[1])]
    if len(bad_years) > 0:
        raise SchemaError(
            f"{len(bad_years)} rows have Year outside {YEAR_RANGE}; "
            f"sample:\n{bad_years.head()}"
        )

    bad_iso = df[~df["ISO3"].astype(str).str.fullmatch(r"[A-Z]{3}")]
    if len(bad_iso) > 0:
        raise SchemaError(
            f"{len(bad_iso)} rows have malformed ISO3 codes; "
            f"sample values: {bad_iso['ISO3'].unique()[:10]}"
        )

    # Values are numeric for continuous metrics; binary/categorical metrics
    # may carry strings. Keep the raw value and add a numeric view; the
    # non-numeric share is reported, not treated as an error.
    df["Value_raw"] = df["Value"]
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df


def metric_coverage(df: pd.DataFrame) -> pd.DataFrame:
    cov = (
        df.groupby(["Metric", "Source"], sort=True)
        .agg(
            n_rows=("Value", "size"),
            n_countries=("ISO3", "nunique"),
            year_min=("Year", "min"),
            year_max=("Year", "max"),
            n_numeric=("Value", "count"),
        )
        .reset_index()
    )
    cov["pct_numeric"] = (cov["n_numeric"] / cov["n_rows"] * 100).round(1)
    return cov.sort_values("n_rows", ascending=False)


def wave_report(df: pd.DataFrame, cov: pd.DataFrame, tag: str, source_csv: Path) -> str:
    dup_key = ["Year", "ISO3", "Metric", "Source"]
    n_dups = int(df.duplicated(subset=dup_key).sum())
    pct_numeric = df["Value"].notna().mean() * 100
    lines = [
        f"# GAID wave report — {tag}",
        "",
        f"- Source file: `{source_csv.name}`",
        f"- Rows: {len(df):,}",
        f"- Unique metrics: {df['Metric'].nunique():,}",
        f"- Countries/territories (ISO3): {df['ISO3'].nunique()}",
        f"- Year range: {int(df['Year'].min())}–{int(df['Year'].max())}",
        f"- Sources: {df['Source'].nunique()} "
        f"({', '.join(sorted(df['Source'].dropna().unique()))})",
        f"- Numeric values: {pct_numeric:.1f}% of rows",
        f"- Duplicate ({', '.join(dup_key)}) rows: {n_dups:,}",
        "",
        "## Rows per source",
        "",
        df["Source"].value_counts().to_frame("rows").to_markdown(),
        "",
        "## Top 20 metrics by coverage",
        "",
        cov.head(20).to_markdown(index=False),
        "",
    ]
    return "\n".join(lines)


def harmonise(wave_dir: Path, tag: str, repo_root: Path) -> dict:
    csv_path = find_ground_truth_csv(wave_dir)
    df = load_canonical(csv_path)
    cov = metric_coverage(df)

    processed = repo_root / "data" / "processed" / tag
    reports = repo_root / "reports" / tag
    processed.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    parquet = processed / "gaid_canonical.parquet"
    df.to_parquet(parquet, index=False)
    cov.to_csv(reports / "metric_coverage.csv", index=False)
    (reports / "wave_report.md").write_text(wave_report(df, cov, tag, csv_path))

    return {
        "tag": tag,
        "source_csv": str(csv_path),
        "rows": len(df),
        "metrics": int(df["Metric"].nunique()),
        "countries": int(df["ISO3"].nunique()),
        "year_min": int(df["Year"].min()),
        "year_max": int(df["Year"].max()),
        "parquet": str(parquet),
        "report": str(reports / "wave_report.md"),
    }
