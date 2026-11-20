/* TradeBot Backtester — karta Initial Balance: štatistika prvej hodiny seansy (logika IB Lab, tester/initial_balance.py). */
"use strict";

// --------------------------------------------------------------------------- //
// Initial Balance
// --------------------------------------------------------------------------- //
//
// Všetko počíta server (/api/ib/summary): dni symbolu sa spočítajú raz a držia v pamäti,
// filter je len prechod cez ne. Tu je formulár, karty, histogramy a tabuľka posledných dní.

const IB_KEY = "tradebot.ib";
const IB_GOLD = "#f0b429";
const IB_DOW = ["", "po", "ut", "st", "št", "pi"];
const ib = {
  meta: null, data: null, seq: 0, timer: null, ready: false,
  f: { symbol: "ES", session: "ny", scope: "pre", dir: "bull", dow: "", bias: "all", bias_break: "with",
       brk: "all", news: "all", period: "all", gran: "15", slot_step: "30", bands: [], close_bands: [], slots: [] },
};

function ibSave() { try { localStorage.setItem(IB_KEY, JSON.stringify(ib.f)); } catch (_) { /* nezapamätá sa */ } }
function ibLoadPrefs() {
  try { const s = JSON.parse(localStorage.getItem(IB_KEY) || "null"); if (s) Object.assign(ib.f, s); } catch (_) { /* súkromné okno */ }
}
function ibMins(hhmm) { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; }
function ibHhmm(m) { return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`; }
function ibPct(v) { return v == null ? "—" : `${dvNum(v, 1)} %`; }
function ibX(v, d = 2) { return v == null ? "—" : (v < 0 ? "−" : "") + dvNum(Math.abs(v), d); }

/** Pásmo časového histogramu, do ktorého padne medián (karta ukazuje koniec jeho 5m slotu). */
function ibTimeBucket(h, gran) {
  if (!h || !h.median) return null;
  const sess = ib.meta.sessions[ib.f.session], start = ibMins(sess.ib[1]);
  const m = ibMins(h.median) - 5;
  return ibHhmm(start + Math.floor((m - start) / gran) * gran);
}
/** Zóna mediánu: retracement zaokrúhli na stotiny (ako `zone()`), extension nie. */
function ibZoneBucket(h, kind) {
  if (!h || h.median == null) return null;
  const v = h.median;
  if (kind === "ext") return `Z${Math.floor(10 * v + 1e-9) + 1}`;
  const z = Math.floor(Math.round(100 * Math.abs(v)) / 100 * 10 + 1e-9) + 1;
  return kind === "signed" && v < 0 ? `P${z}` : `Z${z}`;
}

// ------------------------------------------------------------- formulár --- //

function ibSegment(id, key) {
  for (const b of $$(`#${id} button`)) {
    b.classList.toggle("active", b.dataset.v === ib.f[key]);
    b.onclick = () => { ib.f[key] = b.dataset.v; ibSegment(id, key); ibSync(); ibQuery(); };
  }
}

function ibChips(el, items, key) {
  el.innerHTML = items.map(([v, label]) =>
    `<button type="button" class="chip-btn${ib.f[key].includes(v) ? " active" : ""}" data-v="${esc(v)}">${esc(label)}</button>`).join("");
  for (const b of $$("button", el)) {
    b.onclick = () => {
      const v = key === "slots" ? b.dataset.v : Number(b.dataset.v), arr = ib.f[key], i = arr.indexOf(v);
      if (i >= 0) arr.splice(i, 1); else arr.push(v);
      b.classList.toggle("active", i < 0);
      ibQuery();
    };
  }
}

function ibSlotChips() {
  const sess = ib.meta.sessions[ib.f.session], step = Number(ib.f.slot_step);
  const start = ibMins(sess.ib[1]), end = ibMins(sess.end), items = [];
  for (let m = start; m < end; m += step) items.push([ibHhmm(m), ibHhmm(m)]);
  ib.f.slots = ib.f.slots.filter(s => items.some(([v]) => v === s));
  ibChips($("#ib-slots"), items, "slots");
}

/** Čo sa ukazuje len pred prierazom / len po ňom; „prieraz s biasom" má zmysel len pri zvolenom biase. */
function ibSync() {
  const pre = ib.f.scope === "pre";
  for (const el of $$("#view-ib .ib-pre")) el.hidden = !pre;
  for (const el of $$("#view-ib .ib-post")) el.hidden = pre;
  $("#ib-bb-wrap").hidden = !pre || ib.f.bias === "all";
}

