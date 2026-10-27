/* TradeBot Backtester — Fronta behov, hub (distribuované počítanie) a živý log. */
"use strict";

// --------------------------------------------------------------------------- //
// Fronta
// --------------------------------------------------------------------------- //

/** Fronta každé 2 s, kým niečo beží. Chyba spojenia (reštart webapp, 502) reťaz nesmie zastaviť —
 *  inak by karta navždy ukazovala starý „running" a história by sa po dobehnutí neobnovila (audit N-FE-1). */
async function pollQueue() {
  try {
    await pollQueueOnce();
  } catch (e) {
    const c = $("#queue-count");
    if (c) c.title = `fronta sa nedá načítať (${e.message}) — skúšam znova`;
    clearTimeout(state.pollTimer);
    state.pollTimer = setTimeout(pollQueue, 5000);
  }
}

async function pollQueueOnce() {
  const jobs = await api("/api/queue");
  const cnt = $("#queue-count");
  if (cnt) cnt.title = "";
  // Beh, na ktory caka prop vyzva, uz vo fronte nie je - teda dobehol.
  if (state.propAfterRun && !jobs.some(j => j.id === state.propAfterRun)) {
    const id = state.propAfterRun;
    state.propAfterRun = null;
    runPropForRun(id).catch(e => { const el = $("#nprop-status"); if (el) el.textContent = e.message; });
  }
  const box = $("#queue");
  $("#queue-count").textContent = jobs.length ? String(jobs.length) : "";
  if (!jobs.length) {
    box.innerHTML = `<div class="muted">Nič nebeží.</div>`;
    if (state.pollTimer) { clearTimeout(state.pollTimer); state.pollTimer = null; if (!$("#view-history").hidden) loadRuns(); }
    await refreshLiveLog([]);
    return;
  }
  // Prvky behov sa držia a len aktualizujú — prekreslenie celého HTML každé 2 s by
  // zhodilo pozíciu scrollu v logu a tester by nič nedočítal.
  if (!box.querySelector(".job")) box.innerHTML = "";
  const seen = new Set();
  for (const j of jobs) {
    seen.add(j.id);
    let el = box.querySelector(`.job[data-job="${j.id}"]`);
    if (!el) {
      el = document.createElement("div"); el.className = "job"; el.dataset.job = j.id;
      el.innerHTML = `<div class="head"></div><pre class="live" hidden></pre>`;
      box.append(el);
    }
    const running = j.status === "running";
    // Dva riadky: stav + pár + tlačidlá (nikdy sa nezalomia ani nevytlačia z karty),
    // pod tým poznámka s výpustkou — dlhá poznámka predtým vytlačila ✕ mimo kartu.
    el.querySelector(".head").innerHTML = `<span class="chip ${running ? "warn" : ""}">${j.status}</span>
      <b>${j.settings.pair}</b> <span class="muted">${j.settings.timeframe || "3m"} · ${j.settings.timerange}</span> <span class="spacer"></span>
      <span class="actions">${running ? `<button class="ghost small" data-expand="${j.id}" title="celý log v plnej šírke, s formátovaním">⤢ Log</button>` : ""}
      <button class="ghost small" data-cancel="${j.id}" title="zrušiť beh">✕</button></span>
      ${j.note ? `<div class="note muted" title="${esc(j.note)}">${esc(j.note)}</div>` : ""}`;
    el.querySelector("[data-cancel]").onclick = async () => { await api(`/api/queue/${j.id}/cancel`, { method: "POST" }); pollQueue(); };
    const expand = el.querySelector("[data-expand]");
    if (expand) expand.onclick = () => openLiveLog(j);
    const pre = el.querySelector("pre.live");
    pre.hidden = !running;
    if (running) setLogText(pre, (j.log_tail || []).slice(-12).join("\n"));
  }
  for (const el of box.querySelectorAll(".job")) if (!seen.has(el.dataset.job)) el.remove();
  await refreshLiveLog(jobs);
  clearTimeout(state.pollTimer);
  state.pollTimer = setTimeout(pollQueue, 2000);
}

// --------------------------------------------------------------------------- //
// Hub: distribuované počítanie (docs/HUB.md)
// --------------------------------------------------------------------------- //

