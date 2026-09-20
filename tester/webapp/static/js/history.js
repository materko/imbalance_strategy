/* TradeBot Backtester — História behov a detail behu. */
"use strict";

// --------------------------------------------------------------------------- //
// História
// --------------------------------------------------------------------------- //

const fmt = (v, d = 2) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toFixed(d);
const signed = (v, d = 2, suffix = "") => v === null || v === undefined ? "—" :
  `<span class="${v >= 0 ? "pos" : "neg"}">${v >= 0 ? "+" : ""}${Number(v).toFixed(d)}${suffix}</span>`;
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function fmtVal(v) { return typeof v === "object" && v !== null ? `${v.value} ${v.unit}` : String(v); }

const historyPage = { offset: 0, size: 50, query: "", seq: 0, controller: null };

/** Naplní filtre histórie z metadát. Volá sa raz, po načítaní `/api/meta`. */
function fillHistoryFilters() {
  const strat = $("#filter-strategy");
  const pair = $("#filter-pair");
  const tf = $("#filter-tf");
  if (!strat || strat.dataset.ready) return;
  for (const x of state.meta.strategies || []) {
    strat.append(new Option(x.title, x.key));
  }
  for (const p of state.meta.pairs || []) pair.append(new Option(p.pair, p.pair));
  const tfs = [...new Set((state.meta.pairs || []).flatMap(p => p.timeframes || []))]
    .sort((a, b) => (TF_MINUTES[a] || 0) - (TF_MINUTES[b] || 0));
  for (const x of tfs) tf.append(new Option(x, x));
  strat.dataset.ready = "1";
  // Predvolene sa ukazuje prave aktivna strategia: behy inej strategie maju ine
  // parametre, takze zmiesane v jednej tabulke sa neporovnavaju.
  strat.value = state.strategy || "";
  for (const el of [strat, pair, tf]) el.onchange = () => { historyPage.offset = 0; loadRuns(); };
  $("#filter-reset").onclick = () => {
    strat.value = pair.value = tf.value = "";
    historyPage.offset = 0;
    loadRuns();
  };
}

/** Dopyt = to, co je v hladani, plus zvolene filtre. Filtre sa do textu nepisu, aby
 *  sa uzivatelovi neprepisovalo, co si sam napisal. */
function historyQuery() {
  const casti = [$("#search").value.trim()];
  for (const [id, kluc] of [["#filter-strategy", "strategy"], ["#filter-pair", "pair"],
                            ["#filter-tf", "tf"]]) {
    const v = ($(id)?.value || "").trim();
    if (v) casti.push(`${kluc}=${v}`);
  }
  return casti.filter(Boolean).join(" ");
}

