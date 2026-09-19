/* TradeBot Backtester — Graf páru s kresbami enginu. */
"use strict";

// --------------------------------------------------------------------------- //
// Graf páru s kresbami enginu
//
// Sviečky idú z feather súborov po oknách (/api/candles), kresby behu (zóny, TP/SL
// boxy, štítky…) z chart.json.gz orezané na okno (/api/runs/<id>/chart). Boxy a
// čiary sa kreslia ako scatter trace na skupinu štýlov (nie plotly shapes — tých
// by boli tisíce a graf by sa zasekával); pásy seáns sú shapes, tých je pár.
// Časy sú UTC: Plotly ignoruje časové pásmo v reťazci, tak mu dávame UTC text.
// --------------------------------------------------------------------------- //

// Vrstvy grafu (prepínače) a názvy druhov kresieb dodáva stratégia cez /api/meta
// (`strategies[].layers`, `kind_titles`); vrstva „Obchody Freqtrade" je spoločná.
const TRADES_LAYER = { id: "trades", title: "Obchody Freqtrade", kinds: [], sw: GREEN, hollow_kinds: [] };
function layersFor(strategyKey) {
  const spec = strategySpec(strategyKey);
  const layers = [...((spec && spec.layers) || []), TRADES_LAYER];
  return {
    layers,
    byKind: Object.fromEntries(layers.flatMap(l => l.kinds.map(k => [k, l.id]))),
    titles: (spec && spec.kind_titles) || {},
    hollow: new Set(layers.flatMap(l => l.hollow_kinds || [])),
  };
}
// Minúty na timeframe; ponuku dáva server (/api/meta → pair.timeframes, tester/timeframes.json),
// tu musí byť aspoň to, čo je v nej, inak graf taký TF ticho preskočí.
const TF_MINUTES = { "1m": 1, "2m": 2, "3m": 3, "4m": 4, "5m": 5, "15m": 15, "30m": 30,
  "1h": 60, "2h": 120, "4h": 240, "1d": 1440, "1w": 10080 };
const SPANS = [["4 h", 4 * 3600e3], ["12 h", 12 * 3600e3], ["1 deň", 86400e3], ["3 dni", 3 * 86400e3],
  ["1 týždeň", 7 * 86400e3], ["1 mesiac", 30 * 86400e3], ["1 rok", 365 * 86400e3]];
const MAX_CANDLES = 6000;  // rovnaké ako server (tradebot/webapp/chart.py)
const DASH = { dotted: "dot", dashed: "dash" };

const pc = { rec: null, trades: [], runFrom: 0, runTo: 0, from: 0, to: 0, tf: "auto", layers: {}, meta: null, last: null,
  seq: 0, bound: false, relayoutTimer: null, quietUntil: 0, strategy: "ibs", L: null };

const utc = ms => new Date(ms).toISOString().slice(0, 19).replace("T", " ");
const parseUtc = s => Date.parse(String(s).replace(" ", "T").replace(/(\.\d+)?$/, "Z"));
const fmtPrice = v => Number(v).toLocaleString("en-US", { maximumFractionDigits: 6 });

function layerPrefsKey() { return `tradebot.layers.${pc.strategy}`; }

function loadLayerPrefs() {
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(layerPrefsKey()) || "null"); } catch (_) { /* ignoruj */ }
  pc.layers = {};
  for (const l of pc.L.layers) pc.layers[l.id] = saved && l.id in saved ? !!saved[l.id] : true;
}

function tfOptions() {
  const p = state.meta.pairs.find(x => x.pair === pc.rec.settings.pair);
  const tfs = (p && p.timeframes && p.timeframes.length) ? p.timeframes : ["3m"];
  return tfs.filter(t => t in TF_MINUTES);
}

