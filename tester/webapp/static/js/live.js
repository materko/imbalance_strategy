/* TradeBot Backtester — Karta Live: telemetria zo spustených stratégií (docs/LIVE.md). */
"use strict";

// --------------------------------------------------------------------------- //
// Live: bežiace stratégie (NinjaTrader 8, MetaTrader 5) zo zrkadla webapp
//
// Stránka číta len zrkadlo (`/api/live`, `/api/live/<id>/snapshot`, `/api/live/<id>/events`),
// ktoré plní vlákno LiveMirror na serveri (hub + lokálny spool). Kým je karta otvorená, drží
// otvorený `EventSource` na `/api/live/stream` (SSE): server pošle `instances` (zoznam + stav
// zrkadla) a `events` (nové riadky inštancie) hneď, ako zrkadlo niečo uloží — zoznam sa
// prekreslí a otvorený detail sa **doplní** (bary, ordery, kresby, fills), snapshot sa
// sťahuje znova len pri zmene behu. Bez EventSource alebo po chybe streamu sa karta vráti
// k pôvodnému pollingu každých 5 s (a stream skúsi znova o minútu). Mimo karty sa nič nepýta.
// Graf: sviečky z `bar`, kresby z `draw` zlúčené podľa `id` (update mení pole, delete
// maže) a nakreslené tým istým `objectTraces` ako graf behu, vyplnenia ako značky.
// Behy: každý štart stratégie je nová session; výber „Beh" v detaile načíta snapshot so
// `session=` (celý beh, do 5000 barov). Ukončený beh sa neobnovuje, živý áno.
// Účty a nasadenia (fáza 2b, dole v súbore) idú vždy na hub cez proxy webapp.
// --------------------------------------------------------------------------- //

const LIVE_POLL_MS = 5000;            // polling, keď stream nejde (starý server, proxy bez SSE)
const LIVE_SSE_RETRY_MS = 60000;      // po chybe streamu: polling a o minútu stream znova
const LIVE_DEPLOY_POLL_MS = 15000;    // účty a nasadenia idú z hubu (nie zo zrkadla) — pri streame sa obnovujú takto
const LIVE_WINDOW_BARS = 500;         // „aktuálny" detail drží toľko barov (ako snapshot servera)
const LIVE_FILLS_LAYER = { id: "fills", title: "Vyplnenia u brokera", kinds: [], sw: BLUE, hollow_kinds: [] };
const LIVE_MODIFY_COLOR = "#ff9800";
/** Posuny SL/TP otvorenej pozície (`order` s `a:"modify"`) — malé stupienky na grafe. */
const LIVE_MODIFY_LAYER = { id: "modify", title: "Posuny SL/TP", kinds: [], sw: LIVE_MODIFY_COLOR, hollow_kinds: [] };
/** Polia `update` kresby (názvy atribútov objektu v jadre) → krátke kľúče JSON kresby. */
const LIVE_DRAW_FIELD = { x1_ms: "x1", x2_ms: "x2", x_ms: "x", fill_color: "fc", border_color: "bc",
  border_style: "bs", border_width: "bw", extend_right: "er", color: "c", style: "s", width: "w",
  text: "tx", above: "ab", bg_color: "bg", zone_uid: "z" };

