"""Static site generator for gaid.aiinsocietyhub.com (Phase 3).

Generates real HTML files (SEO-indexable, no client-side routing):
  site/dist/index.html              choropleth + rankings preview + pillars
  site/dist/rankings.html           full sortable table, latest edition
  site/dist/methodology.html        methods summary + robustness results
  site/dist/countries/{ISO3}.html   227 static country profiles
  site/dist/sitemap.xml, robots.txt
plus assets and the JSON data layer copied alongside.

Deploys as plain files to the Hostinger subdomain document root; the main
WordPress site is never touched.
"""

from __future__ import annotations

import json
import math
import shutil
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://gaid.aiinsocietyhub.com"
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


def layout(title: str, description: str, body: str, *, depth: int = 0,
           canonical: str = "", active: str = "") -> str:
    p = "../" * depth
    nav = "".join(
        f'<a href="{p}{href}"{" class=\"active\"" if key == active else ""}>{label}</a>'
        for key, href, label in [("home", "index.html", "Dashboard"),
                                 ("rankings", "rankings.html", "Rankings"),
                                 ("methodology", "methodology.html", "Methodology")])
    return f"""<!DOCTYPE html>
<html lang="en">
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
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{p}assets/style.css">
</head>
<body{body_attr(body)}>
<header class="site"><div class="wrap">
  <span class="brand">Global AI Dataset</span>
  <span class="tagline">the GAID Project &mdash; measuring the world's AI landscape</span>
  <nav class="top">{nav}
    <a href="https://aiinsocietyhub.com/">AI in Society</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="site"><div class="wrap">
  <p><b>GAID — Global AI Dataset Project</b> · Jason Hung ·
  data: <a href="https://doi.org/10.7910/DVN/PUMGYU">Harvard Dataverse (GAID w1 v2)</a> ·
  part of <a href="https://aiinsocietyhub.com/">AI in Society</a>.</p>
  <p class="note">Scores are 0&ndash;100 within each annual edition (relative standing, not absolute
  progress). Countries without sufficient data are unscored &mdash; never imputed. Built {date.today().isoformat()}.</p>
</div></footer>
</body>
</html>"""


def body_attr(body: str) -> str:
    return ""  # overridden for country pages via direct string replace


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
        '<polygon points="{}" fill="none" stroke="#e2dccf" stroke-width="1"/>'.format(
            " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, R * f) for i in range(n))))
        for f in (0.33, 0.66, 1.0))
    axes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{pt(i, R)[0]:.1f}" y2="{pt(i, R)[1]:.1f}" stroke="#e2dccf"/>'
        for i in range(n))
    labels = "".join(
        f'<text x="{pt(i, R + 16)[0]:.1f}" y="{pt(i, R + 16)[1]:.1f}" font-size="12" '
        f'text-anchor="middle" fill="#5a5a5a">{ids[i]}</text>'
        for i in range(n))
    shape = " ".join(f"{x:.1f},{y:.1f}" for x, y in
                     (pt(i, R * scores[ids[i]] / 100) for i in range(n)))
    return (f'<svg viewBox="0 0 260 250" width="260" height="250" role="img" '
            f'aria-label="Pillar radar">{rings}{axes}'
            f'<polygon points="{shape}" fill="rgba(192,57,43,.25)" stroke="#c0392b" '
            f'stroke-width="2"/>{labels}</svg>')


def fmt_score(v) -> str:
    return f"{v:.1f}" if v is not None else "–"