const hubChecked = () => !!$("#hub-run")?.checked;

function hubOptions() {
  const w = $("#hub-maxwait").value;
  const cislo = id => { const v = $(id).value; return v === "" ? null : Number(v); };
  return { queue: $("#hub-queue").checked, max_wait_minutes: w === "" ? null : Number(w),
           plan_total: cislo("#hub-plan-total"),
           plan_done: cislo("#hub-plan-done") };
}

/** Trvanie výpočtu (s) — sekundy, minúty, hodiny. */
function fmtDur(s) {
  if (s === null || s === undefined) return "–";
  if (s < 90) return `${Math.round(s)} s`;
  if (s < 5400) return `${Math.round(s / 60)} min`;
  return `${(s / 3600).toFixed(1)} h`;
}

/** Riadok štatistiky agenta: počty hotových (zlyhané v tooltipe) a priemerné časy. */
function hubStatsRow(a) {
  const st = a.stats || {}, bt = st.backtest || {}, ho = st.hyperopt || {};
  const pocet = (k, n) => `<td class="num" title="${k.failed ? `zlyhalo ${k.failed}` : ""}">${n ?? 0}</td>`;
  return `<tr class="plain"><td><b>${esc(a.name)}</b></td>
    ${pocet(bt, bt.done)}<td class="num">${fmtDur(bt.avg_seconds)}</td>
    ${pocet(ho, ho.done)}<td class="num">${fmtDur(ho.avg_seconds)}</td>
    <td class="num">${bt.day_done ?? 0}</td><td class="num">${fmtDur(bt.day_avg_seconds)}</td>
    <td class="num">${ho.day_done ?? 0}</td><td class="num">${fmtDur(ho.day_avg_seconds)}</td></tr>`;
}

/** Zbalená / rozbalená štatistika agentov — pamätá si to prehliadač. */
const HUB_STATS_KEY = "ibs.hubStatsOpen";
function hubStatsBox() {
  const box = $("#hub-stats-box");
  if (!box || box.dataset.ready) return;
  box.dataset.ready = "1";
  try { const v = localStorage.getItem(HUB_STATS_KEY); if (v !== null) box.open = v === "1"; } catch (_) { /* súkromné okno */ }
  box.addEventListener("toggle", () => {
    try { localStorage.setItem(HUB_STATS_KEY, box.open ? "1" : "0"); } catch (_) { /* ignoruj */ }
  });
}

/** Na akom kóde hub beží a či čaká na reštart na novší (samoaktualizácia). */
function renderHubVersion(hub) {
  const el = $("#hub-version");
  const u = hub.update;
  const ver = hub.version || (u && u.version);
  const pe = hub.persist_error;   // hub nevie zapísať state.json (plný disk) — audit N-HUB-3
  el.hidden = !ver && !pe;
  if (!ver && !pe) return;
  if (!ver) {
    el.textContent = "⚠ hub nezapisuje stav"; el.className = "chip warn";
    el.title = `hub nevie zapísať state.json od ${pe.at}: ${pe.error} — po reštarte by zabudol, čo odvtedy pridelil`;
    return;
  }
  const mine = $("#hub-agent-version").textContent;
  let text = `hub ${ver}`, cls = "chip", title = "commit, na ktorom hub beží";
  if (pe) {
    text += " · ⚠ nezapisuje stav"; cls = "chip warn";
    title += `; hub nevie zapísať state.json od ${pe.at}: ${pe.error} — po reštarte by zabudol, čo odvtedy pridelil`;
    el.textContent = text; el.className = cls; el.title = title;
    return;
  }
  if (u && u.pending) {
    text += ` → ${u.pending}`; cls = "chip warn";
    title = `hub má nový kód ${u.pending}: nové výpočty nechá vo fronte a reštartuje sa, keď dobehnú bežiace` +
      (u.waiting_for ? ` (rozpočítané výpočty: ${u.waiting_for})` : "");
  } else if (mine && mine !== ver) {
    title += ` — táto webapp je na ${mine}`;
  }
  if (u && u.last_error) title += `; posledná aktualizácia zlyhala: ${u.last_error}`;
  if (!u) title += " (samoaktualizácia vypnutá)";
  el.textContent = text; el.className = cls; el.title = title;
}