async function loadRuns() {
  const q = historyQuery();
  if (q !== historyPage.query) { historyPage.offset = 0; historyPage.query = q; }
  const seq = ++historyPage.seq;
  historyPage.controller?.abort();
  historyPage.controller = new AbortController();
  $("#history-error").hidden = true;
  $("#search-count").textContent = "Načítavam…";
  $("#runs-table").setAttribute("aria-busy", "true");
  $("#history-prev").disabled = $("#history-next").disabled = true;
  try {
  const r = await api(`/api/runs?q=${encodeURIComponent(q)}&limit=${historyPage.size}&offset=${historyPage.offset}`,
    { signal: historyPage.controller.signal });
  if (seq !== historyPage.seq) return;
  if (r.total && historyPage.offset >= r.total) {
    historyPage.offset = Math.floor((r.total - 1) / historyPage.size) * historyPage.size;
    return loadRuns();
  }
  $("#search-count").textContent = `${r.total} behov`;
  $("#history-page").textContent = r.total ? `${historyPage.offset + 1}–${historyPage.offset + r.runs.length} z ${r.total}` : "Žiadne behy";
  $("#history-prev").disabled = historyPage.offset === 0;
  $("#history-next").disabled = historyPage.offset + historyPage.size >= r.total;
  const tb = $("#runs-table tbody"), fragment = document.createDocumentFragment();
  for (const run of r.runs) {
    const res = run.result || {};
    const tr = document.createElement("tr");
    const ov = Object.entries(run.overrides || {}).map(([k, v]) => `<span class="kv">${k}=${esc(fmtVal(v))}</span>`).join("");
    const failed = run.status !== "done";
    const strat = run.settings?.strategy || "ibs";
    tr.innerHTML = `<td><div>${run.id}</div><div class="muted small">${(run.created || "").replace("T", " ").slice(0, 16)} · ${esc(run.user || "")}</div></td>
      <td title="${esc(strat)}">${esc((strategySpec(strat) || {}).title || strat)}</td>
      <td>${esc(run.settings?.pair || "")}<div class="muted small">${esc(run.settings?.timeframe || "3m")}</div></td><td>${esc(run.settings?.timerange || "")}<div class="muted small">fee ${run.settings?.fee != null ? (run.settings.fee * 100).toFixed(3) + " %" : "—"} · ${run.settings?.wallet ?? ""}</div></td>
      <td class="num">${failed ? `<span class="status-failed">${esc(run.status)}</span>` : res.trades ?? "—"}</td>
      <td class="num">${signed(res.pnl_pct, 2, " %")}</td><td class="num">${fmt(res.profit_factor, 3)}</td>
      <td class="num">${fmt(res.winrate, 1)}</td><td class="num">${fmt(res.max_drawdown_pct, 2)}</td>
      <td class="num">${res.break_even_pct != null ? fmt(res.break_even_pct, 4) : "—"}</td>
      <td class="num" title="najdlhšia séria ziskov / strát za sebou">${streakHeadline(res.streaks)}</td>
      <td class="ov">${ov || '<span class="muted">Pine defaulty</span>'}</td><td>${esc(run.note || "")}</td>`;
    tr.tabIndex = 0;
    tr.onclick = () => openRun(run.id);
    tr.onkeydown = e => { if (e.key === "Enter") openRun(run.id); };
    fragment.append(tr);
  }
  tb.replaceChildren(fragment);
  if (!r.runs.length) tb.innerHTML = '<tr><td colspan="13" class="empty muted">Žiadne behy nezodpovedajú hľadaniu.</td></tr>';
  tb.closest(".scroll").scrollTop = 0;
  } catch (e) {
    if (seq !== historyPage.seq || e.name === "AbortError") return;
    $("#search-count").textContent = "Načítanie zlyhalo";
    $("#history-error").textContent = `${e.message} — skús Hľadať znova.`;
    $("#history-error").hidden = false;
  } finally {
    if (seq === historyPage.seq) $("#runs-table").removeAttribute("aria-busy");
  }
}

