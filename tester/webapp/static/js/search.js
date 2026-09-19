/* TradeBot Backtester — Hľadanie (sweep / hyperopt / matica): režim, história, otvorenie a zrušenie, odoslanie behu. */
"use strict";

/** Mriežka patrí stratégii, aj tá zapamätaná — parametre sú v každej iné. */
const sweepKey = () => `sweep:${state.strategy}`;

/** „sweep" prejde mriežku, „hyper" v nej hľadá. Zadanie je pre oboje to isté. */
let searchMode = "sweep";
const isHyper = () => searchMode === "hyper";
const isMatrix = () => searchMode === "matrix";

/** Otvorí naposledy pozeranú mriežku tejto stratégie (alebo nechá sekciu prázdnu). */
function restoreSweep() {
  let ulozeny = null;
  try { ulozeny = localStorage.getItem(sweepKey()); } catch (e) { /* súkromné okno */ }
  sweep.id = ulozeny || null;
  clearTimeout(sweep.timer);
  $("#sweep-status").textContent = "";
  $("#sweep-result").innerHTML = "";
  $("#sweep-cancel").hidden = true;
  loadSweepHistory();
  if (ulozeny) pollSweep();
}

/** Po zmene stratégie: iné parametre v ponuke, iná história, iná zapamätaná mriežka. */
function resetSweepForStrategy() {
  $("#sweep-rows").innerHTML = "";
  addSweepRow();
  restoreSweep();
}

/** Naplní ponuku predošlých mriežok — sweep sa dá otvoriť aj o týždeň. */
async function loadSweepHistory() {
  let list = [];
  const cesta = isMatrix() ? "/api/matrices" : (isHyper() ? "/api/hyperopts" : "/api/sweeps");
  try {
    const r = await api(`${cesta}?limit=50&strategy=${encodeURIComponent(state.strategy)}`);
    list = isMatrix() ? r.matrices : (isHyper() ? r.hyperopts : r.sweeps);
  } catch (e) { return; }
  const sel = $("#sweep-past");
  const wrap = sel.closest(".sweep-past");
  wrap.hidden = !list.length;
  // Aj skrytú ponuku treba vyprázdniť, nech v nej po prepnutí stratégie nezostanú
  // mriežky tej predošlej.
  sel.innerHTML = `<option value="">— vyber mriežku z histórie —</option>`;
  if (!list.length) return;
  for (const s of list) {
    const o = document.createElement("option");
    o.value = s.id;
    const stav = isHyper()
      ? `${s.epochs_done || 0}/${s.epochs || "?"} epoch`
      : (s.pending ? `${s.done}/${s.done + s.pending}` : `${s.done} behov`);
    if (isMatrix()) {
      const o = document.createElement("option");
      o.value = s.id;
      o.textContent = `${sweepStamp(s.id)} · ${s.pairs.length} trhov × ${s.timeframes.length} TF · ${stav}`;
      o.title = `${s.timerange} · ${s.relative ? "prahy v ATR" : "prahy nezmenené"}`;
      sel.append(o);
      continue;
    }
    o.textContent = `${sweepStamp(s.id)} · ${s.params.join(" × ")} · ${s.pair} ${s.timeframe}`
      + ` · ${stav}`;
    o.title = `${s.timerange} · ${s.goal_note}`;
    sel.append(o);
  }
  sel.value = sweep.id || "";
}

/** `20260909-201203-ed78` -> `9. 9. 20:12` — id je čitateľné, ale nie na pozeranie. */
function sweepStamp(id) {
  const m = /^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})/.exec(id || "");
  return m ? `${+m[3]}. ${+m[2]}. ${m[4]}:${m[5]}` : id;
}

