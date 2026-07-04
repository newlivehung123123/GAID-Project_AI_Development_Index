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

from . import dataverse, harmonise as harmonise_mod, screening

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


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


def cmd_status(_args) -> int:
    manifest = dataverse.load_manifest(DATA_DIR)
    if manifest is None:
        print("Nothing installed.")
    else:
        print(json.dumps(manifest, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gaid_pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="compare Dataverse against local install")
    p_sync = sub.add_parser("sync", help="download + extract the latest wave")
    p_sync.add_argument("--force", action="store_true",
                        help="re-download even if already up to date")
    sub.add_parser("harmonise", help="validate installed wave into canonical dataset")
    sub.add_parser("screen", help="run indicator screening on the installed wave")
    sub.add_parser("status", help="show the local manifest")
    args = parser.parse_args(argv)
    return {"check": cmd_check, "sync": cmd_sync, "harmonise": cmd_harmonise,
            "screen": cmd_screen, "status": cmd_status}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
