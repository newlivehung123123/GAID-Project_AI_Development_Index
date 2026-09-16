"""Bounding box overlap audit for the paper figures."""
from matplotlib.transforms import Bbox

def _bb(a, r):
    try:
        b = a.get_window_extent(r)
    except TypeError:
        b = a.get_window_extent()
    return b

def _area(p, q):
    w = min(p.x1, q.x1) - max(p.x0, q.x0)
    h = min(p.y1, q.y1) - max(p.y0, q.y0)
    return w * h if w > 0 and h > 0 else 0.0

def audit(fig, name, text_vs_patch=True, tol=1.0):
    fig.canvas.draw(); r = fig.canvas.get_renderer()
    items, patches = [], []
    for ax in fig.axes:
        for t in ax.texts:
            if t.get_text().strip():
                items.append((f"text {t.get_text()!r}", _bb(t, r)))
        for lab, tag in ((ax.xaxis.label, "xlabel"), (ax.yaxis.label, "ylabel"),
                         (ax.title, "title")):
            if lab.get_text().strip():
                items.append((f"{tag} {lab.get_text()[:24]!r}", _bb(lab, r)))
        for axis, labs in ((ax.xaxis, ax.get_xticklabels()),
                           (ax.yaxis, ax.get_yticklabels())):
            lo, hi = sorted(axis.get_view_interval())
            for loc, t in zip(axis.get_ticklocs(), labs):
                if t.get_text().strip() and t.get_visible() and lo <= loc <= hi:
                    items.append((f"tick {t.get_text()[:24]!r}", _bb(t, r)))
        leg = ax.get_legend()
        if leg is not None:
            items.append(("legend", _bb(leg, r)))
        for p in ax.patches:
            try:
                patches.append(_bb(p, r))
            except Exception:
                pass

    bad = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a = _area(items[i][1], items[j][1])
            if a > tol:
                bad.append(f"{items[i][0]}  x  {items[j][0]}  ({a:.0f} px2)")
    if text_vs_patch:
        for lbl, bb in items:
            if lbl.startswith(("tick", "xlabel", "ylabel", "title")):
                continue
            for pb in patches:
                a = _area(bb, pb)
                if a > tol:
                    bad.append(f"{lbl}  x  bar patch  ({a:.0f} px2)")
    print(f"[{name}] {'OVERLAPS' if bad else 'clean'}"
          + ("".join("\n    " + b for b in bad) if bad else ""))
    return bad