function initPairChart(rec, trades) {
  pc.rec = rec; pc.trades = trades; pc.meta = null; pc.last = null; pc.seq++;
  pc.strategy = rec.settings.strategy || "ibs";
  pc.L = layersFor(pc.strategy);
  const [a, b] = rec.settings.timerange.split("-");
  pc.runFrom = Date.parse(`${a.slice(0, 4)}-${a.slice(4, 6)}-${a.slice(6)}T00:00:00Z`);
  pc.runTo = Date.parse(`${b.slice(0, 4)}-${b.slice(4, 6)}-${b.slice(6)}T00:00:00Z`);
  loadLayerPrefs();
  $("#pc-title").textContent = `${rec.settings.pair} · beh na ${rec.settings.timeframe || "3m"} · UTC`;

  const span = $("#pc-span"); span.innerHTML = "";
  for (const [t, ms] of SPANS) { const o = document.createElement("option"); o.value = ms; o.textContent = t; span.append(o); }
  span.value = String(86400e3);
  span.onchange = () => setWindow(pc.from, pc.from + Number(span.value));

  const tf = $("#pc-tf"); tf.innerHTML = `<option value="auto">auto</option>`;
  for (const t of tfOptions()) { const o = document.createElement("option"); o.value = t; o.textContent = t; tf.append(o); }
  tf.value = "auto"; pc.tf = "auto";
  tf.onchange = () => { pc.tf = tf.value; loadPairChart(); };

  $("#pc-start").onclick = () => setWindow(pc.runFrom, pc.runFrom + spanMs());
  $("#pc-prev").onclick = () => setWindow(pc.from - spanMs(), pc.from);
  $("#pc-next").onclick = () => setWindow(pc.to, pc.to + spanMs());
  $("#pc-first-trade").onclick = () => { if (pc.trades.length) jumpToTrade(pc.trades[0]); };
  $("#pc-first-trade").disabled = !pc.trades.length;
  $("#pc-goto").onchange = () => { const v = $("#pc-goto").value; if (v) { const t0 = Date.parse(v + ":00Z"); setWindow(t0, t0 + spanMs()); } };

  chartNote(rec.chart);
  renderLayerToggles();
  if (rec.chart && ["missing", "queued", "running"].includes(rec.chart.state)) ensureChart(rec, rec.chart.state === "missing");

  if (pc.trades.length) jumpToTrade(pc.trades[0]);
  else setWindow(pc.runFrom, pc.runFrom + 86400e3);
}

/**
 * Poznámka pod grafom podľa stavu kresieb. Kresby nie sú v gite — beh ich má len lokálne
 * (čerstvý beh, prepočítaný graf) a inak sa prepočítajú z uloženého configu na pozadí.
 */
function chartNote(ch) {
  const el = $("#pc-note");
  el.classList.remove("warn");
  const st = (ch && ch.state) || "missing";
  if (st === "ready") {
    el.textContent = ch.warning || "";
    el.classList.toggle("warn", !!ch.warning);
  } else if (st === "unavailable") {
    el.textContent = "Tento beh graf nemá (nedobehol) — ukazujú sa len sviečky.";
  } else if (st === "failed") {
    el.innerHTML = `Graf sa nepodarilo prepočítať: ${esc(ch.error || "neznáma chyba")} `
      + `<button class="ghost small" type="button" id="pc-retry">skúsiť znova</button>`;
    const b = $("#pc-retry");
    if (b) b.onclick = () => ensureChart(pc.rec, true);
  } else {
    const riadok = ((ch && ch.log_tail) || []).slice(-1)[0] || "";
    el.textContent = `Počíta sa graf z uloženého configu behu (kresby nie sú v gite)… `
      + (st === "queued" ? "čaká" : "beží") + (riadok ? ` · ${riadok.slice(0, 120)}` : "")
      + " — sviečky a obchody sú vidieť hneď, zóny a štítky pribudnú.";
  }
}

