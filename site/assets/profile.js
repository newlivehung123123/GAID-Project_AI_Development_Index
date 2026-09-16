/* Shared hover national-profile card (cloned from the CORDA dashboard's
   CountryCard): country name, GAID AI Development Index score + rank, and
   all six pillar scores with mini bars. Works across every view — map,
   scatter plot, and ranking tables (any element carrying data-iso3).

   Also provides window.gaidNav(url, key) and a tap-to-peek gate for the
   country links in the ranking tables. On desktop a click opens the country
   page immediately (unchanged). On touch devices (no hover) the FIRST tap
   only reveals the profile card, and a quick second tap on the same country
   opens its page — so on mobile the profile card and the country page no
   longer fire at the same time. */
(function () {
  const isCoarse = () =>
    matchMedia("(hover: none), (pointer: coarse)").matches;

  /* tap-to-peek, double-tap-to-open, shared across every country target
     (map paths and scatter dots via gaidNav, ranking-table rows via the
     delegated click handler below) so the rule is identical everywhere. */
  let lastKey = null, lastT = 0;
  const isConfirmTap = key => {
    const now = Date.now();
    if (key === lastKey && now - lastT < 700) { lastKey = null; return true; }
    lastKey = key; lastT = now; return false;
  };

  // programmatic navigation used by the d3 map + scatter (app.js)
  window.gaidNav = function (url, key) {
    key = key || url;
    if (!isCoarse()) { location.href = url; return; }   // desktop: open now
    if (isConfirmTap(key)) location.href = url;          // 2nd tap: open
    // 1st tap: the profile card shown on the same tap is the answer
  };

  // ranking-table country links follow the same rule; the confirming tap is
  // handled by letting the native <a> navigate, so nothing else about the
  // tables (or the desktop click) changes
  document.addEventListener("click", ev => {
    if (!isCoarse()) return;                             // desktop untouched
    const a = ev.target.closest && ev.target.closest('a[href^="/countries/"]');
    if (!a) return;
    const row = a.closest("[data-iso3]");
    const key = row ? row.dataset.iso3 : a.getAttribute("href");
    if (isConfirmTap(key)) return;                       // 2nd tap: let it open
    ev.preventDefault();                                 // 1st tap: peek only
    if (row && window.gaidProfile) window.gaidProfile.show(row.dataset.iso3, ev);
  }, true);

  // touch: a fresh tap or a scroll dismisses a lingering card (mouseleave
  // never fires reliably on touch screens)
  const dismiss = () => { if (isCoarse() && window.gaidProfile) window.gaidProfile.hide(); };
  document.addEventListener("touchstart", dismiss, { passive: true, capture: true });
  addEventListener("scroll", dismiss, { passive: true });

  /* ── the profile card itself (needs the data, so it loads async) ──── */
  (async function () {
    const [meta, indices] = await Promise.all([
      fetch("/data/meta.json").then(r => r.json()),
      fetch("/data/indices.json").then(r => r.json()),
    ]);
    const names = Object.fromEntries(meta.countries.map(c => [c.iso3, c.name]));
    const ranks = Object.fromEntries(meta.countries.filter(c => c.overall)
      .map(c => [c.iso3, c.overall.rank]));

    const card = document.createElement("div");
    card.className = "profile-card";
    document.body.appendChild(card);

    const edition = () => window.gaidEdition || meta.latest_edition;
    const score = (id, iso3, ed) => (indices[id] || {})[iso3]?.[ed];

    function html(iso3) {
      const ed = edition();
      const ov = score(meta.overall_id, iso3, ed);
      const head = ov !== undefined
        ? `GAID AI Development Index <b>${ov.toFixed(1)}</b>` +
          (ranks[iso3] ? ` · #${ranks[iso3]}` : "") + ` (${ed})`
        : `not ranked on the overall index (${ed})`;
      const rows = Object.entries(meta.pillars).map(([pid, name]) => {
        const v = score(pid, iso3, ed);
        return `<div class="pc-row"><span class="pc-label">${pid} · ${name}</span>` +
          `<span class="pc-bar"><span style="width:${v === undefined ? 0 : v}%"></span></span>` +
          `<span class="pc-val">${v === undefined ? "–" : v.toFixed(1)}</span></div>`;
      }).join("");
      return `<div class="pc-head"><b>${names[iso3] || iso3}</b><span>${head}</span></div>${rows}`;
    }

    window.gaidProfile = {
      show(iso3, ev) { card.innerHTML = html(iso3); card.classList.add("on"); this.move(ev); },
      move(ev) {
        const pad = 12;
        const vw = document.documentElement.clientWidth;
        const vh = document.documentElement.clientHeight;
        const cw = card.offsetWidth, ch = card.offsetHeight;
        // horizontal: prefer right of cursor; flip left if it would overflow
        let x = ev.clientX + 16;
        if (x + cw + pad > vw) x = ev.clientX - cw - 16;
        x = Math.max(pad, Math.min(x, vw - cw - pad));
        // vertical: prefer just above cursor; clamp fully inside the viewport
        let y = Math.min(ev.clientY - 12, vh - ch - pad);
        y = Math.max(pad, y);
        // card is position:absolute, so add the current scroll offset
        card.style.left = (x + window.scrollX) + "px";
        card.style.top = (y + window.scrollY) + "px";
      },
      hide() { card.classList.remove("on"); },
    };

    document.querySelectorAll("[data-iso3]").forEach(el => {
      if (el.tagName === "BODY") return;
      el.addEventListener("mousemove", ev => window.gaidProfile.show(el.dataset.iso3, ev));
      el.addEventListener("mouseleave", () => window.gaidProfile.hide());
    });
  })();
})();
