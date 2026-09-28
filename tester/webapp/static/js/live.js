/* TradeBot Backtester — Karta Live: telemetria zo spustených stratégií (docs/LIVE.md). */
"use strict";

// --------------------------------------------------------------------------- //
// Live: bežiace stratégie (NinjaTrader 8, MetaTrader 5) zo zrkadla webapp
//
// Stránka číta len zrkadlo (`/api/live`, `/api/live/<id>/snapshot`, `/api/live/<id>/events`),
// ktoré plní vlákno LiveMirror na serveri (hub + lokálny spool). Kým je karta otvorená,
// zoznam aj otvorený detail sa obnovujú každých 5 s; inak sa nič nepýta.
// Graf: sviečky z `bar`, kresby z `draw` zlúčené podľa `id` (update mení pole, delete
// maže) a nakreslené tým istým `objectTraces` ako graf behu, vyplnenia ako značky.
// Behy: každý štart stratégie je nová session; výber „Beh" v detaile načíta snapshot so
// `session=` (celý beh, do 5000 barov). Ukončený beh sa neobnovuje, živý áno.
// --------------------------------------------------------------------------- //

const LIVE_POLL_MS = 5000;
const LIVE_FILLS_LAYER = { id: "fills", title: "Vyplnenia u brokera", kinds: [], sw: BLUE, hollow_kinds: [] };
const LIVE_MODIFY_COLOR = "#ff9800";
/** Posuny SL/TP otvorenej pozície (`order` s `a:"modify"`) — malé stupienky na grafe. */
const LIVE_MODIFY_LAYER = { id: "modify", title: "Posuny SL/TP", kinds: [], sw: LIVE_MODIFY_COLOR, hollow_kinds: [] };
/** Polia `update` kresby (názvy atribútov objektu v jadre) → krátke kľúče JSON kresby. */
const LIVE_DRAW_FIELD = { x1_ms: "x1", x2_ms: "x2", x_ms: "x", fill_color: "fc", border_color: "bc",
  border_style: "bs", border_width: "bw", extend_right: "er", color: "c", style: "s", width: "w",
  text: "tx", above: "ab", bg_color: "bg", zone_uid: "z" };

const lv = {
  timer: null, selected: null, instances: [], now: 0, mirror: null,
  snap: null, seq: 0,
  session: "", sessions: [], sessionsKey: "", // vybraný beh ("" = aktuálny naprieč behmi) a zoznam behov inštancie
  strategy: null, L: null, layers: {},       // kontext kresieb pre objectTraces (ako `pc` pri behu)
  fills: {},                                  // id inštancie → { after, fills: [], dirs: {} } (prírastkovo)
};

/** Vybraný beh, alebo null pre „aktuálny". */
function liveChosenSession() { return lv.session ? lv.sessions.find(s => s.session === lv.session) || null : null; }

/** Detail sa obnovuje, kým je zvolený „aktuálny" alebo živý beh; ukončený beh sa už nemení. */
function liveDetailPolls() { const s = liveChosenSession(); return !lv.session || !s || s.live; }

function liveAge(ms, now) {
  if (!ms) return "—";
  const s = Math.max(0, Math.round((now - ms) / 1000));
  if (s < 60) return `pred ${s} s`;
  if (s < 3600) return `pred ${Math.round(s / 60)} min`;
  if (s < 86400) return `pred ${Math.round(s / 3600)} h`;
  return `pred ${Math.round(s / 86400)} d`;
}

/** Zapnutie polling-u karty; `stopLive()` ho vypne (volá showView pri odchode z karty). */
function stopLive() { clearTimeout(lv.timer); lv.timer = null; }