function fmtEta(s) {
  if (s === null || s === undefined) return "–";
  if (s <= 0) return "hneď";
  if (s < 90) return `${Math.round(s)} s`;
  return `${Math.round(s / 60)} min`;
}

/** Dlhé trvanie fronty — minúty, hodiny, dni. */
function fmtLong(s) {
  if (s < 5400) return fmtEta(s);
  if (s < 2 * 86400) return `${(s / 3600).toFixed(1)} h`;
  return `${(s / 86400).toFixed(1)} dňa`;
}

/** Kedy dobehne fronta pri rýchlosti z poslednej hodiny (hub zo staršieho kódu ju nedáva). */
function renderHubQueueEta(t) {
  const el = $("#hub-jobs-eta");
  el.hidden = !t || !t.left;
  if (el.hidden) return;
  const rychlost = `${Math.round(t.per_hour)} hotových/h`;
  if (t.eta_seconds === null || t.eta_seconds === undefined) {
    el.textContent = `dobehne: ? (za poslednú hodinu nič hotové)`; el.className = "chip warn";
  } else {
    const kedy = new Date(Date.now() + t.eta_seconds * 1000);
    const cas = kedy.toLocaleString("sk-SK", { weekday: "short", hour: "2-digit", minute: "2-digit" });
    el.textContent = `dobehne o ~${fmtLong(t.eta_seconds)} (${cas}) · ${rychlost}`; el.className = "chip";
  }
  el.title = `${t.left} živých výpočtov pri rýchlosti hubu za poslednú hodinu (${rychlost}, zlyhané sa nerátajú)`;
}

/** Plány zadávateľov (voliteľné polia pri zadaní na hub): koľko zostáva a kedy to dobehne. */
function renderHubPlans(plans) {
  const box = $("#hub-plans");
  box.hidden = !plans || !plans.length;
  if (box.hidden) return;
  box.querySelector("tbody").innerHTML = plans.map(p => {
    let kedy = "–";
    if (p.left === 0) kedy = '<span class="chip ok">hotový</span>';
    else if (p.eta_seconds !== null && p.eta_seconds !== undefined) {
      const cas = new Date(Date.now() + p.eta_seconds * 1000)
        .toLocaleString("sk-SK", { weekday: "short", hour: "2-digit", minute: "2-digit" });
      kedy = `~${fmtLong(p.eta_seconds)} (${cas})`;
    } else if (p.left === null) kedy = '<span class="muted" title="zadávateľ neuviedol, koľko výpočtov plán má">? (bez „spolu")</span>';
    const tempo = `${Math.round(p.per_hour)} hotových/h ${p.rate_from === "plan" ? "v tomto pláne" : "celý hub (plán za hodinu nič nedokončil)"}`;
    const hotove = `hub ${p.done_hub}${p.done_reported !== null ? `, nahlásené ${p.done_reported}` : ""}${p.failed ? `, zlyhalo ${p.failed}` : ""}`;
    return `<tr class="plain" title="plán od ${esc(p.created || "")}, zadaných na hub ${p.submitted}">
      <td><b>${esc(p.submitter)}</b></td><td>${esc(p.kind || "")}</td>
      <td class="num" title="${esc(hotove)}">${p.done}</td><td class="num">${p.total ?? "?"}</td>
      <td class="num">${p.left ?? "?"}</td><td class="num">${p.live}</td>
      <td title="${esc(tempo)}">${kedy}</td></tr>`;
  }).join("");
}

/** Pri štarte: keď je klon agentom hubu, ukáže sa karta Hub a prepínač „na hube" pri behu. */
async function hubSetup() {
  let h;
  try { h = await api("/api/hub"); } catch (e) { return; }
  $("#hub-accept").onchange = async () => {
    try { await api("/api/hub/accept", { method: "POST", body: JSON.stringify({ accept: $("#hub-accept").checked }) }); }
    catch (e) { $("#hub-error").textContent = e.message; $("#hub-error").hidden = false; }
    loadHub();
  };
  $("#hub-jobs-all").onchange = loadHub;
  $("#hub-cfg-save").onclick = saveHubConfig;
  $("#hub-cfg-issue").onclick = issueHubToken;
  $("#hub-cfg-remove").onclick = removeHubConfig;
  applyHubConfig(h);
  renderHubAgent(h);
  // bodka pri záložke sa obnovuje aj pri zatvorenej karte
  setInterval(() => api("/api/hub").then(hubDot).catch(() => hubDot(null)), 30e3);
}

