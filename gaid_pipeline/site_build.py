"""Static site generator for gaid.aiinsocietyhub.com (Phase 3).

The dashboard is generated as pages OF aiinsocietyhub.com: the header is the
site's own (AI IN SOCIETY brand, utility bar, sticky small-caps nav, Nyx/Eos
toggle) and every page follows the GAIDPage.tsx template — centred Cormorant
page title, author line, body lede, then stacked glass panels each holding a
Cormorant section title + 40px divider + content, with Source-Serif inner
cards. All values are copied verbatim from the theme source (read-only).
"""

from __future__ import annotations

import json
import math
import shutil
import time
from datetime import date
from pathlib import Path

import requests

BUILD = str(int(time.time()))  # cache-buster stamped on every asset URL

BASE_URL = "https://gaid.aiinsocietyhub.com"
MAIN_SITE = "https://aiinsocietyhub.com"
WORLD_GEOJSON = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
PILLAR_BLURBS = {
    "P1": "Publications, citation impact, patents, and responsible-AI research output.",
    "P2": "AI talent concentration, skill penetration, and AI hiring demand.",
    "P3": "Digital-government capacity (World Bank GovTech) and AI legislative activity.",
    "P4": "Private AI investment and newly funded AI companies.",
    "P5": "Frontier compute concentration: national training compute and cluster power.",
    "P6": "Responsible AI capacity (GIRAI), public attitudes, and ICT security.",
}


def world_geojson(repo_root: Path) -> Path:
    cached = repo_root / "data" / "reference" / "world.geo.json"
    if not cached.exists():
        resp = requests.get(WORLD_GEOJSON, timeout=120)
        resp.raise_for_status()
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(resp.content)
    return cached


def panel(title: str, inner: str) -> str:
    """A GAIDPage glass panel: section title + divider + content."""
    return (f'<div class="glass-panel"><h2>{title}</h2>'
            f'<div class="divider"></div>{inner}</div>')


def layout(title: str, description: str, body: str, *, depth: int = 0,
           canonical: str = "", active: str = "", body_attrs: str = "") -> str:
    p = "../" * depth
    nav = "".join(
        f'<li><a href="{p}{href}"{" class=\"active\"" if key == active else ""}>{label}</a></li>'
        for key, href, label in [("home", "index.html", "Dashboard"),
                                 ("rankings", "rankings.html", "Rankings"),
                                 ("methodology", "methodology.html", "Methodology")])
    return f"""<!DOCTYPE html>
<html lang="en" class="eos">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="website">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500;1,600&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,500;0,8..60,600;1,8..60,300;1,8..60,400;1,8..60,500;1,8..60,600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{p}assets/style.css?v={BUILD}">
<script src="{p}assets/theme.js?v={BUILD}"></script>
</head>
<body{body_attrs}>
<header class="site">
  <div class="utility">
    <a class="ubar" href="{MAIN_SITE}/">Subscribe</a>
    <div class="uright">
      <span class="ubar">Global Edition</span>
      <button id="theme-toggle" title="Toggle theme">Νύξ</button>
    </div>
  </div>
  <div class="brandwrap">
    <a class="brand" href="{MAIN_SITE}/">AI <span class="brand-mid">IN</span> SOCIETY</a>
  </div>
  <nav class="top"><ul>{nav}
    <li><a href="{MAIN_SITE}/">Back to Main Site</a></li></ul></nav>
</header>
<main class="wrap">
{body}
</main>
<footer class="site"><div class="wrap">
  <p>GAID — Global AI Dataset Project · Jason Hung ·
  data: <a href="https://doi.org/10.7910/DVN/PUMGYU">Harvard Dataverse (GAID w1 v2)</a> ·
  part of <a href="{MAIN_SITE}/">AI in Society</a>.</p>
  <p class="note">Scores are 0&ndash;100 within each annual edition (relative standing, not absolute
  progress). Countries without sufficient data are unscored &mdash; never imputed. Built {date.today().isoformat()}.</p>
</div></footer>
</body>
</html>"""


def page_title_block(title: str, byline: str, lede: str) -> str:
    """The GAIDPage.tsx opening block: h1 + author line + centred lede."""
    return f"""
<div class="page-title">
  <h1>{title}</h1>
  <p class="author-line">{byline}</p>
  <p class="lede">{lede}</p>
</div>"""


