/* Model Evaluations charts.
   - Marks are coloured by ORGANISATION (Epoch-style: models share their
     lab's colour, embedded per model as m.color at build time); the page
     chrome stays in the site's monochrome design language.
   - Scatter labels: cluster label groups and MERGE groups until no two
     groups' boxes overlap, then sweep inside each group — verified across
     all metric combinations before shipping.
   - The per-model decks are Swiper coverflow carousels (drag / click /
     arrows / keyboard / autoplay). */
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
  function showTip(ev, html, small) {
    tip.innerHTML = html;
    tip.classList.toggle("tip-sm", !!small);
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
  const logoImg = (m, s = 15) => m.logo
    ? `<img class="dev-logo${m.mono ? " mono" : ""}" src="/assets/logos/${m.logo}" width="${s}" height="${s}" alt="">`
    : "";
  const profile = m => `<div class="pc-head"><b>${logoImg(m)}${m.label}</b>
    <span>${m.dev} · ${m.weights} weights</span></div>` +
    ["correct", "fabrication", "refusal", "hedge", "misattribution"].map(k =>
      `<div class="pc-row"><span class="pc-label">${METRICS[k].label.split(" ")[0]}</span>
       <span class="pc-bar"><span style="width:${(m[k] * 100).toFixed(1)}%"></span></span>
       <span class="pc-val">${fmt(k, m[k])}</span></div>`).join("");

  /* instant tooltips for the stacked profile bars */
  document.querySelectorAll(".eval-seg[data-tip]").forEach(seg => {
    seg.addEventListener("mousemove", ev =>
      showTip(ev, `<b>${seg.dataset.tip}</b>`, true));
    seg.addEventListener("mouseleave", hideTip);
  });

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
      .attr("cx", m => x(m[sx.value])).attr("cy", m => y(m[sy.value]))
      .attr("r", 8)
      .attr("fill", m => m.color).attr("fill-opacity", 0.85)
      .attr("stroke", ink(0.8)).attr("stroke-width", 0.8)
      .style("cursor", "pointer")
      .style("opacity", m => active(m) ? 1 : 0.10)
      .on("mousemove", (ev, m) => showTip(ev, profile(m)))
      .on("mouseleave", hideTip);

    /* ── label layout: build groups, then MERGE any groups whose label
       boxes would overlap, re-laying-out until stable ─────────────── */
    const GAP = 17, LH = 13;   // row gap, label box height
    const items = shown.filter(active).map(m => ({
      m, dx: x(m[sx.value]), dy: y(m[sy.value]), w: m.label.length * 6.9,
    }));

    function layoutGroup(gr) {
      // lone label sits beside its dot; groups form a column
      if (gr.items.length === 1) {
        const it = gr.items[0];
        const right = it.dx + 13 + it.w <= W - M.right;
        it.anchor = right ? "start" : "end";
        it.lx = right ? it.dx + 13 : it.dx - 13;
        it.ly = Math.max(M.top + 12, Math.min(it.dy + 4, H - M.bottom - 8));
      } else {
        const maxW = Math.max(...gr.items.map(i => i.w));
        let colX = Math.max(...gr.items.map(i => i.dx)) + 24, anchor = "start";
        if (colX + maxW > W - M.right + 26) {
          colX = Math.min(...gr.items.map(i => i.dx)) - 24; anchor = "end";
        }
        gr.items.sort((a, b) => a.dy - b.dy);
        const total = (gr.items.length - 1) * GAP;
        const meanY = gr.items.reduce((s, i) => s + i.dy, 0) / gr.items.length;
        const y0 = Math.max(M.top + 14,
          Math.min(meanY - total / 2, H - M.bottom - 10 - total));
        gr.items.forEach((it, k) => {
          it.anchor = anchor; it.lx = colX; it.ly = y0 + k * GAP;
        });
      }
      // group bbox from label boxes
      const boxes = gr.items.map(it => ({
        x0: it.anchor === "start" ? it.lx : it.lx - it.w,
        x1: it.anchor === "start" ? it.lx + it.w : it.lx,
        y0: it.ly - LH + 2, y1: it.ly + 4,
      }));
      gr.x0 = Math.min(...boxes.map(b => b.x0)) - 4;
      gr.x1 = Math.max(...boxes.map(b => b.x1)) + 4;
      gr.y0 = Math.min(...boxes.map(b => b.y0)) - 2;
      gr.y1 = Math.max(...boxes.map(b => b.y1)) + 2;
    }

    let groups = items.map(it => ({ items: [it] }));
    for (let pass = 0; pass < 8; pass++) {
      groups.forEach(layoutGroup);
      let merged = false;
      outer:
      for (let i = 0; i < groups.length; i++)
        for (let j = i + 1; j < groups.length; j++) {
          const a = groups[i], b = groups[j];
          if (a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1) {
            a.items = a.items.concat(b.items);
            groups.splice(j, 1);
            merged = true;
            break outer;
          }
        }
      if (!merged) break;
    }
    groups.forEach(layoutGroup);

    items.forEach(it => {
      const displaced =
        Math.abs(it.ly - (it.dy + 4)) > 8 || Math.abs(it.lx - it.dx) > 15;
      if (displaced)
        g.append("line")
          .attr("x1", it.dx + (it.lx > it.dx ? 9 : -9)).attr("y1", it.dy)
          .attr("x2", it.lx + (it.anchor === "start" ? -3 : 3))
          .attr("y2", it.ly - 4)
          .attr("stroke", it.m.color).attr("stroke-opacity", 0.55)
          .attr("stroke-width", 0.9);
      g.append("text").attr("x", it.lx).attr("y", it.ly)
        .attr("text-anchor", it.anchor)
        .attr("font-size", 11.5).attr("font-family", "var(--serif)")
        .attr("font-weight", 600)
        .attr("fill", it.m.color).text(it.m.label);
    });
    const legend = document.getElementById("ev-legend");
    legend.innerHTML = shown.map(m => `
      <div class="lg-row" style="opacity:${active(m) ? 1 : 0.3}">
        ${logoImg(m, 16)}<span style="color:${m.color}">${m.label}</span>
      </div>`).join("");
    document.getElementById("ev-note").textContent =
      `${items.length} of ${shown.length} models shown` +
      (weightFilter === "all" ? "" : ` (${weightFilter} weights)`) +
      ` · colour = developer · hover a point for its full profile.`;
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

  /* ── Swiper coverflow decks: drag / click / arrows / keys / autoplay ── */
  const swipers = [];
  function coverFlow(hostSel, keys, keyOf, xNote) {
    const host = document.querySelector(hostSel);
    host.innerHTML = "";
    host.insertAdjacentHTML("beforeend", `
      <div class="swiper flow-swiper"><div class="swiper-wrapper"></div></div>
      <div class="flow-nav">
        <button class="chip" data-d="-1" aria-label="previous">&#8249;</button>
        <span class="flow-caption"></span>
        <button class="chip" data-d="1" aria-label="next">&#8250;</button>
      </div>`);
    const wrapper = host.querySelector(".swiper-wrapper");
    const caption = host.querySelector(".flow-caption");

    const W = 460, H = 290, M = { top: 16, right: 18, bottom: 34, left: 48 };
    const vals = EVALS.flatMap(m => keys.map(k => keyOf(m, k))).filter(v => v != null);
    const yMax = Math.max(...vals) * 1.1;
    const x = d3.scalePoint().domain(keys).range([M.left, W - M.right]);
    const y = d3.scaleLinear().domain([0, yMax]).range([H - M.bottom, M.top]);
    const line = d3.line().defined(d => d[1] != null)
      .x(d => x(d[0])).y(d => y(d[1]));
    const series = EVALS.map(m => ({ m, pts: keys.map(k => [k, keyOf(m, k)]) }))
      .filter(s => s.pts.some(p => p[1] != null));

    series.forEach(s => {
      const slide = document.createElement("div");
      slide.className = "swiper-slide";
      const card = document.createElement("div");
      card.className = "flow-card";
      card.innerHTML = `<h4>${logoImg(s.m, 16)}${s.m.label}</h4>`;
      slide.appendChild(card);
      wrapper.appendChild(slide);
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
        .attr("fill", "none").attr("stroke", s.m.color).attr("stroke-width", 2.6);
      const on = s.pts.filter(p => p[1] != null);
      svg.selectAll(".pt").data(on).join("circle")
        .attr("cx", d => x(d[0])).attr("cy", d => y(d[1]))
        .attr("r", 4).attr("fill", s.m.color);
      svg.selectAll(".vl").data(on).join("text")
        .attr("x", d => x(d[0])).attr("y", d => y(d[1]) - 10)
        .attr("text-anchor", "middle").attr("font-size", 10.5)
        .attr("font-family", "var(--serif)").attr("fill", "var(--ink)")
        .style("opacity", 0.8).text(d => (d[1] * 100).toFixed(1) + "%");
    });

    const sw = new Swiper(host.querySelector(".flow-swiper"), {
      effect: "coverflow",
      grabCursor: true,
      centeredSlides: true,
      slidesPerView: "auto",
      threshold: 8,   // presses that move <8px are taps, not drags
      rewind: true,   // indefinite cycle: prev at the first card wraps to the
                      // last, next at the last wraps back to the first
      coverflowEffect: { rotate: 38, stretch: 0, depth: 160, modifier: 1,
                         slideShadows: false },
      keyboard: { enabled: true, onlyInViewport: true },
      autoplay: { delay: 3200, pauseOnMouseEnter: true,
                  disableOnInteraction: false },
    });
    const update = () => {
      const m = series[sw.realIndex].m;
      caption.textContent =
        `${m.label} — ${m.dev} · ${m.weights} weights (${sw.realIndex + 1} of ${series.length})`;
    };
    sw.on("slideChange", update);
    update();
    // Tap detection from raw pointer events — Swiper suppresses CLICK events
    // whenever the cursor moves a pixel or two between press and release
    // (the cause of the intermittent dead clicks), but it cannot suppress
    // pointerdown/pointerup. Press+release within 8px/600ms = navigate:
    // a side card jumps to itself; the front card's outer thirds (which
    // visually overlap the neighbours) step prev/next; a real drag swipes.
    const flowEl = host.querySelector(".flow-swiper");
    let px = 0, py = 0, pt = 0;
    flowEl.addEventListener("pointerdown", e => {
      px = e.clientX; py = e.clientY; pt = Date.now();
    });
    flowEl.addEventListener("pointerup", e => {
      if (Math.hypot(e.clientX - px, e.clientY - py) > 8) return;  // drag
      if (Date.now() - pt > 600) return;                           // hold
      const slide = e.target.closest(".swiper-slide");
      if (!slide) return;
      const slides = [...host.querySelectorAll(".swiper-slide")];
      const i = slides.indexOf(slide);
      if (i !== sw.activeIndex) { sw.slideTo(i); return; }
      const r = slide.getBoundingClientRect();
      const fx = (e.clientX - r.left) / r.width;
      if (fx < 0.33) sw.slidePrev();
      else if (fx > 0.67) sw.slideNext();
    });
    host.querySelectorAll(".flow-nav button").forEach(b =>
      b.addEventListener("click", () =>
        +b.dataset.d < 0 ? sw.slidePrev() : sw.slideNext()));
    swipers.push(sw);
  }

  function renderLines() {
    coverFlow("#eval-tiers", ["LIC", "LMC", "UMC", "HIC"],
      (m, k) => m.tiers[k], k => k);
    coverFlow("#eval-thresholds", ["5", "10", "20", "30"],
      (m, k) => m.thresholds[k], k => "±" + k + "%");
  }

  function renderAll() {
    renderScatter();
    swipers.splice(0).forEach(s => s.destroy(true, true));
    renderLines();
  }
  addEventListener("gaid-theme", renderAll);
  renderAll();
})();

/* ── page bookmarks: toggle + active-section tracking ─────────────── */
(function () {
  const toc = document.getElementById("page-toc");
  if (!toc) return;
  const btn = toc.querySelector(".toc-toggle");
  btn.addEventListener("click", ev => {
    ev.stopPropagation();
    toc.classList.toggle("open");
    btn.setAttribute("aria-expanded", toc.classList.contains("open"));
  });
  document.addEventListener("click", ev => {
    if (!toc.contains(ev.target)) toc.classList.remove("open");
  });
  const links = [...toc.querySelectorAll("a")];
  links.forEach(a => a.addEventListener("click", () =>
    toc.classList.remove("open")));
  const byId = new Map(links.map(a => [a.getAttribute("href").slice(1), a]));
  const io = new IntersectionObserver(entries => entries.forEach(en => {
    if (en.isIntersecting) {
      links.forEach(l => l.classList.remove("active"));
      byId.get(en.target.id)?.classList.add("active");
    }
  }), { rootMargin: "-12% 0px -72% 0px" });
  byId.forEach((_, id) => {
    const el = document.getElementById(id);
    if (el) io.observe(el);
  });
})();