def build_country_page(c: dict, profile: dict, meta: dict, latest: int) -> str:
    pillars = meta["pillars"]
    latest_scores = {}
    for pid in list(pillars) + [meta["overall_id"], *meta["lenses"]]:
        by_ed = profile["indices"].get(pid, {})
        if str(latest) in by_ed:
            latest_scores[pid] = by_ed[str(latest)]
    rank_html = ""
    if "overall" in c:
        rank_html = (f'<p class="rank-line">Ranked <b>#{c["overall"]["rank"]}</b> of '
                     f'{meta["n_ranked"]} &middot; GAID Index '
                     f'<b>{c["overall"]["score"]:.1f}</b> ({latest})</p>')
    chips = "".join(
        f'<div class="score-chip">{pid} · {pillars[pid]}<b>{fmt_score(latest_scores.get(pid))}</b></div>'
        for pid in pillars)
    radar = radar_svg({k: v for k, v in latest_scores.items() if k in pillars}, pillars)
    radar_block = (f'<div class="radar-wrap">{radar}<div class="note">Pillar profile, '
                   f'edition {latest}. Scores are relative standing (0&ndash;100) among '
                   f'scored countries; missing axes = insufficient data.</div></div>'
                   if radar else
                   '<p class="note">Not enough pillar coverage for a radar profile — '
                   'see the full metric browser below.</p>')
    name, region, income = c["name"], c.get("region") or "—", c.get("income") or "unclassified"
    body = f"""
<div class="hero profile-head">
  <h1>{name}</h1>
  <div class="meta-line">{region} · {income} · <b>{c["metrics"]:,}</b> GAID indicators</div>
  {rank_html}
</div>
<section><h2>AI development profile</h2>
  <div class="scores">{chips}</div>
  {radar_block}
</section>
<section><h2>All GAID indicators for {name}</h2>
  <p class="note">Every country-level metric in GAID w1 v2 for {name}, grouped by domain.
  Latest observations shown; search to filter.</p>
  <input id="metric-search" type="search" placeholder="Search {c["metrics"]:,} metrics…">
  <div id="metric-browser"><p class="note">Loading…</p></div>
</section>
<script src="../assets/country.js"></script>"""
    html = layout(
        f"{name} — AI development profile | GAID",
        f"AI development profile of {name}: {c['metrics']:,} verified indicators across "
        f"research, talent, governance, investment, compute and responsible AI (GAID dataset).",
        body, depth=1, canonical=f"{BASE_URL}/countries/{c['iso3']}.html")
    return html.replace("<body>", f'<body data-iso3="{c["iso3"]}">', 1)


def build_home(meta: dict, indices: dict, latest: int) -> str:
    ov = meta["overall_id"]
    ranked = sorted([c for c in meta["countries"] if "overall" in c],
                    key=lambda c: c["overall"]["rank"])
    rows = "".join(
        f'<tr><td class="rank num">#{c["overall"]["rank"]}</td>'
        f'<td><a href="countries/{c["iso3"]}.html">{c["name"]}</a></td>'
        f'<td class="num">{c["overall"]["score"]:.1f}</td></tr>'
        for c in ranked[:20])
    pillar_cards = "".join(
        f'<div class="pillar-card"><b>{pid} — {name}</b><p>{PILLAR_BLURBS.get(pid, "")}</p></div>'
        for pid, name in meta["pillars"].items())
    body = f"""
<div class="hero">
  <h1>The global AI landscape,<br>measured country by country.</h1>
  <p class="lede">The GAID dashboard turns the Global AI Dataset — verified indicators from 11
  international sources — into national AI development profiles, composite indices, and a living
  benchmark of how equitably AI capability is distributed worldwide.</p>
  <div class="badges">
    <span class="badge"><b>{len(meta["countries"])}</b>countries &amp; territories</span>
    <span class="badge"><b>1,331</b>verified indicators</span>
    <span class="badge"><b>{meta["n_ranked"]}</b>countries ranked ({latest})</span>
    <span class="badge"><b>6</b>measurement pillars</span>
    <span class="badge">wave <b>{meta["wave"]["tag"]}</b></span>
  </div>
</div>
<section>
  <h2>World map</h2>
  <div class="card">
    <div id="map-controls">
      <label><span>Index</span> <select id="index-select"></select></label>
      <label><span>Edition</span> <input id="edition-slider" type="range" min="0" max="0" value="0">
        <b id="edition-label"></b></label>
    </div>
    <div id="choropleth"></div>
    <div id="legend"></div>
  </div>
  <p class="note">Click a country for its full profile. Darker = higher relative standing.</p>
</section>
<section>
  <h2>Top 20 — GAID AI Development Index, {latest}</h2>
  <table class="data"><thead><tr><th class="num">Rank</th><th>Country</th>
  <th class="num">Score</th></tr></thead><tbody>{rows}</tbody></table>
  <p><a href="rankings.html">Full rankings with all six pillars →</a></p>
</section>
<section>
  <h2>Six measurement pillars</h2>
  <div class="pillars">{pillar_cards}</div>
  <p class="note">Pillars are formative composites with nested equal weights; scores are
  min&ndash;max normalised within each annual edition. <a href="methodology.html">Full
  methodology and robustness results →</a></p>
</section>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="assets/app.js"></script>"""
    return layout(
        "GAID — Global AI Dataset dashboard: national AI development profiles and indices",
        "Interactive dashboard of the Global AI Dataset (GAID): AI development indices, "
        "country profiles and verified indicators for 227 countries and territories.",
        body, canonical=f"{BASE_URL}/", active="home")


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
    body = f"""
<div class="hero"><h1>Rankings — edition {latest}</h1>
<p class="lede">All countries with sufficient coverage for the overall index (&ge;4 of 6 pillars).
Click a column header to sort; click a country for its profile. Unranked countries still have
full <a href="index.html">metric profiles</a>.</p></div>
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
    return layout(f"GAID AI Development Index rankings, {latest}",
                  f"Country rankings on the GAID AI Development Index and its six pillars, edition {latest}.",
                  body, canonical=f"{BASE_URL}/rankings.html", active="rankings")


def build_methodology(meta: dict, latest: int) -> str:
    body = f"""
