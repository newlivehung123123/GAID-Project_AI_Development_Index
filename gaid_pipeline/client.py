"""Cached, budget-capped, resumable eval client (OpenRouter-compatible).

Cost discipline:
- every response is cached in SQLite keyed by (query_id, model_id); re-runs,
  reclassification, and new analyses never re-pay for a query
- a hard budget cap stops the run when cumulative cost reaches the limit
- free-tier daily rate limits stop the run gracefully; re-running the same
  command resumes from the cache
- dry-run mode synthesises deterministic fake responses into a SEPARATE
  cache so the whole downstream pipeline is testable at $0

Runs are always launched by the researcher, never automatically.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 3            # under-retrying is cheap: the cache resumes anything
REQUEST_TIMEOUT = 60       # healthy endpoints answer in ~2-5 s
MAX_CONSECUTIVE_ERRORS = 8 # then skip this model for now and move on


def _db(repo_root: Path, dry_run: bool) -> sqlite3.Connection:
    path = repo_root / "data" / "eval" / (
        "responses_dryrun.sqlite" if dry_run else "responses.sqlite")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            query_id TEXT NOT NULL,
            model_id TEXT NOT NULL,
            prompt_sha TEXT NOT NULL,
            temperature REAL NOT NULL,
            response TEXT,
            finish_reason TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            cost_usd REAL,
            endpoint TEXT,
            created TEXT,
            PRIMARY KEY (query_id, model_id)
        )""")
    return conn


def cached_ids(conn: sqlite3.Connection, model_id: str) -> set[str]:
    rows = conn.execute(
        "SELECT query_id FROM responses WHERE model_id = ?", (model_id,))
    return {r[0] for r in rows}


def _dry_response(row: pd.Series, model_id: str = "") -> str:
    """Deterministic synthetic response so downstream stages are testable.
    Seeded by (query_id, model_id) so panel models differ, which exercises
    the cross-model analyses in stats.py."""
    rng = random.Random(f"{row['query_id']}|{model_id}")
    roll = rng.random()
    if row["variant"] == "v5_structured":
        if roll < 0.5:
            return json.dumps({"value": None, "confidence": "low"})
        value = row["ground_truth"] * rng.uniform(0.7, 1.4)
        return json.dumps({"value": round(value, 3), "confidence": "medium"})
    if roll < 0.6:
        return "I don't know the specific value for that indicator and year."
    if roll < 0.75:
        return "It was relatively low, below the regional average."
    value = row["ground_truth"] * rng.uniform(0.7, 1.4)
    return f"According to available data, the value was approximately {value:,.2f}."


def _call_openrouter(endpoint: str, prompt: str, temperature: float,
                     max_tokens: int, api_key: str) -> dict:
    payload = {
        "model": endpoint,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "usage": {"include": True},
    }
    headers = {"Authorization": f"Bearer {api_key}",
               "HTTP-Referer": "https://aiinsocietyhub.com",
               "X-Title": "GAID eval pipeline"}
    delay = 2.0
    for attempt in range(MAX_RETRIES):
        resp = requests.post(OPENROUTER_URL, json=payload, headers=headers,
                             timeout=REQUEST_TIMEOUT)
        if resp.status_code == 429:
            body = resp.text.lower()
            if "free" in body and ("day" in body or "daily" in body):
                raise DailyLimitReached(resp.text[:300])
            retry_after = resp.headers.get("Retry-After", "")
            wait = float(retry_after) if retry_after.replace(".", "", 1).isdigit() \
                else delay
            time.sleep(min(wait, 120))
            delay = min(delay * 2, 60)
            continue
        if resp.status_code >= 500:
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Exhausted retries for one query on {endpoint}")


class DailyLimitReached(RuntimeError):
    """Free-tier daily quota hit: stop gracefully, resume tomorrow."""


class EndpointStalled(RuntimeError):
    """Endpoint hanging or erroring repeatedly: skip this model for now."""


