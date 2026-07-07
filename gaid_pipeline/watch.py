"""Release watcher: flag-and-wait detection of new frontier models.

Diffs two public, key-free sources against the panel registry and a local
state file:
  1. OpenRouter's /api/v1/models catalogue (every hosted model + created date)
  2. the Hugging Face orgs listed in config/models.yaml (open-weight releases)

Nothing is ever evaluated automatically: matches are written to a report and
the command exits 2 so CI can open a notification issue. Jason reviews, adds
the model to config/models.yaml as `active`, and launches the run himself.
"""

from __future__ import annotations

import fnmatch
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

OPENROUTER_MODELS = "https://openrouter.ai/api/v1/models"
HF_ORG_MODELS = "https://huggingface.co/api/models?author={org}&sort=createdAt&direction=-1&limit=25"


def _load(repo_root: Path) -> tuple[dict, dict]:
    cfg = yaml.safe_load((repo_root / "config" / "models.yaml").read_text())
    state_path = repo_root / "data" / "reference" / "watch_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {
        "seen_openrouter": [], "seen_huggingface": []}
    return cfg, state


def _save_state(repo_root: Path, state: dict) -> None:
    path = repo_root / "data" / "reference" / "watch_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def _excluded(name: str, patterns: list[str]) -> bool:
    low = name.lower()
    return any(fnmatch.fnmatch(low, p.lower()) for p in patterns)


def _openrouter_candidates(cfg: dict, state: dict) -> list[dict]:
    crit = cfg["watch"]["criteria"]
    known = {m["endpoint"] for m in cfg["panel"]} | \
            {m.get("free_endpoint") for m in cfg["panel"]}
    seen = set(state["seen_openrouter"])
    resp = requests.get(OPENROUTER_MODELS, timeout=60)
    resp.raise_for_status()
    now = datetime.now(timezone.utc)
    min_age = timedelta(weeks=crit["min_weeks_public"])
    out = []
    for m in resp.json().get("data", []):
        mid = m.get("id", "")
        if mid in known or mid in seen or ":free" in mid:
            continue
        if _excluded(mid, crit["exclude_patterns"]):
            continue
        created = m.get("created")
        age_ok = created and (now - datetime.fromtimestamp(created, timezone.utc)) >= min_age
        out.append({
            "source": "openrouter", "id": mid,
            "name": m.get("name", mid),
            "created": datetime.fromtimestamp(created, timezone.utc)
                       .date().isoformat() if created else None,
            "min_age_met": bool(age_ok),
            "pricing_per_mtok": {
                "prompt": m.get("pricing", {}).get("prompt"),
                "completion": m.get("pricing", {}).get("completion")},
        })
        seen.add(mid)
    state["seen_openrouter"] = sorted(seen)
    return out


def _huggingface_candidates(cfg: dict, state: dict) -> list[dict]:
    crit = cfg["watch"]["criteria"]
    seen = set(state["seen_huggingface"])
    out = []
    for org in cfg["watch"]["huggingface_orgs"]:
        try:
            resp = requests.get(HF_ORG_MODELS.format(org=org), timeout=60)
            resp.raise_for_status()
        except requests.RequestException:
            continue  # HF hiccup: next weekly run catches up
        for m in resp.json():
            mid = m.get("modelId") or m.get("id", "")
            if mid in seen or _excluded(mid, crit["exclude_patterns"]):
                continue
            out.append({"source": "huggingface", "id": mid,
                        "created": (m.get("createdAt") or "")[:10] or None,
                        "downloads": m.get("downloads")})
            seen.add(mid)
    state["seen_huggingface"] = sorted(seen)
    return out


def run_watch(repo_root: Path, *, bootstrap: bool = False) -> dict:
    """bootstrap=True marks everything currently visible as seen without
    reporting it — run once at setup so only FUTURE releases are flagged."""
    cfg, state = _load(repo_root)
    or_cands = _openrouter_candidates(cfg, state)
    hf_cands = _huggingface_candidates(cfg, state)
    _save_state(repo_root, state)

    if bootstrap:
        return {"bootstrapped": True,
                "marked_seen": {"openrouter": len(or_cands),
                                "huggingface": len(hf_cands)},
                "note": "baseline recorded; future runs flag only new releases"}

    candidates = or_cands + hf_cands
    report_dir = repo_root / "reports"
    report_dir.mkdir(exist_ok=True)
    if candidates:
        stamp = datetime.now(timezone.utc).date().isoformat()
        lines = [f"# Release watch — {stamp}", "",
                 "Policy: flag-and-wait. Review each candidate; to evaluate "
                 "one, add it to `config/models.yaml` as `active` and launch "
                 "`run-eval` yourself.", ""]
        for c in candidates:
            lines.append(f"- **{c['id']}** ({c['source']}, created "
                         f"{c.get('created')}) "
                         + (f"prompt ${c['pricing_per_mtok']['prompt']}/tok"
                            if c.get("pricing_per_mtok") else ""))
        (report_dir / "watch_report.md").write_text("\n".join(lines) + "\n")

    return {"new_candidates": len(candidates),
            "openrouter": [c["id"] for c in or_cands],
            "huggingface": [c["id"] for c in hf_cands],
            "report": str(report_dir / "watch_report.md") if candidates else None,
            "policy": "flag-and-wait — nothing runs automatically"}