/** Vypýta prepočet kresieb (ak treba) a sleduje ho; po dobehnutí prekreslí graf. */
async function ensureChart(rec, request) {
  const id = rec.id;
  let ch;
  try {
    ch = request ? await api(`/api/runs/${id}/chart`, { method: "POST" })
      : await api(`/api/runs/${id}/chart/status`);
  } catch (e) {
    ch = { state: "failed", error: e.message };
  }
  if (pc.rec !== rec) return;          // medzitým sa otvoril iný beh
  rec.chart = ch;
  chartNote(ch);
  if (ch.state === "ready") {
    rec.has_chart = true;
    pc.meta = null;
    renderLayerToggles();
    loadPairChart();
    return;
  }
  if (ch.state === "queued" || ch.state === "running") {
    clearTimeout(pc.replayTimer);
    pc.replayTimer = setTimeout(() => ensureChart(rec, false), 2500);
  }
}

function spanMs() { return Math.max(pc.to - pc.from, 15 * 60e3) || 86400e3; }

function chooseTf(span) {
  const opts = tfOptions();
  if (pc.tf !== "auto") return opts.includes(pc.tf) ? pc.tf : (opts[0] || "3m");
  const fine = opts.filter(t => span / (TF_MINUTES[t] * 60e3) <= MAX_CANDLES * 0.9);
  const idx = Math.max(opts.indexOf(pc.rec.settings.timeframe || "3m"), 0);  // jemnejšie než TF behu nemá zmysel
  const ok = fine.filter(t => opts.indexOf(t) >= idx);
  return ok[0] || fine[0] || opts[opts.length - 1] || "3m";
}

function setWindow(from, to) {
  if (!(to > from)) return;
  pc.from = Math.round(from); pc.to = Math.round(to);
  const preset = SPANS.find(([, ms]) => Math.abs(ms - (pc.to - pc.from)) < 60e3);
  $("#pc-span").value = preset ? String(preset[1]) : "";
  $("#pc-window").textContent = `${utc(pc.from).slice(0, 16)} → ${utc(pc.to).slice(0, 16)}`;
  loadPairChart();
}