function liveSetup() {
  $("#live-back").onclick = () => { lv.selected = null; renderLiveList(); $("#live-detail").hidden = true; $("#live-list").hidden = false; };
  $("#live-session").onchange = async e => {
    lv.session = e.target.value; lv.snap = null;
    if (!lv.selected) return;
    $("#live-detail-error").hidden = true; $("#live-chart").classList.add("loading");
    try { await loadLiveDetail(lv.selected); }
    catch (err) { $("#live-detail-error").textContent = err.message; $("#live-detail-error").hidden = false; }
    finally { $("#live-chart").classList.remove("loading"); }
  };
  // chip pri záložke hneď po štarte — bez otvárania karty
  api("/api/live").then(d => { lv.instances = d.instances; lv.now = d.now; lv.mirror = d.mirror; liveChip(); }).catch(() => {});
}

/** Inštancia je „živá", keď posledná udalosť nie je staršia než 3 bary jej TF. */
function liveAlive(inst) {
  const tf = Math.max(1, Number(inst.tf) || 1);
  return inst.last_t && (lv.now - inst.last_t) <= 3 * tf * 60e3;
}

function liveChip() {
  const n = lv.instances.filter(liveAlive).length;
  $("#live-tab-chip").textContent = n ? String(n) : "";
  $("#live-tab-chip").className = `chip ${n ? "ok" : ""}`;
}

async function loadLive() {
  stopLive();
  if (document.hidden) { lv.timer = setTimeout(loadLive, LIVE_POLL_MS); return; }
  try {
    const d = await api("/api/live");
    lv.instances = d.instances; lv.now = d.now; lv.mirror = d.mirror;
    $("#live-error").hidden = true;
  } catch (e) {
    $("#live-error").textContent = e.message; $("#live-error").hidden = false;
    lv.timer = setTimeout(loadLive, LIVE_POLL_MS);
    return;
  }
  liveChip();
  renderLiveStatus();
  await Promise.all(lv.instances.map(i => loadLiveFills(i.id).catch(() => {})));
  renderLiveList();
  if (lv.selected) {
    // zoznam behov je lacný — obnoví sa vždy (nový štart pribudne, živý sa ukončí); detail len keď sa mení
    await loadLiveSessions(lv.selected).catch(() => {});
    if (liveDetailPolls()) await loadLiveDetail(lv.selected).catch(e => { $("#live-detail-error").textContent = e.message; $("#live-detail-error").hidden = false; });
  }
  if (!$("#view-live").hidden) lv.timer = setTimeout(loadLive, LIVE_POLL_MS);
}

/** Behy inštancie do výberu „Beh": „aktuálny / živý" prvý, potom behy od najnovšieho
 *  (`štart UTC → koniec UTC (bary, fills, profil)`). Prekreslí sa len keď sa zoznam zmenil,
 *  nech obnova každých 5 s nezavrie rozbalený výber. */
async function loadLiveSessions(id) {
  const rows = await api(`/api/live/${encodeURIComponent(id)}/sessions`);
  if (lv.selected !== id) return;
  lv.sessions = rows;
  const key = rows.map(s => `${s.session}:${s.live ? 1 : 0}:${s.ended || 0}:${s.bars}:${s.fills}`).join("|");
  if (key === lv.sessionsKey && $("#live-session").options.length) return;
  lv.sessionsKey = key;
  if (lv.session && !rows.some(s => s.session === lv.session)) lv.session = "";
  const sel = $("#live-session");
  sel.innerHTML = `<option value="">aktuálny / živý (posledných 500 barov)</option>` + rows.map(s => {
    const koniec = s.ended ? utc(s.ended).slice(0, 16) : (s.live ? "beží" : "bez konca");
    const lab = `${utc(s.started).slice(0, 16)} → ${koniec} (${s.bars} barov, ${s.fills} fills${s.profile ? ", " + s.profile : ""})${s.live ? " ● živý" : ""}`;
    return `<option value="${esc(s.session)}">${esc(lab)}</option>`;
  }).join("");
  sel.value = lv.session;
  renderLiveSessionMeta();
}