/** Bodka pri záložke Hub: zelená = agent je na hube prihlásený, oranžová = pripája sa / nebeží,
 *  červená = bez spojenia; bez nastaveného hubu sa neukazuje (chip hovorí „nastaviť"). */
function hubDot(h) {
  const dot = $("#hub-tab-dot");
  if (h && !h.configured) { dot.hidden = true; return; }
  const a = h && h.agent;
  let cls, title;
  if (!h) { cls = "bad"; title = "webapp neodpovedá"; }
  else if (!a) { cls = "warn"; title = "agent nebeží — reštartuj webapp"; }
  else if (a.last_error || h.error) { cls = "bad"; title = `bez spojenia: ${a.last_error || h.error}`; }
  else if (a.updating) { cls = "warn"; title = "agent ťahá kód"; }
  else if (a.registered) { cls = "ok"; title = `online · ${h.config.hub_url}`; }
  else { cls = "warn"; title = "pripája sa"; }
  dot.hidden = false; dot.className = `tab-dot ${cls}`; dot.title = title;
}

/** Nastavenie z /api/hub do formulára a prepínač „na hube" podľa `send`. */
function applyHubConfig(h) {
  const cfg = h.config;
  $("#hub-run-row").hidden = !(cfg && cfg.send);
  $("#hub-tab-chip").textContent = cfg ? "" : "nastaviť";
  $("#hub-settings").open = !cfg;
  $("#hub-settings-hint").textContent = cfg ? `${cfg.name} → ${cfg.hub_url}` : "hub nie je nastavený";
  $("#hub-cfg-remove").hidden = !cfg;
  if (!cfg) return;
  $("#hub-cfg-name").value = cfg.name || "";
  $("#hub-cfg-url").value = cfg.hub_url || "";
  $("#hub-cfg-token").placeholder = cfg.token ? "uložený — nechať prázdne = doterajší" : "token agenta z hubu";
  $("#hub-cfg-parallel").value = cfg.max_parallel || "";
  $("#hub-cfg-accept").checked = !!cfg.accept;
  $("#hub-cfg-send").checked = !!cfg.send;
}

async function saveHubConfig() {
  const btn = $("#hub-cfg-save"); btn.disabled = true;
  $("#hub-cfg-error").hidden = true; $("#hub-cfg-status").textContent = "ukladám a pripájam…";
  try {
    const h = await api("/api/hub/config", { method: "POST", body: JSON.stringify({
      name: $("#hub-cfg-name").value.trim(), hub_url: $("#hub-cfg-url").value.trim(),
      token: $("#hub-cfg-token").value, accept: $("#hub-cfg-accept").checked, send: $("#hub-cfg-send").checked,
      max_parallel: Number($("#hub-cfg-parallel").value) || 0,
    }) });
    $("#hub-cfg-token").value = "";
    applyHubConfig(h); renderHubAgent(h);
    $("#hub-cfg-status").textContent = "uložené; agent sa hlási hubu (stav nižšie sa obnoví o pár sekúnd)";
    setTimeout(loadHub, 3000);
  } catch (e) {
    $("#hub-cfg-error").textContent = e.message; $("#hub-cfg-error").hidden = false;
    $("#hub-cfg-status").textContent = "";
  } finally { btn.disabled = false; }
}

/** Token agenta z hlavného tokenu servera: hub ho vydá pre meno vo formulári, stránka ho vloží
 *  do poľa Token a hneď uloží nastavenie. Hlavný token sa po použití z poľa zmaže. */