function jumpToTrade(t) {
  const open = Date.parse(t.open_date), close = Date.parse(t.close_date || t.open_date);
  const dur = Math.max(close - open, 15 * 60e3);
  const pad = Math.max(dur * 0.6, 2 * 3600e3);
  for (const tr of $$("#trades tbody tr")) tr.classList.toggle("hl", pc.trades[Number(tr.dataset.trade)] === t);
  setWindow(open - pad, close + pad);
  $("#pair-chart").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderLayerToggles() {
  const box = $("#pc-layers"); box.innerHTML = "";
  const counts = (pc.meta && pc.meta.counts) || {};
  for (const l of pc.L.layers) {
    if (!pc.rec.has_chart && l.id !== "trades") continue;
    const n = l.id === "trades" ? pc.trades.length : l.kinds.reduce((s, k) => s + (counts[k] || 0), 0);
    const lab = document.createElement("label"); lab.classList.toggle("off", !pc.layers[l.id]);
    lab.innerHTML = `<input type="checkbox" ${pc.layers[l.id] ? "checked" : ""}> <span class="sw" style="background:${l.sw}"></span>${esc(l.title)} <span class="n">${pc.meta || l.id === "trades" ? n : ""}</span>`;
    lab.querySelector("input").onchange = e => {
      pc.layers[l.id] = e.target.checked; lab.classList.toggle("off", !e.target.checked);
      try { localStorage.setItem(layerPrefsKey(), JSON.stringify(pc.layers)); } catch (_) { /* ignoruj */ }
      if (pc.last) renderPairChart(pc.last.candles, pc.last.objects);
    };
    box.append(lab);
  }
}

async function loadPairChart() {
  const seq = ++pc.seq;
  const el = $("#pair-chart"); el.classList.add("loading");
  const tf = chooseTf(pc.to - pc.from);
  const q = `from=${pc.from}&to=${pc.to}`;
  try {
    const [candles, chart] = await Promise.all([
      api(`/api/candles?pair=${encodeURIComponent(pc.rec.settings.pair)}&tf=${tf}&${q}`),
      pc.rec.has_chart ? api(`/api/runs/${pc.rec.id}/chart?${q}`) : Promise.resolve({ meta: null, objects: [] }),
    ]);
    if (seq !== pc.seq) return;
    if (chart.meta && !pc.meta) { pc.meta = chart.meta; renderLayerToggles(); }
    pc.last = { candles, objects: chart.objects };
    $("#pc-status").textContent = `${tf} · ${candles.t.length} sviečok · ${chart.objects.length} objektov` +
      (candles.truncated ? " · okno orezané, zvoľ hrubší TF" : "");
    renderPairChart(candles, chart.objects);
  } catch (e) {
    if (seq !== pc.seq) return;
    el.innerHTML = `<div class="error">${esc(e.message)}</div>`;
  } finally { if (seq === pc.seq) el.classList.remove("loading"); }
}

function describe(o) {
  const head = `<b>${esc(pc.L.titles[o.k] || o.k)}</b>${o.tx ? " · " + esc(o.tx).replace(/\n/g, " ") : ""}${o.z != null ? ` · zóna #${o.z}` : ""}`;
  if (o.t === "label") return `${head}<br>${utc(o.x).slice(0, 16)} · ${fmtPrice(o.y)}`;
  const y = o.t === "bg" ? "" : `<br>${fmtPrice(Math.max(o.y1, o.y2))} – ${fmtPrice(Math.min(o.y1, o.y2))}`;
  return `${head}<br>${utc(o.x1).slice(0, 16)} → ${utc(o.x2).slice(0, 16)}${y}`;
}

/**
 * Farby kresieb (zóny, štruktúra…) prichádzajú z backendu ako hex/rgba a ich VÝZNAM
 * (LONG/SHORT/silná zóna/…) sa nesmie zmeniť — len na tmavom pozadí by tmavší odtieň
 * (napr. štruktúrna "slate") zanikol a nízkoalfa výplň by nebola vidieť. `chartColor()`
 * preto na tmavej téme len zosvetlí, čo by v nej zaniklo, a zvýrazní priehľadné výplne;
 * na svetlej téme vracia farbu bez zmeny.
 */
function parseAnyColor(c) {
  if (typeof c !== "string") return null;
  let m = /^#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$/.exec(c.trim());
  if (m) {
    const n = parseInt(m[1], 16);
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255, a: m[2] ? parseInt(m[2], 16) / 255 : 1 };
  }
  m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/.exec(c.trim());
  if (m) return { r: +m[1], g: +m[2], b: +m[3], a: m[4] !== undefined ? +m[4] : 1 };
  return null;
}
const colorLuminance = ({ r, g, b }) => (0.299 * r + 0.587 * g + 0.114 * b) / 255;

function chartColor(c) {
  if (!c || !isDarkTheme()) return c;
  const p = parseAnyColor(c);
  if (!p) return c;
  let { r, g, b, a } = p;
  const lum = colorLuminance(p);
  if (lum < 0.42) {
    const t = Math.min(1, (0.42 - lum) / 0.42) * 0.72;  // ako veľmi zosvetliť tmavý odtieň
    r += (255 - r) * t; g += (255 - g) * t; b += (255 - b) * t;
  }
  if (a < 0.35) a = Math.min(0.6, a * 1.8);  // priehľadná výplň potrebuje na tmavom viac alfy
  return `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${a})`;
}

