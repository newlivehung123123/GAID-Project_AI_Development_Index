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
plt.rcParams.update({"font.family": "Helvetica", "font.size": 9,
                     "axes.edgecolor": "black", "axes.linewidth": 0.8,
                     "savefig.dpi": 400, "savefig.bbox": "tight"})

# ---------------------------------------------------------------------------
# Figure 1: the pipeline, deposit to published index
# ---------------------------------------------------------------------------
S = [
 ("Download",
  "The pipeline downloads wave 1 version 2 of the panel from Harvard "
  "Dataverse, doi 10.7910/DVN/PUMGYU. Every file is checked against the "
  "deposited original."),
 ("Combine the sources",
  "All 11 source collections are combined into one panel in which each row "
  "holds one measure, for one country, in one year, alongside the source "
  "collection that reported the value. The panel has 259,546 rows, 24,453 "
  "measures and 227 countries and territories."),
 ("Select the measures",
  "The index uses 22 of the measures, assigned to six pillars. No ranking "
  "published by another organisation, such as the Tortoise Media index, "
  "supplies a measure."),
 ("Build each edition",
  "An edition is built for each year from 2000 to 2025. For every measure, "
  "an edition uses the most recent value a country has in the three years "
  "ending in the edition year. Only the 2024 and 2025 editions hold enough "
  "pillars to construct an overall ranking."),
 ("Put measures on one scale",
  "A few countries record very large counts of publications, patents and "
  "investment while most record small ones, so these counts are put on a log "
  "scale first. Values above the 99th percentile are set to the 99th "
  "percentile and values below the first percentile to the first percentile. "
  "Each measure is then rescaled to a range of 0 to 100, so the lowest "
  "country scores 0 and the highest 100. Reported security breaches are the "
  "one measure where a higher number is worse, so that measure is reversed."),
 ("Combine into pillars",
  "Measures of the same topic are averaged first, and a pillar score is the "
  "average of those group averages, so a topic with many measures cannot "
  "outweigh one with few. A country receives a pillar score only when at "
  "least half of that pillar's measures are present, and an overall score "
  "only when at least four of the six pillars are present."),
 ("Sensitivity checks",
  "Every build is tested four ways, on whether measures in the same group "
  "agree with each other, whether weights taken from the data change the "
  "ranking, whether a different rescaling changes the ranking, and whether "
  "an index built by another organisation puts countries in a similar order."),
 ("Publish",
  "The pipeline writes six pillar scores, an overall score and a readiness "
  "score for every country that qualifies, a panel of 5,381 scores covering "
  "editions 2000 to 2025, and a profile page for each of the 227 countries "
  "and territories, including the ones the index cannot score."),
]

W        = 6.6                  # full text width of the page
SP0, SP1 = 0.14, 0.225          # the gradient spine that carries direction
RX0      = 0.33                 # rules and stage text start here
NX       = 0.66                 # stage number, right aligned
TX0      = 0.80                 # heading and body, left aligned
TX1      = W - 0.04
FS_N, FS_H, FS_B = 9.2, 8.8, 7.9
LH_H, LH_B = FS_H*1.30/72, FS_B*1.34/72
PAD_T, PAD_B, GAP_HB = 0.105, 0.125, 0.050
HEAD_ROOM, FOOT_ROOM = 0.06, 0.26      # above the top rule, below the last

probe = plt.figure(figsize=(W, 10)); probe.canvas.draw()
rend = probe.canvas.get_renderer()

def wrap(s, avail, fs, weight="normal"):
    """Widest wrap whose longest line fits `avail` inches."""
    for width in range(len(s) + 1, 8, -1):
        lines = textwrap.wrap(s, width)
        longest = max(
            probe.text(0, 0, ln, fontsize=fs, fontweight=weight)
                 .get_window_extent(rend).width
            for ln in lines) / probe.dpi
        if longest <= avail:
            return lines
    return textwrap.wrap(s, 12)

rows = []
for head, body in S:
    hl = wrap(head, TX1 - TX0, FS_H, "bold")
    bl = wrap(body, TX1 - TX0, FS_B)
    rows.append((hl, bl, PAD_T + len(hl)*LH_H + GAP_HB + len(bl)*LH_B + PAD_B))
plt.close(probe)

H = sum(r[2] for r in rows) + HEAD_ROOM + FOOT_ROOM
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off"); ax.set_autoscale_on(False)

Y_TOP = H - HEAD_ROOM
Y_BOT = Y_TOP - sum(r[2] for r in rows)

# spine, pale at the deposit and solid at the published index
ax.imshow(np.linspace(0.42, 1.00, 512).reshape(-1, 1), cmap="Greys",
          vmin=0, vmax=1, extent=[SP0, SP1, Y_BOT, Y_TOP], aspect="auto",
          interpolation="bilinear", zorder=1)
ax.set_xlim(0, W); ax.set_ylim(0, H)
ax.add_patch(plt.Polygon([[SP0 - 0.033, Y_BOT], [SP1 + 0.033, Y_BOT],
                          [(SP0 + SP1)/2, Y_BOT - 0.150]],
                         closed=True, facecolor="black", edgecolor="none",
                         zorder=2))

def rule(y, lw, col="black"):
    ax.plot([RX0, TX1], [y, y], lw=lw, color=col, solid_capstyle="butt",
            zorder=2, clip_on=False)

rule(Y_TOP, 1.15)
labels, bands = [], []
y = Y_TOP
for i, (hl, bl, bh) in enumerate(rows):
    y1, y0 = y, y - bh
    bands.append((y0, y1))
    ty = y1 - PAD_T - LH_H*0.76
    labels.append((i, ax.text(NX, ty, str(i + 1), fontsize=FS_N,
                              fontweight="bold", va="baseline", ha="right")))
    for j, ln in enumerate(hl):
        labels.append((i, ax.text(TX0, ty - j*LH_H, ln, fontsize=FS_H,
                                  fontweight="bold", va="baseline",
                                  ha="left")))
    ty -= len(hl)*LH_H + GAP_HB
    for j, ln in enumerate(bl):
        labels.append((i, ax.text(TX0, ty - j*LH_B, ln, fontsize=FS_B,
                                  va="baseline", ha="left", color="0.12")))
    rule(y0, 1.15 if i == len(rows) - 1 else 0.5,
         "black" if i == len(rows) - 1 else "0.62")
    y = y0

bad = audit(fig, "figure 1", text_vs_patch=False)
fig.canvas.draw(); rr = fig.canvas.get_renderer()
def bpx(x0, y0, x1, y1):
    (X0, Y0), (X1, Y1) = ax.transData.transform([[x0, y0], [x1, y1]])
    return Bbox([[X0, Y0], [X1, Y1]])
for i, t in labels:
    b, B = t.get_window_extent(rr), bpx(RX0, bands[i][0], TX1, bands[i][1])
    if not (b.x0 >= B.x0-1 and b.x1 <= B.x1+1
            and b.y0 >= B.y0-1 and b.y1 <= B.y1+1):
        bad.append(f"stage {i+1} text leaves its band: {t.get_text()[:44]!r}")
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
VNAME = {"zscore": "z-score", "percentile": "percentile"}
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
    ax.set_title(f"{VNAME[m]} normalisation\nSpearman rho = {rho:.3f}  (n = {len(j)})",
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
    print(VNAME[m], "n =", len(j), "rho =", round(j["a"].corr(j["b"], method="spearman"), 4))