async function issueHubToken() {
  const btn = $("#hub-cfg-issue");
  const body = { name: $("#hub-cfg-name").value.trim(), hub_url: $("#hub-cfg-url").value.trim(),
                 admin_token: $("#hub-cfg-admin").value.trim(), replace: false };
  $("#hub-cfg-error").hidden = true;
  if (!body.name || !body.hub_url || !body.admin_token) {
    $("#hub-cfg-error").textContent = "vyplň meno agenta, adresu hubu a hlavný token servera";
    $("#hub-cfg-error").hidden = false;
    return;
  }
  btn.disabled = true; $("#hub-cfg-status").textContent = "hub vydáva token…";
  try {
    let r;
    try { r = await api("/api/hub/token", { method: "POST", body: JSON.stringify(body) }); }
    catch (e) {
      if (!/už token má/.test(e.message) || !confirm(`${e.message}.

Vydať nový token aj tak?`)) throw e;
      r = await api("/api/hub/token", { method: "POST", body: JSON.stringify({ ...body, replace: true }) });
    }
    $("#hub-cfg-admin").value = "";
    $("#hub-cfg-token").value = r.token;
    await saveHubConfig();
  } catch (e) {
    $("#hub-cfg-error").textContent = e.message; $("#hub-cfg-error").hidden = false;
    $("#hub-cfg-status").textContent = "";
  } finally { btn.disabled = false; }
}

async function removeHubConfig() {
  if (!confirm("Odpojiť tento klon od hubu a zmazať nastavenie?")) return;
  try {
    const h = await api("/api/hub/config", { method: "DELETE" });
    applyHubConfig(h); renderHubAgent(h);
    $("#hub-cfg-status").textContent = "odpojené";
    $("#hub-agents tbody").innerHTML = ""; $("#hub-stats tbody").innerHTML = ""; $("#hub-jobs tbody").innerHTML = "";
  } catch (e) { $("#hub-cfg-error").textContent = e.message; $("#hub-cfg-error").hidden = false; }
}

// Druh stroja (docs/HUB.md „Druhy agentov“): webapp a headless počítací počítajú, live len obchoduje.
/** Je agent na poslednom `main`? (`hub.code` počíta webapp z `git fetch` na pozadí.) */
function hubCodeChip(ver, code) {
  if (!ver || !code) return "";
  const s = code.versions[ver];
  if (s === undefined) return "";
  if (s === null) return `<span class="chip warn" title="commit ${esc(ver)} tento klon nepozná — agent stojí na nepushnutom kóde, alebo si sprav Pull">?</span>`;
  if (s.ahead) return `<span class="chip warn" title="${s.ahead} commitov agenta nie je v main (nepushnuté)${s.behind ? `, ${s.behind} z main nemá` : ""}">mimo main</span>`;
  if (!s.behind) return `<span class="chip ok" title="na poslednom main (${esc(code.main)})">aktuálny</span>`;
  return `<span class="chip bad" title="main je ${esc(code.main)} — agentovi chýba ${s.behind} commitov; ⟳ ho aktualizuje">−${s.behind}</span>`;
}

/** Tlačidlo „pull + reštart" agenta a stav posledného pokynu (live stroj má vlastné nasadenie). */
function hubUpdateCell(a, code) {
  if (a.role === "live" || !a.online) return "";
  const p = a.pull_result;
  // starý hub zlyhaný pull nezabúda — keď je agent na poslednom main, už nič neznamená
  const aktualny = code && a.version && code.versions[a.version] && !code.versions[a.version].behind;
  const zlyhal = p && !p.ok && p.version === a.version && !aktualny;
  if (a.update_request) return `<span class="chip warn" title="pokyn ${esc(a.update_request)}: dopočíta, git pull, reštart">aktualizuje sa</span> `;
  const tip = p ? `posledný pull ${p.at || ""}: ${p.ok ? "ok" : "zlyhal"} → ${p.version || "?"}${p.output ? "\n" + p.output : ""}` : "";
  return `<button class="ghost small" data-hub-update="${esc(a.name)}" title="dopočítať, git pull a reštart${tip ? "\n" + esc(tip) : ""}">⟳</button>`
    + (zlyhal ? ` <span class="chip bad" title="${esc(tip)}">pull zlyhal</span>` : "") + " ";
}

function anoNie(v) {
  return `<span class="chip ${v ? "ok" : "bad"}">${v ? "áno" : "nie"}</span>`;
}