function objectTraces(objects) {
  const groups = new Map(), shapes = [];
  const group = (key, init) => { let g = groups.get(key); if (!g) { g = init(); groups.set(key, g); } return g; };
  for (const o of objects) {
    const layer = pc.L.byKind[o.k];  // druh mimo vrstiev sa kreslí vždy
    if (layer && !pc.layers[layer]) continue;
    if (pc.L.hollow.has(o.k)) continue;  // kreslí sa ako dutá sviečka, viď candleTraces
    const name = (pc.L.layers.find(l => l.id === layer) || {}).title || o.k;
    const desc = describe(o);
    if (o.t === "bg") {
      shapes.push({ type: "rect", xref: "x", yref: "paper", layer: "below", x0: utc(o.x1), x1: utc(o.x2), y0: 0, y1: 1, fillcolor: chartColor(o.c), line: { width: 0 } });
    } else if (o.t === "box") {
      const fill = chartColor(o.fc) || "rgba(0,0,0,0)", bc = chartColor(o.bc), dash = DASH[o.bs] || "solid", w = o.bw ?? 1;
      const g = group(`box|${fill}|${bc}|${dash}|${w}`, () => ({ type: "scatter", mode: "lines", fill: "toself", fillcolor: fill,
        line: { color: bc, width: w, dash }, x: [], y: [], text: [], hoverinfo: "text", hoveron: "points", showlegend: false, name }));
      const x2 = o.er ? Math.max(o.x2, pc.to) : o.x2;
      g.x.push(utc(o.x1), utc(x2), utc(x2), utc(o.x1), utc(o.x1), null);
      g.y.push(o.y1, o.y1, o.y2, o.y2, o.y1, null);
      g.text.push(desc, desc, desc, desc, desc, "");
    } else if (o.t === "line") {
      const c = chartColor(o.c), dash = DASH[o.s] || "solid", w = o.w ?? 1;
      const g = group(`line|${c}|${dash}|${w}`, () => ({ type: "scatter", mode: "lines", line: { color: c, width: w, dash },
        x: [], y: [], text: [], hoverinfo: "text", showlegend: false, name }));
      g.x.push(utc(o.x1), utc(o.x2), null); g.y.push(o.y1, o.y2, null); g.text.push(desc, desc, "");
    } else if (o.t === "label") {
      const bubble = !!o.bg;
      const g = group(`label|${o.ab ? 1 : 0}|${bubble ? 1 : 0}`, () => {
        const t = { type: "scatter", mode: bubble ? "markers+text" : "text",
          x: [], y: [], text: [], hovertext: [], hoverinfo: "text", showlegend: false, name,
          textposition: o.ab ? "top center" : "bottom center", textfont: { size: 10, color: [] } };
        // Plotly neznesie `marker: undefined` (validácia robí `"line" in marker`), tak kľúč len keď treba.
        if (bubble) t.marker = { symbol: o.ab ? "triangle-down" : "triangle-up", size: 8, color: [] };
        return t;
      });
      g.x.push(utc(o.x)); g.y.push(o.y); g.text.push(esc(o.tx || "").replace(/\n/g, "<br>"));
      g.textfont.color.push(chartColor(bubble ? o.bg : o.c)); g.hovertext.push(desc);
      if (bubble) g.marker.color.push(chartColor(o.bg));
    }
  }
  return { traces: [...groups.values()], shapes };
}

/**
 * Sviečky. Imbalance sviečky (Pine ich vybledne a označí boxom na tele) idú do vlastného
 * trace s priehľadnou výplňou — dutá sviečka s obrysom vo farbe imbalance (zelená bull,
 * tehlová bear). Plotly počíta šírku sviečky naprieč všetkými candlestick trace na osi,
 * takže duté sviečky sú rovnako široké ako ostatné. Na hrubšom TF sa označí sviečka,
 * do ktorej imbalance 3m sviečka časovo patrí.
 */