def radar_svg(scores: dict[str, float], pillars: dict[str, str]) -> str:
    ids = [pid for pid in pillars if pid in scores]
    if len(ids) < 3:
        return ""
    cx, cy, R = 130, 120, 88
    n = len(ids)
    def pt(i, r):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + r * math.cos(a), cy + r * math.sin(a)
    rings = "".join(
        '<polygon points="{}" class="radar-grid"/>'.format(
            " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, R * f) for i in range(n))))
        for f in (0.33, 0.66, 1.0))
    axes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{pt(i, R)[0]:.1f}" y2="{pt(i, R)[1]:.1f}" class="radar-grid"/>'
        for i in range(n))
    labels = "".join(
        f'<text x="{pt(i, R + 16)[0]:.1f}" y="{pt(i, R + 16)[1]:.1f}" font-size="12" '
        f'text-anchor="middle" class="radar-label">{ids[i]}</text>'
        for i in range(n))
    shape = " ".join(f"{x:.1f},{y:.1f}" for x, y in
                     (pt(i, R * scores[ids[i]] / 100) for i in range(n)))
    return (f'<svg viewBox="0 0 260 250" width="260" height="250" role="img" '
            f'aria-label="Pillar radar">{rings}{axes}'
            f'<polygon points="{shape}" class="radar-shape"/>{labels}</svg>')


def fmt_score(v) -> str:
    return f"{v:.1f}" if v is not None else "–"


def build_home(meta: dict, indices: dict, latest: int) -> str:
    ranked = sorted([c for c in meta["countries"] if "overall" in c],
                    key=lambda c: c["overall"]["rank"])
    rows = "".join(
        f'<tr><td class="rank num">#{c["overall"]["rank"]}</td>'
        f'<td><a href="countries/{c["iso3"]}.html">{c["name"]}</a></td>'
        f'<td class="num">{c["overall"]["score"]:.1f}</td></tr>'
        for c in ranked[:20])
    pillar_cards = "".join(
        f'<div class="tone-card"><h3 class="card-title">{pid} — {name}</h3>'
        f'<p class="card-body">{PILLAR_BLURBS.get(pid, "")}</p></div>'
        for pid, name in meta["pillars"].items())
    stats = "".join(
        f'<span class="badge"><b>{v}</b>{label}</span>'
        for v, label in [
            (len(meta["countries"]), "countries &amp; territories"),
            ("1,331", "verified indicators"),
            (meta["n_ranked"], f"countries ranked ({latest})"),
            (6, "measurement pillars"),
            (meta["wave"]["tag"], "wave"),
        ])
    map_inner = f"""
    <div id="map-controls">
      <label><span>Index</span> <select id="index-select"></select></label>
      <label><span>Edition</span> <input id="edition-slider" type="range" min="0" max="0" value="0">
        <b id="edition-label"></b></label>
    </div>
    <div id="choropleth"></div>
    <div id="legend"></div>
    <p class="note" style="margin-top:0.8rem">Click a country for its full profile.
    Darker = higher relative standing.</p>"""
    top20_inner = f"""
    <table class="data"><thead><tr><th class="num">Rank</th><th>Country</th>
    <th class="num">Score</th></tr></thead><tbody>{rows}</tbody></table>
    <a class="cta-link" href="rankings.html">Full rankings with all six pillars →</a>"""
    pillars_inner = f"""
    <div class="cards-stack">{pillar_cards}</div>
    <p class="card-body" style="margin-top:1.1rem">Pillars are formative composites with nested
    equal weights; scores are min&ndash;max normalised within each annual edition.</p>
    <a class="cta-link" href="methodology.html">Full methodology and robustness results →</a>"""
    body = page_title_block(
        "Global AI Dataset (GAID) Project", "Jason Hung",
        "The GAID dashboard turns the Global AI Dataset — verified indicators from 11 "
        "international sources — into national AI development profiles, composite indices, "
        "and a living benchmark of how equitably AI capability is distributed worldwide.",
    ) + f"""
<div class="stat-line">{stats}</div>
{panel("World Map", map_inner)}
{panel(f"Top 20 — GAID AI Development Index, {latest}", top20_inner)}
{panel("Six Measurement Pillars", pillars_inner)}
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="assets/app.js?v={BUILD}"></script>"""
    return layout(
        "Global AI Dataset (GAID) Project — dashboard | AI in Society",
        "Interactive dashboard of the Global AI Dataset (GAID): AI development indices, "
        "country profiles and verified indicators for 227 countries and territories.",
        body, canonical=f"{BASE_URL}/", active="home")