const lv = {
  timer: null, selected: null, instances: [], now: 0, mirror: null, deploy: null,
  snap: null, seq: 0,
  sse: null, sseFailedAt: 0, cursor: 0, snapCursor: 0, deployTimer: null,   // stream (SSE) a kurzory zrkadla
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

/** Vypne obnovu karty: polling, stream aj obnovu nasadení (volá showView pri odchode z karty). */
function stopLive() {
  clearTimeout(lv.timer); lv.timer = null;
  clearTimeout(lv.deployTimer); lv.deployTimer = null;
  if (lv.sse) { lv.sse.close(); lv.sse = null; }
}

/** Stream sa skúša, keď ho prehliadač má a naposledy nezlyhal (po chybe minúta pollingu). */
function liveStreamWanted() {
  return typeof EventSource !== "undefined" && (!lv.sseFailedAt || Date.now() - lv.sseFailedAt > LIVE_SSE_RETRY_MS);
}

/** Otvorí SSE na `/api/live/stream?after=<kurzor>`; chyba = zavrieť a vrátiť sa k pollingu. */
function liveConnectStream() {
  if (lv.sse || $("#view-live").hidden) return;
  const es = new EventSource(`/api/live/stream?after=${lv.cursor || 0}`);
  lv.sse = es;
  es.onmessage = e => {
    let msg; try { msg = JSON.parse(e.data); } catch { return; }
    if (msg.type === "instances") liveApplyInstances(msg);
    else if (msg.type === "events") liveApplyRows(msg.instance, msg.rows || []).catch(() => {});
  };
  es.onerror = () => {
    if (lv.sse !== es) return;
    es.close(); lv.sse = null; lv.sseFailedAt = Date.now();
    if (!$("#view-live").hidden && !lv.timer) lv.timer = setTimeout(loadLive, LIVE_POLL_MS);
  };
  liveScheduleDeploy();
}

/** Pri streame sa účty a nasadenia (hub, nie zrkadlo) obnovujú samostatne a redšie. */
function liveScheduleDeploy() {
  clearTimeout(lv.deployTimer); lv.deployTimer = null;
  if (!lv.sse || $("#view-live").hidden) return;
  lv.deployTimer = setTimeout(async () => {
    if (!lv.selected && lv.deploy && lv.deploy.configured) await loadLiveDeploy().catch(() => {});
    liveScheduleDeploy();
  }, LIVE_DEPLOY_POLL_MS);
}

/** Správa `instances` zo streamu: to isté, čo odpoveď `/api/live`. */
function liveApplyInstances(d) {
  lv.instances = d.instances; lv.now = d.now; lv.mirror = d.mirror; lv.deploy = d.deploy || lv.deploy;
  if (d.cursor) lv.cursor = Math.max(lv.cursor, d.cursor);
  $("#live-error").hidden = true;
  liveChip(); renderLiveStatus(); renderLiveList();
  if (lv.selected && lv.snap) { renderLiveCards(lv.snap); $("#live-detail-status").innerHTML = liveStatusChip(lv.snap.instance); }
}

/** Nové riadky inštancie zo streamu: fills/ordery do `lv.fills` (pozícia v zozname) a keď je
 *  inštancia otvorená, doplní ich do snapshotu namiesto jeho sťahovania. Snapshot sa sťahuje
 *  znova len pri zmene behu (nový `hello` v „aktuálnom" pohľade). */
async function liveApplyRows(id, rows) {
  if (!rows.length) return;
  const f = lv.fills[id] || (lv.fills[id] = { after: 0, fills: [], dirs: {} });
  for (const r of rows) {
    if (r.id <= f.after) continue;
    const ev = r.event;
    if (ev.k === "fill") { f.after = r.id; f.fills.push(ev); }
    else if (ev.k === "order" && ev.a === "entry") { f.after = r.id; f.dirs[ev.id] = Number(ev.dir ?? (ev.p && ev.p.dir) ?? 1) || 1; }
  }
  lv.cursor = Math.max(lv.cursor, ...rows.map(r => r.id));
  if (lv.selected !== id || !lv.snap) return;
  const snap = lv.snap;
  const nove = rows.filter(r => r.id > lv.snapCursor);
  if (!nove.length) return;
  lv.snapCursor = Math.max(...nove.map(r => r.id));
  const chosen = liveChosenSession();
  if (lv.session) {
    if (!chosen || !chosen.live) return;                       // ukončený beh sa nemení
  } else if (nove.some(r => r.event.k === "hello" && r.session !== snap.instance.last_session)) {
    // nový beh v „aktuálnom" pohľade: zoznam behov aj snapshot znova (predhistória sa prehráva)
    await Promise.all([loadLiveSessions(id).catch(() => {}), loadLiveDetail(id)]);
    return;
  }
  let bars = false, zmena = false;
  const firstBt = snap.bars.length ? snap.bars[0].bt : 0;
  for (const r of nove) {
    if (lv.session && r.session !== lv.session) continue;
    const ev = r.event;
    zmena = true;
    if (ev.k === "bar") {
      const i = snap.bars.findIndex(b => b.bt === ev.bt);
      if (i >= 0) snap.bars[i] = ev; else snap.bars.push(ev);
      bars = true;
      if (typeof ev.bt === "number") snap.instance.last_bar_ms = Math.max(snap.instance.last_bar_ms || 0, ev.bt);
    } else if (ev.k === "order") snap.orders.push(ev);
    else if (ev.k === "event") snap.events.push(ev);
    else if (ev.k === "draw") snap.draw.push(ev);
    else if (ev.k === "fill") snap.fills.push(ev);
    else if (ev.k === "stat") snap.stats = ev.stats || snap.stats;
    else if (ev.k === "note" || ev.k === "bye") { snap.notes.push(ev); if (snap.notes.length > 20) snap.notes.shift(); }
    else if (ev.k === "hello") snap.instance.profile = ev.profile || snap.instance.profile;
    if (typeof ev.t === "number") snap.instance.last_t = Math.max(snap.instance.last_t || 0, ev.t);
  }
  if (!zmena) return;
  if (bars) {
    snap.bars.sort((a, b) => a.bt - b.bt);
    if (!lv.session && snap.bars.length > LIVE_WINDOW_BARS) snap.bars.splice(0, snap.bars.length - LIVE_WINDOW_BARS);
    const since = snap.bars[0].bt;
    if (since !== firstBt) {   // okno sa posunulo — čo je pred ním, ide preč (ako snapshot servera)
      for (const k of ["orders", "events", "draw"]) snap[k] = snap[k].filter(x => (x.bt ?? since) >= since);
      snap.fills = snap.fills.filter(x => (x.ft ?? since) >= since);
    }
  }
  renderLiveCards(snap);
  if (bars || nove.some(r => ["draw", "fill", "order"].includes(r.event.k))) renderLiveChart(snap);
  renderLiveOrders(snap.orders);
  renderLiveFills(snap.fills, lv.session ? null : lv.fills[id]);
  renderLiveNotes(snap.notes);
  renderLiveStats(snap.stats);
  $("#live-detail-status").innerHTML = liveStatusChip(snap.instance);
  if (nove.some(r => ["hello", "bye", "bar", "fill"].includes(r.event.k))) loadLiveSessions(id).catch(() => {});
}

function liveSetup() {
  $("#live-back").onclick = () => { lv.selected = null; renderLiveList(); $("#live-detail").hidden = true; $("#live-list").hidden = false; $("#live-deploy").hidden = false; };
  $("#live-session").onchange = async e => {
    lv.session = e.target.value; lv.snap = null;
    if (!lv.selected) return;
    $("#live-detail-error").hidden = true; $("#live-chart").classList.add("loading");
    try { await loadLiveDetail(lv.selected); }
    catch (err) { $("#live-detail-error").textContent = err.message; $("#live-detail-error").hidden = false; }
    finally { $("#live-chart").classList.remove("loading"); }
  };
  // chip pri záložke hneď po štarte — bez otvárania karty
  api("/api/live").then(d => { lv.instances = d.instances; lv.now = d.now; lv.mirror = d.mirror; lv.deploy = d.deploy; liveChip(); }).catch(() => {});
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
    lv.instances = d.instances; lv.now = d.now; lv.mirror = d.mirror; lv.deploy = d.deploy;
    lv.cursor = d.cursor || lv.cursor;
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
  // účty a nasadenia z hubu (fáza 2b) — len keď je zoznam na obrazovke, detail ich nepotrebuje
  if (!lv.selected) await loadLiveDeploy().catch(e => { $("#ld-error").textContent = e.message; $("#ld-error").hidden = false; });
  if (lv.selected) {
    // zoznam behov je lacný — obnoví sa vždy (nový štart pribudne, živý sa ukončí); detail len keď sa mení
    await loadLiveSessions(lv.selected).catch(() => {});
    if (liveDetailPolls()) await loadLiveDetail(lv.selected).catch(e => { $("#live-detail-error").textContent = e.message; $("#live-detail-error").hidden = false; });
  }
  if ($("#view-live").hidden) return;
  // stream namiesto pollingu; keď nejde, polling ako doteraz
  if (liveStreamWanted()) liveConnectStream();
  if (!lv.sse) lv.timer = setTimeout(loadLive, LIVE_POLL_MS);
}

/** Behy inštancie do výberu „Beh": „aktuálny / živý" prvý, potom behy od najnovšieho
 *  (`štart UTC → koniec UTC (bary, fills, profil)`). Prekreslí sa len keď sa zoznam zmenil,
 *  nech obnova nezavrie rozbalený výber. */
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
  const stav = s.live ? (lv.sse ? "beží (živé aktualizácie)" : "beží (obnova každých 5 s)") : (s.ended ? `ukončený ${utc(s.ended)} UTC · dôvod: ${s.reason || "—"}` : "bez `bye` a ticho — ukončený bez rozlúčky (pád, výpadok spoolu)");
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
  parts.push(lv.sse ? "stream" : "polling 5 s");
  $("#live-status").textContent = parts.join(" · ");
  const err = $("#live-error");
  if (m.last_error) { err.textContent = `zrkadlo: ${m.last_error}`; err.hidden = false; }
}

