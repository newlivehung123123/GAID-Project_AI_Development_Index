"""Command-line entry point for the GAID pipeline.

    python -m gaid_pipeline check       # is there a newer wave on Dataverse?
    python -m gaid_pipeline sync        # download + extract it if so
    python -m gaid_pipeline harmonise   # validate installed wave -> canonical dataset
    python -m gaid_pipeline status      # what is installed locally
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import (client, dashboard_data, dataverse, harmonise as harmonise_mod,
               indices as indices_mod, queries as queries_mod,
               results as results_mod, screening, site_build,
               stats as stats_mod, validate as validate_mod, watch as watch_mod)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from .env (gitignored) so secrets never live in
    code and never need a manual `export`. Real env vars take precedence."""
    import os
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def cmd_check(_args) -> int:
    latest, manifest, new = dataverse.check(DATA_DIR)
    installed = manifest["installed"]["filename"] if manifest else "nothing"
    print(f"Latest on Dataverse : {latest.filename} "
          f"(dataset {latest.dataset_doi}, v{latest.dataset_version})")
    print(f"Installed locally   : {installed}")
    print(f"New wave available  : {'YES' if new else 'no'}")
    return 0


def cmd_sync(args) -> int:
    result = dataverse.sync(DATA_DIR, force=args.force)
    if result["changed"]:
        m = result["manifest"]
        print(f"Synced {m['installed']['filename']} -> {m['extracted_to']}")
    else:
        print("Already up to date.")
    return 0


def cmd_harmonise(_args) -> int:
    manifest = dataverse.load_manifest(DATA_DIR)
    if manifest is None:
        print("Nothing installed. Run `python -m gaid_pipeline sync` first.",
              file=sys.stderr)
        return 1
    wave = manifest["installed"]
    tag = f"w{wave['wave']}_v{wave['version']}"
    summary = harmonise_mod.harmonise(Path(manifest["extracted_to"]), tag, REPO_ROOT)
    print(json.dumps(summary, indent=2))
    return 0


def _installed_tag() -> str | None:
    manifest = dataverse.load_manifest(DATA_DIR)
    if manifest is None:
        return None
    wave = manifest["installed"]
    return f"w{wave['wave']}_v{wave['version']}"


def cmd_screen(_args) -> int:
    tag = _installed_tag()
    if tag is None:
        print("Nothing installed. Run sync + harmonise first.", file=sys.stderr)
        return 1
    parquet = DATA_DIR / "processed" / tag / "gaid_canonical.parquet"
    if not parquet.exists():
        print(f"{parquet} not found. Run `python -m gaid_pipeline harmonise` first.",
              file=sys.stderr)
        return 1
    summary = screening.screen(parquet, tag, REPO_ROOT)
    print(json.dumps(summary, indent=2))
    return 0


def cmd_indices(_args) -> int:
    tag = _installed_tag()
    parquet = DATA_DIR / "processed" / tag / "gaid_canonical.parquet"
    if tag is None or not parquet.exists():
        print("Run sync + harmonise first.", file=sys.stderr)
        return 1
    print(json.dumps(indices_mod.build_indices(parquet, tag, REPO_ROOT), indent=2))
    return 0


def cmd_site_data(_args) -> int:
    tag = _installed_tag()
    canonical = DATA_DIR / "processed" / tag / "gaid_canonical.parquet"
    idx = DATA_DIR / "processed" / tag / "indices.parquet"
    if tag is None or not canonical.exists() or not idx.exists():
        print("Run sync + harmonise + indices first.", file=sys.stderr)
        return 1
    print(json.dumps(dashboard_data.build_site_data(canonical, idx, tag,
                                                    REPO_ROOT), indent=2))
    return 0


def cmd_site_build(_args) -> int:
    if not (REPO_ROOT / "site" / "data" / "meta.json").exists():
        print("Run `python -m gaid_pipeline site-data` first.", file=sys.stderr)
        return 1
    print(json.dumps(site_build.build_site(REPO_ROOT), indent=2))
    return 0


