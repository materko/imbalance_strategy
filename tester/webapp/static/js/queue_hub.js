/* TradeBot Backtester — Fronta behov, hub (distribuované počítanie) a živý log. */
"use strict";

// --------------------------------------------------------------------------- //
// Fronta
// --------------------------------------------------------------------------- //

async function pollQueue() {
  const jobs = await api("/api/queue");
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
  return { queue: $("#hub-queue").checked, max_wait_minutes: w === "" ? null : Number(w) };
}

function fmtEta(s) {
  if (s === null || s === undefined) return "–";
  if (s <= 0) return "hneď";
  if (s < 90) return `${Math.round(s)} s`;
  return `${Math.round(s / 60)} min`;
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
  $("#hub-cfg-remove").onclick = removeHubConfig;
  applyHubConfig(h);
  renderHubAgent(h);
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

async function removeHubConfig() {
  if (!confirm("Odpojiť tento klon od hubu a zmazať nastavenie?")) return;
  try {
    const h = await api("/api/hub/config", { method: "DELETE" });
    applyHubConfig(h); renderHubAgent(h);
    $("#hub-cfg-status").textContent = "odpojené";
    $("#hub-agents tbody").innerHTML = ""; $("#hub-jobs tbody").innerHTML = "";
  } catch (e) { $("#hub-cfg-error").textContent = e.message; $("#hub-cfg-error").hidden = false; }
}

function renderHubAgent(h) {
  const a = h.agent, cfg = h.config;
  $("#hub-agent-none").hidden = !!cfg;
  $("#hub-agent").hidden = !cfg;
  if (!cfg) return;
  $("#hub-agent-name").textContent = cfg.name;
  $("#hub-agent-url").textContent = cfg.hub_url;
  $("#hub-accept").checked = a ? a.accept : cfg.accept;
  $("#hub-accept").disabled = !a;
  $("#hub-agent-send").textContent = cfg.send ? "posiela" : "neposiela";
  $("#hub-agent-send").className = `chip ${cfg.send ? "ok" : ""}`;
  $("#hub-agent-version").textContent = a && a.version ? a.version : "";
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
      + "(nepozná ich, alebo ich medzitým dal inému) — behy sú v histórii tohto klonu.";
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

async function loadHub() {
  clearTimeout(state.hubTimer); state.hubTimer = null;
  let h;
  try { h = await api("/api/hub"); $("#hub-error").hidden = true; }
  catch (e) { $("#hub-error").textContent = e.message; $("#hub-error").hidden = false; return; }
  renderHubAgent(h);
  if (!h.configured) { $("#hub-agents tbody").innerHTML = ""; $("#hub-jobs tbody").innerHTML = ""; return; }
  const hub = h.hub;
  if (!hub) {
    if (h.error) { $("#hub-error").textContent = `hub: ${h.error}`; $("#hub-error").hidden = false; }
    $("#hub-agents tbody").innerHTML = ""; $("#hub-jobs tbody").innerHTML = "";
  } else {
    $("#hub-agents-count").textContent = `${hub.online} online`;
    $("#hub-agents tbody").innerHTML = hub.agents.map(a => `<tr class="plain">
      <td><b>${esc(a.name)}</b></td>
      <td><span class="chip ${a.online ? "ok" : ""}">${a.online ? "online" : "offline"}</span>${a.needs_restart ? ' <span class="chip warn" title="po git pull čaká na reštart">reštart</span>' : ""}${a.updating ? ' <span class="chip warn" title="agent ťahá kód (git pull) — dovtedy nič nové nedostane">ťahá kód</span>' : ""}</td>
      <td>${esc(a.version || "–")}</td><td class="num">${a.cores ?? "–"}</td><td class="num">${a.slots ?? "–"}</td><td class="num">${a.used ?? 0}</td>
      <td>${a.accept ? "áno" : "nie"}${a.accept_request !== null && a.accept_request !== undefined ? ` → ${a.accept_request ? "áno" : "nie"}` : ""}</td>
      <td>${fmtEta(a.eta_free_1)}</td><td>${fmtEta(a.eta_free_all)}</td>
      <td>${a.online ? "" : `<button class="ghost small" data-hub-forget="${esc(a.name)}" title="vyhodiť agenta z hubu (premenovaný stroj, zrušený agent)">✕</button>`}</td></tr>`).join("");
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
  if (!$("#view-hub").hidden) state.hubTimer = setTimeout(loadHub, 10000);
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