function candleTraces(candles, objects) {
  const marks = new Map();  // index sviečky -> farba obrysu
  if (pc.L.hollow.size) {
    const t = candles.t;
    for (const o of objects) {
      if (!pc.L.hollow.has(o.k) || o.t !== "box") continue;
      const layer = pc.L.byKind[o.k];
      if (layer && !pc.layers[layer]) continue;
      let lo = 0, hi = t.length - 1, idx = -1;
      while (lo <= hi) { const m = (lo + hi) >> 1; if (t[m] <= o.x1) { idx = m; lo = m + 1; } else hi = m - 1; }
      if (idx >= 0 && (idx + 1 >= t.length || o.x1 < t[idx + 1])) marks.set(idx, chartColor(o.bc));
    }
  }
  const base = (name, inc, dec, fill) => ({ type: "candlestick", x: [], open: [], high: [], low: [], close: [], name, showlegend: false, whiskerwidth: 0.3,
    increasing: { line: { color: inc, width: 1 }, fillcolor: fill || inc }, decreasing: { line: { color: dec, width: 1 }, fillcolor: fill || dec } });
  const normal = base(pc.rec.settings.pair, GREEN, RED);
  const hollow = new Map();
  for (let i = 0; i < candles.t.length; i++) {
    let tr = normal;
    const col = marks.get(i);
    if (col) {
      tr = hollow.get(col);
      if (!tr) { tr = base("Dutá sviečka", col, col, "rgba(0,0,0,0)"); hollow.set(col, tr); }
    }
    tr.x.push(utc(candles.t[i])); tr.open.push(candles.o[i]); tr.high.push(candles.h[i]); tr.low.push(candles.l[i]); tr.close.push(candles.c[i]);
  }
  return [normal, ...hollow.values()];
}

function tradeTraces() {
  if (!pc.layers.trades) return [];
  const inWin = pc.trades.filter(t => Date.parse(t.close_date || t.open_date) >= pc.from && Date.parse(t.open_date) <= pc.to);
  if (!inWin.length) return [];
  const cur = (pc.rec.result || {}).stake_currency || "USDT";
  const entry = { type: "scatter", mode: "markers", x: [], y: [], text: [], hoverinfo: "text", showlegend: false, name: "Vstup",
    marker: { symbol: [], size: 11, color: [], line: { color: "#fff", width: 1 } } };
  const exit = { type: "scatter", mode: "markers", x: [], y: [], text: [], hoverinfo: "text", showlegend: false, name: "Výstup",
    marker: { symbol: "x", size: 9, color: [], line: { width: 0 } } };
  const win = { type: "scatter", mode: "lines", x: [], y: [], hoverinfo: "skip", showlegend: false, line: { color: GREEN, width: 1.5, dash: "dot" } };
  const loss = { type: "scatter", mode: "lines", x: [], y: [], hoverinfo: "skip", showlegend: false, line: { color: RED, width: 1.5, dash: "dot" } };
  for (const t of inWin) {
    const long = !t.is_short, good = (t.profit_abs || 0) >= 0;
    const txt = `<b>${long ? "LONG" : "SHORT"}</b> ${esc(t.enter_tag || "")}<br>vstup ${fmtPrice(t.open_rate)} · ${utc(Date.parse(t.open_date)).slice(0, 16)}` +
      `<br>výstup ${fmtPrice(t.close_rate)} · ${utc(Date.parse(t.close_date)).slice(0, 16)} · ${esc(t.exit_reason || "")}` +
      `<br>PnL ${Number(t.profit_abs).toFixed(2)} ${cur} (${(t.profit_ratio * 100).toFixed(2)} %)`;
    entry.x.push(utc(Date.parse(t.open_date))); entry.y.push(t.open_rate); entry.text.push(txt);
    entry.marker.symbol.push(long ? "triangle-up" : "triangle-down"); entry.marker.color.push(long ? GREEN : RED);
    exit.x.push(utc(Date.parse(t.close_date))); exit.y.push(t.close_rate); exit.text.push(txt); exit.marker.color.push(good ? GREEN : RED);
    const ln = good ? win : loss;
    ln.x.push(utc(Date.parse(t.open_date)), utc(Date.parse(t.close_date)), null); ln.y.push(t.open_rate, t.close_rate, null);
  }
  return [win, loss, entry, exit];
}