def build_country_page(c: dict, profile: dict, meta: dict, latest: int) -> str:
    pillars = meta["pillars"]
    latest_scores = {}
    for pid in list(pillars) + [meta["overall_id"], *meta["lenses"]]:
        by_ed = profile["indices"].get(pid, {})
        if str(latest) in by_ed:
            latest_scores[pid] = by_ed[str(latest)]
    name, region, income = c["name"], c.get("region") or "—", c.get("income") or "unclassified"
    byline = f"{region} · {income} · {c['metrics']:,} GAID indicators"
    rank_lede = (f'Ranked <b>#{c["overall"]["rank"]}</b> of {meta["n_ranked"]} on the GAID AI '
                 f'Development Index — score <b>{c["overall"]["score"]:.1f}</b> ({latest}).'
                 if "overall" in c else
                 "Not yet ranked on the overall index (insufficient pillar coverage) — the full "
                 "indicator profile is below.")
    chips = "".join(
        f'<div class="tone-card score-chip">{pid} · {pillars[pid]}'
        f'<b>{fmt_score(latest_scores.get(pid))}</b></div>'
        for pid in pillars)
    radar = radar_svg({k: v for k, v in latest_scores.items() if k in pillars}, pillars)
    radar_block = (f'<div class="radar-wrap">{radar}<p class="card-body" style="max-width:300px">'
                   f'Pillar profile, edition {latest}. Scores are relative standing '
                   f'(0&ndash;100) among scored countries; missing axes = insufficient data.</p></div>'
                   if radar else
                   '<p class="card-body">Not enough pillar coverage for a radar profile — see the '
                   'full metric browser below.</p>')
    profile_inner = f'<div class="scores">{chips}</div>{radar_block}'
    browser_inner = f"""
    <p class="card-body">Every country-level metric in GAID w1 v2 for {name}, grouped by
    domain. Latest observations shown; search to filter.</p>
    <input id="metric-search" type="search" placeholder="Search {c["metrics"]:,} metrics…">
    <div id="metric-browser"><p class="note">Loading…</p></div>"""
    body = page_title_block(name, byline, rank_lede) + f"""
{panel("AI Development Profile", profile_inner)}
{panel(f"All GAID Indicators for {name}", browser_inner)}
<script src="../assets/country.js?v={BUILD}"></script>"""
    return layout(
        f"{name} — AI development profile | GAID | AI in Society",
        f"AI development profile of {name}: {c['metrics']:,} verified indicators across "
        f"research, talent, governance, investment, compute and responsible AI (GAID dataset).",
        body, depth=1, canonical=f"{BASE_URL}/countries/{c['iso3']}.html",
        body_attrs=f' data-iso3="{c["iso3"]}"')


def build_rankings(meta: dict, indices: dict, latest: int) -> str:
    cols = [meta["overall_id"], *meta["pillars"], *meta["lenses"]]
    heads = "".join(f'<th class="num">{"Overall" if c == meta["overall_id"] else c}</th>'
                    for c in cols)
    ranked = sorted([c for c in meta["countries"] if "overall" in c],
                    key=lambda c: c["overall"]["rank"])
    rows = []
    for c in ranked:
        cells = ""
        for col in cols:
            v = indices.get(col, {}).get(c["iso3"], {}).get(str(latest))
            cells += f'<td class="num">{fmt_score(v)}</td>'
        rows.append(f'<tr><td class="rank num">#{c["overall"]["rank"]}</td>'
                    f'<td><a href="countries/{c["iso3"]}.html">{c["name"]}</a></td>{cells}</tr>')
    table_inner = f"""
    <table class="data" id="rank-table"><thead><tr>
    <th class="num">Rank</th><th>Country</th>{heads}</tr></thead>
    <tbody>{"".join(rows)}</tbody></table>
    <script>
    document.querySelectorAll("#rank-table th").forEach((th, i) => th.addEventListener("click", () => {{
      const tb = th.closest("table").querySelector("tbody");
      const asc = th.dataset.asc !== "true"; th.dataset.asc = asc;
      [...tb.rows].sort((a, b) => {{
        const av = a.cells[i].innerText.replace(/[#,]/g, ""), bv = b.cells[i].innerText.replace(/[#,]/g, "");
        const an = parseFloat(av), bn = parseFloat(bv);
        const cmp = isNaN(an) || isNaN(bn) ? av.localeCompare(bv) : an - bn;
        return asc ? cmp : -cmp;
      }}).forEach(r => tb.appendChild(r));
    }})));
    </script>"""
    body = page_title_block(
        "Global AI Dataset (GAID) Project", "Jason Hung",
        f"Country rankings on the GAID AI Development Index, edition {latest}. All countries "
        "with sufficient coverage for the overall index (≥4 of 6 pillars); click a column "
        "header to sort, click a country for its profile.",
    ) + panel(f"Rankings — Edition {latest}", table_inner)
    return layout(f"GAID AI Development Index rankings, {latest} | AI in Society",
                  f"Country rankings on the GAID AI Development Index and its six pillars, edition {latest}.",
                  body, canonical=f"{BASE_URL}/rankings.html", active="rankings")