function hubKind(a) {
  if (a.role === "live") return '<span class="chip warn" title="obchodný stroj (NinjaTrader/MT5) — výpočty nikdy neberie">live</span>';
  if (a.kind === "webapp") return '<span class="chip" title="Tester v prehliadači — počíta, keď prijíma">webapp</span>';
  if (a.kind === "headless") return '<span class="chip" title="headless agent, len počíta pre hub">počítací</span>';
  return "";
}

function renderHubAgent(h) {
  const a = h.agent, cfg = h.config;
  $("#hub-agent-none").hidden = !!cfg;
  $("#hub-agent").hidden = !cfg;
  if (!cfg) return;
  $("#hub-agent-name").textContent = cfg.name;
  $("#hub-agent-url").textContent = cfg.hub_url;
  const live = (a ? a.role : cfg.role) === "live";
  $("#hub-accept").checked = a ? a.accept : cfg.accept;
  $("#hub-accept").disabled = !a || live;
  $("#hub-accept").title = live ? "obchodný stroj (rola live) výpočty neprijíma" : "";
  $("#hub-agent-send").textContent = cfg.send ? "posiela" : "neposiela";
  $("#hub-agent-send").className = `chip ${cfg.send ? "ok" : ""}`;
  $("#hub-agent-version").textContent = a && a.version ? a.version : "";
  hubDot(h);
  const chip = $("#hub-agent-chip");
  if (!a) { chip.textContent = "agent nebeží"; chip.className = "chip warn"; }
  else if (a.last_error) { chip.textContent = "bez spojenia"; chip.className = "chip bad"; }
  else if (a.updating) { chip.textContent = "ťahá kód"; chip.className = "chip warn"; }
  else { chip.textContent = a.registered ? "online" : "pripája sa"; chip.className = `chip ${a.registered ? "ok" : "warn"}`; }
  const warn = $("#hub-agent-warn");
  if (a && a.needs_restart) { warn.textContent = "Agent si stiahol nový kód (git pull) — reštartuj webapp, inak beží na starom."; warn.hidden = false; }
  else if (a && a.last_error) {
    const drzi = Object.values(a.computing || {}).filter(c => c.deliver_fails).length;
    warn.textContent = a.last_error + (drzi
      ? ` — ${drzi} spočítaných výsledkov si agent drží a odovzdá ich, keď sa hub vráti`
      : " — čo už počíta, dopočíta aj bez hubu");
    warn.hidden = false;
  }
  else if (a && Object.keys(a.undelivered || {}).length) {
    warn.textContent = `Hub neprijal ${Object.keys(a.undelivered).length} spočítaných výpočtov `
      + "(nepozná ich, alebo ich medzitým dal inému) — behy sú v histórii tohto klonu. ";
    const zabudni = document.createElement("button");
    zabudni.className = "ghost small"; zabudni.textContent = "✕ zabudnúť";
    zabudni.title = "skryť hlásenie — behy ostanú v histórii";
    zabudni.onclick = () => hubAkcia(() => api("/api/hub/undelivered", { method: "DELETE" }));
    warn.append(zabudni);
    warn.hidden = false;
  }
  else warn.hidden = true;
  const pocita = a ? Object.keys(a.computing || {}).length : 0;
  const poslane = a ? Object.values(a.sent || {}).filter(s => !s.collected).length : 0;
  const caka = a ? (a.pending_upload || 0) : 0;
  const neodovzdane = a ? Object.keys(a.undelivered || {}).length : 0;
  $("#hub-agent-info").textContent = a
    ? `${a.cores} jadier, ${a.slots} slotov · počíta ${pocita} · čaká na výsledok ${poslane}`
      + (caka ? ` · spočítané, čaká na hub ${caka}` : "")
      + (neodovzdane ? ` · neodovzdané ${neodovzdane}` : "")
    : "agent sa spúšťa spolu s webapp — reštartuj ju, keď si config pridal až teraz";
}

/** Akcia nad hubom (zrušenie výpočtu, vyhodenie agenta): spraví ju, prekreslí kartu a
 *  až potom vypíše chybu — inak ju prekreslenie hneď zmaže a klik vyzerá, že sa nestalo nič. */
