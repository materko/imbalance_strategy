/* TradeBot Backtester — Navigácia a štart. */
"use strict";

// --------------------------------------------------------------------------- //
// Navigácia a štart
// --------------------------------------------------------------------------- //

/** Čip Hub v hornom prehľade: koľko agentov je online, koľko výpočtov čaká a beží. */
function statusHub(h) {
  const el = $("#sb-hub"), hub = h && h.hub;
  el.hidden = !!(h && !h.configured);
  const dot = el.querySelector(".tab-dot");
  if (!hub) { $("#sb-hub-text").textContent = h ? "bez spojenia" : "—"; dot.className = `tab-dot ${h ? "bad" : ""}`; return; }
  const parts = [`${hub.online ?? 0} online`, `${hub.queued ?? 0} v rade`];
  if (hub.running) parts.push(`${hub.running} beží`);
  $("#sb-hub-text").textContent = parts.join(" · ");
  dot.className = `tab-dot ${h.error ? "bad" : "ok"}`;
}

/** Čip Live v hornom prehľade: koľko inštancií stratégií naživo beží z koľkých. */
function statusLive(alive, total, error) {
  $("#sb-live-text").textContent = error ? "bez spojenia" : (total ? `${alive} beží z ${total}` : "nič nebeží");
  $("#sb-live").querySelector(".tab-dot").className = `tab-dot ${error ? "bad" : (alive ? "ok" : "")}`;
}

function showView(name) {
  for (const b of $$(".tabs button")) b.classList.toggle("active", b.dataset.view === name);
  const label = $(`.tabs button[data-view="${name}"]`);
  if (label) $("#sb-title").textContent = label.textContent.replace(/nastaviť|\d+/g, "").trim();
  // Karta je v adrese (#new, #analytics…), aby F5 ostal na tej istej karte; úvodná je katalóg (bez #).
  history.replaceState(null, "", name === "catalog" ? location.pathname + location.search : `#${name}`);
  $("#view-catalog").hidden = name !== "catalog";
  if (name === "catalog") loadCatalog();
  $("#view-new").hidden = name !== "new"; $("#view-history").hidden = name !== "history";
  $("#view-analytics").hidden = name !== "analytics";
  $("#view-diversify").hidden = name !== "diversify";
  if (name === "diversify") loadDiversify();
  $("#view-livediv").hidden = name !== "livediv";
  if (name === "livediv") loadLiveDiv();
  $("#view-hub").hidden = name !== "hub";
  $("#view-live").hidden = name !== "live";
  if (name === "hub") loadHub(); else if (state.hubTimer) { clearTimeout(state.hubTimer); state.hubTimer = null; }
  // karta Live sa obnovuje každých 5 s, kým je otvorená; inak sa nič nepýta
  if (name === "live") loadLive(); else stopLive();
  // karta História je vždy celý zoznam — otvorený detail behu sa zavrie, nech neprekrýva tabuľku
  if (name === "history") { closeDetail(); loadRuns(); }
  // Historia analytiky je per strategia, takze sa nacita az pri otvoreni karty - vtedy
  // uz je jasne, ktora strategia je zvolena.
  if (name === "analytics") {
    fillAnalyticsStrategy($("#an-strategy")?.value || "");
    fillAnalyticsProfile(); fillAnalyticsPairs();
    refreshAnalyticsPlan();          // zavolá aj históriu
  }
}