/** Fills a smery vstupov inštancie — prírastkovo od posledného rowid, nech sa pri obnove neťahá všetko. */
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
  $("#live-list").hidden = true; $("#live-deploy").hidden = true; $("#live-detail").hidden = false;
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
  lv.snapCursor = snap.cursor || 0;   // riadky za ním dopĺňa stream, nie ďalší snapshot
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
    showlegend: false, shapes, uirevision: `${snap.instance.id}:${snap.session || ""}`,   // pan/zoom prežije obnovu (stream aj polling); zmena behu ho vráti
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

// --------------------------------------------------------------------------- //
// Fáza 2b: účty a nasadenia (docs/LIVE.md) — požadovaný stav na hube vs. čo agent aplikoval
//
// Webapp nič nezrkadlí, každé načítanie ide cez `/api/live/accounts|deployments|agents|audit`
// na hub. Mutácie len s admin tokenom (`deploy.admin` v `/api/live`); bez neho sú tlačidlá
// vypnuté a v hlavičke je chip „len na čítanie". Tabuľky sa prekresľujú len keď sa dáta
// zmenili, nech obnova (pri streame každých 15 s, pri pollingu 5 s) nezavrie rozbalený výber.
// --------------------------------------------------------------------------- //

const ld = {
  admin: false, configured: false, accounts: [], deployments: [], agents: [],
  key: "", auditKey: "", profiles: {},   // profily podľa stratégie (cache pre výber)
  formsReady: false,
};

const LD_MODE_LABEL = { enabled: "obchoduje", paused: "pauza", flatten: "flatten" };

function ldUser() { return typeof currentUser === "function" ? currentUser() : null; }

/** Načíta účty, nasadenia a agentov z hubu (cez webapp); hub mimo → chyba v sekcii, tabuľky ostanú. */
async function loadLiveDeploy() {
  const d = lv.deploy || {};
  ld.admin = !!d.admin; ld.configured = !!d.configured;
  $("#ld-readonly").hidden = ld.admin;
  if (!ld.configured) {
    $("#ld-error").textContent = "hub nie je nastavený — účty a nasadenia žijú na hube (karta Hub)";
    $("#ld-error").hidden = false;
    return;
  }
  try {
    const [accounts, deployments, agents] = await Promise.all([
      api("/api/live/accounts"), api("/api/live/deployments"), api("/api/live/agents").catch(() => ld.agents),
    ]);
    ld.accounts = accounts; ld.deployments = deployments; ld.agents = agents;
    $("#ld-error").hidden = true;
  } catch (e) {
    $("#ld-error").textContent = `hub: ${e.message}`; $("#ld-error").hidden = false;
    return;
  }
  renderLiveDeploy();
  if ($("#ld-audit-box").open) loadLiveAudit().catch(() => {});
}