def build_methodology(meta: dict, latest: int) -> str:
    construction = """
    <p class="card-body">All values come from the
    <a href="https://doi.org/10.7910/DVN/PUMGYU">GAID dataset</a> (11 verified international
    sources, 227 countries and territories); no modelled or imputed values anywhere. Six
    formative pillars — Research &amp; Innovation; Talent &amp; Skills; Governance &amp;
    Regulation; AI Economy &amp; Investment; Infrastructure &amp; Compute; Responsible AI &amp;
    Society — each combine verified indicators in nested equal-weight groups.</p>
    <p class="card-body" style="margin-top:1.1rem">Scores are computed per annual edition: each
    component contributes its latest observation within a three-year lookback window, and its
    vintage is recorded. Heavy-tailed counts are log-transformed, winsorised at the 1st/99th
    percentiles, then min&ndash;max scaled to 0&ndash;100 within each edition — scores measure
    relative standing among scored countries, not absolute progress. A pillar is scored only
    when at least half its components are present; the overall index requires at least four of
    six pillars.</p>"""
    robustness = f"""
    <p class="card-body"><b>Weighting.</b> Equal-weight and PCA-derived scores correlate at
    &rho; = 0.95&ndash;1.00 across pillars — the transparent equal-weight choice is empirically
    indistinguishable from the data-driven alternative.</p>
    <p class="card-body" style="margin-top:1.1rem"><b>Normalisation sensitivity.</b> Rankings
    correlate at &rho; = 0.92&ndash;1.00 across min&ndash;max, z-score and percentile
    variants.</p>
    <p class="card-body" style="margin-top:1.1rem"><b>External validity.</b> Against the fully
    held-out Tortoise Global AI Index: overall &rho; = 0.82; Research 0.76, Talent 0.87,
    Commercial 0.73. Divergences on the government-strategy and infrastructure pillars reflect
    different constructs, documented as interpretation caveats in the per-wave report.</p>
    <p class="card-body" style="margin-top:1.1rem"><b>Internal consistency.</b> Reflective
    component groups reach Cronbach&rsquo;s &alpha; = 0.96 (GovTech; GIRAI). Pillars are
    formative composites, so cross-facet &alpha; is informational, not a test (OECD/JRC
    Handbook on Composite Indicators).</p>"""
    provenance = f"""
    <p class="card-body">The GAID dataset is published on
    <a href="https://doi.org/10.7910/DVN/PUMGYU">Harvard Dataverse</a> and updated annually;
    this dashboard rebuilds automatically from the latest wave. The pipeline (sync &rarr;
    harmonise &rarr; screen &rarr; indices &rarr; site) is open-source Python with per-wave
    validation reports. Responsible-AI components incorporate dimension scores from the
    <a href="https://www.global-index.ai/">Global Index on Responsible AI</a> with
    attribution.</p>"""
    body = page_title_block(
        "Global AI Dataset (GAID) Project", "Jason Hung",
        "How the GAID composite indices are constructed, and the robustness results behind "
        "them. The full machine-generated validation report ships with every data wave.",
    ) + (panel("Construction", construction)
         + panel(f"Robustness — Wave {meta['wave']['tag']}, Edition {latest}", robustness)
         + panel("Provenance &amp; Reuse", provenance))
    return layout("GAID methodology: composite index construction and robustness | AI in Society",
                  "How GAID composite AI indices are constructed: formative pillars, "
                  "edition-based normalisation, equal weights, and robustness results.",
                  body, canonical=f"{BASE_URL}/methodology.html", active="methodology")


def build_site(repo_root: Path) -> dict:
    data_dir = repo_root / "site" / "data"
    meta = json.loads((data_dir / "meta.json").read_text())
    indices = json.loads((data_dir / "indices.json").read_text())
    latest = meta["latest_edition"]
    dist = repo_root / "site" / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    (dist / "countries").mkdir(parents=True)

    shutil.copytree(repo_root / "site" / "assets", dist / "assets")
    shutil.copy(world_geojson(repo_root), dist / "assets" / "world.geo.json")
    shutil.copytree(data_dir, dist / "data")

    (dist / "index.html").write_text(build_home(meta, indices, latest))
    (dist / "rankings.html").write_text(build_rankings(meta, indices, latest))
    (dist / "methodology.html").write_text(build_methodology(meta, latest))

    urls = [f"{BASE_URL}/", f"{BASE_URL}/rankings.html", f"{BASE_URL}/methodology.html"]
    for c in meta["countries"]:
        profile = json.loads((data_dir / "countries" / f"{c['iso3']}.json").read_text())
        (dist / "countries" / f"{c['iso3']}.html").write_text(
            build_country_page(c, profile, meta, latest))
        urls.append(f"{BASE_URL}/countries/{c['iso3']}.html")

    (dist / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    (dist / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")

    n_pages = len(list(dist.rglob("*.html")))
    size_mb = sum(p.stat().st_size for p in dist.rglob("*") if p.is_file()) / 1e6
    return {"pages": n_pages, "urls_in_sitemap": len(urls),
            "dist_size_mb": round(size_mb, 1), "dist": str(dist)}