async function init() {
  // Téma: atribút už nastavil inline skript v <head> (proti bliknutiu); tu len
  // označíme aktívne tlačidlo a napojíme prepínanie/systémovú zmenu.
  const themePref = loadThemePref();
  applyTheme(themePref);
  for (const b of $$("#theme-switch button")) b.onclick = () => setTheme(b.dataset.theme);
  if (systemDark) systemDark.addEventListener("change", () => { if (loadThemePref() === "auto") applyTheme("auto"); });

  state.meta = await api("/api/meta");
  Object.assign(state.meta, (await ensureStrategyMeta(state.strategy).catch(() => null)) || {});
  fillSettings();
  $("#strategy").value = state.strategy;
  renderStrategyPicker();
  // Východisko sú Pine defaulty; referenčné profily (golden test, MultiCharts) sú na výber.
  const preferred = "";
  $("#profile").value = preferred;
  await loadProfile(preferred);
  pollQueue();
  gitStatus();
  hubSetup();
  liveSetup();
  setupDiversify();
  setupLiveDiv();

  $$(".tabs button").forEach(b => b.onclick = () => showView(b.dataset.view));
  $("#run").onclick = submitRun;
  $("#param-filter").oninput = applyParamFilter;
  $("#mode-basic").onclick = () => setParamMode("basic");
  $("#mode-all").onclick = () => setParamMode("all");
  $("#only-changed").onchange = applyParamFilter;
  $("#reset-params").onclick = () => setParams(state.base, false);
  $("#search-btn").onclick = loadRuns;
  $("#history-prev").onclick = () => { historyPage.offset = Math.max(0, historyPage.offset - historyPage.size); loadRuns(); };
  $("#history-next").onclick = () => { historyPage.offset += historyPage.size; loadRuns(); };
  $("#history-size").onchange = e => { historyPage.size = Number(e.target.value); historyPage.offset = 0; loadRuns(); };
  $("#search").onkeydown = e => { if (e.key === "Enter") loadRuns(); };
  $("#search-help-btn").onclick = () => $("#search-help").hidden = !$("#search-help").hidden;
  $("#back").onclick = closeDetail;
  $("#git-close").onclick = () => { $("#git-box").hidden = true; };
  $("#live-log-close").onclick = closeLiveLog;
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !$("#live-log").hidden) closeLiveLog(); });
  $("#load-params").onclick = loadDetailIntoForm;
  $("#run-peek-close").onclick = closePeek;
  $("#run-peek-open").onclick = () => historyPeek.id && openRun(historyPeek.id);
  $("#run-peek-load").onclick = async () => { if (historyPeek.id) { await openRun(historyPeek.id); await loadDetailIntoForm(); } };
  for (const b of $$(".chip-btn[data-range]")) b.onclick = () => setQuickRange(b.dataset.range);
  for (const field of [$("#from"), $("#to"), $("#pair"), $("#profile")]) field.addEventListener("change", () => markQuickRange(null));
  initSweep();
  $("#an-run").onclick = loadAnalytics;
  $("#an-profile").onchange = onAnalyticsProfileChange;
  $("#an-pair").onchange = () => { fillAnalyticsTf(); refreshAnalyticsPlan(); };
  $("#an-tf").onchange = refreshAnalyticsPlan;
  $("#an-query").oninput = () => loadAnalyticsHistory();
  $("#an-paper").onclick = writePaper;
  $("#an-save").onclick = saveAnalytics;
  $("#posudok-save").onclick = savePosudok;
  $("#posudok-zadanie").onclick = copyZadanie;
  $("#an-history").onchange = () => openAnalyticsHistory($("#an-history").value);
  $("#ai-box").addEventListener("toggle", () => { if ($("#ai-box").open) loadAiMeta(); });
  for (const el of [$("#ai-enabled"), $("#ai-minprob")]) el.onchange = aiWarn;
  for (const [box, p] of [["#prop-box", "prop"], ["#nprop-box", "nprop"]]) {
    $(box).addEventListener("toggle", () => {
      if ($(box).open) loadPropMeta(p).catch(e => { $(`#${p}-status`) && ($(`#${p}-status`).textContent = e.message); });
    });
  }
  $("#an-query").onkeydown = e => { if (e.key === "Enter") loadAnalytics(); };
  $("#mc-box").addEventListener("toggle", () => { if ($("#mc-box").open) loadMonteCarlo(); });
  $("#mc-run").onclick = () => loadMonteCarlo(true);
  $("#delete-run").onclick = async () => {
    if (!confirm("Zmazať tento beh z histórie? (zmaže adresár v runs/)")) return;
    await api(`/api/runs/${state.detailId}`, { method: "DELETE" }); closeDetail(); loadRuns();
  };
  $("#profile-save").onclick = saveFormAsProfile;
  $("#profile-rename").onclick = renameProfile;
  $("#profile-delete").onclick = deleteProfile;
  $("#save-profile").onclick = saveRunAsProfile;
  $("#git-pull").onclick = () => gitAction("pull");
  $("#git-push").onclick = () => gitAction("push");

  initCatalog();
  for (const b of $$("#statusbar [data-go]")) b.onclick = () => showView(b.dataset.go);

  const view = location.hash.slice(1);
  showView($$(".tabs button").some(b => b.dataset.view === view) ? view : "catalog");
}

init().catch(e => { document.body.insertAdjacentHTML("afterbegin", `<div class="error">${esc(e.message)}</div>`); });