/** Prepne medzi „prejdi mriežku" a „hľadaj v nej" — riadky parametrov ostávajú. */
async function setSearchMode(mode) {
  searchMode = mode;
  for (const [key, id] of [["sweep", "#mode-sweep"], ["hyper", "#mode-hyper"], ["matrix", "#mode-matrix"]]) {
    $(id).classList.toggle("active", mode === key);
    $(id).setAttribute("aria-pressed", String(mode === key));
  }
  for (const el of $$(".hyper-only")) el.hidden = mode !== "hyper";
  for (const el of $$(".matrix-only")) el.hidden = mode !== "matrix";
  // Matica nemení parameter, ale trh — riadky parametrov by tam mýlili.
  $("#sweep-rows").hidden = mode === "matrix";
  $("#sweep-add").hidden = mode === "matrix";
  if (mode === "matrix") await initMatrixPick();
  $("#sweep-status").textContent = "";
  $("#sweep-result").innerHTML = "";
  $("#sweep-cancel").hidden = true;
  if (mode === "hyper") await loadHyperMeta();
  $("#search-hint").textContent =
    mode === "hyper" ? (state.hyperMeta.note || "Hľadá v rozsahu a učí sa. Víťaz sa preverí na piatich oknách.")
    : mode === "matrix" ? "Že myšlienka drží aj mimo trhu, na ktorom sa ladila, je najsilnejší dôkaz kvality, aký sa z histórie dá dostať."
    : "Každý bod mriežky je obyčajný backtest a ostane v histórii.";
  refreshSweep();
  loadSweepHistory();
}

/** Čo o ladení vie stratégia — odporúčaný priestor a varovania. */
async function loadHyperMeta() {
  try {
    state.hyperMeta = await api(`/api/hyperopt/meta?strategy=${encodeURIComponent(state.strategy)}`);
  } catch (e) { state.hyperMeta = {}; }
  return state.hyperMeta;
}

/** Naplní riadky priestorom, ktorý stratégia odporúča. */
async function fillSuggested() {
  const meta = await loadHyperMeta();
  const odporucane = meta.suggested || {};
  if (!Object.keys(odporucane).length) {
    $("#sweep-status").textContent = "táto stratégia odporúčaný priestor nemá";
    return;
  }
  $("#sweep-rows").innerHTML = "";
  for (const [name, spec] of Object.entries(odporucane)) {
    addSweepRow(name);
    const row = $$("#sweep-rows .sweep-row").at(-1);
    row.querySelector("input.spec").value = spec;
  }
  refreshSweep();
}

/** Otvorí mriežku z histórie — tú istú tabuľku, aká bola po dobehnutí. */
function openSweep(id) {
  if (isMatrix()) return openMatrix(id);
  if (isHyper()) return openHyper(id);
  sweep.id = id || null;
  const sel = $("#sweep-past");
  if (sel && [...sel.options].some(o => o.value === id)) sel.value = id;
  try {
    id ? localStorage.setItem(sweepKey(), id) : localStorage.removeItem(sweepKey());
  } catch (e) { /* súkromné okno */ }
  clearTimeout(sweep.timer);
  if (!id) { $("#sweep-status").textContent = ""; $("#sweep-result").innerHTML = ""; return; }
  $("#sweep-box").open = true;
  pollSweep();
}

/** Otvorí maticu z histórie. */
function openMatrix(id) {
  matrixState.id = id || null;
  try {
    id ? localStorage.setItem(matrixKey(), id) : localStorage.removeItem(matrixKey());
  } catch (e) { /* súkromné okno */ }
  clearTimeout(matrixState.timer);
  if (!id) { $("#sweep-status").textContent = ""; $("#sweep-result").innerHTML = ""; return; }
  $("#sweep-box").open = true;
  pollMatrix();
}

/** Otvorí hyperopt z histórie — epochy, víťaz aj overenie na oknách. */
function openHyper(id) {
  hyper.id = id || null;
  try {
    id ? localStorage.setItem(hyperKey(), id) : localStorage.removeItem(hyperKey());
  } catch (e) { /* súkromné okno */ }
  clearTimeout(hyper.timer);
  if (!id) { $("#sweep-status").textContent = ""; $("#sweep-result").innerHTML = ""; return; }
  $("#sweep-box").open = true;
  pollHyper();
}

/** Zruší bežiaci hyperopt (a s ním overovacie behy, ktoré ešte nezačali). */
async function cancelHyper() {
  if (!hyper.id) return;
  try {
    await api(`/api/queue/${hyper.id}/cancel`, { method: "POST" });
    $("#sweep-status").textContent = "zrušené";
    pollQueue();
    pollHyper();
  } catch (e) { $("#sweep-status").textContent = e.message; }
}