/** Riadok pod hlavičkou pre vybraný beh: id, agent, profil, stroj, štart, koniec a dôvod. */
function renderLiveSessionMeta() {
  const box = $("#live-session-meta"), s = liveChosenSession();
  if (!s) { box.hidden = true; box.textContent = ""; return; }
  const inst = lv.snap && lv.snap.instance || {};
  const stav = s.live ? "beží (obnova každých 5 s)" : (s.ended ? `ukončený ${utc(s.ended)} UTC · dôvod: ${s.reason || "—"}` : "bez `bye` a ticho — ukončený bez rozlúčky (pád, výpadok spoolu)");
  box.textContent = `beh ${s.session} · agent ${s.agent || "—"} · profil ${s.profile || "—"} · stroj ${inst.host || "—"}`
    + ` · štart ${utc(s.started)} UTC · ${stav} · ${s.bars} barov · ${s.orders} orderov · ${s.fills} fillov`;
  box.hidden = false;
}

function renderLiveStatus() {
  const m = lv.mirror || {};
  const parts = [];
  parts.push(m.hub_url ? `hub ${m.hub_url} · kurzor ${m.hub_cursor}` : "hub: nenastavený (karta Hub)");
  parts.push(m.local_roots && m.local_roots.length ? `lokálny spool: ${m.local_roots.join(", ")}` : "lokálny spool: žiadny");
  parts.push(m.running ? (m.last_ok ? `synchronizované ${liveAge(m.last_ok * 1000, lv.now)}` : "zrkadlo beží, zatiaľ nič") : "zrkadlo nebeží (štartuje sa s webapp)");
  $("#live-status").textContent = parts.join(" · ");
  const err = $("#live-error");
  if (m.last_error) { err.textContent = `zrkadlo: ${m.last_error}`; err.hidden = false; }
}

/** Fills a smery vstupov inštancie — prírastkovo od posledného rowid, nech sa každých 5 s neťahá všetko. */
async function loadLiveFills(id) {
  const f = lv.fills[id] || (lv.fills[id] = { after: 0, fills: [], dirs: {} });
  const rows = await api(`/api/live/${encodeURIComponent(id)}/events?after=${f.after}&kinds=fill,order&limit=5000`);
  for (const r of rows) {
    f.after = Math.max(f.after, r.id);
    const ev = r.event;
    if (ev.k === "fill") f.fills.push(ev);
    else if (ev.k === "order" && ev.a === "entry") f.dirs[ev.id] = Number(ev.dir ?? (ev.p && ev.p.dir) ?? 1) || 1;
  }
  return f;
}

/** Odhad pozície z fillov: za každé id vstupy − výstupy (v množstve) × smer vstupu z orderu. */
function livePosition(f) {
  if (!f || !f.fills.length) return null;
  const net = {};
  for (const x of f.fills) net[x.id] = (net[x.id] || 0) + (x.side === "in" ? 1 : -1) * Number(x.qty || 0);
  let qty = 0; const open = [];
  for (const [id, q] of Object.entries(net)) {
    if (Math.abs(q) < 1e-9) continue;
    const dir = f.dirs[id] || 1;
    qty += q * dir; open.push(`${id} ${q * dir > 0 ? "long" : "short"} ${Math.abs(q)}`);
  }
  return { qty, open };
}

function liveFillsToday(f) {
  if (!f) return 0;
  const start = Math.floor(lv.now / 86400e3) * 86400e3;
  return f.fills.filter(x => x.ft >= start).length;
}

function liveStatusChip(inst) {
  const alive = liveAlive(inst);
  const tester = inst.hello && inst.hello.tester ? ' <span class="chip warn" title="beží v Strategy Testeri / Analyzeri">tester</span>' : "";
  return `<span class="chip ${alive ? "ok" : ""}" title="${alive ? "posledná udalosť do 3 barov" : "bez udalostí dlhšie než 3 bary"}">${alive ? "živá" : "ticho"}</span>${tester}`;
}