function ldStatusChip(dep) {
  const a = dep.applied, live = dep.live || {};
  if (!dep.active) {
    return a && a.status === "removed" ? `<span class="chip" title="agent inštanciu z platformy odstránil">odstránené</span>`
      : `<span class="chip warn" title="čaká, kým agent inštanciu z platformy odstráni">odstraňuje sa</span>`;
  }
  if (a && a.status === "error") return `<span class="chip bad" title="${esc(a.error || "")}">chyba</span>`;
  if (!a) return `<span class="chip warn" title="agent nasadenie ešte nepotvrdil">čaká</span>`;
  if (a.config_hash !== dep.config_hash || a.mode !== dep.mode || a.status === "pending") {
    const co = [];
    if (a.config_hash !== dep.config_hash) co.push("profil");
    if (a.mode !== dep.mode) co.push("režim");
    if (a.status === "pending") co.push("čaká na flat");
    return `<span class="chip warn" title="agent ešte neaplikoval: ${esc(co.join(", "))}">čaká</span>`;
  }
  if (live.alive) return `<span class="chip ok" title="inštancia v spoole žije (udalosť do 3 barov)">živá</span>`;
  return `<span class="chip" title="${live.seen ? "aplikované, ale spool je ticho dlhšie než 3 bary" : "aplikované, inštancia v spoole ešte nie je"}">ok</span>`;
}

function ldAppliedCell(dep) {
  const a = dep.applied;
  if (!a) return `<span class="muted">—</span>`;
  const hashOk = a.config_hash === dep.config_hash;
  const modeOk = a.mode === dep.mode;
  const err = a.status === "error" ? ` <span class="small err" title="${esc(a.error || "")}">${esc((a.error || "").slice(0, 60))}</span>` : "";
  return `<span title="hash ${esc(a.config_hash || "—")}" class="${hashOk ? "" : "err"}">${hashOk ? "profil ✓" : "profil ≠"}</span>
    · <span class="${modeOk ? "" : "err"}">${esc(LD_MODE_LABEL[a.mode] || a.mode || "—")}</span>
    <span class="muted small">${a.ts ? liveAge(a.ts * 1000, lv.now) : ""}</span>${err}`;
}

/** Chip stavu kódu (fáza 2c): `{installed, state}` nasadenia alebo platformy agenta. */
function ldCodeChip(cs, wanted) {
  if (!cs) return `<span class="chip" title="stroj kód nehlási">neznámy</span>`;
  const sha = cs.installed ? String(cs.installed).slice(0, 7) : "";
  if (cs.state === "ok") return `<span class="chip ok" title="platforma má ${esc(sha)}${wanted ? ` (chcené ${esc(String(wanted).slice(0, 7))})` : ""}">kód: aktuálny</span>`;
  if (cs.state === "outdated") return `<span class="chip warn" title="platforma má ${esc(sha)}, chcené ${esc(String(wanted || "").slice(0, 7) || "?")} — Aktualizovať kód v sekcii Stroje">kód: zastaraný ${esc(sha)}</span>`;
  return `<span class="chip" title="platforma nehlási installed.json (kód nainštalovaný ručne pred fázou 2c, alebo nikdy)">kód: neznámy</span>`;
}

/** Posledná aktualizácia kódu, ktorú agent hlásil (`live.code_update`): stav, verzia, dôvod. */
function ldCodeUpdateCell(a) {
  const cu = a.live && a.live.code_update;
  const cielovy = a.code_target;
  const caka = cielovy ? `<span class="chip warn" title="hub posiela cieľ ${esc(cielovy.version)} v každom heartbeate, kým ho agent nepotvrdí">čaká: ${esc(String(cielovy.version).slice(0, 7))}${cielovy.force ? " (force)" : ""}</span> ` : "";
  if (!cu) return caka || `<span class="muted">—</span>`;
  const ver = String(cu.version || "").slice(0, 7);
  if (cu.status === "ok") return `${caka}<span class="chip ok" title="${esc(JSON.stringify(cu.platforms || {}))}">${esc(ver)} ok${cu.noop ? " (už bol)" : ""}</span> <span class="muted small">${cu.ts ? liveAge(cu.ts * 1000, lv.now) : ""}${cu.needs_restart ? " · agent čaká na reštart" : ""}</span>`;
  if (cu.status === "blocked") return `${caka}<span class="chip warn" title="${esc((cu.reasons || []).join("\n"))}">blokované: ${esc((cu.reasons || [])[0] || cu.error || "")}</span>`;
  return `${caka}<span class="chip bad" title="${esc(cu.error || "")}">${esc(ver)} chyba: ${esc((cu.error || "").slice(0, 80))}</span>`;
}