async function hubAkcia(fn) {
  let chyba = null;
  try { await fn(); } catch (e) { chyba = e.message; }
  await loadHub();
  if (chyba) { $("#hub-error").textContent = chyba; $("#hub-error").hidden = false; }
}

/** Karta Hub sa obnovuje na pozadí každých 10 s, kým je otvorená — aj po chybe (webapp
 *  zaneprázdnená počítaním, hub sa reštartuje), inak by obnovovanie potichu prestalo. */
async function loadHub() {
  clearTimeout(state.hubTimer); state.hubTimer = null;
  try { await renderHub(); }
  finally {
    clearTimeout(state.hubTimer);
    state.hubTimer = $("#view-hub").hidden ? null : setTimeout(loadHub, 10000);
  }
}

async function renderHub() {
  let h;
  try { h = await api("/api/hub"); $("#hub-error").hidden = true; }
  catch (e) { $("#hub-error").textContent = e.message; $("#hub-error").hidden = false; return; }
  renderHubAgent(h);
  if (!h.configured) { $("#hub-agents tbody").innerHTML = ""; $("#hub-stats tbody").innerHTML = ""; $("#hub-jobs tbody").innerHTML = ""; return; }
  const hub = h.hub;
  if (!hub) {
    if (h.error) { $("#hub-error").textContent = `hub: ${h.error}`; $("#hub-error").hidden = false; }
    $("#hub-agents tbody").innerHTML = ""; $("#hub-stats tbody").innerHTML = ""; $("#hub-jobs tbody").innerHTML = "";
  } else {
    $("#hub-agents-count").textContent = `${hub.online} online`;
    renderHubVersion(hub);
    hubStatsBox();
    $("#hub-stats-old").hidden = hub.agents.some(a => a.stats);
    $("#hub-agents tbody").innerHTML = hub.agents.map(a => `<tr class="plain">
      <td><b>${esc(a.name)}</b> ${hubKind(a)}</td>
      <td><span class="chip ${a.online ? "ok" : ""}">${a.online ? "online" : "offline"}</span>${a.needs_restart ? ' <span class="chip warn" title="po git pull čaká na reštart">reštart</span>' : ""}${a.updating ? ' <span class="chip warn" title="agent ťahá kód (git pull) — dovtedy nič nové nedostane">ťahá kód</span>' : ""}</td>
      <td>${esc(a.version || "–")} ${hubCodeChip(a.version, hub.code)}</td><td class="num">${a.cores ?? "–"}</td><td class="num">${a.slots ?? "–"}</td><td class="num">${a.used ?? 0}</td>
      <td>${anoNie(a.accept)}${a.accept_request !== null && a.accept_request !== undefined ? ` → ${anoNie(a.accept_request)}` : ""}</td>
      <td>${fmtEta(a.eta_free_1)}</td><td>${fmtEta(a.eta_free_all)}</td>
      <td>${hubUpdateCell(a, hub.code)}${a.online ? "" : `<button class="ghost small" data-hub-forget="${esc(a.name)}" title="vyhodiť agenta z hubu (premenovaný stroj, zrušený agent)">✕</button>`}</td></tr>`).join("");
    for (const b of $$("[data-hub-update]")) b.onclick = async () => {
      const meno = b.dataset.hubUpdate, vsetci = meno === "*";
      if (!confirm(`${vsetci ? "Všetci online počítajúci agenti" : `Agent „${meno}"`} prestane brať nové výpočty, `
                   + "dopočíta bežiace, spraví git pull a reštartuje sa. Pokračovať?")) return;
      await hubAkcia(() => api(`/api/hub/agents/${encodeURIComponent(meno)}/update`, { method: "POST" }));
    };
    $("#hub-stats tbody").innerHTML = hub.agents.filter(a => a.role !== "live" || (a.stats && a.stats.done))
      .map(hubStatsRow).join("");
    for (const b of $$("[data-hub-forget]")) b.onclick = async () => {
      const meno = b.dataset.hubForget;
      if (!confirm(`Vyhodiť agenta „${meno}" z hubu?

Čo ešte počítal, sa vráti do fronty alebo `
                   + "zlyhá. Keď ten stroj ešte beží pod týmto menom, prihlási sa späť.")) return;
      const token = confirm(`Odobrať mu aj token?

OK = áno (premenovaný stroj ho pod starým menom `
                            + "už nepotrebuje), Zrušiť = token nechať.");
      await hubAkcia(() => api(`/api/hub/agents/${encodeURIComponent(meno)}?token=${token}`,
                               { method: "DELETE" }));
    };
    let jobs = hub.jobs;
    if ($("#hub-jobs-all").checked) {
      try { jobs = await api("/api/hub/jobs?live=false"); } catch (e) { /* ostane živý zoznam */ }
    }
    $("#hub-jobs-count").textContent = `${hub.queued} vo fronte · ${hub.running} počíta`;
    renderHubQueueEta(hub.throughput);
    renderHubPlans(hub.plans);
    const zive = new Set(["queued", "assigned", "running", "cancelling"]);
    $("#hub-jobs tbody").innerHTML = jobs.map(j => {
      const s = j.summary || {};
      const chip = j.status === "done" ? "ok" : (j.status === "failed" ? "bad" : (zive.has(j.status) ? "warn" : ""));
      const postup = j.progress === null || j.progress === undefined ? "–" : `${Math.round(100 * j.progress)} %`;
      const zostava = j.eta_seconds !== null && j.eta_seconds !== undefined ? fmtEta(j.eta_seconds)
        : (j.estimate_seconds ? "~" + fmtEta(j.estimate_seconds) : "–");
      return `<tr class="plain" title="${esc(j.note || "")}${j.error ? "\n" + esc(j.error) : ""}">
        <td>${esc(j.id)}</td><td>${esc(j.kind)}</td><td><span class="chip ${chip}">${esc(j.status)}</span></td>
        <td>${esc(j.agent || "–")}</td><td>${esc(j.submitter || "–")}</td><td>${esc(j.version || "–")}</td>
        <td class="num">${postup}</td><td>${zive.has(j.status) ? zostava : "–"}</td>
        <td>${esc(s.pair || "")} ${esc(s.timeframe || "")} ${esc(s.timerange || "")}</td>
        <td>${zive.has(j.status) ? `<button class="ghost small" data-hub-cancel="${esc(j.id)}" title="zrušiť výpočet (hub to povie počítajúcemu aj zadávajúcemu agentovi)">✕</button>` : ""}</td></tr>`;
    }).join("") || `<tr class="plain"><td colspan="10" class="muted">nič</td></tr>`;
    for (const b of $$("[data-hub-cancel]")) b.onclick = async () =>
      hubAkcia(() => api(`/api/hub/jobs/${b.dataset.hubCancel}/cancel`, { method: "POST" }));
  }
}