function renderLiveList() {
  const list = lv.instances;
  $("#live-count").textContent = list.length ? String(list.length) : "";
  $("#live-empty").hidden = !!list.length;
  $("#live-table").parentElement.hidden = !list.length;
  $("#live-table tbody").innerHTML = list.map(i => {
    const f = lv.fills[i.id];
    const pos = livePosition(f);
    const posTxt = pos === null ? "—" : (pos.qty > 0 ? `+${pos.qty}` : String(pos.qty));
    return `<tr data-live="${esc(i.id)}" class="${i.id === lv.selected ? "hl" : ""}">
      <td>${liveStatusChip(i)}</td><td>${esc(i.platform || "—")}</td><td>${esc(i.account || "—")}</td>
      <td><b>${esc(i.symbol || "—")}</b></td><td>${i.tf ? i.tf + "m" : "—"}</td><td>${esc(i.strategy || "—")}</td>
      <td>${esc(i.profile || "—")}</td><td>${esc(i.host || "—")}</td><td>${esc(i.agent || "—")}</td>
      <td title="${i.last_bar_ms ? utc(i.last_bar_ms) + " UTC (otvorenie baru)" : ""}">${i.last_bar_ms ? `${liveAge(i.last_bar_ms, lv.now)} <span class="muted">${utc(i.last_bar_ms).slice(5, 16)}</span>` : "—"}</td>
      <td class="num" title="${pos ? esc(pos.open.join(", ")) : "žiadne vyplnenia"}">${posTxt}</td>
      <td class="num">${liveFillsToday(f)}</td></tr>`;
  }).join("");
  for (const tr of $$("#live-table tbody tr")) tr.onclick = () => openLiveDetail(tr.dataset.live);
}

async function openLiveDetail(id) {
  lv.selected = id; lv.snap = null;
  lv.session = ""; lv.sessions = []; lv.sessionsKey = "";
  $("#live-session").innerHTML = `<option value="">aktuálny / živý</option>`;
  $("#live-session-meta").hidden = true;
  $("#live-list").hidden = true; $("#live-detail").hidden = false;
  $("#live-detail-error").hidden = true;
  $("#live-title").textContent = id;
  $("#live-chart").classList.add("loading");
  try { await Promise.all([loadLiveDetail(id), loadLiveSessions(id).catch(() => {})]); }
  catch (e) { $("#live-detail-error").textContent = e.message; $("#live-detail-error").hidden = false; }
  finally { $("#live-chart").classList.remove("loading"); }
}

async function loadLiveDetail(id) {
  const seq = ++lv.seq;
  const session = lv.session;
  const q = session ? `session=${encodeURIComponent(session)}` : "bars=500";   // beh: celý (server dá do 5000 barov)
  const snap = await api(`/api/live/${encodeURIComponent(id)}/snapshot?${q}`);
  if (seq !== lv.seq || lv.selected !== id || lv.session !== session) return;
  lv.snap = snap;
  const inst = snap.instance;
  if (lv.strategy !== inst.strategy) {
    lv.strategy = inst.strategy;
    // vrstvy podľa stratégie (cez /api/meta); neznáma stratégia → kresby bez vrstiev, predvolený štýl
    const L = layersFor(inst.strategy);
    L.layers = [...L.layers.filter(l => l.id !== "trades"), LIVE_FILLS_LAYER, LIVE_MODIFY_LAYER];
    lv.L = L;
    lv.layers = {};
    for (const l of L.layers) lv.layers[l.id] = true;
    renderLiveLayers();
  }
  $("#live-title").textContent = `${inst.symbol} · ${inst.tf}m · ${inst.strategy}`;
  $("#live-meta").textContent = `${inst.platform} · účet ${inst.account} · profil ${inst.profile || "—"} · stroj ${inst.host || "—"}`
    + ` · agent ${inst.agent || "—"} · posledný beh ${inst.last_session || "—"} · UTC`;
  $("#live-detail-status").innerHTML = liveStatusChip(inst);
  renderLiveSessionMeta();
  renderLiveCards(snap);
  renderLiveChart(snap);
  renderLiveOrders(snap.orders);
  // vybraný beh: len jeho fills; „aktuálny": všetky, čo zrkadlo o inštancii má
  renderLiveFills(snap.fills, session ? null : lv.fills[id]);
  renderLiveNotes(snap.notes);
  renderLiveStats(snap.stats);
}