function renderPairChart(candles, objects) {
  const el = $("#pair-chart");
  const { traces, shapes } = objectTraces(objects);
  let lo = Math.min(...candles.l), hi = Math.max(...candles.h);
  if (!Number.isFinite(lo)) { lo = 0; hi = 1; }
  const pad = (hi - lo) * 0.05 || 1;
  const grid = chartGridColor();
  Plotly.react(el, [...traces, ...candleTraces(candles, objects), ...tradeTraces()], {
    height: 640, margin: { l: 10, r: 70, t: 8, b: 36 }, template: plotlyTemplate(), dragmode: "pan", hovermode: "closest",
    showlegend: false, shapes,
    xaxis: { type: "date", range: [utc(pc.from), utc(pc.to)], rangeslider: { visible: false }, showgrid: true, gridcolor: grid },
    yaxis: { side: "right", range: [lo - pad, hi + pad], showgrid: true, gridcolor: grid, fixedrange: false },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  }, { displaylogo: false, responsive: true, scrollZoom: true, modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"] });
  pc.quietUntil = Date.now() + 400;
  if (!pc.bound) {
    pc.bound = true;
    el.on("plotly_relayout", ev => {
      // Len skutočný pan/zoom používateľa: ten má vždy oba kraje osi x. Autosize,
      // dvojklik (autorange) a echo nášho vlastného rozsahu sa ignorujú, inak by sa
      // graf po každom vykreslení načítaval znova a okno by rástlo samo.
      if (Date.now() < pc.quietUntil || ev.autosize || !("xaxis.range[0]" in ev) || !("xaxis.range[1]" in ev)) return;
      const a = parseUtc(ev["xaxis.range[0]"]), b = parseUtc(ev["xaxis.range[1]"]);
      if (!Number.isFinite(a) || !Number.isFinite(b) || b <= a) return;
      if (Math.abs(a - pc.from) < 1000 && Math.abs(b - pc.to) < 1000) return;
      const cur = pc.to - pc.from, span = b - a;
      // Posun v rámci načítaného okna netreba načítavať; von z okna alebo výrazný zoom áno.
      if (a >= pc.from && b <= pc.to && span > cur * 0.45) return;
      // Jeden krok nesmie okno zväčšiť viac než 4× — poistka proti slučke.
      const limit = cur * 4;
      const mid = (a + b) / 2, half = Math.min(span, limit) / 2;
      clearTimeout(pc.relayoutTimer);
      pc.relayoutTimer = setTimeout(() => setWindow(mid - half, mid + half), 250);
    });
  }
}

function closeDetail() {
  $("#run-detail").hidden = true;
  $("#runs-table").parentElement.parentElement.hidden = false;
  state.detailId = null;
}

async function loadDetailIntoForm() {
  const r = await api(`/api/runs/${state.detailId}`);
  const rec = r.record;
  setStrategy(rec.settings.strategy || "ibs");  // formulár musí byť tej stratégie, ktorej sú parametre
  state.profile = rec.settings.profile || null;
  // základ = profil (aby sa zvýraznili odchýlky), hodnoty = beh. Profil behu už nemusí
  // existovať (archivované presety) — vtedy je základom Pine default a odchýlky sú voči nemu.
  let base = {};
  if (state.profile) {
    try { base = (await api(`/api/profiles/${state.profile.split("/").map(encodeURIComponent).join("/")}?strategy=${encodeURIComponent(state.strategy)}`)).params; }
    catch (_) { state.profile = null; }
  }
  $("#profile").value = state.profile && state.meta.profiles.includes(state.profile) ? state.profile : "";
  setParams(base, true);
  setParams(rec.params, false);
  $("#pair").value = rec.settings.pair; $("#pair").onchange();
  fillTimeframes(rec.settings.pair, rec.settings.timeframe || "3m");
  const [a, b] = rec.settings.timerange.split("-");
  $("#from").value = `${a.slice(0, 4)}-${a.slice(4, 6)}-${a.slice(6)}`; $("#to").value = `${b.slice(0, 4)}-${b.slice(4, 6)}-${b.slice(6)}`;
  $("#fee").value = rec.settings.fee != null ? (rec.settings.fee * 100) : ""; $("#wallet").value = rec.settings.wallet;
  $("#detail").checked = !!rec.settings.timeframe_detail; $("#note").value = rec.note || "";
  showView("new");
}
