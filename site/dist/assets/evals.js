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

    /* labels: cluster dots that share horizontal space; a lone dot gets its
       label beside it, a dense cluster gets a tidy label COLUMN beside the
       cluster with a thin leader line from each label to its dot */
    const GAP = 17;
    const clamp = v => Math.max(M.top + 12, Math.min(v, H - M.bottom - 8));
    const items = shown.filter(active).map(m => ({
      m, dx: x(m[sx.value]), dy: y(m[sy.value]), w: m.label.length * 6.8,
    })).sort((a, b) => a.dx - b.dx);
    const clusters = [];
    for (const it of items) {
      const cur = clusters.at(-1);
      const reach = it.dx + 13 + it.w;                 // label extent if placed right
      if (cur && it.dx <= cur.maxReach + 10) {
        cur.items.push(it); cur.maxReach = Math.max(cur.maxReach, reach);
      } else clusters.push({ items: [it], maxReach: reach });
    }
    clusters.forEach(c => {
      if (c.items.length === 1) {
        const it = c.items[0];
        it.anchor = it.dx + 13 + it.w > W - M.right ? "end" : "start";
        it.lx = it.anchor === "start" ? it.dx + 13 : it.dx - 13;
        it.ly = clamp(it.dy + 4);
        return;
      }
      const maxW = Math.max(...c.items.map(i => i.w));
      let colX = Math.max(...c.items.map(i => i.dx)) + 22, anchor = "start";
      if (colX + maxW > W - M.right + 24) {
        colX = Math.min(...c.items.map(i => i.dx)) - 22; anchor = "end";
      }
      c.items.sort((a, b) => a.dy - b.dy);
      const total = (c.items.length - 1) * GAP;
      const meanY = c.items.reduce((s, i) => s + i.dy, 0) / c.items.length;
      let y0 = Math.max(M.top + 14,
        Math.min(meanY - total / 2, H - M.bottom - 10 - total));
      c.items.forEach((it, k) => {
        it.anchor = anchor; it.lx = colX; it.ly = y0 + k * GAP;
      });
    });
    items.forEach(it => {
      const moved = Math.abs(it.ly - (it.dy + 4)) > 8 || Math.abs(it.lx - it.dx) > 15;
      if (moved)
        g.append("line")
          .attr("x1", it.dx + (it.lx > it.dx ? 9 : -9)).attr("y1", it.dy)
          .attr("x2", it.lx + (it.anchor === "start" ? -3 : 3))
          .attr("y2", it.ly - 4)
          .attr("stroke", ink(0.28)).attr("stroke-width", 0.8);
      g.append("text").attr("x", it.lx).attr("y", it.ly)
        .attr("text-anchor", it.anchor)
        .attr("font-size", 11.5).attr("font-family", "var(--serif)")
        .attr("fill", "var(--ink)").style("opacity", 0.88)
        .text(it.m.label);
    });
    document.getElementById("ev-note").textContent =
      `${items.length} of ${shown.length} models shown` +
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

  /* ── Cover Flow: one card per model, iTunes-style 3D deck ───────── */
  function coverFlow(hostSel, keys, keyOf, xNote) {
    const host = document.querySelector(hostSel);
    host.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "flow-wrap";
    wrap.tabIndex = 0;
    const stage = document.createElement("div");
    stage.className = "flow-stage";
    wrap.appendChild(stage);
    const nav = document.createElement("div");
    nav.className = "flow-nav";
    nav.innerHTML = `<button class="chip" data-d="-1" aria-label="previous">&#8249;</button>
      <span class="flow-caption"></span>
      <button class="chip" data-d="1" aria-label="next">&#8250;</button>`;
    host.appendChild(wrap);
    host.appendChild(nav);
    const caption = nav.querySelector(".flow-caption");

    const W = 460, H = 290, M = { top: 16, right: 18, bottom: 34, left: 48 };
    const vals = EVALS.flatMap(m => keys.map(k => keyOf(m, k))).filter(v => v != null);
    const yMax = Math.max(...vals) * 1.1;
    const x = d3.scalePoint().domain(keys).range([M.left, W - M.right]);
    const y = d3.scaleLinear().domain([0, yMax]).range([H - M.bottom, M.top]);
    const line = d3.line().defined(d => d[1] != null)
      .x(d => x(d[0])).y(d => y(d[1]));
    const series = EVALS.map(m => ({ m, pts: keys.map(k => [k, keyOf(m, k)]) }))
      .filter(s => s.pts.some(p => p[1] != null));

    let idx = 0;
    const cards = series.map((s, i) => {
      const card = document.createElement("div");
      card.className = "flow-card";
      const name = document.createElement("h4");
      name.textContent = s.m.label;
      card.appendChild(name);
      stage.appendChild(card);
      const svg = d3.select(card).append("svg").attr("viewBox", `0 0 ${W} ${H}`);
      [0, yMax / 2, yMax].forEach(v => {
        svg.append("line").attr("x1", M.left).attr("x2", W - M.right)
          .attr("y1", y(v)).attr("y2", y(v)).attr("stroke", ink(0.12));
        svg.append("text").attr("x", M.left - 6).attr("y", y(v) + 3.5)
          .attr("text-anchor", "end").attr("font-size", 11)
          .attr("font-family", "var(--serif)").attr("fill", "var(--ink)")
          .style("opacity", 0.6).text((v * 100).toFixed(0) + "%");
      });
      keys.forEach(k =>
        svg.append("text").attr("x", x(k)).attr("y", H - 10)
          .attr("text-anchor", "middle").attr("font-size", 11)
          .attr("font-family", "var(--serif)").attr("fill", "var(--ink)")
          .style("opacity", 0.6).text(xNote(k)));
      series.forEach(o => {
        if (o.m.id === s.m.id) return;
        svg.append("path").datum(o.pts).attr("d", line)
          .attr("fill", "none").attr("stroke", ink(0.09)).attr("stroke-width", 1);
      });
      svg.append("path").datum(s.pts).attr("d", line)
        .attr("fill", "none").attr("stroke", ink(0.85)).attr("stroke-width", 2.4);
      const on = s.pts.filter(p => p[1] != null);
      svg.selectAll(".pt").data(on).join("circle")
        .attr("cx", d => x(d[0])).attr("cy", d => y(d[1]))
        .attr("r", 4).attr("fill", ink(0.9));
      svg.selectAll(".vl").data(on).join("text")
        .attr("x", d => x(d[0])).attr("y", d => y(d[1]) - 9)
        .attr("text-anchor", "middle").attr("font-size", 10.5)
        .attr("font-family", "var(--serif)").attr("fill", "var(--ink)")
        .style("opacity", 0.75).text(d => (d[1] * 100).toFixed(1) + "%");
      card.addEventListener("click", () => {
        if (i !== idx) { idx = i; update(); }
      });
      return card;
    });

    function update() {
      cards.forEach((c, i) => {
        const off = i - idx, abs = Math.abs(off);
        c.style.transform =
          `translate(-50%, -50%) translateX(${off * 92}px) ` +
          `translateZ(${off === 0 ? 110 : -60 - abs * 40}px) ` +
          `rotateY(${off === 0 ? 0 : off < 0 ? 52 : -52}deg) ` +
          `scale(${off === 0 ? 1 : 0.72})`;
        c.style.zIndex = 100 - abs;
        c.style.opacity = abs > 3 ? 0 : 1;
        c.style.pointerEvents = abs > 3 ? "none" : "auto";
        c.classList.toggle("front", off === 0);
      });
      const m = series[idx].m;
      caption.textContent =
        `${m.label} — ${m.dev} · ${m.weights} weights (${idx + 1} of ${series.length})`;
    }
    const step = d => { idx = Math.max(0, Math.min(series.length - 1, idx + d)); update(); };
    nav.querySelectorAll("button").forEach(b =>
      b.addEventListener("click", () => step(+b.dataset.d)));
    wrap.addEventListener("keydown", ev => {
      if (ev.key === "ArrowLeft") { step(-1); ev.preventDefault(); }
      if (ev.key === "ArrowRight") { step(1); ev.preventDefault(); }
    });
    update();
  }

  function renderLines() {
    coverFlow("#eval-tiers", ["LIC", "LMC", "UMC", "HIC"],
      (m, k) => m.tiers[k], k => k);
    coverFlow("#eval-thresholds", ["5", "10", "20", "30"],
      (m, k) => m.thresholds[k], k => "±" + k + "%");
  }

  function renderAll() { renderScatter(); renderLines(); }
  addEventListener("gaid-theme", renderAll);
  renderAll();
})();
