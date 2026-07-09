/* Model Evaluations charts: metric-space scatter explorer, income-tier
   lines, and threshold-sensitivity curves. Same d3 + monochrome ink-alpha
   language as the home page (scatter-dot / axis classes); re-renders on the
   Nyx/Eos toggle. Data is embedded at build time as EVALS. */
(function () {
  const METRICS = {
    fabrication:   { label: "Fabrication rate", pct: true },
    correct:       { label: "Correct rate", pct: true },
    refusal:       { label: "Refusal rate", pct: true },
    hedge:         { label: "Hedge rate", pct: true },
    misattribution:{ label: "Misattribution rate", pct: true },
    attempt:       { label: "Attempt rate (commits to an answer)", pct: true },
    precision:     { label: "Precision when attempting (correct / attempted)", pct: true },
    within_half:   { label: "Within ½ order of magnitude", pct: true },
    median_log:    { label: "Median |log₁₀ model/truth| (lower = closer)", pct: false },
  };
  const fmt = (k, v) => v == null ? "–"
    : METRICS[k].pct ? (v * 100).toFixed(1) + "%" : v.toFixed(3);
  const ink = a => `rgba(${getComputedStyle(document.documentElement)
    .getPropertyValue("--ink-rgb").trim()}, ${a})`;

  /* tooltip reuses the site's profile-card styling */
  const tip = document.createElement("div");
  tip.className = "profile-card";
  document.body.appendChild(tip);
  function showTip(ev, html) {
    tip.innerHTML = html;
    tip.classList.add("on");
    const pad = 12, vw = document.documentElement.clientWidth;
    let x = ev.clientX + 16;
    if (x + tip.offsetWidth + pad > vw) x = ev.clientX - tip.offsetWidth - 16;
    tip.style.left = (Math.max(pad, x) + window.scrollX) + "px";
    tip.style.top = (ev.clientY - tip.offsetHeight - 14 + window.scrollY) + "px";
  }
  const hideTip = () => tip.classList.remove("on");
  const profile = m => `<div class="pc-head"><b>${m.label}</b>
    <span>${m.dev} · ${m.weights} weights</span></div>` +
    ["correct", "fabrication", "refusal", "hedge", "misattribution"].map(k =>
      `<div class="pc-row"><span class="pc-label">${METRICS[k].label.split(" ")[0]}</span>
       <span class="pc-bar"><span style="width:${(m[k] * 100).toFixed(1)}%"></span></span>
       <span class="pc-val">${fmt(k, m[k])}</span></div>`).join("");

  /* ── metric-space scatter ──────────────────────────────────────── */
  const sx = document.getElementById("ev-x"), sy = document.getElementById("ev-y");
  for (const sel of [sx, sy]) Object.entries(METRICS).forEach(([k, v]) => {
    const o = document.createElement("option");
    o.value = k; o.textContent = v.label; sel.appendChild(o);
  });
  sx.value = "attempt"; sy.value = "fabrication";
  let weightFilter = "all";

  function renderScatter() {
    const host = d3.select("#eval-scatter");
    host.selectAll("*").remove();
    const W = 960, H = 500, M = { top: 20, right: 40, bottom: 54, left: 62 };
    const svg = host.append("svg").attr("viewBox", `0 0 ${W} ${H}`);
    const xs = EVALS.map(m => m[sx.value]).filter(v => v != null);
    const ys = EVALS.map(m => m[sy.value]).filter(v => v != null);
    const padDom = a => {
      const lo = Math.min(...a), hi = Math.max(...a), p = (hi - lo) * 0.12 || 0.05;
      return [Math.max(0, lo - p), hi + p];
    };
    const x = d3.scaleLinear().domain(padDom(xs)).range([M.left, W - M.right]);
    const y = d3.scaleLinear().domain(padDom(ys)).range([H - M.bottom, M.top]);
    const tickFmt = k => v => METRICS[k].pct ? (v * 100).toFixed(0) + "%" : v;
    svg.append("g").attr("class", "axis")
      .attr("transform", `translate(0,${H - M.bottom})`)
      .call(d3.axisBottom(x).ticks(6).tickFormat(tickFmt(sx.value))
        .tickSize(-(H - M.top - M.bottom)));
    svg.append("g").attr("class", "axis")
      .attr("transform", `translate(${M.left},0)`)
      .call(d3.axisLeft(y).ticks(6).tickFormat(tickFmt(sy.value))
        .tickSize(-(W - M.left - M.right)));
    svg.append("text").attr("class", "axis-title")
      .attr("x", (M.left + W - M.right) / 2).attr("y", H - 12)
      .attr("text-anchor", "middle").text(METRICS[sx.value].label);
    svg.append("text").attr("class", "axis-title")
      .attr("transform", `translate(16,${(M.top + H - M.bottom) / 2}) rotate(-90)`)
      .attr("text-anchor", "middle").text(METRICS[sy.value].label);

    const shown = EVALS.filter(m => m[sx.value] != null && m[sy.value] != null);
    const g = svg.append("g");
    g.selectAll("circle").data(shown).join("circle")
      .attr("class", "scatter-dot")
      .attr("cx", m => x(m[sx.value])).attr("cy", m => y(m[sy.value]))
      .attr("r", 8)
      .style("opacity", m => weightFilter === "all" || m.weights === weightFilter ? 1 : 0.12)
      .on("mousemove", (ev, m) => showTip(ev, profile(m)))
      .on("mouseleave", hideTip);
    g.selectAll("text").data(shown).join("text")
      .attr("x", m => x(m[sx.value]) + 11).attr("y", m => y(m[sy.value]) + 4)
      .attr("font-size", 11.5).attr("font-family", "var(--serif)")
      .attr("fill", "var(--ink)")
      .style("opacity", m => weightFilter === "all" || m.weights === weightFilter ? 0.85 : 0.10)
      .text(m => m.label);
    document.getElementById("ev-note").textContent =
      `${shown.length} models · dots use the site's monochrome scale; ` +
      `labels follow the filter.`;
  }

  document.querySelectorAll("#ev-filter .chip").forEach(btn =>
    btn.addEventListener("click", () => {
      weightFilter = btn.dataset.w;
      document.querySelectorAll("#ev-filter .chip").forEach(b =>
        b.classList.toggle("on", b === btn));
      renderScatter();
    }));
  sx.addEventListener("change", renderScatter);
  sy.addEventListener("change", renderScatter);

  /* ── shared line chart (income tiers / thresholds) ─────────────── */
  function lineChart(hostSel, keys, keyOf, xLabel) {
    const host = d3.select(hostSel);
    host.selectAll("*").remove();
    const W = 960, H = 400, M = { top: 20, right: 130, bottom: 50, left: 62 };
    const svg = host.append("svg").attr("viewBox", `0 0 ${W} ${H}`);
    const x = d3.scalePoint().domain(keys).range([M.left, W - M.right]);
    const vals = EVALS.flatMap(m => keys.map(k => keyOf(m, k))).filter(v => v != null);
    const y = d3.scaleLinear()
      .domain([0, Math.max(...vals) * 1.12]).range([H - M.bottom, M.top]);
    svg.append("g").attr("class", "axis")
      .attr("transform", `translate(0,${H - M.bottom})`)
      .call(d3.axisBottom(x).tickSize(-(H - M.top - M.bottom)));
    svg.append("g").attr("class", "axis")
      .attr("transform", `translate(${M.left},0)`)
      .call(d3.axisLeft(y).ticks(5).tickFormat(v => (v * 100).toFixed(0) + "%")
        .tickSize(-(W - M.left - M.right)));
    svg.append("text").attr("class", "axis-title")
      .attr("x", (M.left + W - M.right) / 2).attr("y", H - 10)
      .attr("text-anchor", "middle").text(xLabel);
    svg.append("text").attr("class", "axis-title")
      .attr("transform", `translate(16,${(M.top + H - M.bottom) / 2}) rotate(-90)`)
      .attr("text-anchor", "middle").text("Fabrication rate");

    const line = d3.line().defined(d => d[1] != null)
      .x(d => x(d[0])).y(d => y(d[1]));
    const g = svg.append("g");
    // draw lines first, collect label targets, then resolve label overlaps
    const entries = [];
    EVALS.forEach(m => {
      const pts = keys.map(k => [k, keyOf(m, k)]);
      if (!pts.some(p => p[1] != null)) return;
      const path = g.append("path").datum(pts)
        .attr("d", line).attr("fill", "none")
        .attr("stroke", ink(0.32)).attr("stroke-width", 1.6);
      const dots = g.append("g").selectAll("circle")
        .data(pts.filter(p => p[1] != null)).join("circle")
        .attr("cx", d => x(d[0])).attr("cy", d => y(d[1]))
        .attr("r", 3.5).attr("fill", ink(0.5));
      entries.push({ m, path, dots,
                     yEnd: y(pts.filter(p => p[1] != null).at(-1)[1]) });
    });
    // simple 1-D collision pass: keep labels >= 13px apart, inside the frame
    entries.sort((a, b) => a.yEnd - b.yEnd);
    let prev = M.top - 13;
    entries.forEach(e => { e.yLab = Math.max(e.yEnd, prev + 13); prev = e.yLab; });
    const overflow = entries.length ? entries.at(-1).yLab - (H - M.bottom) : 0;
    if (overflow > 0) entries.forEach(e => e.yLab -= overflow);
    entries.forEach(e => {
      const label = g.append("text")
        .attr("x", W - M.right + 8).attr("y", e.yLab + 4)
        .attr("font-size", 10.5).attr("font-family", "var(--serif)")
        .attr("fill", "var(--ink)").style("opacity", 0.55).text(e.m.label);
      const focus = on => {
        e.path.attr("stroke", ink(on ? 0.9 : 0.32))
              .attr("stroke-width", on ? 2.6 : 1.6);
        e.dots.attr("fill", ink(on ? 0.95 : 0.5)).attr("r", on ? 4.5 : 3.5);
        label.style("opacity", on ? 1 : 0.55)
             .attr("font-weight", on ? 600 : 400);
      };
      for (const el of [e.path, e.dots, label])
        el.on("mousemove", ev => { focus(true); showTip(ev, profile(e.m)); })
          .on("mouseleave", () => { focus(false); hideTip(); });
    });
  }

  function renderLines() {
    lineChart("#eval-tiers", ["LIC", "LMC", "UMC", "HIC"],
      (m, k) => m.tiers[k], "World Bank income tier (low → high income)");
    lineChart("#eval-thresholds", ["5", "10", "20", "30"],
      (m, k) => m.thresholds[k], "Correctness tolerance (± %)");
  }

  function renderAll() { renderScatter(); renderLines(); }
  addEventListener("gaid-theme", renderAll);
  renderAll();
})();
