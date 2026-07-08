"""One-off cleanup for the 2026-07-08 reasoning-truncation incident.

glm-5-2 and gpt-5-5 were elicited with provider-default reasoning enabled;
max_tokens (220) was consumed by hidden thinking, so their cached responses
are overwhelmingly empty (glm 92%, gpt-5.5 100%) or contain provider
truncation warnings instead of answers. This script:

  1. archives ALL cached rows for the two models to a quarantine parquet
     (auditability — the spend and the failure mode stay on record), then
  2. deletes them from the response cache, so the fixed elicitation
     (reasoning off / minimal, see config/models.yaml) re-runs them cleanly.

Run only while no eval session is writing to the cache.
"""

from datetime import date
from pathlib import Path
import sqlite3

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "data" / "eval" / "responses.sqlite"
MODELS = ("glm-5-2", "gpt-5-5")

conn = sqlite3.connect(DB)
ph = ",".join("?" * len(MODELS))
df = pd.read_sql_query(
    f"SELECT * FROM responses WHERE model_id IN ({ph})", conn, params=MODELS)
if df.empty:
    print("nothing to quarantine — cache already clean")
else:
    out = DB.parent / f"quarantine_reasoning_incident_{date.today().isoformat()}.parquet"
    df.to_parquet(out, index=False)
    conn.execute(f"DELETE FROM responses WHERE model_id IN ({ph})", MODELS)
    conn.commit()
    conn.execute("VACUUM")
    empty = int((df["response"].isna() | (df["response"].str.strip() == "")).sum())
    print(f"quarantined {len(df)} rows ({empty} empty, "
          f"${df['cost_usd'].sum():.2f} sunk) -> {out.name}")
    print("cache is clean; both models will re-run in full under the "
          "fixed elicitation settings")
conn.close()
