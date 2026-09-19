/* TradeBot Backtester — Navigácia a štart. */
"use strict";

// --------------------------------------------------------------------------- //
// Navigácia a štart
// --------------------------------------------------------------------------- //

function showView(name) {
  for (const b of $$(".tabs button")) b.classList.toggle("active", b.dataset.view === name);
  $("#view-new").hidden = name !== "new"; $("#view-history").hidden = name !== "history";
  $("#view-analytics").hidden = name !== "analytics";
  $("#view-hub").hidden = name !== "hub";
  if (name === "hub") loadHub(); else if (state.hubTimer) { clearTimeout(state.hubTimer); state.hubTimer = null; }
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
  Object.assign(state.meta, strategyMeta(state.strategy) || {});
  fillSettings();
  $("#strategy").value = state.strategy;
  // Východisko sú Pine defaulty; referenčné profily (golden test, MultiCharts) sú na výber.
  const preferred = "";
  $("#profile").value = preferred;
  await loadProfile(preferred);
  pollQueue();
  gitStatus();
  hubSetup();

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
}

init().catch(e => { document.body.insertAdjacentHTML("afterbegin", `<div class="error">${esc(e.message)}</div>`); });
