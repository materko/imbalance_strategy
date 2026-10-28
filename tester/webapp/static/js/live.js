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

const LIVE_FILLS_PAGE = 5000;         // fillov a orderov na jednu požiadavku (server viac nedá)
const LIVE_POLL_MS = 5000;            // polling, keď stream nejde (starý server, proxy bez SSE)
const LIVE_SSE_RETRY_MS = 60000;      // po chybe streamu: polling a o minútu stream znova
const LIVE_DEPLOY_POLL_MS = 5000;     // účty a nasadenia idú z hubu (nie zo zrkadla) — pri streame sa obnovujú takto; živosť z hubu dopĺňa stream (`ldLive`)
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
  showStale: false,                           // ukázať aj staré inštancie (bez nasadenia, ticho > LIVE_STALE_DAYS)
};

/** Inštancia bez aktívneho nasadenia a bez udalosti dlhšie než toľko dní sa v zozname skrýva (starý beh,
 *  odstránené nasadenie — spool aj zrkadlo ju majú ďalej, ukáže ju odkaz pod tabuľkou). */
const LIVE_STALE_DAYS = 3;

function liveStale(inst) {
  if ((ld.deployments || []).some(d => d.active && d.instance === inst.id)) return false;
  return !inst.last_t || (lv.now - inst.last_t) > LIVE_STALE_DAYS * 86400e3;
}

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
  if (ld.deployments.length && !lv.selected) renderLiveDeploy();   // živosť nasadení zo streamu (`ldLive`), nie až z hubu
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
    if (ev.k === "hb") {                                        // ping: len stav, graf ani tabuľky sa nemenia
      snap.instance.last_t = Math.max(snap.instance.last_t || 0, ev.t);
      snap.instance.last_hb = Math.max(snap.instance.last_hb || 0, ev.t);
      $("#live-detail-status").innerHTML = liveStatusChip(snap.instance);
      continue;
    }
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
  // a potom každých 30 s, aj keď je karta zatvorená (otvorenú drží aktuálnu stream)
  setInterval(() => api("/api/live").then(d => liveChip(d.instances, d.now, d.mirror)).catch(() => liveChip([], 0, { last_error: "webapp neodpovedá" })), 30e3);
}

/** Stav inštancie — to isté ako `tradebot.live.store.liveness`: `live`, `closed` (pinguje `hb`, ale
 *  bary nechodia — trh zatvorený) alebo `silent`. Kto pinguje (posledný ping nie je o viac než 3 min
 *  starší než posledná udalosť), žije 3 min od poslednej udalosti; bez pingov 3 bary TF ako predtým. */
const LIVE_HB_MS = 180e3;
function liveState(inst, now = lv.now) {
  const lastT = Number(inst.last_t) || 0;
  if (!lastT) return "silent";
  const tfMs = Math.max(1, Number(inst.tf) || 1) * 60e3;
  const lastHb = Number(inst.last_hb) || 0;
  const pinguje = lastHb > 0 && lastT - lastHb <= LIVE_HB_MS;
  if (now - lastT > (pinguje ? LIVE_HB_MS : 3 * tfMs)) return "silent";
  const bar = Number(inst.last_bar_ms) || 0;
  return pinguje && (!bar || now - bar > 4 * tfMs) ? "closed" : "live";
}

/** Inštancia je „živá" (beží, aj keď trh stojí) — `liveState` nie je `silent`. */
function liveAlive(inst, now = lv.now) {
  return liveState(inst, now) !== "silent";
}

/** Bodka a počet živých pri záložke Live; bez argumentov zo stavu karty. */
function liveChip(list = lv.instances, now = lv.now, mirror = lv.mirror) {
  const n = list.filter(i => liveAlive(i, now)).length;
  const chyba = mirror && mirror.last_error;
  $("#live-tab-chip").textContent = n ? String(n) : "";
  $("#live-tab-chip").className = `chip ${n ? "ok" : ""}`;
  const dot = $("#live-tab-dot");
  dot.className = `tab-dot ${chyba ? "bad" : (n ? "ok" : "")}`;
  dot.title = chyba ? `zrkadlo: ${chyba}` : (n ? `beží ${n} z ${list.length}` : "nič nebeží");
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
  if (m.gaps_refilled) parts.push(`doplnené z hubu ${m.gaps_refilled} udalostí`);
  $("#live-status").textContent = parts.join(" · ");
  const err = $("#live-error");
  const gaps = m.gaps || [];
  if (m.last_error) { err.textContent = `zrkadlo: ${m.last_error}`; err.hidden = false; }
  else if (gaps.length) {
    const spolu = gaps.reduce((a, g) => a + g.missing, 0);
    const hub = gaps.filter(g => g.on_hub === true).length;
    err.textContent = `chýba ${spolu} udalostí v ${gaps.length} ${gaps.length === 1 ? "mieste" : "miestach"} `
      + (hub === gaps.length ? "— chýbajú aj na hube, stratili sa cestou z platformy (spool / agent)"
        : hub ? `— ${hub} z nich chýbajú aj na hube (stratili sa cestou z platformy), ostatné sa nedali dotiahnuť`
        : "— hub ich nedal, zrkadlo to skúša znova každú minútu");
    err.hidden = false;
  }
}

/** Diery v `seq` inštancie (zo stavu zrkadla) ako text do title. */
function liveGapsOf(id) {
  return ((lv.mirror && lv.mirror.gaps) || []).filter(g => g.instance === id);
}

/** Fills a smery vstupov inštancie — prírastkovo od posledného rowid, nech sa pri obnove neťahá všetko. */
async function loadLiveFills(id) {
  const f = lv.fills[id] || (lv.fills[id] = { after: 0, fills: [], dirs: {} });
  // po stránkach, kým server nevráti menej než limit — inak by filly za 5 000. riadkom chýbali navždy (N-FE-3)
  for (;;) {
    const rows = await api(`/api/live/${encodeURIComponent(id)}/events?after=${f.after}&kinds=fill,order&limit=${LIVE_FILLS_PAGE}`);
    for (const r of rows) {
      f.after = Math.max(f.after, r.id);
      const ev = r.event;
      if (ev.k === "fill") f.fills.push(ev);
      else if (ev.k === "order" && ev.a === "entry") f.dirs[ev.id] = Number(ev.dir ?? (ev.p && ev.p.dir) ?? 1) || 1;
    }
    if (rows.length < LIVE_FILLS_PAGE) break;
  }
  // vstupy bez zatvorenia, ktoré už nebežia — server pozná aj bary (cena prešla SL / TP), ako stránka výsledkov
  try { f.lost = (await api(`/api/live/${encodeURIComponent(id)}/lost`)).lost || {}; } catch (e) { f.lost = f.lost || {}; }
  return f;
}

/** Odhad pozície z fillov: za každé id vstupy − výstupy (v množstve) × smer vstupu z orderu. Vstup bez
 *  zatvorenia v telemetrii (reštart platformy), ktorý už nebeží — inštancia neskôr vstúpila do ďalšieho
 *  obchodu (vždy len jedna pozícia) alebo podľa servera cena prešla jeho SL / TP —, sa nepočíta: je v `lost`. */
function livePosition(f) {
  if (!f || !f.fills.length) return null;
  const net = {}, firstIn = {};
  for (const x of f.fills) {
    net[x.id] = (net[x.id] || 0) + (x.side === "in" ? 1 : -1) * Number(x.qty || 0);
    if (x.side !== "in") continue;
    const ft = Number(x.ft || x.t || 0);
    if (!(x.id in firstIn)) firstIn[x.id] = ft;
  }
  // „neskôr vstúpila" len podľa vstupu s iným id — čiastočné vyplnenie toho istého vstupu (qty 2 po 1) nie je
  // ďalší obchod (N-FE-2); to isté pravidlo má server (`tester/dashboard/live.py`)
  const laterOther = id => Object.entries(firstIn).some(([o, t]) => o !== id && t > firstIn[id]);
  let qty = 0; const open = [], lost = [];
  for (const [id, q] of Object.entries(net)) {
    if (Math.abs(q) < 1e-9) continue;
    const dir = f.dirs[id] || 1, side = `${id} ${q * dir > 0 ? "long" : "short"} ${Math.abs(q)}`;
    const why = (f.lost || {})[id] || (q > 0 && laterOther(id) ? "neskôr vstúpila do ďalšieho obchodu" : "");
    if (why) { lost.push(`${side} bez zatvorenia v telemetrii (${why}) — do pozície sa nepočíta`); continue; }
    qty += q * dir; open.push(side);
  }
  return { qty, open, lost };
}

/** Pozícia u brokera z posledného pingu `hb` (`pos`, `pos_px`, `pos_of`) a s čím ju porovnať: pri `account`
 *  (NinjaTrader — celý účet na inštrumente) so súčtom odhadov všetkých inštancií toho účtu a symbolu, pri `magic`
 *  (MT5 — len tento EA) s odhadom inštancie. `null`, keď platforma pozíciu nehlási (starší kód). */
function liveBroker(inst) {
  const hb = inst.hb || {};
  if (typeof hb.pos !== "number") return null;
  const same = hb.pos_of === "account"
    ? lv.instances.filter(i => i.platform === inst.platform && i.account === inst.account && i.symbol === inst.symbol)
    : [inst];
  let expected = 0;
  for (const i of same) { const p = livePosition(lv.fills[i.id]); expected += p ? p.qty : 0; }
  return { qty: hb.pos, price: hb.pos_px, scope: hb.pos_of, t: hb.t, expected, shared: same.length > 1 };
}