/** Tabuľka strojov (agentov): kód agenta, kód platforiem proti webapp, tlačidlo „Aktualizovať kód“. */
function renderLiveAgents() {
  const agents = ld.agents.slice().sort((a, b) => (b.online - a.online) || a.name.localeCompare(b.name));
  $("#ld-ag-count").textContent = agents.length ? String(agents.length) : "";
  $("#ld-ag-empty").hidden = !!agents.length;
  $("#ld-agents").parentElement.hidden = !agents.length;
  const mine = lv.deploy && lv.deploy.version ? String(lv.deploy.version) : "";
  $("#ld-agents tbody").innerHTML = agents.map(a => {
    const cs = (a.live && a.live.code_state) || {};
    const platformy = Object.keys(cs).length
      ? Object.entries(cs).map(([p, s]) => `${esc(p)}: ${ldCodeChip(s, mine)}`).join(" ")
      : `<span class="muted">${a.live && a.live.drivers && a.live.drivers.length ? esc(a.live.drivers.join(", ")) + ": kód: neznámy" : "bez platformy"}</span>`;
    const dis = ld.admin && a.online ? "" : "disabled";
    const stav = `<span class="chip ${a.online ? "ok" : ""}">${a.online ? "online" : "offline"}</span>${a.updating ? ' <span class="chip warn" title="agent práve mení kód alebo ťahá commit">mení kód</span>' : ""}${a.needs_restart ? ' <span class="chip warn" title="agent má na disku nový kód a čaká na reštart (headless sa reštartuje sám, webapp reštartuj ručne)">reštart</span>' : ""}`;
    const verzia = a.version ? `<code title="${esc(a.version)}">${esc(String(a.version).slice(0, 7))}</code>${mine && a.version !== mine ? ` <span class="muted small" title="webapp ${esc(mine)}">≠ webapp</span>` : ""}` : "—";
    return `<tr class="plain" data-agent="${esc(a.name)}"><td><b>${esc(a.name)}</b></td><td>${stav}</td><td>${verzia}</td>
      <td>${platformy}</td><td>${ldCodeUpdateCell(a)}</td>
      <td class="ld-actions" style="white-space:nowrap">
        <label class="inline small" title="preskočiť bránu: kód sa vymení, aj keď nasadenia obchodujú alebo majú pozíciu — MT5 terminál sa reštartuje s pozíciou u brokera"><input type="checkbox" class="ld-force"> aj s otvorenými pozíciami</label>
        <button class="small" data-update="1" ${dis} title="nasadiť commit tejto webapp (${esc(mine || "?")}) na platformy stroja">Aktualizovať kód</button>
        ${a.code_target ? `<button class="small ghost" data-cancel="1" ${ld.admin ? "" : "disabled"} title="stiahnuť cieľ z hubu (čo už agent urobil, ostáva)">zrušiť</button>` : ""}
      </td></tr>`;
  }).join("");
  for (const tr of $$("#ld-agents tbody tr")) {
    const name = tr.dataset.agent;
    const upd = tr.querySelector("button[data-update]");
    if (upd) upd.onclick = () => ldUpdateCode(name, tr.querySelector("input.ld-force").checked);
    const cancel = tr.querySelector("button[data-cancel]");
    if (cancel) cancel.onclick = () => ldCancelCode(name);
  }
}

async function ldUpdateCode(name, force) {
  const mine = lv.deploy && lv.deploy.version ? String(lv.deploy.version) : "";
  const agent = ld.agents.find(a => a.name === name) || {};
  const platformy = (agent.live && agent.live.drivers) || [];
  const co = [];
  if (platformy.includes("mt5")) co.push("MT5 terminály stroja sa zavrú a po inštalácii DLL reštartujú (výpadok ~1 min; EA prehrá predhistóriu)");
  if (platformy.includes("ninjatrader")) co.push("NinjaTrader sa prekompiluje (F5 v NinjaScript Editore, NT musí bežať) a AddOn nabehne v novej generácii (nová session)");
  const otazka = `Aktualizovať kód na stroji „${name}“ na commit ${mine ? mine.slice(0, 7) : "?"} (commit tejto webapp)?\n\n`
    + `Agent najprv pullne kód. ${co.join("; ") || "Platformy podľa driverov agenta."}.\n\n`
    + (force ? "VYNÚTENÉ: brána sa preskočí — aj keď nasadenia obchodujú alebo majú otvorenú pozíciu."
             : "Prejde, len keď sú všetky nasadenia stroja v pauze/flatten a bez otvorenej pozície (inak „blokované“).");
  if (!confirm(otazka)) return;
  try {
    await api(`/api/live/agents/${encodeURIComponent(name)}/update`, { method: "POST", body: JSON.stringify({ force: !!force, user: ldUser() }) });
    await loadLiveDeploy();
  } catch (e) { ldFail(e); }
}

async function ldCancelCode(name) {
  try {
    await api(`/api/live/agents/${encodeURIComponent(name)}/update?user=${encodeURIComponent(ldUser() || "")}`, { method: "DELETE" });
    await loadLiveDeploy();
  } catch (e) { ldFail(e); }
}

/** „Nasadiť“: keď má stroj vybraného účtu starší kód než táto webapp, poradí najprv aktualizovať (neblokuje). */
function ldCodeHint() {
  const box = $("#ld-d-code-hint");
  const acc = ld.accounts.find(a => a.id === $("#ld-d-account").value);
  const agent = acc && ld.agents.find(a => a.name === acc.agent);
  const mine = lv.deploy && lv.deploy.version ? String(lv.deploy.version) : "";
  const cs = agent && agent.live && agent.live.code_state && agent.live.code_state[acc.platform];
  if (!acc || !agent || !mine || !cs || cs.state === "ok") { box.hidden = true; box.textContent = ""; return; }
  box.textContent = cs.state === "outdated"
    ? `Stroj ${acc.agent} má na platforme ${acc.platform} kód ${String(cs.installed).slice(0, 7)}, táto webapp je na ${mine.slice(0, 7)} — nasadenie vznikne z novšieho kódu; najprv „Aktualizovať kód“ v sekcii Stroje (nasadiť sa dá aj tak).`
    : `Stroj ${acc.agent} nehlási, z akého commitu je kód na platforme ${acc.platform} (installed.json chýba) — po nasadení zváž „Aktualizovať kód“ v sekcii Stroje.`;
  box.hidden = false;
}