def cmd_queries(_args) -> int:
    tag = _installed_tag()
    obs = DATA_DIR / "processed" / tag / "observations.parquet"
    if tag is None or not obs.exists():
        print("Run sync + harmonise + screen first.", file=sys.stderr)
        return 1
    print(json.dumps(queries_mod.generate(obs, tag, REPO_ROOT), indent=2))
    return 0


def cmd_run_eval(args) -> int:
    tag = _installed_tag()
    qpath = DATA_DIR / "processed" / tag / "queries.parquet"
    if tag is None or not qpath.exists():
        print("Run the pipeline through `queries` first.", file=sys.stderr)
        return 1
    import pandas as pd
    queries = pd.read_parquet(qpath)
    models = {m["id"]: m for m in yaml.safe_load(
        (REPO_ROOT / "config" / "models.yaml").read_text())["panel"]}
    if args.model not in models:
        print(f"Unknown model '{args.model}'. Panel: {sorted(models)}",
              file=sys.stderr)
        return 1
    generation = yaml.safe_load(
        (REPO_ROOT / "config" / "prompts.yaml").read_text())["generation"]
    summary = client.run_eval(
        queries, models[args.model], REPO_ROOT, budget_usd=args.budget,
        generation=generation, dry_run=args.dry_run, limit=args.limit,
        use_free_endpoint=not args.paid, workers=args.workers)
    print(json.dumps(summary, indent=2))
    return 0


def cmd_run_panel(args) -> int:
    """Run every `active` panel model in sequence, one budget cap each.
    Free endpoints by default; resumable exactly like run-eval."""
    tag = _installed_tag()
    qpath = DATA_DIR / "processed" / tag / "queries.parquet"
    if tag is None or not qpath.exists():
        print("Run the pipeline through `queries` first.", file=sys.stderr)
        return 1
    import pandas as pd
    queries = pd.read_parquet(qpath)
    panel = yaml.safe_load(
        (REPO_ROOT / "config" / "models.yaml").read_text())["panel"]
    generation = yaml.safe_load(
        (REPO_ROOT / "config" / "prompts.yaml").read_text())["generation"]
    active = [m for m in panel if m.get("status") == "active"]
    summaries = []
    for model in active:
        print(f"--- {model['id']} ---", file=sys.stderr)
        summary = client.run_eval(
            queries, model, REPO_ROOT, budget_usd=args.budget_per_model,
            generation=generation, dry_run=args.dry_run,
            use_free_endpoint=not args.paid)
        summaries.append(summary)
        print(json.dumps(summary, indent=2), file=sys.stderr)
    total = sum(s["spent_usd"] for s in summaries)
    done = all(s["remaining"] == 0 for s in summaries)
    print(json.dumps({
        "models_run": [s["model"] for s in summaries],
        "total_spent_usd": round(total, 4),
        "panel_complete": done,
        "resume": None if done else "re-run the same command to continue "
                                    "from the cache",
        "sessions": summaries}, indent=2))
    return 0


def cmd_stats(args) -> int:
    tag = _installed_tag()
    if tag is None:
        print("Run sync first.", file=sys.stderr)
        return 1
    print(json.dumps(stats_mod.run_stats(
        tag, REPO_ROOT, dry_run=args.dry_run, mixed=args.mixed), indent=2))
    return 0


def cmd_watch(args) -> int:
    summary = watch_mod.run_watch(REPO_ROOT, bootstrap=args.bootstrap)
    print(json.dumps(summary, indent=2))
    # exit 2 signals "candidates found" so CI can open a notification issue
    return 2 if summary.get("new_candidates") else 0


def cmd_classify(args) -> int:
    tag = _installed_tag()
    qpath = DATA_DIR / "processed" / tag / "queries.parquet"
    print(json.dumps(results_mod.build_results(
        qpath, tag, REPO_ROOT, dry_run=args.dry_run), indent=2))
    return 0