async function openRun(id) {
  const r = await api(`/api/runs/${id}`);
  const rec = r.record;
  state.detailId = id;
  state.detailRecord = rec;
  $("#runs-table").parentElement.parentElement.hidden = true;
  $("#run-detail").hidden = false;
  const runStrategy = rec.settings.strategy || "ibs";
  const runMeta = strategyMeta(runStrategy) || state.meta;
  $("#detail-title").textContent = `${(strategySpec(runStrategy) || {}).title || runStrategy} · ${rec.settings.pair} · ${rec.settings.timeframe || "3m"} · ${rec.settings.timerange}`;
  $("#detail-meta").textContent = `${rec.id} · ${rec.user || ""} · ${(rec.created || "").replace("T", " ").slice(0, 16)} · profil ${rec.settings.profile || "(Pine)"} · poplatok ${rec.settings.fee != null ? (rec.settings.fee * 100).toFixed(3) + " %" : "—"} · peňaženka ${rec.settings.wallet} · engine ${rec.settings.engine || "freqtrade"}${rec.settings.exchange ? " (" + rec.settings.exchange + ")" : ""} · detail ${rec.settings.timeframe_detail || "bez"}${rec.note ? " · " + rec.note : ""}`;
  // Beh z mriežky sa dá otvoriť aj z histórie, takže musí byť vidieť, že je jej súčasťou
  // — a musí sa dať vrátiť späť na celú tabuľku.
  const znacka = (rec.settings.sweep || {}).id;
  const spat = $("#detail-sweep");
  spat.hidden = !znacka;
  if (znacka) {
    spat.textContent = `↩ mriežka ${sweepStamp(znacka)}`;
    spat.title = `celá mriežka ${znacka}`;
    spat.onclick = () => { showView("new"); openSweep(znacka); };
  }
  $("#download-profile").href = `/api/runs/${id}/profile.json`;
  $("#save-profile-msg").classList.remove("err");
  // Starší beh nezapísal celý config — profil z neho doplní chýbajúce polia dnešnými defaultmi.
  const chyba = rec.missing_params || [];
  $("#save-profile-msg").textContent = chyba.length
    ? `beh nemá zapísaných ${chyba.length} polí configu (starší beh) — uložený profil ich doplní dnešnými defaultmi: ${chyba.slice(0, 8).join(", ")}${chyba.length > 8 ? "…" : ""}`
    : "";
  $("#detail-error").hidden = !rec.error; $("#detail-error").textContent = rec.error || "";
  // beh, ktory mal signaly ale ziadny obchod, nie je platny vysledok - musi to povedat
  const warn = (rec.result || {}).warning;
  $("#detail-warning").hidden = !warn; $("#detail-warning").textContent = warn || "";

  const res = rec.result || {};
  const cur = res.stake_currency || "USDT";
  $("#cards").innerHTML = rec.status !== "done" ? "" : [
    card("Total PnL", signed(res.pnl_abs, 2, " " + cur), signed(res.pnl_pct, 2, " %")),
    card("Max drawdown", `${fmt(res.max_drawdown_abs)} ${cur}`, `${fmt(res.max_drawdown_pct)} %`),
    card("Profitable trades", `${fmt(res.winrate, 2)} %`, `${res.wins}/${res.trades}`),
    card("Profit factor", fmt(res.profit_factor, 3), ""),
    card("Break-even poplatok", res.break_even_pct != null ? `${fmt(res.break_even_pct, 4)} %` : "—", "na stranu; Binance taker 0,05 %"),
    card("Buy & hold", signed(res.market_change_pct, 2, " %"), `${res.duration_s ?? "?"} s výpočtu`),
    card("Najdlhšia séria", streakHeadline(res.streaks), "výhry / straty za sebou"),
  ].join("");

  drawChart(rec.series || { equity: [], market: [] }, res);

  const ov = rec.overrides || {};
  $("#detail-overrides").innerHTML = Object.keys(ov).length
    ? `<table class="runs"><tbody>${Object.entries(ov).map(([k, v]) => `<tr><td><code>${k}</code></td><td>${esc(fmtVal(v))}</td><td class="muted">Pine: ${esc(fmtVal(runMeta.defaults[k]))}</td></tr>`).join("")}</tbody></table>`
    : `<div class="muted">Pine defaulty bez zmeny.</div>`;
  const ex = res.exits || {};
  $("#detail-exits").innerHTML = Object.keys(ex).length
    ? `<table class="runs"><thead><tr><th>Dôvod</th><th class="num">n</th><th class="num">PnL ${cur}</th></tr></thead><tbody>${Object.entries(ex).map(([k, v]) => `<tr><td>${k}</td><td class="num">${v.n}</td><td class="num">${signed(v.pnl_abs)}</td></tr>`).join("")}</tbody></table>`
    : `<div class="muted">—</div>`;

  const trades = r.trades || [];
  $("#detail-streaks").innerHTML = rec.status !== "done" ? "" : [
    streakTable("win", res.streaks, trades, cur),
    streakTable("loss", res.streaks, trades, cur),
  ].join("");
  for (const tr of $$("#detail-streaks tr[data-trade]")) tr.onclick = () => jumpToTrade(trades[Number(tr.dataset.trade)]);

  $("#trade-count").textContent = trades.length;
  const cols = ["open_date", "close_date", "open_rate", "close_rate", "amount", "profit_abs", "profit_ratio", "exit_reason", "enter_tag"];
  $("#trades thead").innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>`;
  $("#trades tbody").innerHTML = trades.map((t, i) => `<tr data-trade="${i}" title="ukázať na grafe">${cols.map(c => {
    let v = t[c];
    if (c.endsWith("_date") && v) v = String(v).replace("T", " ").slice(0, 16);
    if (c === "profit_abs") return `<td class="num">${signed(v)}</td>`;
    if (c === "profit_ratio") return `<td class="num">${signed(v * 100, 2, " %")}</td>`;
    if (typeof v === "number") v = Number.isInteger(v) ? v : v.toFixed(4);
    return `<td>${esc(v ?? "")}</td>`;
  }).join("")}</tr>`).join("");
  for (const tr of $$("#trades tbody tr")) tr.onclick = () => jumpToTrade(trades[Number(tr.dataset.trade)]);

  initPairChart(rec, trades);
  initMonteCarlo(rec);

  $("#detail-params").innerHTML = `<table class="runs"><tbody>${Object.entries(rec.params || {}).filter(([k]) => !k.startsWith("_")).map(([k, v]) => `<tr><td><code>${k}</code></td><td>${esc(fmtVal(v))}</td></tr>`).join("")}</tbody></table>`;
  $("#detail-log").textContent = await api(`/api/runs/${id}/log`);
}

function card(k, v, s) { return `<div class="kcard"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`; }

/** `+5 / −3` — najdlhšia séria ziskov a najdlhšia séria strát za sebou. */
function streakHeadline(streaks) {
  const w = (streaks || {}).win, l = (streaks || {}).loss;
  if (!w && !l) return "—";
  return `<span class="pos">+${w ? w.n : 0}</span> / <span class="neg">−${l ? l.n : 0}</span>`;
}

/**
 * Jedna séria: kedy bola, za koľko — a obchody, z ktorých je zložená.
 * Séria nesie indexy do obchodov behu, riadky sa berú z nich (súhrn ich neopakuje).
 */
function streakTable(kind, streaks, trades, cur) {
  const s = (streaks || {})[kind];
  const nazov = kind === "win" ? "Zisky za sebou" : "Straty za sebou";
  if (!s || !s.n) return `<div><h4>${nazov}</h4><div class="muted">—</div></div>`;
  const kedy = `${String(s.start || "").replace("T", " ").slice(0, 16)} → ${String(s.end || "").replace("T", " ").slice(0, 16)}`;
  const viac = s.count > 1 ? ` · rovnako dlhých sérií: ${s.count}` : "";
  const riadky = trades.slice(s.from_i, s.to_i + 1).map((t, i) => `
    <tr data-trade="${s.from_i + i}" title="ukázať na grafe">
      <td class="num">${s.from_i + i + 1}</td>
      <td>${esc(String(t.open_date || "").replace("T", " ").slice(0, 16))}</td>
      <td>${esc(String(t.close_date || "").replace("T", " ").slice(0, 16))}</td>
      <td class="num">${signed(t.profit_abs)}</td>
      <td class="num">${signed(t.profit_ratio * 100, 2, " %")}</td>
      <td>${esc(t.exit_reason ?? "")}</td>
    </tr>`).join("");
  return `<div>
    <h4>${nazov}: ${s.n}</h4>
    <div class="muted small">${esc(kedy)} · spolu ${signed(s.pnl_abs, 2, " " + cur)}${viac}</div>
    <table class="runs"><thead><tr><th class="num">#</th><th>vstup</th><th>výstup</th>
      <th class="num">PnL ${cur}</th><th class="num">%</th><th>dôvod</th></tr></thead>
      <tbody>${riadky}</tbody></table>
  </div>`;
}