function liveBrokerText(b) {
  if (b === null) return `<span class="muted" title="platforma pozíciu účtu do telemetrie nehlási (starší kód AddOnu / EA)">—</span>`;
  const n = b.qty > 0 ? `+${b.qty}` : String(b.qty);
  const kde = b.scope === "account" ? `celý účet na inštrumente${b.shared ? " (aj iné inštancie)" : ""}` : "pozície tohto EA (magic)";
  const tip = `${kde}${b.qty ? ` @${b.price}` : ""}, ping ${b.t ? liveAge(b.t, lv.now) : "—"}`;
  const zle = Math.abs(b.qty - b.expected) > 1e-9;
  return `<span title="${esc(tip)}">${n}</span>` + (zle
    ? ` <span class="chip bad" title="${esc(`odhad z fillov dáva ${b.expected > 0 ? "+" : ""}${b.expected}, u brokera je ${n} — výstup alebo vstup do telemetrie neprišiel`)}">≠</span>`
    : "");
}

/** Pozícia do tabuľky a karty: číslo, pri vstupe bez zatvorenia s výstrahou. */
function livePosText(pos) {
  if (pos === null) return "—";
  const n = pos.qty > 0 ? `+${pos.qty}` : String(pos.qty);
  return pos.lost.length ? `${n} <span class="chip warn" title="${esc(pos.lost.join("\n"))}">?</span>` : n;
}

function liveFillsToday(f) {
  if (!f) return 0;
  const start = Math.floor(lv.now / 86400e3) * 86400e3;
  return f.fills.filter(x => x.ft >= start).length;
}

function liveStatusChip(inst) {
  const stav = liveState(inst);
  const tester = inst.hello && inst.hello.tester ? ' <span class="chip warn" title="beží v Strategy Testeri / Analyzeri">tester</span>' : "";
  const gaps = liveGapsOf(inst.id);
  const diera = gaps.length ? ` <span class="chip bad" title="${esc(gaps.map(g => `beh ${g.session}: chýba seq ${g.first}–${g.last} (${g.missing})${g.on_hub ? ", aj na hube" : ""}`).join("\n"))}">chýbajú dáta</span>` : "";
  const chip = {
    live: `<span class="chip ok" title="${inst.last_hb ? "ping alebo udalosť do 3 min" : "posledná udalosť do 3 barov"}">živá</span>`,
    closed: `<span class="chip ok" title="platforma pinguje, ale bar neprišiel dlhšie než 4 bary — trh je zatvorený">trh zatvorený</span>`,
    silent: `<span class="chip" title="${inst.last_hb ? "ani ping, ani udalosť dlhšie než 3 min — platforma spadla alebo zamrzla" : "bez udalostí dlhšie než 3 bary"}">ticho</span>`,
  }[stav];
  return `${chip}${tester}${diera}`;
}

const liveTxt = (x, y) => String(x).localeCompare(String(y), "sk", { numeric: true, sensitivity: "base" });

/** Predvolené poradie tabuľky inštancií: platforma, účet, symbol, TF, stratégia, profil (prázdne na koniec). */
function liveOrder(a, b) {
  const txt = (x, y) => (!x - !y) || liveTxt(x || "", y || "");
  return txt(a.platform, b.platform) || txt(a.account, b.account) || txt(a.symbol, b.symbol)
    || (!a.tf - !b.tf) || ((Number(a.tf) || 0) - (Number(b.tf) || 0))
    || txt(a.strategy, b.strategy) || txt(a.profile, b.profile) || txt(a.id, b.id);
}

/** Hodnota stĺpca na triedenie klikom na hlavičku (`data-k`); null/"" ide vždy na koniec. */
const LIVE_SORT = {
  state: i => ({ live: 0, closed: 1, silent: 2 })[liveState(i)],
  platform: i => i.platform, account: i => i.account, symbol: i => i.symbol, tf: i => Number(i.tf) || null,
  strategy: i => i.strategy, profile: i => i.profile, host: i => i.host, agent: i => i.agent,
  bar: i => i.last_bar_ms || null,
  pos: i => { const p = livePosition(lv.fills[i.id]); return p ? p.qty : null; },
  broker: i => { const b = liveBroker(i); return b ? b.qty : null; },
  fills: i => liveFillsToday(lv.fills[i.id]),
};
const LIVE_SORT_KEY = "tradebot.live.sort";

function liveSortLoad() {
  try { return JSON.parse(localStorage.getItem(LIVE_SORT_KEY) || "null"); } catch (_) { return null; }
}

/** Klik na hlavičku: prvý vzostupne, druhý zostupne, tretí späť na predvolené poradie. */
function liveSortClick(k) {
  const s = lv.sort;
  lv.sort = !s || s.k !== k ? { k, dir: 1 } : (s.dir === 1 ? { k, dir: -1 } : null);
  try { localStorage.setItem(LIVE_SORT_KEY, JSON.stringify(lv.sort)); } catch (_) { /* súkromné okno */ }
  renderLiveList();
}

function liveSorted(list) {
  const s = lv.sort, f = s && LIVE_SORT[s.k];
  if (!f) return list.slice().sort(liveOrder);
  return list.map(i => [i, f(i)]).sort(([a, x], [b, y]) => {
    const prazdne = (x === null || x === undefined || x === "") - (y === null || y === undefined || y === "");
    if (prazdne) return prazdne;
    const c = typeof x === "number" && typeof y === "number" ? x - y : liveTxt(x, y);
    return c * s.dir || liveOrder(a, b);
  }).map(([i]) => i);
}

// Skupiny tabuľky inštancií: jeden účet na platforme (ten istý login na NT a MT5 sú dva účty). Hlavička
// skupiny nesie súhrn riadkov pod ňou, takže zbalená skupina povie to podstatné aj bez nich. Predvolene
// je každá skupina zbalená, rozbalené si pamätá prehliadač (localStorage), aj nový účet tak príde zbalený;
// poradie skupín ide podľa ich prvej inštancie v triedení.
const LIVE_EXPANDED_KEY = "tradebot.live.expanded";
const liveGroupKey = i => `${i.platform || ""}|${i.account || ""}`;

function liveExpandedSave() {
  try { localStorage.setItem(LIVE_EXPANDED_KEY, JSON.stringify([...lv.expanded])); } catch (_) { /* súkromné okno */ }
}

function liveToggleGroup(key) {
  if (lv.expanded.has(key)) lv.expanded.delete(key); else lv.expanded.add(key);
  liveExpandedSave();
  renderLiveList();
}

/** Názov účtu z hubu (sekcia Účty): cez nasadenie inštancie, inak podľa platformy a loginu. */
function liveAccountLabel(i) {
  const dep = ld.deployments.find(d => d.instance === i.id);
  const acc = ld.accounts.find(a => dep ? a.id === dep.account
    : a.platform === i.platform && [a.id, String(a.login), `${a.login}-${a.server}`].includes(String(i.account)));
  return acc && acc.label && acc.label !== i.account ? acc.label : "";
}

/** Rôzne hodnoty do bunky súhrnu: najviac `max`, zvyšok ako „+N", celý zoznam v title. */
function liveUniqCell(vals, max = 3) {
  const u = [...new Set(vals.filter(v => v !== null && v !== undefined && v !== ""))].sort(liveTxt);
  if (!u.length) return "—";
  const txt = u.slice(0, max).map(v => esc(v)).join(", ") + (u.length > max ? ` <span class="muted">+${u.length - max}</span>` : "");
  return u.length > max ? `<span title="${esc(u.join(", "))}">${txt}</span>` : txt;
}

/** Pozícia podľa symbolu („MNQ +2 · MES −1", „flat"); `null` → „—". */
function liveBySymbolText(bySym) {
  if (bySym === null) return "—";
  const n = Object.entries(bySym).filter(([, q]) => Math.abs(q) > 1e-9).sort(([a], [b]) => liveTxt(a, b));
  return n.length ? n.map(([s, q]) => `${esc(s)} ${q > 0 ? "+" : ""}${q}`).join(" · ") : "flat";
}