function renderLiveDeploy() {
  const accById = Object.fromEntries(ld.accounts.map(a => [a.id, a]));
  const deps = ld.deployments;
  const key = JSON.stringify([ld.admin, ld.accounts, Object.keys(ld.profiles), ld.agents, lv.deploy && lv.deploy.version,
    deps.map(d => [d.id, d.mode, d.active, d.config_hash, d.profile, d.applied, d.live && d.live.alive, d.live && d.live.last_bar_ms, d.code_state])]);
  const instances = new Set(lv.instances.map(i => i.id));
  if (key !== ld.key) {
    ld.key = key;
    $("#ld-dep-count").textContent = deps.length ? String(deps.filter(d => d.active).length) : "";
    $("#ld-empty").hidden = !!deps.length;
    $("#ld-deployments").parentElement.hidden = !deps.length;
    $("#ld-deployments tbody").innerHTML = deps.map(d => {
      const acc = accById[d.account] || {};
      const live = d.live || {};
      const dis = ld.admin && d.active ? "" : "disabled";
      const inst = instances.has(d.instance)
        ? `<a href="#" data-inst="${esc(d.instance)}" title="otvoriť detail inštancie">${esc(d.instance)}</a>`
        : `<span class="muted" title="v zrkadle zatiaľ nie je">${esc(d.instance)}</span>`;
      return `<tr class="plain" data-dep="${esc(d.id)}">
        <td>${ldStatusChip(d)}</td>
        <td title="${esc(acc.agent || "")}">${esc(acc.label || d.account)} <span class="muted small">${esc(acc.agent || "")}</span></td>
        <td>${esc(d.strategy)}</td><td><b>${esc(d.symbol)}</b></td><td>${d.tf}m</td>
        <td><select class="small ld-profile" ${dis} title="zmena profilu: aplikuje sa, až keď je stratégia bez pozície">${ldProfileOptions(d.strategy, d.profile)}</select></td>
        <td><span class="chip ${d.mode === "enabled" ? "ok" : (d.mode === "flatten" ? "bad" : "warn")}">${esc(LD_MODE_LABEL[d.mode] || d.mode)}</span></td>
        <td>${ldAppliedCell(d)}</td>
        <td>${ldCodeChip(d.code_state, d.version)}</td>
        <td>${inst}${live.host ? ` <span class="muted small">${esc(live.host)}</span>` : ""}</td>
        <td title="${live.last_bar_ms ? utc(live.last_bar_ms) + " UTC" : ""}">${live.last_bar_ms ? liveAge(live.last_bar_ms, lv.now) : "—"}</td>
        <td class="ld-actions" style="white-space:nowrap">
          ${d.mode === "enabled" ? `<button class="small" data-mode="paused" ${dis} title="nové vstupy sa neposielajú; SL/TP bežia ďalej">pauza</button>`
                                 : `<button class="small" data-mode="enabled" ${dis}>zapnúť</button>`}
          <button class="small danger" data-mode="flatten" ${dis} title="zrušiť čakajúce vstupy a zavrieť pozíciu, potom pauza">flatten</button>
          <button class="small ghost danger" data-del="1" ${ld.admin ? "" : "disabled"} title="${d.active ? "vypnúť (agent odstráni z platformy), po potvrdení zmazať" : "zmazať z hubu"}">${d.active ? "odstrániť" : "zmazať"}</button>
        </td></tr>`;
    }).join("");
    for (const tr of $$("#ld-deployments tbody tr")) {
      const id = tr.dataset.dep;
      for (const b of tr.querySelectorAll("button[data-mode]")) b.onclick = () => ldSetMode(id, b.dataset.mode);
      const del = tr.querySelector("button[data-del]"); if (del) del.onclick = () => ldDelete(id);
      const sel = tr.querySelector("select.ld-profile"); if (sel) sel.onchange = () => ldSetProfile(id, sel);
      const a = tr.querySelector("a[data-inst]"); if (a) a.onclick = e => { e.preventDefault(); openLiveDetail(a.dataset.inst); };
    }
    renderLiveAccounts(deps);
    renderLiveAgents();
    // profily stratégií v tabuľke — po načítaní sa riadky prekreslia s celou ponukou
    for (const s of new Set(deps.map(d => d.strategy))) ldLoadProfiles(s).catch(() => {});
  }
  if (!ld.formsReady) { ldSetupForms(); ld.formsReady = true; }
  ldFillFormSelects();
  ldCodeHint();
}

function ldProfileOptions(strategy, current) {
  const p = ld.profiles[strategy];
  const names = p ? p.profiles.slice() : [];
  if (current && !names.includes(current)) names.unshift(current);
  if (!names.length) names.push(current || "");
  return names.map(n => {
    const title = p && p.profile_titles && p.profile_titles[n];
    return `<option value="${esc(n)}" ${n === current ? "selected" : ""}>${esc(title && title !== n ? `${n} — ${title}` : n)}</option>`;
  }).join("");
}

function renderLiveAccounts(deps) {
  const list = ld.accounts;
  $("#ld-acc-count").textContent = list.length ? String(list.length) : "";
  $("#ld-acc-empty").hidden = !!list.length;
  $("#ld-accounts").parentElement.hidden = !list.length;
  $("#ld-accounts tbody").innerHTML = list.map(a => {
    const n = deps.filter(d => d.account === a.id).length;
    return `<tr class="plain" data-acc="${esc(a.id)}"><td><code>${esc(a.id)}</code></td><td>${esc(a.label)}</td><td>${esc(a.agent)}</td>
      <td>${esc(a.platform)}</td><td>${esc(a.login)}</td><td>${esc(a.server || "—")}</td><td title="${esc(a.terminal || "")}">${esc(a.terminal ? a.terminal.slice(-28) : "—")}${a.portable ? ' <span class="chip">portable</span>' : ""}</td>
      <td>${a.secret_pending ? '<span class="chip warn" title="agent si ho ešte neprevzal">čaká</span>' : '<span class="muted">—</span>'}</td>
      <td class="num">${n}</td>
      <td><button class="small ghost danger" data-del="1" ${ld.admin ? "" : "disabled"} title="${n ? "účet má nasadenia — zmazanie ich vyhodí tiež" : "zmazať účet"}">zmazať</button></td></tr>`;
  }).join("");
  for (const tr of $$("#ld-accounts tbody tr")) tr.querySelector("button[data-del]").onclick = () => ldDeleteAccount(tr.dataset.acc);
}