/** Zruší všetky nedobehnuté body mriežky — náhrada za strop na jej veľkosť. */
async function cancelSweep() {
  if (!sweep.id) return;
  const btn = $("#sweep-cancel");
  btn.disabled = true;
  try {
    const r = await api(`/api/sweeps/${sweep.id}/cancel`, { method: "POST" });
    $("#sweep-status").textContent = `zrušených ${r.cancelled} behov`;
    pollQueue();
    pollSweep();
  } catch (e) {
    $("#sweep-status").textContent = e.message;
  } finally { btn.disabled = false; }
}

function initSweep() {
  const goal = $("#sweep-goal");
  goal.innerHTML = "";
  for (const [key, title] of Object.entries(GOAL_TITLES)) {
    const o = document.createElement("option"); o.value = key; o.textContent = title; goal.append(o);
  }
  $("#sweep-rows").innerHTML = "";
  addSweepRow();
  $("#sweep-add").onclick = () => addSweepRow();
  $("#sweep-run").onclick = startSearch;
  $("#sweep-cancel").onclick = () => (isHyper() ? cancelHyper() : cancelSweep());
  $("#mode-sweep").onclick = () => setSearchMode("sweep");
  $("#mode-hyper").onclick = () => setSearchMode("hyper");
  $("#mode-matrix").onclick = () => setSearchMode("matrix");
  $("#matrix-pairs").onchange = refreshSweep;
  $("#matrix-all").onclick = () => {
    for (const o of $("#matrix-pairs").options) o.selected = true;
    refreshSweep();
  };
  $("#matrix-relative").onchange = refreshSweep;
  $("#hyper-suggested").onclick = fillSuggested;
  $("#hyper-epochs").oninput = refreshSweep;
  $("#sweep-past").onchange = () => openSweep($("#sweep-past").value);
  // Sweep cez noc: po zavretí a otvorení stránky sa mriežka nájde tam, kde skončila
  // — tá, ktorú tester pozeral pri tejto stratégii.
  restoreSweep();
}

/** Zadanie behu z formulára — to isté telo použije jeden beh aj sweep. */
function runBody() {
  return {
    params: state.params,
    strategy: state.strategy,
    pair: $("#pair").value,
    engine: $("#engine").value || null,
    exchange: $("#exchange").value || null,
    timeframe: $("#tf").value,
    timerange: timerange(),
    fee: $("#fee").value === "" ? null : Number($("#fee").value) / 100,
    wallet: Number($("#wallet").value),
    timeframe_detail: $("#detail").checked ? "1m" : null,
    profile: profileForRun(),
    note: $("#note").value.trim(),
    user: currentUser(),
    ai: aiBody(),
  };
}

async function submitRun() {
  const btn = $("#run"); btn.disabled = true; $("#run-error").hidden = true;
  try {
    if (hubChecked()) {
      // Beh ide na hub: spočíta ho voľný agent, výsledok si agent tejto webapp vyzdvihne
      // sám a beh sa objaví v histórii ako každý iný.
      const job = await api("/api/hub/runs", { method: "POST", body: JSON.stringify({ ...runBody(), ...hubOptions() }) });
      $("#hub-run-info").textContent = `zadané na hub: ${job.id} · ${job.status}${job.agent ? " · " + job.agent : ""}`;
      return;
    }
    const job = await api("/api/runs", { method: "POST", body: JSON.stringify(runBody()) });
    // Vyzva sa pocita az z hotovych obchodov, takze si beh zapamatame a pockame naň.
    // Len ked si ju tester sam otvoril - zatvorena vyzva sa nepocita ani neotvara.
    state.propAfterRun = ($("#nprop-box")?.open && $("#nprop-after")?.checked && job?.id) ? job.id : null;
    await pollQueue();
  } catch (e) {
    $("#run-error").textContent = e.message; $("#run-error").hidden = false;
  } finally { btn.disabled = false; }
}
