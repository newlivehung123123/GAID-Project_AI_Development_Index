"""Build the four black-and-white figures for the GAID AI Development Index
paper. Run after `python -m gaid_pipeline indices`.

    python paper/make_figures.py

Every figure is checked for overlapping text by figure_audit.audit before it
is written, so a figure cannot be saved with colliding labels.
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.transforms import Bbox

from gaid_pipeline import indices as IX
from figure_audit import audit, _area

OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.edgecolor": "black", "axes.linewidth": 0.8,
                     "savefig.dpi": 400, "savefig.bbox": "tight"})

# ---------------------------------------------------------------------------
# Figure 1: the pipeline, deposit to published index
# ---------------------------------------------------------------------------
S = [
 ("Source deposit",
  "Harvard Dataverse, doi 10.7910/DVN/PUMGYU, wave 1 version 2",
  "MD5 checksum and file size checked before every run"),
 ("Harmonisation",
  "one long panel keyed on year, country, metric and source",
  "259,546 rows, 24,453 metrics, 227 countries and territories"),
 ("Screening and mapping",
  "indicators assigned to 22 components in six pillars",
  "composite indices published by others are held out and are never used as components"),
 ("Edition assembly",
  "latest observation within three years of the edition year",
  "editions 2000 to 2025"),
 ("Transformation",
  "log1p on skewed counts, winsorise, min-max to 0 to 100",
  "direction applied so that a higher score is always the better outcome"),
 ("Aggregation",
  "equal weights within each group, then equal across groups",
  "a pillar needs half of its components and the overall index needs four pillars"),
 ("Validation and audit",
  "reliability, dimensionality, normalisation variants, convergence",
  "reported in full and never used to reweight the index"),
 ("Outputs",
  "pillar scores, overall index, policy lenses, country profiles",
  "5,381 panel rows, 227 country profiles"),
]

W = 7.4
BX0, BX1 = 0.05, 4.15
NX0, NX1 = 4.45, 7.35
PAD = 0.14
FS_H, FS_B, FS_N = 8.6, 7.6, 7.4
LH_H, LH_B, LH_N = FS_H*1.4/72, FS_B*1.38/72, FS_N*1.38/72
GAP = 0.30

probe = plt.figure(figsize=(W, 10)); probe.canvas.draw()
rend = probe.canvas.get_renderer()

def wrap(s, avail, fs):
    """Widest wrap whose longest line fits `avail` inches."""
    for width in range(len(s) + 1, 8, -1):
        lines = textwrap.wrap(s, width)
        longest = max(
            probe.text(0, 0, ln, fontsize=fs).get_window_extent(rend).width
            for ln in lines) / probe.dpi
        if longest <= avail:
            return lines
    return textwrap.wrap(s, 12)

rows = []
for head, body, note in S:
    hl = wrap(head, BX1 - BX0 - 2*PAD - 0.30, FS_H)
    bl = wrap(body, BX1 - BX0 - 2*PAD - 0.08, FS_B)
    nl = wrap(note, NX1 - NX0 - 0.08, FS_N)
    hbox = 2*PAD + len(hl)*LH_H + 0.06 + len(bl)*LH_B
    rows.append((hl, bl, nl, max(hbox, len(nl)*LH_N + 0.16)))
plt.close(probe)

H = sum(r[3] for r in rows) + GAP*(len(rows)-1) + 0.06
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

boxes, inner, notes = [], [], []
y = H - 0.03
for i, (hl, bl, nl, bh) in enumerate(rows):
    y1, y0 = y, y - bh
    shade = 0.945 - 0.175 * (i / (len(rows) - 1))
    ax.add_patch(FancyBboxPatch(
        (BX0, y0), BX1 - BX0, bh,
        boxstyle="round,pad=0.004,rounding_size=0.06",
        linewidth=1.0, edgecolor="black", facecolor=str(shade),
        linestyle=(0, (4, 2)) if i == 6 else "solid"))
    boxes.append((BX0, y0, BX1, y1))

    ty = y1 - PAD - LH_H*0.78
    inner.append((i, ax.text(BX0 + PAD, ty, f"{i+1}", fontsize=FS_H,
                             fontweight="bold", va="baseline", ha="left")))
    for j, ln in enumerate(hl):
        inner.append((i, ax.text(BX0 + PAD + 0.30, ty - j*LH_H, ln,
                                 fontsize=FS_H, fontweight="bold",
                                 va="baseline", ha="left")))
    ty -= len(hl)*LH_H + 0.06
    for j, ln in enumerate(bl):
        inner.append((i, ax.text(BX0 + PAD, ty - j*LH_B, ln, fontsize=FS_B,
                                 va="baseline", ha="left")))

    ny = (y0 + y1)/2 + (len(nl)-1)*LH_N/2 - LH_N*0.30
    for j, ln in enumerate(nl):
        notes.append(ax.text(NX0, ny - j*LH_N, ln, fontsize=FS_N,
                             va="baseline", ha="left", color="0.15"))

    if i < len(rows) - 1:
        ax.add_patch(FancyArrowPatch((2.0, y0 - 0.03), (2.0, y0 - GAP + 0.02),
                                     arrowstyle="-|>", mutation_scale=11,
                                     linewidth=1.0, color="black"))
    y = y0 - GAP

bad = audit(fig, "figure 1", text_vs_patch=False)
fig.canvas.draw(); rr = fig.canvas.get_renderer()
def bpx(b):
    (X0, Y0), (X1, Y1) = ax.transData.transform([[b[0], b[1]], [b[2], b[3]]])
    return Bbox([[X0, Y0], [X1, Y1]])
for i, t in inner:
    b, B = t.get_window_extent(rr), bpx(boxes[i])
    if not (b.x0 >= B.x0-1 and b.x1 <= B.x1+1 and b.y0 >= B.y0-1 and b.y1 <= B.y1+1):
        bad.append(f"box {i+1} text escapes its box: {t.get_text()[:44]!r}")
for t in notes:
    b = t.get_window_extent(rr)
    for k, bx in enumerate(boxes):
        if _area(b, bpx(bx)) > 1:
            bad.append(f"note over box {k+1}: {t.get_text()[:44]!r}")
print("[figure 1 containment]", "OVERLAPS" if bad else "clean",
      *("\n    " + x for x in bad))

fig.savefig(OUT / "figure1_workflow.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# Figures 2 to 4: coverage, pillar coverage by income tier, rank stability
# ---------------------------------------------------------------------------
cfg = IX.load_config(ROOT)
df  = pd.read_parquet(ROOT / "data" / "processed" / "w1_v2" / "gaid_canonical.parquet")
df  = df[df["Value"].notna()]
meta = json.load(open(ROOT / "site" / "data" / "meta.json"))
inc = {c["iso3"]: (c.get("income") or "Unclassified") for c in meta["countries"]}

pil25 = IX.compute_edition(df, cfg, 2025)
frame = pd.DataFrame({p: v["score"] for p, v in pil25.items()})
npill = frame.notna().sum(axis=1)
TIERS = ["High income", "Upper middle income", "Lower middle income",
         "Low income", "Unclassified"]
SHADE = [0.15, 0.42, 0.66, 0.88, 1.00]    # greyscale ramp, dark = high income

# ---- Figure 2: coverage cliff, stacked by income tier -----------------------
ks = list(range(1, 7))
mat = np.array([[sum(1 for i in npill[npill >= k].index if inc.get(i) == t)
                 for k in ks] for t in TIERS])
fig, ax = plt.subplots(figsize=(5.4, 3.4))
bottom = np.zeros(len(ks))
for row, t, s in zip(mat, TIERS, SHADE):
    ax.bar(ks, row, 0.62, bottom=bottom, label=t, color=str(s),
           edgecolor="black", linewidth=0.6)
    bottom += row
for k, tot in zip(ks, mat.sum(axis=0)):
    ax.text(k, tot + 4, str(tot), ha="center", va="bottom", fontsize=8.5)
ax.axvline(3.5, color="black", lw=0.9, ls=(0, (4, 3)))
ax.text(3.60, 126, "threshold for the\noverall index", fontsize=7.6,
            ha="left", va="center")
ax.set_xlabel("Minimum number of pillars a country must score")
ax.set_ylabel("Countries and territories")
ax.set_xticks(ks); ax.set_ylim(0, 232)
ax.legend(frameon=False, fontsize=7.2, loc="upper right", handlelength=1.3,
          labelspacing=0.32)
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
audit(fig, "figure 2")
fig.savefig(OUT / "figure2_coverage_cliff.png"); plt.close(fig)

# ---- Figure 3: pillar coverage by income tier -------------------------------
names = {p: cfg["pillars"][p]["name"] for p in cfg["pillars"]}
pids = list(cfg["pillars"])
pm = np.array([[int(frame[p].notna()[[i for i in frame.index if inc.get(i) == t]].sum())
                for p in pids] for t in TIERS])
fig, ax = plt.subplots(figsize=(5.8, 3.4))
y = np.arange(len(pids)); left = np.zeros(len(pids))
for row, t, s in zip(pm, TIERS, SHADE):
    ax.barh(y, row, 0.6, left=left, label=t, color=str(s),
            edgecolor="black", linewidth=0.6)
    left += row
for i, tot in enumerate(pm.sum(axis=0)):
    ax.text(tot + 3, i, str(tot), va="center", fontsize=8.5)
ax.set_yticks(y); ax.set_yticklabels([f"{p}  {names[p]}" for p in pids], fontsize=8.2)
ax.invert_yaxis(); ax.set_xlim(0, 218)
ax.set_xlabel("Countries and territories scored, 2025 edition")
ax.legend(frameon=False, fontsize=7.2, loc="center left",
          bbox_to_anchor=(0.72, 0.30), handlelength=1.3)
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
audit(fig, "figure 3")
fig.savefig(OUT / "figure3_pillar_coverage.png"); plt.close(fig)

# ---- Figure 4: rank stability under normalisation variants -------------------
ov_id = cfg["overall"]["id"]
base = IX.aggregate_indices(pil25, cfg)[ov_id]
variants = {}
for m in ("zscore", "percentile"):
    variants[m] = IX.aggregate_indices(IX.compute_edition(df, cfg, 2025, m), cfg)[ov_id]
fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.3), sharey=True)
for ax, (m, s) in zip(axes, variants.items()):
    j = pd.concat([base, s], axis=1, keys=["a", "b"]).dropna()
    ra, rb = j["a"].rank(ascending=False), j["b"].rank(ascending=False)
    rho = j["a"].corr(j["b"], method="spearman")
    ax.plot([0, 66], [0, 66], color="black", lw=0.7, ls=(0, (4, 3)))
    ax.scatter(ra, rb, s=15, facecolor="0.55", edgecolor="black", linewidth=0.5)
    ax.set_xlabel("Rank, headline min-max")
    ax.set_title(f"{m} normalisation\nSpearman rho = {rho:.3f}  (n = {len(j)})",
                 fontsize=8.5)
    ax.set_xlim(0, 67); ax.set_ylim(0, 67)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
axes[0].set_ylabel("Rank, variant normalisation")
audit(fig, "figure 4", text_vs_patch=False)
fig.savefig(OUT / "figure4_rank_stability.png"); plt.close(fig)
print("cliff totals", mat.sum(axis=0).tolist())
print("pillar totals", pm.sum(axis=0).tolist())
for m, s in variants.items():
    j = pd.concat([base, s], axis=1, keys=["a","b"]).dropna()
    print(m, "n =", len(j), "rho =", round(j["a"].corr(j["b"], method="spearman"), 4))