<div class="hero"><h1>Methodology</h1>
<p class="lede">How GAID composite indices are built, and the robustness results behind them.
The full machine-generated validation report ships with every data wave.</p></div>
<section class="prose">
<h2>Construction</h2>
<ul>
<li><b>Data.</b> All values come from the <a href="https://doi.org/10.7910/DVN/PUMGYU">GAID
dataset</a> (11 verified international sources, 227 countries/territories). No modelled or
imputed values anywhere.</li>
<li><b>Six formative pillars</b> (Research &amp; Innovation; Talent &amp; Skills; Governance &amp;
Regulation; AI Economy &amp; Investment; Infrastructure &amp; Compute; Responsible AI &amp;
Society), each combining verified indicators in nested equal-weight groups.</li>
<li><b>Editions.</b> Scores are computed per year; each component contributes its latest
observation within a three-year lookback window, and its vintage is recorded.</li>
<li><b>Normalisation.</b> Heavy-tailed counts are log-transformed, winsorised at the 1st/99th
percentiles, then min&ndash;max scaled to 0&ndash;100 <i>within each edition</i> — scores measure
relative standing among scored countries, not absolute progress.</li>
<li><b>Coverage rules.</b> A pillar is scored only when at least half its components are present;
the overall index requires &ge;4 of 6 pillars; no imputation. Grey map areas mean
insufficient data, by design.</li>
</ul>
<h2>Robustness (wave {meta["wave"]["tag"]}, edition {latest})</h2>
<ul>
<li><b>Weighting.</b> Equal-weight and PCA-derived scores correlate at &rho; = 0.95&ndash;1.00
across pillars — the transparent equal-weight choice is empirically indistinguishable from the
data-driven alternative.</li>
<li><b>Normalisation sensitivity.</b> Rankings correlate at &rho; = 0.92&ndash;1.00 across
min&ndash;max, z-score and percentile variants.</li>
<li><b>External validity.</b> Against the fully held-out Tortoise Global AI Index: overall
&rho; = 0.82; Research 0.76, Talent 0.87, Commercial 0.73. Divergences on the government-strategy
and infrastructure pillars reflect different constructs (operational capacity vs. announced
strategy; frontier compute vs. general connectivity), and are documented as interpretation
caveats in the per-wave report.</li>
<li><b>Internal consistency.</b> Reflective component groups reach Cronbach&rsquo;s &alpha; = 0.96
(GovTech; GIRAI). Pillars themselves are formative composites, so cross-facet &alpha; is
reported for information, not as a test (OECD/JRC Handbook on Composite Indicators).</li>
</ul>
<h2>Provenance &amp; reuse</h2>
<ul>
<li>Dataset: GAID on <a href="https://doi.org/10.7910/DVN/PUMGYU">Harvard Dataverse</a>, updated
annually; this dashboard rebuilds automatically from the latest wave.</li>
<li>Pipeline: open-source Python (sync &rarr; harmonise &rarr; screen &rarr; indices &rarr; site),
with per-wave validation reports.</li>
<li>Responsible-AI components incorporate dimension scores from the
<a href="https://www.global-index.ai/">Global Index on Responsible AI</a> with attribution.</li>
</ul>
</section>"""
    return layout("GAID methodology: composite index construction and robustness",
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
