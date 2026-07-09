/* Model Evaluations charts: metric-space scatter explorer + small-multiple
   line panels (one per model — the readable monochrome alternative to
   spaghetti lines). Same ink-alpha language as the rest of the site;
   re-renders on the Nyx/Eos toggle. Data embedded at build time as EVALS. */
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
    let y = ev.clientY - tip.offsetHeight - 14;
    if (y < pad) y = ev.clientY + 18;
    tip.style.left = (Math.max(pad, x) + window.scrollX) + "px";
    tip.style.top = (y + window.scrollY) + "px";
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
  const active = m => weightFilter === "all" || m.weights === weightFilter;

  function renderScatter() {
    const host = d3.select("#eval-scatter");
    host.selectAll("*").remove();
    const W = 960, H = 520, M = { top: 26, right: 46, bottom: 60, left: 64 };
    const svg = host.append("svg").attr("viewBox", `0 0 ${W} ${H}`);
    const xs = EVALS.map(m => m[sx.value]).filter(v => v != null);
    const ys = EVALS.map(m => m[sy.value]).filter(v => v != null);
    const padDom = a => {
      const lo = Math.min(...a), hi = Math.max(...a), p = (hi - lo) * 0.14 || 0.05;
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
      .attr("x", (M.left + W - M.right) / 2).attr("y", H - 14)
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
      .style("opacity", m => active(m) ? 1 : 0.12)
      .on("mousemove", (ev, m) => showTip(ev, profile(m)))
      .on("mouseleave", hideTip);

    /* labels: only for active models; flip to the left near the right edge,
       then relax measured bounding-box collisions inside the plot frame */
    const labelNodes = shown.filter(active).map(m => {
      let lx = x(m[sx.value]) + 12, anchor = "start";
      if (lx + m.label.length * 7 > W - M.right) {
        lx = x(m[sx.value]) - 12; anchor = "end";
      }
      const ly = Math.max(M.top + 12,
        Math.min(y(m[sy.value]) + 4, H - M.bottom - 8));
      return g.append("text").attr("x", lx).attr("y", ly)
        .attr("text-anchor", anchor)
        .attr("font-size", 11.5).attr("font-family", "var(--serif)")
        .attr("fill", "var(--ink)").style("opacity", 0.85)
        .text(m.label).node();
    });
    /* group labels whose x-ranges overlap, then run an ordered vertical
       sweep within each group — deterministic, no oscillation */
    const boxes = labelNodes.map(n => {
      const b = n.getBBox();
      return { n, x0: b.x, x1: b.x + b.width, ty: +n.getAttribute("y") };
    }).sort((a, b) => a.x0 - b.x0);
    const clusters = [];
    for (const b of boxes) {
      const cur = clusters.at(-1);
      if (cur && b.x0 <= cur.maxX1 + 8) {
        cur.items.push(b); cur.maxX1 = Math.max(cur.maxX1, b.x1);
      } else clusters.push({ items: [b], maxX1: b.x1 });
    }
    const GAP = 16;
    clusters.forEach(c => {
      c.items.sort((a, b) => a.ty - b.ty);
      let prev = M.top + 12 - GAP;
      c.items.forEach(it => { it.ty = Math.max(it.ty, prev + GAP); prev = it.ty; });
      const over = c.items.at(-1).ty - (H - M.bottom - 6);
      if (over > 0) {
        let next = Infinity;
        for (let i = c.items.length - 1; i >= 0; i--) {
          c.items[i].ty = Math.min(c.items[i].ty - over, next - GAP);
          next = c.items[i].ty;
        }
      }
      c.items.forEach(it => it.n.setAttribute("y", it.ty));
    });
    document.getElementById("ev-note").textContent =
      `${labelNodes.length} of ${shown.length} models shown` +
      (weightFilter === "all" ? "" : ` (${weightFilter} weights)`) +
      ` · hover a point for its full category profile.`;
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

  /* ── small multiples: one readable panel per model ─────────────── */
  function smallMultiples(hostSel, keys, keyOf, xNote) {
    const host = document.querySelector(hostSel);
    host.innerHTML = "";
    const grid = document.createElement("div");
    grid.className = "eval-grid";
    host.appendChild(grid);

    const W = 220, H = 150, M = { top: 12, right: 12, bottom: 24, left: 34 };
    const vals = EVALS.flatMap(m => keys.map(k => keyOf(m, k))).filter(v => v != null);
    const yMax = Math.max(...vals) * 1.1;
    const x = d3.scalePoint().domain(keys).range([M.left, W - M.right]);
    const y = d3.scaleLinear().domain([0, yMax]).range([H - M.bottom, M.top]);
    const line = d3.line().defined(d => d[1] != null)
      .x(d => x(d[0])).y(d => y(d[1]));
    const series = EVALS.map(m => ({ m, pts: keys.map(k => [k, keyOf(m, k)]) }))
      .filter(s => s.pts.some(p => p[1] != null));

    series.forEach(s => {
      const cell = document.createElement("div");
      cell.className = "eval-cell";
      const name = document.createElement("h4");
      name.textContent = s.m.label;
      cell.appendChild(name);
      grid.appendChild(cell);
      const svg = d3.select(cell).append("svg").attr("viewBox", `0 0 ${W} ${H}`);
      // y gridlines + labels (0 and max)
      [0, yMax].forEach(v => {
        svg.append("line").attr("x1", M.left).attr("x2", W - M.right)
          .attr("y1", y(v)).attr("y2", y(v)).attr("stroke", ink(0.12));
        svg.append("text").attr("x", M.left - 5).attr("y", y(v) + 3.5)
          .attr("text-anchor", "end").attr("font-size", 9)
          .attr("font-family", "var(--serif)").attr("fill", "var(--ink)")
          .style("opacity", 0.55).text((v * 100).toFixed(0) + "%");
      });
      // x labels: first and last key only
      [keys[0], keys.at(-1)].forEach(k =>
        svg.append("text").attr("x", x(k)).attr("y", H - 8)
          .attr("text-anchor", k === keys[0] ? "start" : "end")
          .attr("font-size", 9).attr("font-family", "var(--serif)")
          .attr("fill", "var(--ink)").style("opacity", 0.55).text(xNote(k)));
      // context: every other model, faint
      series.forEach(o => {
        if (o.m.id === s.m.id) return;
        svg.append("path").datum(o.pts).attr("d", line)
          .attr("fill", "none").attr("stroke", ink(0.08)).attr("stroke-width", 1);
      });
      // this model, bold
      svg.append("path").datum(s.pts).attr("d", line)
        .attr("fill", "none").attr("stroke", ink(0.85)).attr("stroke-width", 2.2);
      svg.selectAll(".pt").data(s.pts.filter(p => p[1] != null)).join("circle")
        .attr("cx", d => x(d[0])).attr("cy", d => y(d[1]))
        .attr("r", 3).attr("fill", ink(0.9));
      cell.addEventListener("mousemove", ev => showTip(ev,
        `<div class="pc-head"><b>${s.m.label}</b>
         <span>${s.m.dev} · ${s.m.weights} weights</span></div>` +
        s.pts.map(([k, v]) => `<div class="pc-row">
          <span class="pc-label">${xNote(k)}</span>
          <span class="pc-bar"><span style="width:${v == null ? 0 : v / yMax * 100}%"></span></span>
          <span class="pc-val">${v == null ? "–" : (v * 100).toFixed(1) + "%"}</span></div>`).join("")));
      cell.addEventListener("mouseleave", hideTip);
    });
  }

  function renderLines() {
    smallMultiples("#eval-tiers", ["LIC", "LMC", "UMC", "HIC"],
      (m, k) => m.tiers[k], k => k);
    smallMultiples("#eval-thresholds", ["5", "10", "20", "30"],
      (m, k) => m.thresholds[k], k => "±" + k + "%");
  }

  function renderAll() { renderScatter(); renderLines(); }
  addEventListener("gaid-theme", renderAll);
  renderAll();
})();