async function setupIb() {
  if (ib.ready) return;
  ib.ready = true;
  ibLoadPrefs();
  try { ib.meta = await api("/api/ib/meta"); } catch (e) { $("#ib-status").textContent = e.message; ib.ready = false; return; }
  const syms = ib.meta.symbols || [];
  if (!syms.includes(ib.f.symbol)) ib.f.symbol = syms.includes("ES") ? "ES" : (syms[0] || "");
  $("#ib-symbol").innerHTML = syms.map(s => `<option>${esc(s)}</option>`).join("");
  const selects = { "ib-symbol": "symbol", "ib-session": "session", "ib-dow": "dow", "ib-bias": "bias", "ib-bias-break": "bias_break",
                    "ib-brk": "brk", "ib-news": "news", "ib-period": "period", "ib-gran": "gran", "ib-slot-step": "slot_step" };
  for (const [id, key] of Object.entries(selects)) {
    const el = $(`#${id}`);
    el.value = ib.f[key];
    if (el.value !== String(ib.f[key])) ib.f[key] = el.value;   // uložená hodnota, ktorú select už nepozná
    el.onchange = () => {
      ib.f[key] = el.value;
      if (key === "session" || key === "slot_step") ibSlotChips();
      ibSync(); ibQuery();
    };
  }
  ibSegment("ib-scope", "scope");
  ibSegment("ib-dir", "dir");
  ibChips($("#ib-bands"), ib.meta.ib_bands.map((l, i) => [i, l]), "bands");
  ibChips($("#ib-close"), Array.from({ length: 10 }, (_, i) => [i + 1, `${dvNum(i / 10, 1)}–${dvNum(i / 10 + 0.09, 2)}`]), "close_bands");
  ibSlotChips();
  ibSync();
}

async function loadIb() {
  await setupIb();
  if (ib.meta && !ib.data) ibQuery(0);
}

function ibQuery(delay = 250) {
  clearTimeout(ib.timer);
  ib.timer = setTimeout(ibFetch, delay);
}

async function ibFetch() {
  if (!ib.meta || !ib.f.symbol) return;
  ibSave();
  const f = ib.f, q = new URLSearchParams({
    symbol: f.symbol, session: f.session, scope: f.scope, dir: f.dir, bias: f.bias, bias_break: f.bias_break,
    brk: f.brk, news: f.news, period: f.period, gran: f.gran, slot_step: f.slot_step,
    bands: f.bands.join(","), close_bands: f.close_bands.join(","), slots: f.scope === "post" ? f.slots.join(",") : "",
  });
  if (f.dow) q.set("dow", f.dow);
  const seq = ++ib.seq, cold = !(ib.meta.cached || []).includes(`${f.symbol}:${f.session}`);
  $("#ib-status").textContent = cold ? `počítam dni ${f.symbol} (prvýkrát ~10 s)…` : "počítam…";
  try {
    const d = await api(`/api/ib/summary?${q}`);
    if (seq !== ib.seq) return;              // medzitým prišiel novší filter
    (ib.meta.cached = ib.meta.cached || []).push(`${f.symbol}:${f.session}`);
    ib.data = d;
    $("#ib-status").textContent = "";
    ibRender();
  } catch (e) {
    if (seq === ib.seq) $("#ib-status").textContent = e.message;
  }
}

// ---------------------------------------------------------------- výstup --- //

function ibTile(label, value, sub = "") {
  return `<div class="kpi-tile"><span>${esc(label)}</span><b>${value}</b>${sub ? `<small>${sub}</small>` : ""}</div>`;
}
function ibZoneTile(label, h, time) {
  if (!h || !h.n) return ibTile(label, "—");
  const t = time && time.n ? ` · ${esc(time.median)}` : "";
  return ibTile(label, `${ibX(h.median)}${t}`, `70 % ${ibX(h.p70)}${time && time.n ? ` · ${esc(time.p70)}` : ""} · n ${h.n}`);
}
function ibTimeTile(label, h) {
  if (!h || !h.n) return ibTile(label, "—");
  return ibTile(label, esc(h.median), `70 % ${esc(h.p70)} · n ${h.n}`);
}

function ibHistCard(id, title, h, kind) {
  if (!h || !h.n) return `<div class="card"><h3>${esc(title)}</h3><p class="hint">žiadne dni</p></div>`;
  const med = kind === "time" ? `${esc(h.median)}` : ibX(h.median);
  const p70 = kind === "time" ? `${esc(h.p70)}` : ibX(h.p70);
  const out = h.excluded ? ` · mimo grafu ${h.excluded} (≥ 3 IB)` : "";
  return `<div class="card"><h3>${esc(title)} <span class="hint">medián ${med} · 70 % ${p70} · n ${h.n}${out}</span></h3><div id="${id}" class="ib-hist"></div></div>`;
}