/** Profily stratégie do výberu (cache; po načítaní sa tabuľka prekreslí, nech má riadok všetky možnosti). */
async function ldLoadProfiles(strategy) {
  if (!strategy) return null;
  if (ld.profiles[strategy]) return ld.profiles[strategy];
  const p = await api(`/api/live/profiles?strategy=${encodeURIComponent(strategy)}`);
  ld.profiles[strategy] = p;
  renderLiveDeploy();
  return p;
}

function ldFillFormSelects() {
  // účet do „Nasadiť"
  const selA = $("#ld-d-account"), curA = selA.value;
  selA.innerHTML = ld.accounts.map(a => `<option value="${esc(a.id)}">${esc(a.label)} · ${esc(a.agent)} · ${esc(a.platform)}</option>`).join("")
    || `<option value="">— najprv pridaj účet —</option>`;
  if (curA && ld.accounts.some(a => a.id === curA)) selA.value = curA;
  selA.onchange = () => ldCodeHint();
  // agent do „Pridať účet": online prví; platformy z ich driverov
  const selAg = $("#ld-a-agent"), curAg = selAg.value;
  const agents = ld.agents.slice().sort((a, b) => (b.online - a.online) || a.name.localeCompare(b.name));
  selAg.innerHTML = agents.map(a => `<option value="${esc(a.name)}">${esc(a.name)}${a.online ? "" : " (offline)"}${a.live && a.live.drivers && a.live.drivers.length ? " · " + esc(a.live.drivers.join(", ")) : ""}</option>`).join("")
    || `<option value="">— žiadny agent na hube —</option>`;
  if (curAg && agents.some(a => a.name === curAg)) selAg.value = curAg;
  const drivers = new Set(); for (const a of agents) for (const d of (a.live && a.live.drivers) || []) drivers.add(d);
  $("#ld-a-platforms").innerHTML = [...drivers].map(d => `<option value="${esc(d)}">`).join("");
  // stratégie z /api/meta
  const selS = $("#ld-d-strategy");
  if (!selS.options.length && state.meta && state.meta.strategies) {
    selS.innerHTML = state.meta.strategies.map(s => `<option value="${esc(s.key)}">${esc(s.title || s.key)}</option>`).join("");
    selS.onchange = () => ldFormProfiles();
    ldFormProfiles();
  }
  for (const b of ["#ld-d-submit", "#ld-a-submit"]) $(b).disabled = !ld.admin;
  const hint = ld.admin ? "" : "len na čítanie (bez admin tokenu)";
  if (!$("#ld-d-status").textContent || !ld.admin) $("#ld-d-status").textContent = hint;
  if (!$("#ld-a-status").textContent || !ld.admin) $("#ld-a-status").textContent = hint;
}

async function ldFormProfiles() {
  const strategy = $("#ld-d-strategy").value, sel = $("#ld-d-profile");
  sel.innerHTML = `<option value="">načítavam…</option>`;
  try {
    const p = await ldLoadProfiles(strategy);
    sel.innerHTML = ldProfileOptions(strategy, p.profiles[0] || "");
  } catch (e) { sel.innerHTML = `<option value="">${esc(e.message)}</option>`; }
}

function ldSetupForms() {
  $("#ld-d-submit").onclick = async () => {
    const btn = $("#ld-d-submit"); btn.disabled = true; $("#ld-d-error").hidden = true; $("#ld-d-status").textContent = "posielam na hub…";
    try {
      const body = { account: $("#ld-d-account").value, strategy: $("#ld-d-strategy").value, symbol: $("#ld-d-symbol").value.trim(),
        tf: Number($("#ld-d-tf").value) || 0, profile: $("#ld-d-profile").value, mode: $("#ld-d-mode").value || "paused", user: ldUser() };
      if (!body.account) throw new Error("vyber účet");
      if (!body.symbol) throw new Error("zadaj symbol");
      const d = await api("/api/live/deployments", { method: "POST", body: JSON.stringify(body) });
      $("#ld-d-status").textContent = `nasadené: ${d.instance} (agent si to vezme v najbližšom heartbeate${d.mode === "paused" ? "; štartuje pauznuté — zapni v tabuľke" : ""})`;
      $("#ld-d-symbol").value = "";
      await loadLiveDeploy();
    } catch (e) { $("#ld-d-error").textContent = e.message; $("#ld-d-error").hidden = false; $("#ld-d-status").textContent = ""; }
    finally { btn.disabled = !ld.admin; }
  };
  $("#ld-a-submit").onclick = async () => {
    const btn = $("#ld-a-submit"); btn.disabled = true; $("#ld-a-error").hidden = true; $("#ld-a-status").textContent = "posielam na hub…";
    try {
      const body = { agent: $("#ld-a-agent").value, platform: $("#ld-a-platform").value.trim(), label: $("#ld-a-label").value.trim(),
        id: $("#ld-a-id").value.trim() || null,
        login: $("#ld-a-login").value.trim(), server: $("#ld-a-server").value.trim(), terminal: $("#ld-a-terminal").value.trim(),
        portable: $("#ld-a-portable").checked, password: $("#ld-a-password").value || null, user: ldUser() };
      if (!body.agent) throw new Error("vyber agenta (stroj)");
      if (!body.platform) throw new Error("zadaj platformu");
      if (!body.login) throw new Error("zadaj login");
      const a = await api("/api/live/accounts", { method: "POST", body: JSON.stringify(body) });
      $("#ld-a-password").value = "";   // heslo odišlo raz; v stránke neostáva
      $("#ld-a-status").textContent = `účet ${a.id} pridaný${a.secret_pending ? " — heslo čaká na prevzatie agentom" : ""}`;
      for (const id of ["#ld-a-label", "#ld-a-id", "#ld-a-login", "#ld-a-server", "#ld-a-terminal"]) $(id).value = "";
      ldAccountIdHint();
      await loadLiveDeploy();
    } catch (e) { $("#ld-a-error").textContent = e.message; $("#ld-a-error").hidden = false; $("#ld-a-status").textContent = ""; }
    finally { btn.disabled = !ld.admin; }
  };
  $("#ld-audit-box").ontoggle = () => { if ($("#ld-audit-box").open) loadLiveAudit().catch(() => {}); };
  for (const id of ["#ld-a-label", "#ld-a-login"]) $(id).oninput = ldAccountIdHint;
  ldAccountIdHint();
}