def cmd_validate_export(args) -> int:
    tag = _installed_tag()
    suffix = "_dryrun" if args.dry_run else ""
    rpath = DATA_DIR / "processed" / tag / f"results{suffix}.parquet"
    out = REPO_ROOT / "reports" / tag / "human_coding.csv"
    print(json.dumps(validate_mod.export_sample(rpath, out), indent=2))
    return 0


def cmd_validate_kappa(_args) -> int:
    tag = _installed_tag()
    coded = REPO_ROOT / "reports" / tag / "human_coding.csv"
    print(json.dumps(validate_mod.cohen_kappa(coded), indent=2))
    return 0


def cmd_status(_args) -> int:
    manifest = dataverse.load_manifest(DATA_DIR)
    if manifest is None:
        print("Nothing installed.")
    else:
        print(json.dumps(manifest, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(prog="gaid_pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="compare Dataverse against local install")
    p_sync = sub.add_parser("sync", help="download + extract the latest wave")
    p_sync.add_argument("--force", action="store_true",
                        help="re-download even if already up to date")
    sub.add_parser("harmonise", help="validate installed wave into canonical dataset")
    sub.add_parser("screen", help="run indicator screening on the installed wave")
    sub.add_parser("indices", help="compute composite indices + validation report")
    sub.add_parser("site-data", help="export static JSON for the dashboard")
    sub.add_parser("site-build", help="generate the static dashboard site (site/dist)")
    sub.add_parser("queries", help="generate the versioned query set")
    p_run = sub.add_parser("run-eval", help="run one model over the query set "
                                            "(cached, budget-capped, resumable)")
    p_run.add_argument("--model", required=True)
    p_run.add_argument("--budget", type=float, default=5.0,
                       help="hard USD cap for this session (default 5)")
    p_run.add_argument("--limit", type=int, default=None,
                       help="max queries this session")
    p_run.add_argument("--dry-run", action="store_true",
                       help="synthetic responses, $0, separate cache")
    p_run.add_argument("--workers", type=int, default=4,
                       help="parallel request threads (default 4)")
    p_run.add_argument("--paid", action="store_true",
                       help="use the paid endpoint instead of the free tier")
    p_panel = sub.add_parser("run-panel", help="run every active panel model "
                                               "(sequential, budget-capped each)")
    p_panel.add_argument("--budget-per-model", type=float, default=5.0)
    p_panel.add_argument("--dry-run", action="store_true")
    p_panel.add_argument("--paid", action="store_true")
    p_cls = sub.add_parser("classify", help="classify cached responses ($0)")
    p_cls.add_argument("--dry-run", action="store_true")
    p_stats = sub.add_parser("stats", help="statistical analysis of results ($0)")
    p_stats.add_argument("--dry-run", action="store_true")
    p_stats.add_argument("--mixed", action="store_true",
                         help="also fit the (slow) mixed-effects robustness model")
    p_watch = sub.add_parser("watch", help="flag new frontier releases "
                                           "(flag-and-wait; never runs anything)")
    p_watch.add_argument("--bootstrap", action="store_true",
                         help="record the current catalogue as baseline")
    p_vex = sub.add_parser("validate-export",
                           help="export blind-coding CSV for human validation")
    p_vex.add_argument("--dry-run", action="store_true")
    sub.add_parser("validate-kappa", help="Cohen's kappa from the coded CSV")
    sub.add_parser("status", help="show the local manifest")
    args = parser.parse_args(argv)
    return {"check": cmd_check, "sync": cmd_sync, "harmonise": cmd_harmonise,
            "screen": cmd_screen, "indices": cmd_indices,
            "site-data": cmd_site_data, "site-build": cmd_site_build,
            "queries": cmd_queries,
            "run-eval": cmd_run_eval, "run-panel": cmd_run_panel,
            "classify": cmd_classify, "stats": cmd_stats, "watch": cmd_watch,
            "validate-export": cmd_validate_export,
            "validate-kappa": cmd_validate_kappa,
            "status": cmd_status}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