def run_eval(queries: pd.DataFrame, model: dict, repo_root: Path, *,
             budget_usd: float, generation: dict, dry_run: bool = False,
             limit: int | None = None, use_free_endpoint: bool = True,
             workers: int = 4) -> dict:
    model_id = model["id"]
    endpoint = (model.get("free_endpoint") or model["endpoint"]
                ) if use_free_endpoint else model["endpoint"]
    conn = _db(repo_root, dry_run)
    done = cached_ids(conn, model_id)
    todo = queries[~queries["query_id"].isin(done)]
    if limit:
        todo = todo.head(limit)

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not dry_run and not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set (put it in .env or export it)")

    spent = 0.0
    completed = 0
    stop_reason = "finished"
    if not dry_run:
        print(f"[{model_id}] {len(todo)} queries to run on {endpoint} "
              f"({len(done)} already cached) — budget ${budget_usd}",
              file=sys.stderr)

    def work(row: pd.Series) -> tuple[pd.Series, str, dict]:
        if dry_run:
            return row, _dry_response(row, model_id), {
                "cost": 0.0, "prompt_tokens": 0, "completion_tokens": 0}
        body = _call_openrouter(endpoint, row["prompt"],
                                generation["temperature"],
                                generation["max_tokens"], api_key)
        text = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {}) or {}
        return row, text, usage

    failed = 0
    consecutive_errors = 0
    try:
        with ThreadPoolExecutor(max_workers=1 if dry_run else workers) as pool:
            futures = [pool.submit(work, row) for _, row in todo.iterrows()]
            for fut in as_completed(futures):
                try:
                    row, text, usage = fut.result()
                except DailyLimitReached:
                    raise
                except Exception as exc:
                    # one bad query never crashes a run: count it, keep going;
                    # a WALL of failures means the endpoint itself is sick
                    failed += 1
                    consecutive_errors += 1
                    print(f"[{model_id}] query failed "
                          f"({type(exc).__name__}: {str(exc)[:80]}) — "
                          f"{consecutive_errors} consecutive", file=sys.stderr)
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        stop_reason = (
                            f"endpoint stalling/erroring "
                            f"({consecutive_errors} consecutive failures) — "
                            f"skipped for now; re-run later to resume")
                        for f in futures:
                            f.cancel()
                        break
                    continue
                consecutive_errors = 0
                cost = float(usage.get("cost") or 0.0)
                spent += cost
                conn.execute(
                    "INSERT OR REPLACE INTO responses VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (row["query_id"], model_id,
                     hashlib.sha1(row["prompt"].encode()).hexdigest()[:16],
                     generation["temperature"], text, "stop",
                     usage.get("prompt_tokens"), usage.get("completion_tokens"),
                     cost, endpoint,
                     datetime.now(timezone.utc).isoformat(timespec="seconds")))
                conn.commit()
                completed += 1
                if not dry_run and completed % 100 == 0:
                    print(f"[{model_id}] {completed}/{len(todo)} done — "
                          f"${spent:.2f} spent", file=sys.stderr)
                if spent >= budget_usd:
                    stop_reason = f"budget cap ${budget_usd} reached"
                    for f in futures:
                        f.cancel()
                    break
    except DailyLimitReached as exc:
        stop_reason = f"free-tier daily limit: {exc}"
    finally:
        conn.close()

    return {
        "model": model_id, "endpoint": endpoint, "dry_run": dry_run,
        "already_cached": len(done), "completed_this_session": completed,
        "failed_this_session": failed,
        "remaining": len(todo) - completed, "spent_usd": round(spent, 4),
        "stop_reason": stop_reason,
        "resume": "re-run the same command; cached queries are skipped",
    }


def load_responses(repo_root: Path, dry_run: bool = False) -> pd.DataFrame:
    conn = _db(repo_root, dry_run)
    df = pd.read_sql_query("SELECT * FROM responses", conn)
    conn.close()
    return df
