/* Home page: choropleth + scatter plot (d3), one edition control for both.
   Hovering a country in either view shows the shared national-profile card
   (profile.js), as on the CORDA dashboard. */
(async function () {
  const [meta, indices, world] = await Promise.all([
    fetch("/data/meta.json").then(r => r.json()),
    fetch("/data/indices.json").then(r => r.json()),
    fetch("/assets/world.geo.json").then(r => r.json()),
  ]);

  const names = Object.fromEntries(meta.countries.map(c => [c.iso3, c.name]));
  const indexSel = document.getElementById("index-select");
  const edSlider = document.getElementById("edition-slider");
  const edLabel = document.getElementById("edition-label");
  const sx = document.getElementById("scatter-x");
  const sy = document.getElementById("scatter-y");

  const ids = [meta.overall_id, ...Object.keys(meta.pillars), ...Object.keys(meta.lenses)];
  const labels = {
    [meta.overall_id]: "Overall — GAID AI Development Index",
    ...Object.fromEntries(Object.entries(meta.pillars).map(([k, v]) => [k, k + " — " + v])),
    ...Object.fromEntries(Object.entries(meta.lenses).map(([k, v]) => [k, v])),
  };
  for (const sel of [indexSel, sx, sy]) {
    if (!sel) continue;
    ids.forEach(id => {
      const o = document.createElement("option");
      o.value = id; o.textContent = labels[id] || id;
      sel.appendChild(o);
    });
  }

  const inkRGB = () => getComputedStyle(document.documentElement)
    .getPropertyValue("--ink-rgb").trim();
  const ramp = t => `rgba(${inkRGB()}, ${(0.07 + 0.85 * t).toFixed(3)})`;

  function editionsFor(id) {
    const eds = new Set();
    Object.values(indices[id] || {}).forEach(byEd => Object.keys(byEd).forEach(e => eds.add(+e)));
    return [...eds].sort((a, b) => a - b);
  }
  const scoresAt = (id, edition) => {
    const out = {};
    Object.entries(indices[id] || {}).forEach(([iso, byEd]) => {
      if (byEd[edition] !== undefined) out[iso] = byEd[edition];
    });
    return out;
  };

  /* ── choropleth ─────────────────────────────────────────────── */
  const W = 960, H = 480;
  const mapSvg = d3.select("#choropleth").append("svg").attr("viewBox", `0 0 ${W} ${H}`);
  const proj = d3.geoNaturalEarth1().fitSize([W, H], world);
  const geopath = d3.geoPath(proj);
  const feats = world.features.filter(f => f.id !== "ATA");
  const mapPaths = mapSvg.append("g").selectAll("path").data(feats).join("path")
    .attr("d", geopath)
    .attr("stroke-width", 0.5)
    .style("cursor", "pointer")
    .on("click", (_, d) => { if (names[d.id]) location.href = "/countries/" + d.id + ".html"; })
    .on("mousemove", (ev, d) => {
      if (window.gaidProfile && names[d.id]) window.gaidProfile.show(d.id, ev);
    })
    .on("mouseleave", () => window.gaidProfile && window.gaidProfile.hide());

  /* ── scatter plot ───────────────────────────────────────────── */
  const SW = 960, SH = 520, M = { top: 20, right: 30, bottom: 52, left: 56 };
  const scatterSvg = d3.select("#scatterplot").append("svg")
    .attr("viewBox", `0 0 ${SW} ${SH}`);
  const sg = scatterSvg.append("g");
  const xScale = d3.scaleLinear().domain([0, 102]).range([M.left, SW - M.right]);
  const yScale = d3.scaleLinear().domain([0, 102]).range([SH - M.bottom, M.top]);
  const xAxisG = scatterSvg.append("g").attr("class", "axis")
    .attr("transform", `translate(0,${SH - M.bottom})`);
  const yAxisG = scatterSvg.append("g").attr("class", "axis")
    .attr("transform", `translate(${M.left},0)`);
  const xTitle = scatterSvg.append("text").attr("class", "axis-title")
    .attr("x", (M.left + SW - M.right) / 2).attr("y", SH - 12).attr("text-anchor", "middle");
  const yTitle = scatterSvg.append("text").attr("class", "axis-title")
    .attr("transform", `translate(16,${(M.top + SH - M.bottom) / 2}) rotate(-90)`)
    .attr("text-anchor", "middle");

  function renderScatter(edition) {
    if (!sx || !sy) return;
    const xs = scoresAt(sx.value, edition);
    const ys = scoresAt(sy.value, edition);
    const pts = Object.keys(xs).filter(iso => ys[iso] !== undefined)
      .map(iso => ({ iso, x: xs[iso], y: ys[iso] }));
    xAxisG.call(d3.axisBottom(xScale).ticks(5).tickSize(-(SH - M.top - M.bottom)));
    yAxisG.call(d3.axisLeft(yScale).ticks(5).tickSize(-(SW - M.left - M.right)));
    xTitle.text(`${labels[sx.value]} (${edition})`);
    yTitle.text(`${labels[sy.value]} (${edition})`);
    sg.selectAll("circle").data(pts, d => d.iso).join("circle")
      .attr("class", "scatter-dot")
      .attr("cx", d => xScale(d.x)).attr("cy", d => yScale(d.y)).attr("r", 6)
      .style("cursor", "pointer")
      .on("click", (_, d) => location.href = "/countries/" + d.iso + ".html")
      .on("mousemove", (ev, d) => window.gaidProfile && window.gaidProfile.show(d.iso, ev))
      .on("mouseleave", () => window.gaidProfile && window.gaidProfile.hide());
    document.getElementById("scatter-note").textContent =
      `${pts.length} countries with both scores in edition ${edition}. ` +
      `Hover for the national profile; click a dot to open the country page.`;
  }

  /* ── shared render ──────────────────────────────────────────── */
  let jumpToLatest = true;
  function render() {
    const id = indexSel.value;
    const eds = editionsFor(id);
    edSlider.min = 0; edSlider.max = eds.length - 1;
    if (jumpToLatest || +edSlider.value > eds.length - 1) {
      edSlider.value = eds.length - 1;
      jumpToLatest = false;
    }
    const edition = eds[+edSlider.value] ?? eds[eds.length - 1];
    edLabel.textContent = edition;
    window.gaidEdition = edition;   // the profile card follows this edition

    const scores = scoresAt(id, edition);
    mapPaths
      .attr("stroke", `rgba(${inkRGB()}, 0.22)`)
      .attr("fill", d => scores[d.id] !== undefined
        ? ramp(scores[d.id] / 100) : `rgba(${inkRGB()}, 0.045)`);
    document.getElementById("legend").textContent =
      `${Object.keys(scores).length} countries scored · 0–100 within edition ${edition} · ` +
      `grey = insufficient data (no imputation)`;
    renderScatter(edition);
  }

  indexSel.value = meta.overall_id;
  if (sx) sx.value = "P1";
  if (sy) sy.value = meta.overall_id;
  indexSel.addEventListener("change", () => { jumpToLatest = true; render(); });
  edSlider.addEventListener("input", render);
  if (sx) sx.addEventListener("change", render);
  if (sy) sy.addEventListener("change", render);
  addEventListener("gaid-theme", render);
  render();
})();