function renderLiveLayers() {
  const box = $("#live-layers"); box.innerHTML = "";
  for (const l of lv.L.layers) {
    const lab = document.createElement("label"); lab.classList.toggle("off", !lv.layers[l.id]);
    lab.innerHTML = `<input type="checkbox" ${lv.layers[l.id] ? "checked" : ""}> <span class="sw" style="background:${l.sw}"></span>${esc(l.title)}`;
    lab.querySelector("input").onchange = e => {
      lv.layers[l.id] = e.target.checked; lab.classList.toggle("off", !e.target.checked);
      if (lv.snap) renderLiveChart(lv.snap);
    };
    box.append(lab);
  }
}

function renderLiveCards(snap) {
  const inst = snap.instance, bars = snap.bars, last = bars[bars.length - 1];
  const f = lv.fills[inst.id], pos = livePosition(f);
  const cards = [
    card("posledný bar", last ? liveAge(last.bt, lv.now) : "—", last ? utc(last.bt) + " UTC" : "bez barov"),
    card("posledná udalosť", liveAge(inst.last_t, lv.now), inst.last_t ? utc(inst.last_t) + " UTC" : ""),
    card("engine", last ? (last.ready ? "obchoduje" : "prehráva") : "—", last ? `bias ${last.mb ?? "—"}${last.cs ? " · koniec seansy" : ""}` : ""),
    card("pozícia", pos === null ? "—" : (pos.qty > 0 ? `+${pos.qty}` : String(pos.qty)), pos && pos.open.length ? pos.open.join(", ") : "odhad z fillov"),
    card("fills dnes", String(liveFillsToday(f)), f ? `${f.fills.length} spolu v zrkadle` : ""),
    card(snap.session ? "barov v behu" : "barov v okne", String(bars.length), `${snap.orders.length} orderov · ${snap.draw.length} kresieb`),
  ];
  $("#live-cards").innerHTML = cards.join("");
}

/** Kresby zo všetkých `draw` udalostí zlúčené podľa `id`: nový objekt prepíše starý (po reštarte
 *  prídu znova), `update` mení jedno pole, `delete` maže. Objekty bez id sa len pridajú. */
function liveMergeDrawings(drawEvents) {
  const objs = new Map(); let anon = 0;
  for (const ev of drawEvents) {
    for (const d of (ev.d || [])) {
      if (d.t === "delete") { objs.delete(d.id); continue; }
      if (d.t === "update") {
        const o = objs.get(d.id);
        if (o) o[LIVE_DRAW_FIELD[d.f] || d.f] = d.v;
        continue;
      }
      objs.set(d.id || `_${anon++}`, { ...d });
    }
  }
  return [...objs.values()];
}

function liveFillTraces(snap) {
  if (!lv.layers.fills) return [];
  const dirs = (lv.fills[snap.instance.id] || {}).dirs || {};
  const entry = { type: "scatter", mode: "markers", x: [], y: [], text: [], hoverinfo: "text", showlegend: false, name: "Vstup",
    marker: { symbol: [], size: 11, color: [], line: { color: "#fff", width: 1 } } };
  const exit = { type: "scatter", mode: "markers", x: [], y: [], text: [], hoverinfo: "text", showlegend: false, name: "Výstup",
    marker: { symbol: "x", size: 9, color: BLUE, line: { width: 0 } } };
  for (const f of snap.fills) {
    const dir = dirs[f.id] || 0;
    const txt = `<b>${f.side === "in" ? "VSTUP" : "VÝSTUP"}</b> ${esc(f.id)}${f.exit ? " · " + esc(f.exit) : ""}<br>${fmtPrice(f.price)} × ${f.qty} · ${utc(f.ft)}${f.ready ? "" : " · ready=false"}`;
    if (f.side === "in") {
      entry.x.push(utc(f.ft)); entry.y.push(f.price); entry.text.push(txt);
      entry.marker.symbol.push(dir < 0 ? "triangle-down" : (dir > 0 ? "triangle-up" : "diamond"));
      entry.marker.color.push(dir < 0 ? RED : (dir > 0 ? GREEN : BLUE));
    } else { exit.x.push(utc(f.ft)); exit.y.push(f.price); exit.text.push(txt); }
  }
  return [entry, exit];
}

