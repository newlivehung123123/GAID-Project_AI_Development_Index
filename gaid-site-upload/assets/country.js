/* Country profile: loads the country's own JSON and renders the full
   metric browser (all analytical GAID metrics, grouped by category). */
(async function () {
  const iso3 = document.body.dataset.iso3;
  const data = await fetch("/data/countries/" + iso3 + ".json").then(r => r.json());

  const byCat = {};
  Object.entries(data.metrics).forEach(([name, m]) => {
    (byCat[m.category] ||= []).push({ name, ...m });
  });

  const host = document.getElementById("metric-browser");
  const frag = document.createDocumentFragment();
  Object.keys(byCat).sort().forEach(cat => {
    const det = document.createElement("details");
    det.className = "mcat";
    const rows = byCat[cat].sort((a, b) => a.name.localeCompare(b.name));
    det.innerHTML = `<summary>${cat} <small>(${rows.length} metrics)</small></summary>`;
    rows.forEach(m => {
      const years = Object.keys(m.values).sort();
      const shown = years.slice(-4).map(y =>
        `${y}: <b>${fmt(m.values[y])}</b>`).join(" · ");
      const div = document.createElement("div");
      div.className = "metric-row";
      div.innerHTML = `<span class="mname">${m.name}` +
        `<div class="msrc">${m.source} · ${years[0]}–${years[years.length - 1]}` +
        ` · ${years.length} obs</div></span>` +
        `<span class="metric-vals">${shown}</span>`;
      det.appendChild(div);
    });
    frag.appendChild(det);
  });
  host.textContent = "";
  host.appendChild(frag);

  function fmt(v) {
    if (Math.abs(v) >= 1e15) return v.toExponential(2);
    if (Math.abs(v) >= 1000) return v.toLocaleString("en", { maximumFractionDigits: 0 });
    return v.toLocaleString("en", { maximumFractionDigits: 3 });
  }

  document.getElementById("metric-search").addEventListener("input", ev => {
    const q = ev.target.value.toLowerCase();
    document.querySelectorAll("details.mcat").forEach(det => {
      let any = false;
      det.querySelectorAll(".metric-row").forEach(row => {
        const hit = !q || row.textContent.toLowerCase().includes(q);
        row.style.display = hit ? "" : "none";
        any = any || hit;
      });
      det.style.display = any ? "" : "none";
      if (q && any) det.open = true;
    });
  });
})();