/** Id účtu tak, ako ho spraví hub z názvu (`_slug` v `tradebot/live/deploy.py`): malé písmená, číslice, `.-_`;
 *  ukáže sa ako placeholder políčka „Id účtu“, kým ho človek nezadá sám. */
function ldSlug(text) {
  return String(text || "").trim().toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^[-._]+|[-._]+$/g, "") || "ucet";
}

function ldAccountIdHint() {
  const el = $("#ld-a-id");
  if (el) el.placeholder = ldSlug($("#ld-a-label").value || $("#ld-a-login").value);
}

function ldFail(e) { $("#ld-error").textContent = e.message; $("#ld-error").hidden = false; }

async function ldSetMode(id, mode) {
  if (mode === "flatten" && !confirm("Flatten: zrušiť všetky čakajúce vstupy a zavrieť otvorenú pozíciu u brokera. Potom sa stratégia správa ako v pauze. Pokračovať?")) return;
  try {
    await api(`/api/live/deployments/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ mode, user: ldUser() }) });
    await loadLiveDeploy();
  } catch (e) { ldFail(e); }
}

async function ldSetProfile(id, sel) {
  const dep = ld.deployments.find(d => d.id === id);
  const profile = sel.value;
  if (!dep || profile === dep.profile) return;
  if (!confirm(`Zmeniť profil nasadenia ${dep.symbol} ${dep.tf}m na „${profile}“? Aplikuje sa, až keď je stratégia bez pozície a bez čakajúcich vstupov (vynútenie = najprv flatten).`)) { sel.value = dep.profile; return; }
  try {
    await api(`/api/live/deployments/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ profile, user: ldUser() }) });
    await loadLiveDeploy();
  } catch (e) { sel.value = dep.profile; ldFail(e); }
}

async function ldDelete(id) {
  const dep = ld.deployments.find(d => d.id === id);
  if (!dep) return;
  const otazka = dep.active
    ? `Odstrániť nasadenie ${dep.symbol} ${dep.tf}m (${dep.strategy}) z účtu? Agent inštanciu z platformy odstráni; otvorená pozícia sa nezatvára (na to je flatten). Po potvrdení agentom sa dá zmazať z hubu.`
    : `Zmazať nasadenie ${dep.symbol} ${dep.tf}m z hubu? Keď to agent ešte nepotvrdil, zmaže sa aj tak (force).`;
  if (!confirm(otazka)) return;
  try {
    await api(`/api/live/deployments/${encodeURIComponent(id)}?force=${dep.active ? "false" : "true"}&user=${encodeURIComponent(ldUser() || "")}`, { method: "DELETE" });
    await loadLiveDeploy();
  } catch (e) { ldFail(e); }
}

async function ldDeleteAccount(id) {
  const acc = ld.accounts.find(a => a.id === id);
  const n = ld.deployments.filter(d => d.account === id).length;
  if (!acc) return;
  if (!confirm(`Zmazať účet „${acc.label}“ (${acc.id})?${n ? ` Má ${n} nasadení — zmažú sa z hubu tiež a agent ich má z platformy odstrániť sám.` : ""}`)) return;
  try {
    await api(`/api/live/accounts/${encodeURIComponent(id)}?force=${n ? "true" : "false"}&user=${encodeURIComponent(ldUser() || "")}`, { method: "DELETE" });
    await loadLiveDeploy();
  } catch (e) { ldFail(e); }
}

async function loadLiveAudit() {
  const rows = await api("/api/live/audit?limit=50");
  const key = rows.length ? `${rows[0].id}:${rows.length}` : "0";
  if (key === ld.auditKey) return;
  ld.auditKey = key;
  const short = v => { if (v === null || v === undefined) return ""; const s = JSON.stringify(v); return s.length > 90 ? s.slice(0, 89) + "…" : s; };
  $("#ld-audit tbody").innerHTML = rows.map(r => `<tr class="plain"><td>${utc(r.ts * 1000).slice(0, 19)}</td><td>${esc(r.by || "—")}</td>
    <td>${esc(r.action)}</td><td>${esc(r.account || "")}</td><td>${esc(r.deployment || "")}</td>
    <td class="small" title="${esc(JSON.stringify({ old: r.old, new: r.new }))}">${esc(short(r.new) || short(r.old))}</td></tr>`).join("")
    || `<tr class="plain"><td colspan="6" class="muted">zatiaľ nič</td></tr>`;
}