/** Posuny SL/TP (`order` `a:"modify"`) ako malé stupienky na čase baru: SL plný, TP dutý. */
function liveModifyTraces(snap) {
  if (!lv.layers.modify) return [];
  const mk = (name, symbol) => ({ type: "scatter", mode: "markers", x: [], y: [], text: [], hoverinfo: "text", showlegend: false, name,
    marker: { symbol, size: 9, color: LIVE_MODIFY_COLOR, line: { color: LIVE_MODIFY_COLOR, width: 1.5 } } });
  const sl = mk("SL", "line-ew"), tp = mk("TP", "line-ew-open");
  for (const o of snap.orders) {
    if (o.a !== "modify") continue;
    const p = o.p || {};
    const txt = `<b>POSUN</b> ${esc(o.id)}${o.r ? " · " + esc(o.r) : ""}<br>SL ${liveNum(p.sl)} · TP ${liveNum(p.tp)} · ${utc(o.bt)}`;
    if (p.sl !== null && p.sl !== undefined) { sl.x.push(utc(o.bt)); sl.y.push(p.sl); sl.text.push(txt); }
    if (p.tp !== null && p.tp !== undefined) { tp.x.push(utc(o.bt)); tp.y.push(p.tp); tp.text.push(txt); }
  }
  return [sl, tp];
}