function liveGroupRow(key, members, collapsed) {
  const first = members[0];
  const stavy = { live: 0, closed: 0, silent: 0 };
  for (const i of members) stavy[liveState(i)]++;
  const chips = [
    stavy.live ? `<span class="chip ok" title="ping alebo udalosť do 3 min">${stavy.live} živ${stavy.live === 1 ? "á" : (stavy.live <= 4 ? "é" : "ých")}</span>` : "",
    stavy.closed ? `<span class="chip ok" title="platforma pinguje, ale bary nechodia — trh je zatvorený">${stavy.closed} trh zatvorený</span>` : "",
    stavy.silent ? `<span class="chip" title="bez pingu aj udalosti — platforma spadla, zamrzla alebo stratégia nebeží">${stavy.silent} ticho</span>` : "",
  ].filter(Boolean);
  const tester = members.filter(i => i.hello && i.hello.tester).length;
  if (tester) chips.push(`<span class="chip warn" title="beží v Strategy Testeri / Analyzeri">tester ${tester}</span>`);
  const diery = members.filter(i => liveGapsOf(i.id).length).length;
  if (diery) chips.push(`<span class="chip bad" title="${diery} z ${members.length} inštancií má diery v dátach — detail v riadku">chýbajú dáta</span>`);

  // pozícia z fillov a u brokera po symboloch; pri NinjaTraderi (`account`) hlási každá inštancia celý účet
  // na inštrumente — berie sa najčerstvejší ping, pri MT5 (`magic`) len svoj EA — sčíta sa
  let pos = null, lost = 0, broker = null, zle = 0, fills = 0, bar = 0;
  const brokerT = {};
  for (const i of members) {
    const f = lv.fills[i.id], p = livePosition(f), sym = i.symbol || "?";
    fills += liveFillsToday(f);
    bar = Math.max(bar, Number(i.last_bar_ms) || 0);
    if (p) { pos = pos || {}; pos[sym] = (pos[sym] || 0) + p.qty; lost += p.lost.length; }
    const b = liveBroker(i);
    if (!b) continue;
    broker = broker || {};
    if (b.scope === "account") {
      if ((Number(b.t) || 0) >= (brokerT[sym] ?? -1)) { broker[sym] = b.qty; brokerT[sym] = Number(b.t) || 0; }
    } else broker[sym] = (broker[sym] || 0) + b.qty;
    if (Math.abs(b.qty - b.expected) > 1e-9) zle++;
  }
  const label = liveAccountLabel(first);
  const selected = collapsed && members.some(i => i.id === lv.selected);
  return `<tr class="live-group${selected ? " hl" : ""}" data-group="${esc(key)}" title="${collapsed ? "rozbaliť" : "zbaliť"} účet">
    <td><span class="live-caret">${collapsed ? "▸" : "▾"}</span>${chips.join(" ") || "—"}</td>
    <td>${esc(first.platform || "—")}</td>
    <td><b>${esc(first.account || "—")}</b>${label ? ` <span class="muted small">${esc(label)}</span>` : ""}
      <span class="chip" title="inštancií na účte">${members.length}</span></td>
    <td><b>${liveUniqCell(members.map(i => i.symbol))}</b></td>
    <td>${liveUniqCell(members.map(i => i.tf ? i.tf + "m" : ""))}</td>
    <td>${liveUniqCell(members.map(i => i.strategy), 2)}</td>
    <td>${liveUniqCell(members.map(i => i.profile), 1)}</td>
    <td>${liveUniqCell(members.map(i => i.host), 2)}</td>
    <td>${liveUniqCell(members.map(i => i.agent), 2)}</td>
    <td title="${bar ? utc(bar) + " UTC — najčerstvejší bar účtu" : ""}">${bar ? `${liveAge(bar, lv.now)} <span class="muted">${utc(bar).slice(5, 16)}</span>` : "—"}</td>
    <td class="num" title="súčet odhadov z fillov po symboloch">${liveBySymbolText(pos)}${lost ? ` <span class="chip warn" title="vstup bez zatvorenia v telemetrii — detail v riadku">?</span>` : ""}</td>
    <td class="num" title="u brokera po symboloch (NinjaTrader: celý účet na inštrumente, MT5: súčet EA)">${liveBySymbolText(broker)}${zle ? ` <span class="chip bad" title="${zle} z ${members.length} inštancií nesedí s odhadom z fillov — detail v riadku">≠</span>` : ""}</td>
    <td class="num">${fills}</td></tr>`;
}

function renderLiveList() {
  if (lv.sort === undefined) lv.sort = liveSortLoad();
  if (!lv.expanded) {
    try { lv.expanded = new Set(JSON.parse(localStorage.getItem(LIVE_EXPANDED_KEY) || "[]")); } catch (_) { lv.expanded = new Set(); }
  }
  for (const th of $$("#live-table th.sort")) {
    th.dataset.dir = lv.sort && lv.sort.k === th.dataset.k ? lv.sort.dir : "";
    th.onclick = () => liveSortClick(th.dataset.k);
  }
  const stare = lv.instances.filter(liveStale);
  const list = liveSorted(lv.showStale ? lv.instances : lv.instances.filter(i => !liveStale(i)));
  const st = $("#live-stale");
  st.hidden = !stare.length;
  st.innerHTML = stare.length ? `<a href="#">${lv.showStale ? "skryť" : "ukázať"} ${stare.length} ${stare.length === 1 ? "starú inštanciu" : (stare.length <= 4 ? "staré inštancie" : "starých inštancií")}</a> — bez aktívneho nasadenia a bez udalosti viac než ${LIVE_STALE_DAYS} dni` : "";
  if (stare.length) st.querySelector("a").onclick = e => { e.preventDefault(); lv.showStale = !lv.showStale; renderLiveList(); };
  const alive = list.filter(i => liveAlive(i)).length;
  $("#live-count").textContent = list.length ? `${alive} živ${alive === 1 ? "á" : (alive >= 2 && alive <= 4 ? "é" : "ých")} z ${list.length}` : "";
  $("#live-count").className = `chip ${alive ? "ok" : ""}`;
  $("#live-empty").hidden = !!list.length;
  $("#live-table").parentElement.hidden = !list.length;
  const groups = new Map();
  for (const i of list) {
    const k = liveGroupKey(i);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(i);
  }
  const fold = $("#live-fold-all"), vsetky = [...groups.keys()].every(k => !lv.expanded.has(k));
  fold.hidden = groups.size < 2;
  fold.textContent = vsetky ? "rozbaliť všetky" : "zbaliť všetky";
  fold.onclick = () => {
    for (const k of groups.keys()) { if (vsetky) lv.expanded.add(k); else lv.expanded.delete(k); }
    liveExpandedSave();
    renderLiveList();
  };
  $("#live-table tbody").innerHTML = [...groups].map(([k, members]) => {
    const zbalena = !lv.expanded.has(k);
    return liveGroupRow(k, members, zbalena) + (zbalena ? "" : members.map(liveInstanceRow).join(""));
  }).join("");
  for (const tr of $$("#live-table tbody tr[data-live]")) tr.onclick = () => openLiveDetail(tr.dataset.live);
  for (const tr of $$("#live-table tbody tr[data-group]")) tr.onclick = () => liveToggleGroup(tr.dataset.group);
}

function liveInstanceRow(i) {
  const f = lv.fills[i.id];
  const pos = livePosition(f);
  const posTxt = livePosText(pos);
  return `<tr data-live="${esc(i.id)}" class="live-member${i.id === lv.selected ? " hl" : ""}">
    <td>${liveStatusChip(i)}</td><td class="muted">${esc(i.platform || "—")}</td><td class="muted">${esc(i.account || "—")}</td>
    <td><b>${esc(i.symbol || "—")}</b></td><td>${i.tf ? i.tf + "m" : "—"}</td><td>${esc(i.strategy || "—")}</td>
    <td>${esc(i.profile || "—")}</td><td>${esc(i.host || "—")}</td><td>${esc(i.agent || "—")}</td>
    <td title="${i.last_bar_ms ? utc(i.last_bar_ms) + " UTC (otvorenie baru)" : ""}">${i.last_bar_ms ? `${liveAge(i.last_bar_ms, lv.now)} <span class="muted">${utc(i.last_bar_ms).slice(5, 16)}</span>` : "—"}</td>
    <td class="num" title="${pos ? esc(pos.open.join(", ") || "flat") : "žiadne vyplnenia"}">${posTxt}</td>
    <td class="num">${liveBrokerText(liveBroker(i))}</td>
    <td class="num">${liveFillsToday(f)}</td></tr>`;
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
    card("pozícia", livePosText(pos), esc(pos && (pos.open.length || pos.lost.length) ? [...pos.open, ...pos.lost].join(", ") : "odhad z fillov")),
    card("u brokera", liveBrokerText(liveBroker(inst)), "z platformy (ping hb)"),
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
  editing: null,   // id účtu, ktorý sa práve upravuje vo formulári (inak pridávanie)
  expanded: null,  // rozbalené účty v tabuľke nasadení (Set, localStorage)
  showRemoved: false,  // ukázať aj odstránené nasadenia
};

/** Platformy účtov — čo sa pri účte vypĺňa (`PLATFORMS` v `tradebot/live/deploy.py`). */
const LD_PLATFORMS = {
  mt5: { title: "MetaTrader 5", password: true, terminal: true },
  ninjatrader: { title: "NinjaTrader 8", password: false, terminal: false },
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
    renderLiveList();   // názvy účtov v hlavičkách skupín
  } catch (e) {
    $("#ld-error").textContent = `hub: ${e.message}`; $("#ld-error").hidden = false;
    return;
  }
  renderLiveDeploy();
  if ($("#ld-audit-box").open) loadLiveAudit().catch(() => {});
}

/** Živosť nasadenia: čerstvejší z hubu (`dep.live`, obnova každých `LIVE_DEPLOY_POLL_MS`) a zo zrkadla tejto webapp
 *  (`lv.instances`, prichádza streamom hneď) — inak stav v Nasadeniach zaostával za zoznamom inštancií nad ním. */
function ldLive(dep) {
  const hub = dep.live || {};
  const inst = lv.instances.find(i => i.id === dep.instance);
  if (!inst || (Number(inst.last_t) || 0) <= (Number(hub.last_t) || 0)) return hub;
  const state = liveState(inst);
  return { ...hub, seen: true, alive: state !== "silent", state, last_t: inst.last_t, last_bar_ms: inst.last_bar_ms,
           last_hb: inst.last_hb, session: inst.last_session, host: inst.host || hub.host };
}

function ldStatusChip(dep) {
  const a = dep.applied, live = ldLive(dep);
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
  if (live.state === "closed") return `<span class="chip ok" title="platforma pinguje, ale bary nechodia — trh je zatvorený">trh zatvorený</span>`;
  if (live.alive) return `<span class="chip ok" title="inštancia v spoole žije (ping alebo udalosť nedávno)">živá</span>`;
  return `<span class="chip" title="${live.seen ? "aplikované, ale spool je ticho dlhšie než 3 bary" : "aplikované, inštancia v spoole ešte nie je"}">ok</span>`
    + ldIssueChip(a);
}

/** Aplikované (`ok`), ale inštancia na platforme nenabehla: agent posiela dôvod z logu platformy v `error`
 *  so začiatkom „nenabehla: “ (prejde aj cez starší hub) — upozornenie, nie chyba; plný text v title. */
