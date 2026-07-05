/* Home page: interactive choropleth (d3 v7 via CDN) with index + edition controls. */
(async function () {
  const [meta, indices, world] = await Promise.all([
    fetch("data/meta.json").then(r => r.json()),
    fetch("data/indices.json").then(r => r.json()),
    fetch("assets/world.geo.json").then(r => r.json()),
  ]);

  const names = Object.fromEntries(meta.countries.map(c => [c.iso3, c.name]));
  const indexSel = document.getElementById("index-select");
  const edSlider = document.getElementById("edition-slider");
  const edLabel = document.getElementById("edition-label");

  const ids = [meta.overall_id, ...Object.keys(meta.pillars), ...Object.keys(meta.lenses)];
  const labels = {
    [meta.overall_id]: "Overall — GAID AI Development Index",
    ...Object.fromEntries(Object.entries(meta.pillars).map(([k, v]) => [k, k + " — " + v])),
    ...Object.fromEntries(Object.entries(meta.lenses).map(([k, v]) => [k, v])),
  };
  ids.forEach(id => {
    const o = document.createElement("option");
    o.value = id; o.textContent = labels[id] || id;
    indexSel.appendChild(o);
  });

  // editions available for the chosen id
  function editionsFor(id) {
    const eds = new Set();
    Object.values(indices[id] || {}).forEach(byEd => Object.keys(byEd).forEach(e => eds.add(+e)));
    return [...eds].sort((a, b) => a - b);
  }

  const box = document.getElementById("choropleth");
  const W = 960, H = 480;
  const svg = d3.select(box).append("svg").attr("viewBox", `0 0 ${W} ${H}`);
  const proj = d3.geoNaturalEarth1().fitSize([W, H], world);
  const path = d3.geoPath(proj);
  const tip = d3.select("body").append("div").attr("class", "map-tooltip");
  const ramp = d3.interpolateRgb("#f0e4d0", "#7a1408");

  const g = svg.append("g");
  const feats = world.features.filter(f => f.id !== "ATA");
  const paths = g.selectAll("path").data(feats).join("path")
    .attr("d", path)
    .attr("stroke", "#c9c2b2").attr("stroke-width", 0.5)
    .style("cursor", "pointer")
    .on("click", (_, d) => { if (names[d.id]) location.href = "countries/" + d.id + ".html"; });

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

    const scores = {};
    Object.entries(indices[id] || {}).forEach(([iso, byEd]) => {
      if (byEd[edition] !== undefined) scores[iso] = byEd[edition];
    });
    paths
      .attr("fill", d => scores[d.id] !== undefined ? ramp(scores[d.id] / 100) : "#eceae4")
      .on("mousemove", (ev, d) => {
        const v = scores[d.id];
        tip.style("opacity", 1)
          .style("left", (ev.pageX + 14) + "px").style("top", (ev.pageY - 12) + "px")
          .html(`<b>${names[d.id] || d.properties.name}</b><br>` +
                (v !== undefined ? `${labels[id] || id}: <b>${v.toFixed(1)}</b> (${edition})`
                                 : "no score this edition"));
      })
      .on("mouseleave", () => tip.style("opacity", 0));

    const n = Object.keys(scores).length;
    document.getElementById("legend").textContent =
      `${n} countries scored · 0–100 within edition ${edition} · grey = insufficient data (no imputation)`;
  }

  indexSel.value = meta.overall_id;
  indexSel.addEventListener("change", () => { jumpToLatest = true; render(); });
  edSlider.addEventListener("input", render);
  render();
})();
