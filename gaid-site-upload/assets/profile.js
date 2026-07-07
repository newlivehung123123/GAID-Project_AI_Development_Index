/* Shared hover national-profile card (cloned from the CORDA dashboard's
   CountryCard): country name, GAID AI Development Index score + rank, and
   all six pillar scores with mini bars. Works across every view — map,
   scatter plot, and ranking tables (any element carrying data-iso3). */
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