function ldIssueChip(a) {
  const text = a && a.status === "ok" ? String(a.error || "") : "";
  if (!text.startsWith("nenabehla: ")) return "";
  const kratko = text.length > 70 ? text.slice(0, 69) + "…" : text;
  return ` <span class="chip warn" title="${esc(text + " — z logu platformy na stroji (NinjaTrader: TradeBot\\logs\\addon_*.txt), platforma skúša znova sama")}">${esc(kratko)}</span>`;
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
  if (cs.lost) return `<span class="chip warn" title="commit nasadenia ${esc(String(wanted || "").slice(0, 7) || "?")} v histórii nie je (bol len v klone a git pull --rebase ho prepísal) — porovnať sa nedá; platforma má ${esc(sha)}. Nový profil nasadenia zapíše aktuálny commit">kód: ${esc(sha)}, commit nasadenia stratený</span>`;
  return `<span class="chip" title="platforma nehlási installed.json (kód nainštalovaný ručne pred fázou 2c, alebo nikdy)">kód: neznámy</span>`;
}

/** Odosielanie spoolu agenta (`live.ship`): čip, keď čaká viac než 1 MB (backlog histórie po reštarte platforiem)
 *  alebo posledný POST zlyhal; inak nič. */
function ldShipChip(ship) {
  if (!ship) return "";
  const mb = (Number(ship.pending_bytes) || 0) / 1048576;
  const ms = v => (v == null ? "?" : `${Math.round(v)} ms`);
  const tip = `spool čaká ${mb.toFixed(1)} MB, dávka ${ship.batch ?? "?"} udalostí${ship.last_ok ? `, posledné odoslanie ${liveAge(ship.last_ok * 1000, Date.now())}` : ""}`
    + (ship.post_ms != null ? `\nna dávku: čítanie spoolu ${ms(ship.read_ms)}, POST na hub ${ms(ship.post_ms)}; ${Math.round(ship.rate || 0)} udalostí/s; súborov v spoole ${ship.files ?? "?"}` : "")
    + (ship.last_error ? `\n${ship.last_error}` : "");
  if (ship.last_error) return ` <span class="chip bad" title="${esc(tip)}">spool: chyba</span>`;
  return mb >= 1 ? ` <span class="chip warn" title="${esc(tip)}">spool ${mb.toFixed(0)} MB</span>` : "";
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

/** Agenti, ktorí vedia live: majú aspoň jeden driver platformy (NinjaTrader, MT5). Agent bez
 *  platformy (napr. server, ktorý len počíta backtesty) účet ani nasadenie mať nemôže. */
function ldLiveAgents() {
  return ld.agents.filter(a => a.live && a.live.drivers && a.live.drivers.length)
    .sort((a, b) => (b.online - a.online) || a.name.localeCompare(b.name));
}

/** Tabuľka strojov (agentov): kód agenta, kód platforiem proti webapp, tlačidlo „Aktualizovať kód“. */
function renderLiveAgents() {
  const agents = ldLiveAgents();
  $("#ld-ag-count").textContent = agents.length ? String(agents.length) : "";
  $("#ld-ag-empty").hidden = !!agents.length;
  $("#ld-agents").parentElement.hidden = !agents.length;
  const mine = lv.deploy && lv.deploy.version ? String(lv.deploy.version) : "";
  const nepushnute = lv.deploy && lv.deploy.pushed === false;
  $("#ld-agents tbody").innerHTML = agents.map(a => {
    const cs = (a.live && a.live.code_state) || {};
    const platformy = Object.keys(cs).length
      ? Object.entries(cs).map(([p, s]) => `${esc(p)}: ${ldCodeChip(s, mine)}`).join(" ")
      : `<span class="muted">${a.live && a.live.drivers && a.live.drivers.length ? esc(a.live.drivers.join(", ")) + ": kód: neznámy" : "bez platformy"}</span>`;
    const dis = ld.admin && a.online ? "" : "disabled";
    const stav = `<span class="chip ${a.online ? "ok" : ""}">${a.online ? "online" : "offline"}</span>${a.updating ? ' <span class="chip warn" title="agent práve mení kód alebo ťahá commit">mení kód</span>' : ""}${a.needs_restart ? ' <span class="chip warn" title="agent má na disku nový kód a čaká na reštart (headless sa reštartuje sám, webapp reštartuj ručne)">reštart</span>' : ""}`;
    const verzia = a.version ? `<code title="${esc(a.version)}">${esc(String(a.version).slice(0, 7))}</code>${mine && a.version !== mine ? ` <span class="muted small" title="webapp ${esc(mine)}">≠ webapp</span>` : ""}` : "—";
    return `<tr class="plain" data-agent="${esc(a.name)}"><td><b>${esc(a.name)}</b></td><td>${stav}${ldShipChip(a.live && a.live.ship)}</td><td>${verzia}</td>
      <td>${platformy}</td><td>${ldCodeUpdateCell(a)}</td>
      <td class="ld-actions">
        <label class="inline small" title="preskočiť bránu: kód sa vymení, aj keď nasadenia obchodujú alebo majú pozíciu — MT5 terminál sa reštartuje s pozíciou u brokera"><input type="checkbox" class="ld-force"> aj s otvorenými pozíciami</label>
        <button class="small" data-update="1" ${dis} title="nasadiť commit tejto webapp (${esc(mine || "?")}) na platformy stroja">Aktualizovať kód</button>
        ${nepushnute ? `<span class="chip warn" title="commit ${esc(mine)} je len v tomto klone — agent ho pri aktualizácii zo GitHubu nestiahne; najprv git push origin main">nie je na GitHube</span>` : ""}
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
  const name = $("#ld-d-agent").value;
  const agent = acc && ld.agents.find(a => a.name === name);
  const mine = lv.deploy && lv.deploy.version ? String(lv.deploy.version) : "";
  const cs = agent && agent.live && agent.live.code_state && agent.live.code_state[acc.platform];
  if (!acc || !agent || !mine || !cs || cs.state === "ok") { box.hidden = true; box.textContent = ""; return; }
  const pushnut = lv.deploy && lv.deploy.pushed === false ? ` Commit ${mine.slice(0, 7)} ale nie je na GitHube — stroj si ho nestiahne, najprv git push origin main.` : "";
  box.textContent = (cs.state === "outdated"
    ? `Stroj ${name} má na platforme ${acc.platform} kód ${String(cs.installed).slice(0, 7)}, táto webapp je na ${mine.slice(0, 7)} — po nasadení sa kód na stroji aktualizuje sám (stav v sekcii Stroje).`
    : `Stroj ${name} nehlási, z akého commitu je kód na platforme ${acc.platform} (installed.json chýba) — po nasadení sa kód na stroji aktualizuje sám (stav v sekcii Stroje).`) + pushnut;
  box.hidden = false;
}

/** Polia s `data-ld-only="<platforma>"` v kontajneri: viditeľné len pre danú platformu. */
function ldShowPlatform(container, platform) {
  for (const el of container.querySelectorAll("[data-ld-only]")) el.hidden = el.dataset.ldOnly !== platform;
}

function renderLiveDeploy() {
  const deps = ld.deployments;
  const key = JSON.stringify([ld.admin, ld.accounts, Object.keys(ld.profiles), ld.agents, lv.deploy && lv.deploy.version, lv.deploy && lv.deploy.pushed,
    deps.map(d => { const l = ldLive(d); return [d.id, d.mode, d.active, d.config_hash, d.profile, d.applied, l.alive, l.state, l.last_bar_ms, l.seen, d.code_state]; })]);
  if (key !== ld.key) {
    ld.key = key;
    renderLdDeployments();
    renderLiveAccounts(deps);
    renderLiveAgents();
    // profily stratégií v tabuľke — po načítaní sa riadky prekreslia s celou ponukou
    for (const s of new Set(deps.map(d => d.strategy))) ldLoadProfiles(s).catch(() => {});
  }
  if (!ld.formsReady) { ldSetupForms(); ld.formsReady = true; }
  ldFillFormSelects();
  ldCodeHint();
}

/** Stav nasadenia na súhrn skupiny a skrývanie — to isté rozhodovanie ako `ldStatusChip`. */
function ldState(dep) {
  const a = dep.applied;
  if (!dep.active) return a && a.status === "removed" ? "removed" : "removing";
  if (a && a.status === "error") return "error";
  if (!a || a.config_hash !== dep.config_hash || a.mode !== dep.mode || a.status === "pending") return "pending";
  const live = ldLive(dep);
  if (live.state === "closed") return "closed";
  return live.alive ? "live" : "ok";
}

// Skupiny tabuľky nasadení: jeden účet z hubu, ako pri tabuľke inštancií — hlavička nesie súhrn, predvolene
// je zbalená a rozbalené si pamätá prehliadač. Odstránené nasadenia (agent ich z platformy už zmazal) sa
// skrývajú, ukáže ich odkaz pod tabuľkou.
const LD_EXPANDED_KEY = "tradebot.live.ld.expanded";

function ldExpandedSave() {
  try { localStorage.setItem(LD_EXPANDED_KEY, JSON.stringify([...ld.expanded])); } catch (_) { /* súkromné okno */ }
}

function ldToggleGroup(key) {
  if (ld.expanded.has(key)) ld.expanded.delete(key); else ld.expanded.add(key);
  ldExpandedSave();
  renderLdDeployments();
}

const LD_GROUP_CHIPS = [
  ["live", "ok", "živé", "inštancia žije"], ["closed", "ok", "trh zatvorený", "platforma pinguje, ale bary nechodia"],
  ["pending", "warn", "čaká", "agent ešte neaplikoval profil alebo režim"], ["error", "bad", "chyba", "chyba pri aplikovaní"],
  ["ok", "", "ok", "aplikované, spool je ticho"], ["removing", "warn", "odstraňuje sa", "čaká, kým agent inštanciu z platformy odstráni"],
  ["removed", "", "odstránené", "agent inštanciu z platformy odstránil"],
];

function ldGroupRow(key, members, collapsed) {
  const acc = ld.accounts.find(a => a.id === key) || {};
  const stavy = {};
  for (const d of members) { const s = ldState(d); stavy[s] = (stavy[s] || 0) + 1; }
  const chips = LD_GROUP_CHIPS.filter(([s]) => stavy[s]).map(([s, cls, txt, title]) =>
    `<span class="chip ${cls}" title="${esc(title)}">${stavy[s]} ${esc(s === "live" && stavy[s] > 4 ? "živých" : txt)}</span>`);
  const cs = members.filter(d => d.active).map(d => d.code_state && d.code_state.state);
  const stary = cs.filter(s => s === "outdated").length;
  const kod = !cs.length ? "—" : stary ? `<span class="chip warn" title="${stary} z ${cs.length} aktívnych nasadení má na platforme starší kód">${stary} zastaraný</span>`
    : cs.every(s => s === "ok") ? `<span class="chip ok">aktuálny</span>` : `<span class="muted">—</span>`;
  const bar = Math.max(0, ...members.map(d => Number(ldLive(d).last_bar_ms) || 0));
  const plat = LD_PLATFORMS[acc.platform];
  const n = action => members.filter(LD_GROUP_ACTIONS[action].pick).length;
  const btn = (action, cls, txt, title) => {
    const k = n(action);
    return `<button class="small ${cls}" data-group-action="${action}" ${ld.admin && k ? "" : "disabled"} title="${esc(title)} (${k}) — najprv sa opýta">${txt} všetky</button>`;
  };
  return `<tr class="ld-group" data-group="${esc(key)}" title="${collapsed ? "rozbaliť" : "zbaliť"} účet">
    <td><span class="live-caret">${collapsed ? "▸" : "▾"}</span>${chips.join(" ") || "—"}</td>
    <td title="účet ${esc(key)}"><b>${esc(acc.label || key)}</b> <span class="muted small">${esc(plat ? plat.title : acc.platform || "")}</span>
      <span class="chip" title="nasadení na účte">${members.length}</span>
      <div class="muted small">${liveUniqCell(members.map(d => d.agent), 2)}</div></td>
    <td>${liveUniqCell(members.map(d => d.strategy), 2)}</td>
    <td><b>${liveUniqCell(members.map(d => d.symbol))}</b></td>
    <td>${liveUniqCell(members.map(d => d.tf ? d.tf + "m" : ""))}</td>
    <td>${liveUniqCell(members.map(d => d.profile), 1)}</td>
    <td>${liveUniqCell(members.filter(d => d.active).map(d => LD_MODE_LABEL[d.mode] || d.mode), 3)}</td>
    <td></td><td>${kod}</td><td></td>
    <td title="${bar ? utc(bar) + " UTC — najčerstvejší bar účtu" : ""}">${bar ? liveAge(bar, lv.now) : "—"}</td>
    <td class="ld-actions">
      ${btn("paused", "", "pauza", "pozastaviť obchodujúce nasadenia účtu")}
      ${btn("flatten", "danger", "flatten", "zrušiť čakajúce vstupy a zavrieť pozície všetkých aktívnych nasadení účtu")}
      ${btn("delete", "ghost danger", "odstrániť", "odstrániť všetky aktívne nasadenia účtu z platformy")}
    </td></tr>`;
}

function renderLdDeployments() {
  if (!ld.expanded) {
    try { ld.expanded = new Set(JSON.parse(localStorage.getItem(LD_EXPANDED_KEY) || "[]")); } catch (_) { ld.expanded = new Set(); }
  }
  const accById = Object.fromEntries(ld.accounts.map(a => [a.id, a]));
  const deps = ld.deployments;
  const instances = new Set(lv.instances.map(i => i.id));
  const odstranene = deps.filter(d => ldState(d) === "removed");
  const list = ld.showRemoved ? deps : deps.filter(d => ldState(d) !== "removed");
  const st = $("#ld-removed");
  st.hidden = !odstranene.length;
  st.innerHTML = odstranene.length ? `<a href="#">${ld.showRemoved ? "skryť" : "ukázať"} ${ldPocet(odstranene.length, "odstránené nasadenie", "odstránené nasadenia", "odstránených nasadení")}</a> — agent ich z platformy už zmazal, na hube ostávajú do zmazania` : "";
  if (odstranene.length) st.querySelector("a").onclick = e => { e.preventDefault(); ld.showRemoved = !ld.showRemoved; renderLdDeployments(); };
  $("#ld-dep-count").textContent = deps.length ? String(deps.filter(d => d.active).length) : "";
  $("#ld-empty").hidden = !!deps.length;
  $("#ld-deployments").parentElement.hidden = !list.length;
  const groups = new Map();
  for (const d of list) {
    if (!groups.has(d.account)) groups.set(d.account, []);
    groups.get(d.account).push(d);
  }
  const fold = $("#ld-fold-all"), vsetky = [...groups.keys()].every(k => !ld.expanded.has(k));
  fold.hidden = groups.size < 2;
  fold.textContent = vsetky ? "rozbaliť všetky" : "zbaliť všetky";
  fold.onclick = () => {
    for (const k of groups.keys()) { if (vsetky) ld.expanded.add(k); else ld.expanded.delete(k); }
    ldExpandedSave();
    renderLdDeployments();
  };
  $("#ld-deployments tbody").innerHTML = [...groups].map(([k, members]) => {
    const zbalena = !ld.expanded.has(k);
    return ldGroupRow(k, members, zbalena) + (zbalena ? "" : members.map(d => ldDeploymentRow(d, accById, instances)).join(""));
  }).join("");
  for (const tr of $$("#ld-deployments tbody tr[data-group]")) {
    tr.onclick = () => ldToggleGroup(tr.dataset.group);
    for (const b of tr.querySelectorAll("button[data-group-action]")) {
      b.onclick = e => { e.stopPropagation(); ldGroupAction(tr.dataset.group, b.dataset.groupAction); };
    }
  }
  for (const tr of $$("#ld-deployments tbody tr[data-dep]")) {
    const id = tr.dataset.dep;
    for (const b of tr.querySelectorAll("button[data-mode]")) b.onclick = () => ldSetMode(id, b.dataset.mode);
    const del = tr.querySelector("button[data-del]"); if (del) del.onclick = () => ldDelete(id);
    const sel = tr.querySelector("select.ld-profile"); if (sel) sel.onchange = () => ldSetProfile(id, sel);
    const a = tr.querySelector("a[data-inst]"); if (a) a.onclick = e => { e.preventDefault(); openLiveDetail(a.dataset.inst); };
  }
}

function ldDeploymentRow(d, accById, instances) {
  const acc = accById[d.account] || {};
  const live = ldLive(d);
  const dis = ld.admin && d.active ? "" : "disabled";
  const inst = instances.has(d.instance)
    ? `<a href="#" data-inst="${esc(d.instance)}" title="otvoriť detail inštancie">${esc(d.instance)}</a>`
    : `<span class="muted" title="v zrkadle zatiaľ nie je">${esc(d.instance)}</span>`;
  return `<tr class="plain ld-member" data-dep="${esc(d.id)}">
    <td>${ldStatusChip(d)}</td>
    <td title="účet ${esc(d.account)} na stroji ${esc(d.agent || "?")}">${esc(acc.label || d.account)} <span class="muted small">${esc(d.agent || "")}</span></td>
    <td>${esc(d.strategy)}${d.slot ? ` <span class="chip" title="slot nasadenia v id inštancie">${esc(d.slot)}</span>` : ""}${d.own_terminal ? ` <span class="muted small" title="vlastný (portable) terminál len pre toto nasadenie">vlastný terminál</span>` : ""}</td><td><b>${esc(d.symbol)}</b>${ldRouteChip(d, accById)}</td><td>${d.tf}m</td>
    <td><select class="small ld-profile" ${dis} title="zmena profilu: aplikuje sa, až keď je stratégia bez pozície">${ldProfileOptions(d.strategy, d.profile)}</select></td>
    <td><span class="chip ${d.mode === "enabled" ? "ok" : (d.mode === "flatten" ? "bad" : "warn")}">${esc(LD_MODE_LABEL[d.mode] || d.mode)}</span></td>
    <td>${ldAppliedCell(d)}</td>
    <td>${ldCodeChip(d.code_state, d.version)}</td>
    <td>${inst}${live.host ? ` <span class="muted small">${esc(live.host)}</span>` : ""}</td>
    <td title="${live.last_bar_ms ? utc(live.last_bar_ms) + " UTC" : ""}">${live.last_bar_ms ? liveAge(live.last_bar_ms, lv.now) : "—"}</td>
    <td class="ld-actions">
      ${d.mode === "enabled" ? `<button class="small" data-mode="paused" ${dis} title="nové vstupy sa neposielajú; SL/TP bežia ďalej">pauza</button>`
                             : `<button class="small" data-mode="enabled" ${dis}>zapnúť</button>`}
      <button class="small danger" data-mode="flatten" ${dis} title="zrušiť čakajúce vstupy a zavrieť pozíciu, potom pauza">flatten</button>
      <button class="small ghost danger" data-del="1" ${ld.admin ? "" : "disabled"} title="${d.active ? "vypnúť (agent odstráni z platformy), po potvrdení zmazať" : "zmazať z hubu"}">${d.active ? "odstrániť" : "zmazať"}</button>
    </td></tr>`;
}

/** Route do MT5 exekútora (docs/ROUTING.md): kam idú ordery a stav exekútora z posledného pingu inštancie (`hb.route`). */
const LD_ROUTE_STATE = { ok: ["ok", "exekútor ok"], no_executor: ["bad", "exekútor nebeží"], stale: ["bad", "exekútor neodpovedá"],
  disconnected: ["bad", "MT5 bez spojenia"], trade_disabled: ["bad", "AutoTrading vypnutý"], symbol_missing: ["bad", "symbol chýba"],
  account_mismatch: ["bad", "iný účet"], netting_unsupported: ["bad", "netting účet"], route_pending: ["warn", "čaká na exekútor"] };
function ldRouteChip(d, accById) {
  const r = d.route;
  if (!r) return "";
  if (r.error) return `<div class="small"><span class="chip bad" title="${esc(r.error)}">route poškodená</span></div>`;
  const acc = accById[r.account] || {};
  const inst = lv.instances.find(i => i.id === d.instance);
  // stav route len z čerstvého pingu živej inštancie — mŕtva inštancia nesmie ukazovať posledné „ok"
  const hb = inst && inst.hb;
  const fresh = !!hb && Number(lv.now) > 0 && liveAlive(inst) && Number(hb.t) > 0 && lv.now - Number(hb.t) <= LIVE_HB_MS;
  const st = fresh ? hb.route : null;
  const [cls, text] = st ? (LD_ROUTE_STATE[st] || ["", st])
    : ["", inst ? "stav neznámy — inštancia nepinguje" : "stav neznámy — inštancia nebeží"];
  const qty = r.qty && r.qty.mode === "fixed" ? `${r.qty.lots} lot/kontrakt` : "objem podľa hodnoty bodu";
  // prečo exekútor nebeží: hlásenie agenta k jeho grafu (chýba MT5 driver, terminál, inštalácia)
  const exErr = d.executor && d.executor.status === "error" ? d.executor.error : "";
  return `<div class="small" title="ordery idú do MT5 exekútora na účte ${esc(r.account)}${r.to ? ` (${esc(r.to)})` : ""}; ceny ${esc(r.price || "basis")}, ${esc(qty)}">`
    + `→ MT5 <b>${esc(r.symbol)}</b> <span class="muted">${esc(acc.label || r.account)}</span>`
    + (d.active ? ` <span class="chip ${cls}">${esc(text)}</span>` : "")
    + (exErr ? ` <span class="chip bad" title="${esc(exErr)}">exekútor: ${esc(exErr.length > 60 ? exErr.slice(0, 57) + "…" : exErr)}</span>` : "")
    + `</div>`;
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

/** Nasadenia účtu, ktoré na platforme bežia alebo majú bežať (aktívne) — tie bránia zmazaniu účtu
 *  a po úprave prihlásenia sa reštartujú. */
function ldActiveOn(accId) { return ld.deployments.filter(d => d.account === accId && d.active); }

/** „1 nasadenie / 2 nasadenia / 5 nasadení" — slovenský tvar podľa počtu. */
function ldPocet(n, jeden, dva, pat) { return `${n} ${n === 1 ? jeden : (n >= 2 && n <= 4 ? dva : pat)}`; }

/** Prehľad „kde beží“: každé nasadenie účtu so stavom, strojom a režimom. */
function ldAccountUsage(a, deps) {
  const mine = deps.filter(d => d.account === a.id);
  if (!mine.length) return `<span class="muted">nikde</span>`;
  return mine.map(d => `<div class="small" style="white-space:nowrap">${ldStatusChip(d)} ${esc(d.strategy)} <b>${esc(d.symbol)}</b> ${d.tf}m
    · <span title="stroj (agent hubu)">${esc(d.agent || "?")}</span>${d.active ? ` · ${esc(LD_MODE_LABEL[d.mode] || d.mode)}` : ""}</div>`).join("");
}

function ldSecretCell(a) {
  if (!(LD_PLATFORMS[a.platform] || {}).password) return `<span class="muted" title="NinjaTrader sa prihlasuje zapamätaným loginom">—</span>`;
  if (!a.secret) return `<span class="chip warn" title="bez hesla terminál použije prihlásenie, ktoré si pamätá sám">nezadané</span>`;
  if ((a.secret_waiting || []).length) return `<span class="chip warn" title="tieto stroje si heslo ešte neprevzali (príde v najbližšom heartbeate)">čaká: ${esc(a.secret_waiting.join(", "))}</span>`;
  return `<span class="chip ok" title="uložené na hube šifrované; všetky stroje s nasadením ho majú">uložené</span>`;
}

function renderLiveAccounts(deps) {
  const list = ld.accounts;
  $("#ld-acc-count").textContent = list.length ? String(list.length) : "";
  $("#ld-acc-empty").hidden = !!list.length;
  $("#ld-accounts").parentElement.hidden = !list.length;
  $("#ld-accounts tbody").innerHTML = list.map(a => {
    const bezi = ldActiveOn(a.id).length;
    const plat = LD_PLATFORMS[a.platform];
    return `<tr class="plain" data-acc="${esc(a.id)}"><td>${esc(a.label)} <span class="muted small"><code>${esc(a.id)}</code></span></td>
      <td>${esc(plat ? plat.title : a.platform)}</td><td>${esc(a.login)}</td><td>${esc(a.server || "—")}</td>
      <td>${ldSecretCell(a)}</td><td>${ldAccountUsage(a, deps)}</td>
      <td style="white-space:nowrap"><button class="small" data-edit="1" ${ld.admin ? "" : "disabled"}>upraviť</button>
        <button class="small ghost danger" data-del="1" ${ld.admin && !bezi ? "" : "disabled"}
          title="${bezi ? `na účte beží ${ldPocet(bezi, "nasadenie", "nasadenia", "nasadení")} — najprv ich odstráň (tabuľka Nasadenia)` : "zmazať účet"}">zmazať</button></td></tr>`;
  }).join("");
  for (const tr of $$("#ld-accounts tbody tr")) {
    tr.querySelector("button[data-del]").onclick = () => ldDeleteAccount(tr.dataset.acc);
    tr.querySelector("button[data-edit]").onclick = () => ldEditAccount(tr.dataset.acc);
  }
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
  selA.innerHTML = ld.accounts.map(a => `<option value="${esc(a.id)}">${esc(a.label)} · ${esc((LD_PLATFORMS[a.platform] || {}).title || a.platform)}</option>`).join("")
    || `<option value="">— najprv pridaj účet —</option>`;
  if (curA && ld.accounts.some(a => a.id === curA)) selA.value = curA;
  selA.onchange = () => { ldFillAgents(); ldCodeHint(); ldFormDefaults(); };
  ldFillAgents();
  // ordery do MT5 exekútora (NinjaTrader): MT5 účty hubu
  const selR = $("#ld-d-route"), curR = selR.value;
  selR.innerHTML = `<option value="">tu — na účte nasadenia</option>`
    + ld.accounts.filter(a => a.platform === "mt5").map(a => `<option value="${esc(a.id)}">MT5 exekútor · ${esc(a.label)}</option>`).join("");
  if (curR && ld.accounts.some(a => a.id === curR)) selR.value = curR;
  selR.onchange = ldFillAgents;   // route chce na stroji aj MT5 driver (exekútor beží tam, kde NinjaTrader)
  $("#ld-d-route-qty").onchange = ldRouteFields;
  ldFillAgents();
  // stratégie z /api/meta — na live (NinjaTrader aj MT5) beží len C# jadro
  const selS = $("#ld-d-strategy");
  if (!selS.options.length && state.meta && state.meta.strategies) {
    // webapp pred reštartom (starý /api/meta) príznak `csharp` nemá — vtedy všetky
    const vie = state.meta.strategies.some(s => "csharp" in s);
    const cs = state.meta.strategies.filter(s => !vie || s.csharp);
    selS.innerHTML = cs.map(s => `<option value="${esc(s.key)}">${esc(s.title || s.key)}</option>`).join("")
      || `<option value="">— žiadna stratégia s C# jadrom —</option>`;
    selS.onchange = () => ldFormProfiles();
    $("#ld-d-profile").onchange = () => ldFormDefaults();
    ldFormProfiles();
  }
  for (const b of ["#ld-d-submit", "#ld-a-submit"]) $(b).disabled = !ld.admin;
  const hint = ld.admin ? "" : "len na čítanie (bez admin tokenu)";
  if (!$("#ld-d-status").textContent || !ld.admin) $("#ld-d-status").textContent = hint;
  if (!$("#ld-a-status").textContent || !ld.admin) $("#ld-a-status").textContent = hint;
}

/** Polia route (symbol, objem) len keď ordery idú do MT5; loty len pri pevnom objeme. */
function ldRouteFields() {
  const acc = ld.accounts.find(a => a.id === $("#ld-d-account").value);
  const nt = !!acc && acc.platform === "ninjatrader";
  const routed = nt && !!$("#ld-d-route").value;
  for (const el of $$("#ld-deploy-box .ld-route-only")) el.hidden = !routed;
  if (routed && $("#ld-d-route-qty").value !== "fixed") $("#ld-d-route-lots").closest("label").hidden = true;
  // ponuka symbolov z heartbeatu exekútora MT5 účtu (Market Watch, hlási agent); hub iný symbol odmietne
  const mt5 = routed ? ld.accounts.find(a => a.id === $("#ld-d-route").value) : null;
  const names = (mt5 && Array.isArray(mt5.exec_symbols)) ? mt5.exec_symbols : [];
  $("#ld-d-route-symbols").innerHTML = names.map(n => `<option value="${esc(n)}"></option>`).join("");
  $("#ld-d-route-symbol").title = names.length ? `exekútor účtu hlási ${names.length} symbolov (Market Watch)`
    : "exekútor účtu ešte nehlásil symboly — hub symbol neoverí";
}

/** Stroje do „Nasadiť": agenti s driverom platformy vybraného účtu (online prví), pri route do MT5 aj s driverom
 *  MT5 — exekútor beží na stroji NinjaTradera; polia terminálu len pri MT5. */
function ldFillAgents() {
  const acc = ld.accounts.find(a => a.id === $("#ld-d-account").value);
  const platform = acc ? acc.platform : "";
  ldShowPlatform($("#ld-deploy-box"), platform);
  ldRouteFields();
  const routed = platform === "ninjatrader" && !!($("#ld-d-route") || {}).value;
  const need = [platform, routed ? "mt5" : ""].filter(Boolean);
  const sel = $("#ld-d-agent"), cur = sel.value;
  const agents = ldLiveAgents().filter(a => need.every(p => (a.live.drivers || []).includes(p)));
  const title = need.map(p => (LD_PLATFORMS[p] || {}).title || p).join(" + ") || "platformou";
  sel.innerHTML = agents.map(a => `<option value="${esc(a.name)}">${esc(a.name)}${a.online ? "" : " (offline)"}</option>`).join("")
    || `<option value="">— žiadny stroj s ${esc(title)} —</option>`;
  if (cur && agents.some(a => a.name === cur)) sel.value = cur;
  sel.onchange = () => { ldTerminalHint(); ldCodeHint(); };
  $("#ld-d-own").onchange = ldTerminalHint;
  ldTerminalHint();
}

/** MT5: účet beží na stroji v jednom spoločnom termináli — keď už tam nejaké nasadenie má, nové ide do toho istého;
 *  s „vlastný terminál" dostane stratégia vlastnú portable kópiu a terminál/portable sa nevypĺňa. */
function ldTerminalHint() {
  const box = $("#ld-d-terminal-hint");
  const acc = ld.accounts.find(a => a.id === $("#ld-d-account").value);
  const agent = $("#ld-d-agent").value;
  const term = $("#ld-d-terminal"), port = $("#ld-d-portable");
  if ($("#ld-d-own").checked && acc && (LD_PLATFORMS[acc.platform] || {}).terminal) {
    term.disabled = port.disabled = true;
    box.textContent = `Vlastný terminál: driver na stroji ${agent || "?"} spraví portable kópiu terminálu len pre túto stratégiu `
      + `(tester/live/mt5/<účet>/units/<nasadenie>/). Jej pridanie ani odobratie nereštartuje ostatné stratégie účtu.`;
    box.hidden = false;
    return;
  }
  const iny = acc && (LD_PLATFORMS[acc.platform] || {}).terminal
    && ld.deployments.find(d => d.account === acc.id && d.agent === agent && d.active && !d.own_terminal);
  term.disabled = port.disabled = !!iny;
  if (iny) {
    term.value = iny.terminal || ""; port.checked = !!iny.portable;
    box.textContent = `Účet už na stroji ${agent} beží v termináli ${iny.terminal || "nainštalovanom"}${iny.portable ? " (portable)" : ""} — ďalšie nasadenie pôjde do toho istého ako ďalší graf. Pridanie reštartuje terminál so všetkými grafmi účtu (EA si otvorené pozície po štarte prevezme, čakajúce vstupy zruší); bez reštartu ostatných = „vlastný terminál“.`;
    box.hidden = false;
  } else {
    if (term.dataset.locked) { term.value = ""; port.checked = false; }
    box.hidden = true; box.textContent = "";
  }
  term.dataset.locked = iny ? "1" : "";
}

async function ldFormProfiles() {
  const strategy = $("#ld-d-strategy").value, sel = $("#ld-d-profile");
  sel.innerHTML = `<option value="">načítavam…</option>`;
  try {
    const p = await ldLoadProfiles(strategy);
    sel.innerHTML = ldProfileOptions(strategy, p.profiles[0] || "");
  } catch (e) { sel.innerHTML = `<option value="">${esc(e.message)}</option>`; }
  ldFormDefaults();
}

/** Symbol a TF z profilu pre platformu účtu — placeholder polí; prázdne pole = toto pôjde na hub. */
async function ldFormDefaults() {
  const account = $("#ld-d-account").value, strategy = $("#ld-d-strategy").value, profile = $("#ld-d-profile").value;
  const sym = $("#ld-d-symbol"), tf = $("#ld-d-tf");
  const kluc = JSON.stringify([account, strategy, profile]);
  ld.defaultsKey = kluc;
  if (!account || !strategy || !profile) { sym.placeholder = tf.placeholder = "z profilu"; sym.title = tf.title = ""; return; }
  try {
    const d = await api(`/api/live/deploy-defaults?account=${encodeURIComponent(account)}&strategy=${encodeURIComponent(strategy)}&profile=${encodeURIComponent(profile)}`);
    if (ld.defaultsKey !== kluc) return;
    const odkial = { "účet": "už beží na účte", "front-month": "front-month podľa dátumu", "profil": "z inštrumentu profilu" };
    sym.placeholder = d.symbol ? `${d.symbol} (z profilu)` : "zadaj — z profilu sa nedá";
    sym.title = d.symbol ? `${d.symbol}: ${odkial[d.symbol_from] || d.symbol_from || ""}${d.instrument ? ` · ${d.instrument}` : ""}` : (d.symbol_error || "");
    tf.placeholder = d.tf ? `${d.tf} (z profilu)` : "zadaj";
    tf.title = d.tf ? "" : (d.tf_error || "");
  } catch (e) { if (ld.defaultsKey === kluc) { sym.placeholder = tf.placeholder = "z profilu"; sym.title = e.message; } }
}

/** Čo sa stalo s kódom stroja po nasadení (`code_update` z webapp). */
function ldCodeUpdateNote(cu) {
  if (!cu) return "";
  if (cu.requested) return ` · kód na ${cu.agent} sa aktualizuje na ${String(cu.version).slice(0, 7)}${cu.force ? "" : " (brána: ostatné nasadenia stroja musia byť v pauze a bez pozície)"} — stav v sekcii Stroje`;
  if (cu.error) return ` · kód stroja sa neaktualizoval: ${cu.error}`;
  return "";
}

function ldSetupForms() {
  $("#ld-d-submit").onclick = async () => {
    const btn = $("#ld-d-submit"); btn.disabled = true; $("#ld-d-error").hidden = true; $("#ld-d-status").textContent = "posielam na hub…";
    try {
      const acc = ld.accounts.find(a => a.id === $("#ld-d-account").value);
      const mt5 = acc && (LD_PLATFORMS[acc.platform] || {}).terminal;
      const body = { account: $("#ld-d-account").value, agent: $("#ld-d-agent").value, strategy: $("#ld-d-strategy").value,
        symbol: $("#ld-d-symbol").value.trim(), tf: Number($("#ld-d-tf").value) || 0, profile: $("#ld-d-profile").value,
        mode: $("#ld-d-mode").value || "paused", user: ldUser() };
      const own = !!mt5 && $("#ld-d-own").checked;
      Object.assign(body, { own_terminal: own, slot: mt5 ? $("#ld-d-slot").value.trim() : "",
        terminal: mt5 && !own ? $("#ld-d-terminal").value.trim() : "", portable: mt5 && !own ? $("#ld-d-portable").checked : false });
      if (acc && acc.platform === "ninjatrader" && $("#ld-d-route").value) {
        const mode = $("#ld-d-route-qty").value;
        body.route = { via: "mt5", account: $("#ld-d-route").value, symbol: $("#ld-d-route-symbol").value.trim(),
          qty: mode === "fixed" ? { mode, lots: Number($("#ld-d-route-lots").value) || 0 } : { mode } };
      }
      if (!body.account) throw new Error("vyber účet");
      if (!body.agent) throw new Error("vyber stroj, na ktorom má stratégia bežať");
      if (!body.strategy) throw new Error("vyber stratégiu s C# jadrom");
      const d = await api("/api/live/deployments", { method: "POST", body: JSON.stringify(body) });
      $("#ld-d-status").textContent = `nasadené: ${d.symbol} ${d.tf}m → ${d.instance} na ${d.agent} (agent si to vezme v najbližšom heartbeate${d.mode === "paused" ? "; štartuje pauznuté — zapni v tabuľke" : ""})${ldCodeUpdateNote(d.code_update)}`;
      $("#ld-d-symbol").value = ""; $("#ld-d-tf").value = ""; $("#ld-d-slot").value = ""; $("#ld-d-route-symbol").value = "";
      await loadLiveDeploy();
    } catch (e) { $("#ld-d-error").textContent = e.message; $("#ld-d-error").hidden = false; $("#ld-d-status").textContent = ""; }
    finally { btn.disabled = !ld.admin; }
  };
  $("#ld-a-platform").onchange = () => ldShowPlatform($("#ld-acc-box"), $("#ld-a-platform").value);
  ldShowPlatform($("#ld-acc-box"), $("#ld-a-platform").value);
  $("#ld-a-submit").onclick = ldSaveAccount;
  $("#ld-a-cancel").onclick = () => ldResetAccountForm();
  $("#ld-audit-box").ontoggle = () => { if ($("#ld-audit-box").open) loadLiveAudit().catch(() => {}); };
  for (const id of ["#ld-a-label", "#ld-a-login-mt5", "#ld-a-login-nt"]) $(id).oninput = ldAccountIdHint;
  ldAccountIdHint();
}

/** Login a server z polí platformy (MT5 číslo účtu + server, NT meno účtu + pripojenie). */
function ldAccountForm() {
  const platform = $("#ld-a-platform").value;
  const sfx = platform === "mt5" ? "mt5" : "nt";
  return { platform, label: $("#ld-a-label").value.trim(), login: $(`#ld-a-login-${sfx}`).value.trim(),
           server: $(`#ld-a-server-${sfx}`).value.trim(),
           symbols: platform === "mt5" ? ldParseAliases($("#ld-a-symbols").value) : null,
           password: (LD_PLATFORMS[platform] || {}).password ? $("#ld-a-password").value : "" };
}

/** `NAS100=US100.cash, XAUUSD=XAUUSD.r` → {NAS100: "US100.cash", …} (aliasy symbolov MT5 účtu pre route). */
function ldParseAliases(text) {
  const out = {};
  for (const part of String(text || "").split(/[,;\n]/)) {
    const [k, v] = part.split("=").map(x => (x || "").trim());
    if (k && v) out[k] = v;
  }
  return out;
}
function ldAliasesText(map) { return Object.entries(map || {}).map(([k, v]) => `${k}=${v}`).join(", "); }

function ldResetAccountForm(status = "") {
  ld.editing = null;
  for (const id of ["#ld-a-label", "#ld-a-id", "#ld-a-login-mt5", "#ld-a-server-mt5", "#ld-a-login-nt", "#ld-a-server-nt", "#ld-a-password", "#ld-a-symbols"]) $(id).value = "";
  $("#ld-a-id").disabled = false; $("#ld-a-platform").disabled = false;
  $("#ld-a-title").textContent = "Pridať účet";
  $("#ld-a-submit").textContent = "Pridať účet";
  $("#ld-a-cancel").hidden = true;
  $("#ld-a-password").placeholder = "";
  $("#ld-a-error").hidden = true;
  $("#ld-a-status").textContent = status;
  ldShowPlatform($("#ld-acc-box"), $("#ld-a-platform").value);
  ldAccountIdHint();
}

/** „upraviť": formulár sa naplní účtom; id sa nemení, platforma len kým účet nemá nasadenia. */
function ldEditAccount(id) {
  const a = ld.accounts.find(x => x.id === id);
  if (!a) return;
  ldResetAccountForm();
  ld.editing = id;
  const sfx = a.platform === "mt5" ? "mt5" : "nt";
  $("#ld-a-platform").value = a.platform;
  $("#ld-a-platform").disabled = ld.deployments.some(d => d.account === id);
  $("#ld-a-label").value = a.label || "";
  $("#ld-a-id").value = a.id; $("#ld-a-id").disabled = true;
  $(`#ld-a-login-${sfx}`).value = a.login || "";
  $(`#ld-a-server-${sfx}`).value = a.server || "";
  $("#ld-a-password").placeholder = a.secret ? "uložené — nechať prázdne = nemeniť" : "";
  $("#ld-a-symbols").value = ldAliasesText(a.symbols);
  $("#ld-a-title").textContent = `Upraviť účet ${a.label}`;
  $("#ld-a-submit").textContent = "Uložiť zmeny";
  $("#ld-a-cancel").hidden = false;
  ldShowPlatform($("#ld-acc-box"), a.platform);
  $("#ld-acc-box").open = true;
  $("#ld-acc-box").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function ldSaveAccount() {
  const btn = $("#ld-a-submit"); $("#ld-a-error").hidden = true;
  const f = ldAccountForm();
  try {
    if (!f.login) throw new Error(f.platform === "mt5" ? "zadaj číslo účtu" : "zadaj meno účtu v NinjaTraderi");
    if (!ld.editing) {
      btn.disabled = true; $("#ld-a-status").textContent = "posielam na hub…";
      const body = { ...f, id: $("#ld-a-id").value.trim() || null, password: f.password || null, user: ldUser() };
      const a = await api("/api/live/accounts", { method: "POST", body: JSON.stringify(body) });
      ldResetAccountForm(`účet ${a.id} pridaný${a.secret ? " — heslo je na hube, stroje ho dostanú s prvým nasadením" : ""}`);
      await loadLiveDeploy();
      return;
    }
    const a = ld.accounts.find(x => x.id === ld.editing);
    if (!a) throw new Error("účet už na hube nie je");
    const zmena = {};
    for (const k of ["platform", "label", "login", "server"]) if (f[k] !== (a[k] || "")) zmena[k] = f[k];
    if (f.password) zmena.password = f.password;
    if (f.symbols && JSON.stringify(f.symbols) !== JSON.stringify(a.symbols || {})) zmena.symbols = f.symbols;
    if (!Object.keys(zmena).length) { ldResetAccountForm("bez zmeny"); return; }
    // nové prihlásenie (login, server, heslo) = stroje inštancie zastavia, prihlásia sa znova a spustia
    const prihlasenie = ["platform", "login", "server", "password"].some(k => k in zmena);
    const bezi = ldActiveOn(a.id);
    if (prihlasenie && bezi.length) {
      const zoznam = bezi.map(d => `• ${d.strategy} ${d.symbol} ${d.tf}m na ${d.agent} (${LD_MODE_LABEL[d.mode] || d.mode})`).join("\n");
      if (!confirm(`Na účte „${a.label}“ beží ${ldPocet(bezi.length, "inštancia stratégie", "inštancie stratégií", "inštancií stratégií")}:\n${zoznam}\n\n`
        + `Po uložení sa zastavia, účet sa na strojoch upraví (nové prihlásenie) a inštancie sa znova spustia. `
        + `Otvorené pozície u brokera sa tým nezatvárajú (na to je flatten). Pokračovať?`)) return;
    }
    btn.disabled = true; $("#ld-a-status").textContent = "ukladám na hub…";
    await api(`/api/live/accounts/${encodeURIComponent(a.id)}`, { method: "PATCH", body: JSON.stringify({ ...zmena, user: ldUser() }) });
    ldResetAccountForm(`účet ${a.id} upravený${prihlasenie && bezi.length ? " — stroje inštancie reštartujú v najbližšom heartbeate" : ""}`);
    await loadLiveDeploy();
  } catch (e) { $("#ld-a-error").textContent = e.message; $("#ld-a-error").hidden = false; $("#ld-a-status").textContent = ""; }
  finally { btn.disabled = !ld.admin; }
}

/** Id účtu tak, ako ho spraví hub z názvu (`_slug` v `tradebot/live/deploy.py`): malé písmená, číslice, `.-_`;
 *  ukáže sa ako placeholder políčka „Id účtu“, kým ho človek nezadá sám. */
function ldSlug(text) {
  return String(text || "").trim().toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^[-._]+|[-._]+$/g, "") || "ucet";
}

function ldAccountIdHint() {
  const el = $("#ld-a-id");
  if (el && !ld.editing) el.placeholder = ldSlug($("#ld-a-label").value || ldAccountForm().login);
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

/** Hromadná akcia na skupine (účte) v tabuľke nasadení: vždy sa najprv opýta so zoznamom nasadení, ktorých sa
 *  týka; potom ide nasadenie po nasadení rovnakým volaním ako tlačidlá v riadku a chyby zhrnie na konci. */
const LD_GROUP_ACTIONS = {
  paused: { pick: d => d.active && d.mode === "enabled", what: "Pozastaviť",
            note: "Nové vstupy sa neposielajú; SL/TP otvorených pozícií bežia ďalej." },
  flatten: { pick: d => d.active && d.mode !== "flatten", what: "FLATTEN",
             note: "Zrušia sa všetky čakajúce vstupy a zavrú otvorené pozície u brokera, potom pauza." },
  delete: { pick: d => d.active, what: "ODSTRÁNIŤ",
            note: "Agent inštancie z platformy odstráni; otvorené pozície sa nezatvárajú (na to je flatten). Z hubu sa dajú zmazať až po potvrdení agentom." },
};

async function ldGroupAction(key, action) {
  const spec = LD_GROUP_ACTIONS[action];
  const acc = ld.accounts.find(a => a.id === key) || {};
  const deps = ld.deployments.filter(d => d.account === key && spec.pick(d));
  if (!deps.length) return;
  const zoznam = deps.map(d => `  • ${d.symbol} ${d.tf}m — ${d.strategy}${d.slot ? ` (${d.slot})` : ""} · ${LD_MODE_LABEL[d.mode] || d.mode}`).join("\n");
  if (!confirm(`${spec.what} ${ldPocet(deps.length, "nasadenie", "nasadenia", "nasadení")} na účte „${acc.label || key}“?\n\n${zoznam}\n\n${spec.note}\n\nNaozaj pokračovať?`)) return;
  const chyby = [];
  for (const d of deps) {
    try {
      if (action === "delete") {
        await api(`/api/live/deployments/${encodeURIComponent(d.id)}?force=false&user=${encodeURIComponent(ldUser() || "")}`, { method: "DELETE" });
      } else {
        await api(`/api/live/deployments/${encodeURIComponent(d.id)}`, { method: "PATCH", body: JSON.stringify({ mode: action, user: ldUser() }) });
      }
    } catch (e) { chyby.push(`${d.symbol} ${d.tf}m ${d.strategy}: ${e.message}`); }
  }
  await loadLiveDeploy().catch(() => {});
  if (chyby.length) ldFail(new Error(`${chyby.length} z ${deps.length} zlyhalo — ${chyby.join("; ")}`));
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
  if (!acc) return;
  const bezi = ldActiveOn(id);
  if (bezi.length) { ldFail(new Error(`na účte „${acc.label}“ beží ${ldPocet(bezi.length, "nasadenie", "nasadenia", "nasadení")} — najprv ich odstráň`)); return; }
  if (!confirm(`Zmazať účet „${acc.label}“ (${acc.id})? Heslo sa z hubu zmaže.`)) return;
  try {
    await api(`/api/live/accounts/${encodeURIComponent(id)}?user=${encodeURIComponent(ldUser() || "")}`, { method: "DELETE" });
    if (ld.editing === id) ldResetAccountForm();
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