function renderLiveChart(snap) {
  const el = $("#live-chart"), bars = snap.bars;
  if (!bars.length) { el.innerHTML = `<div class="muted" style="padding:16px">Zatiaľ žiadny bar — engine ešte nič neuzavrel.</div>`; return; }
  const tfMs = Math.max(1, Number(snap.instance.tf) || 1) * 60e3;
  const candles = { t: bars.map(b => b.bt), o: bars.map(b => b.o), h: bars.map(b => b.h), l: bars.map(b => b.l), c: bars.map(b => b.c) };
  const from = candles.t[0], to = candles.t[candles.t.length - 1] + tfMs;
  const ctx = { L: lv.L, layers: lv.layers, to };
  const objects = liveMergeDrawings(snap.draw);
  const { traces, shapes } = objectTraces(objects, ctx);
  let lo = Math.min(...candles.l), hi = Math.max(...candles.h);
  if (!Number.isFinite(lo)) { lo = 0; hi = 1; }
  const pad = (hi - lo) * 0.05 || 1, grid = chartGridColor();
  const posuny = snap.orders.filter(o => o.a === "modify").length;
  $("#live-chart-note").textContent = `${bars.length} barov · ${objects.length} objektov · ${snap.fills.length} fillov`
    + `${posuny ? ` · ${posuny} posunov SL/TP` : ""} ${snap.session ? `v behu ${snap.session}` : "v okne"}`;
  // vybraný beh sa ukáže celý; „aktuálny" posledných 200 barov (zvyšok je za posunom)
  const okno = snap.session ? from : Math.max(from, to - 200 * tfMs);
  Plotly.react(el, [...traces, ...candleTraces(candles, objects, ctx, snap.instance.symbol), ...liveFillTraces(snap), ...liveModifyTraces(snap)], {
    height: 640, margin: { l: 10, r: 70, t: 8, b: 36 }, template: plotlyTemplate(), dragmode: "pan", hovermode: "closest",
    showlegend: false, shapes, uirevision: `${snap.instance.id}:${snap.session || ""}`,   // pan/zoom prežije obnovu každých 5 s; zmena behu ho vráti
    xaxis: { type: "date", range: [utc(okno), utc(to)], rangeslider: { visible: false }, showgrid: true, gridcolor: grid },
    yaxis: { side: "right", range: [lo - pad, hi + pad], showgrid: true, gridcolor: grid, fixedrange: false, autorange: true },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  }, { displaylogo: false, responsive: true, scrollZoom: true, modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"] });
}

function liveDir(o) { const d = Number(o.dir ?? (o.p && o.p.dir)); return d > 0 ? "long" : (d < 0 ? "short" : "—"); }
const liveNum = v => (v === null || v === undefined || v === "" ? "—" : fmtPrice(v));

/** Tabuľka zámerov: entry/cancel/close ako doteraz, `modify` = riadok „posun SL/TP" (id, SL, TP, dôvod). */
function renderLiveOrders(orders) {
  const rows = orders.slice(-40).reverse();
  $("#live-orders tbody").innerHTML = rows.map(o => {
    const p = o.p || {};
    const modify = o.a === "modify";
    const chip = o.a === "entry" ? "ok" : (o.a === "cancel" || modify ? "" : "warn");
    const akcia = modify ? "posun SL/TP" : o.a;
    return `<tr class="plain"><td>${utc(o.bt).slice(5, 16)}</td><td><span class="chip ${chip}"${modify ? ` style="border-color:${LIVE_MODIFY_COLOR}"` : ""}>${esc(akcia)}</span></td><td>${esc(o.id)}</td>
      <td>${modify ? "—" : esc(o.ot || "—")}</td><td>${liveDir(o)}</td><td class="num">${modify ? "—" : liveNum(p.e)}</td><td class="num">${liveNum(p.sl)}</td>
      <td class="num">${liveNum(p.tp)}</td><td class="num">${modify ? "—" : liveNum(p.q)}</td><td title="${esc(o.r || "")}">${esc(o.r || "")}</td>
      <td>${o.ready ? "áno" : "nie"}</td></tr>`;
  }).join("") || `<tr class="plain"><td colspan="11" class="muted">žiadne ordery ${lv.session ? "v behu" : "v okne"}</td></tr>`;
}

function renderLiveFills(inWindow, f) {
  // „aktuálny": v okne snapshotu môže byť fillov málo — tabuľka berie všetky, čo zrkadlo o inštancii má;
  // vybraný beh: len jeho (f je null)
  const all = f && f.fills.length ? f.fills : inWindow;
  const rows = all.slice(-60).reverse();
  $("#live-fills tbody").innerHTML = rows.map(x => `<tr class="plain"><td>${utc(x.ft)}</td><td>${esc(x.id)}</td>
      <td>${x.side === "in" ? "vstup" : "výstup"}</td><td>${esc(x.exit || "—")}</td><td class="num">${liveNum(x.price)}</td>
      <td class="num">${liveNum(x.qty)}</td><td>${x.ready ? "áno" : "nie"}</td></tr>`).join("")
    || `<tr class="plain"><td colspan="7" class="muted">žiadne vyplnenia</td></tr>`;
}

function renderLiveNotes(notes) {
  $("#live-notes").innerHTML = notes.length ? `<ul class="small">${notes.slice().reverse().map(n => {
    const lvl = n.k === "bye" ? "warn" : (n.level || "info");
    const txt = n.k === "bye" ? `ukončené: ${n.reason || "—"}` : n.text;
    return `<li><span class="chip ${lvl === "error" ? "bad" : (lvl === "warn" ? "warn" : "")}">${esc(lvl)}</span> <span class="muted">${utc(n.t).slice(5, 16)}</span> ${esc(txt)}</li>`;
  }).join("")}</ul>` : `<div class="muted">žiadne</div>`;
}

function renderLiveStats(stats) {
  if (!stats || !Object.keys(stats).length) { $("#live-stats").innerHTML = `<div class="muted">engine ešte nič nehlásil (píše sa pri ukončení)</div>`; return; }
  $("#live-stats").innerHTML = `<table class="runs"><tbody>${Object.entries(stats).map(([k, v]) =>
    `<tr class="plain"><td>${esc(k)}</td><td class="num">${typeof v === "number" ? fmtPrice(v) : esc(v)}</td></tr>`).join("")}</tbody></table>`;
}