function ibRender() {
  const d = ib.data, out = $("#ib-out");
  $("#ib-range").textContent = d.first ? `${d.symbol} · ${d.first} – ${d.last} · ${d.total} dní` : "";
  const pre = d.scope === "pre";
  let warn = "";
  if (d.news_coverage) warn = `<p class="hint">Filter správ pozná len dni ${esc(d.news_coverage[0])} – ${esc(d.news_coverage[1])} (tester/calendar.py); staršie dni do výberu nejdú.</p>`;
  else if (ib.f.news !== "all") warn = `<p class="hint">Kalendár správ nie je k dispozícii — filter správ nevyberie žiadny deň.</p>`;
  let tiles, hists;
  if (pre) {
    tiles = [ibTile("dní", dvNum(d.n)), ibTile("prieraz IB high", ibPct(d.break_high_pct)), ibTile("prieraz IB low", ibPct(d.break_low_pct)),
             ibTile("bez prierazu", ibPct(d.no_break_pct)), ibTimeTile("čas prierazu", d.break_time),
             ibZoneTile("before-break retracement", d.before_break_retr, d.before_break_time)];
    hists = [["ib-h1", "Čas prierazu", d.break_time, "time"], ["ib-h2", "Before-break retracement", d.before_break_retr, "zone"],
             ["ib-h3", "Čas before-break", d.before_break_time, "time"]];
  } else {
    tiles = [ibTile("dní", dvNum(d.n)), ibTile("len jeden okraj", ibPct(d.single_break_pct)), ibTile("extension ≥ 0,25", ibPct(d.ext_over_025_pct)),
             ibTile("retracement ≥ 0,25", ibPct(d.retr_over_025_pct)), ibTile("retracement ≥ 0,5", ibPct(d.retr_over_05_pct)),
             ibTile("HOS/LOS ≥ 0,5", ibPct(d.magic_over_05_pct)), ibZoneTile("max retracement", d.max_retr, d.max_retr_time),
             ibZoneTile("max extension", d.max_ext, d.max_ext_time), ibZoneTile("HOS/LOS", d.magic, d.magic_time),
             ibTimeTile("čas double break", d.double_break_time)];
    hists = [["ib-h1", "Max retracement", d.max_retr, "zone"], ["ib-h2", "Čas max retracementu", d.max_retr_time, "time"],
             ["ib-h3", "Max extension", d.max_ext, "ext"], ["ib-h4", "Čas max extension", d.max_ext_time, "time"],
             ["ib-h5", "HOS/LOS retracement", d.magic, "signed"], ["ib-h6", "Čas HOS/LOS", d.magic_time, "time"],
             ["ib-h7", "Čas double breaku", d.double_break_time, "time"]];
  }
  ib.hists = hists;
  out.innerHTML = `${warn}<div class="kpi-row">${tiles.join("")}</div>
    <div class="ib-grid">${hists.map(([id, t, h, k]) => ibHistCard(id, t, h, k)).join("")}</div>
    ${ibDaysTable(d)}`;
  ibCharts();
}

function ibCharts() {
  if (!ib.hists || typeof Plotly === "undefined" || $("#view-ib").hidden) return;
  const gran = Number(ib.data.gran || ib.f.gran), cfg = { displaylogo: false, responsive: true };
  for (const [id, , h, kind] of ib.hists) {
    if (!h || !h.n || !$(`#${id}`)) continue;
    const xs = Object.keys(h.pct), ys = Object.values(h.pct);
    const hot = kind === "time" ? ibTimeBucket(h, gran) : ibZoneBucket(h, kind);
    Plotly.newPlot(id, [{ type: "bar", x: xs, y: ys, marker: { color: xs.map(x => (x === hot ? IB_GOLD : BLUE)) },
                          hovertemplate: "%{x}: %{y:.1f} %<extra></extra>" }], {
      height: 240, margin: { l: 40, r: 10, t: 6, b: 40 }, template: plotlyTemplate(), bargap: 0.12, showlegend: false,
      xaxis: { type: "category", tickangle: kind === "time" && xs.length > 14 ? -45 : 0 }, yaxis: { ticksuffix: " %", gridcolor: chartGridColor() },
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    }, cfg);
  }
}

function ibDaysTable(d) {
  if (!d.days || !d.days.length) return "";
  const out = { high: "↑ high", low: "↓ low", none: "—" };
  const rows = d.days.map(r => `<tr><td>${esc(r.date)}</td><td>${IB_DOW[r.dow] || ""}</td><td>${esc(r.bias)}</td>
    <td class="num">${dvNum(r.ib_high, 2)}</td><td class="num">${dvNum(r.ib_low, 2)}</td><td class="num">${dvNum(r.ibPct, 2)} %</td>
    <td class="num">${ibX(r.ibClose)}</td><td>${out[r.outcome] || esc(r.outcome)}${r.slot ? ` ${esc(r.slot)}` : ""}${r.dbl ? ` · oba (${esc(r.dblSlot || "")})` : ""}</td>
    <td class="num">${ibX(r.bbScale)}</td><td class="num">${ibX(r.scale)}</td><td class="num">${ibX(r.ext)}</td><td class="num">${ibX(r.magicScale)}</td></tr>`).join("");
  const more = d.selected > d.days.length ? ` <span class="hint">posledných ${d.days.length} z ${dvNum(d.selected)}</span>` : "";
  return `<div class="card"><h3>Dni${more}</h3><div class="scroll"><table class="runs ib-days"><thead><tr>
    <th>dátum</th><th>deň</th><th>bias</th><th class="num">IB high</th><th class="num">IB low</th><th class="num">IB %</th>
    <th class="num">IB close</th><th>prieraz (ET)</th><th class="num">before-break</th><th class="num">max retr.</th>
    <th class="num">max ext.</th><th class="num">HOS/LOS</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
}