/** Nový text logu bez straty pozície: ak bol scroll na konci, ostane na konci (sleduje beh),
 *  ak si tester odscrolloval hore, nič sa mu nepohne. */
function setLogText(pre, text) {
  if (pre.textContent === text) return;
  const atEnd = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 8;
  pre.textContent = text;
  if (atEnd) pre.scrollTop = pre.scrollHeight;
}

/** Celý log bežiaceho behu v plnej šírke (Freqtrade tabuľky sú široké — bez zalamovania). */
function openLiveLog(job) {
  state.liveLog = job.id;
  $("#live-log").hidden = false;
  $("#live-log-title").textContent = `${job.settings.pair} · ${job.settings.timeframe || "3m"} · ${job.settings.timerange}${job.note ? " · " + job.note : ""} — beží`;
  $("#live-log-text").textContent = "";
  refreshLiveLog();
}

function closeLiveLog() { state.liveLog = null; $("#live-log").hidden = true; }

async function refreshLiveLog(jobs) {
  const id = state.liveLog;
  if (!id) return;
  const pre = $("#live-log-text");
  try { setLogText(pre, await api(`/api/runs/${id}/log`)); } catch (e) { pre.textContent = e.message; }
  if ($("#live-log-follow").checked) pre.scrollTop = pre.scrollHeight;
  // `jobs` je stav fronty z pollQueue; bez neho (otvorenie okna) sa nadpis nemení
  if (jobs !== undefined && !jobs.some(j => j.id === id)) $("#live-log-title").textContent = $("#live-log-title").textContent.replace(/ — beží$/, " — dobehol");
}
