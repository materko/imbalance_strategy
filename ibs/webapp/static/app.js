/* IBS Backtester — jednostránková aplikácia bez frameworku. */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const GREEN = "#089981", RED = "#f23645", BLUE = "#2962ff";
const UNITS = ["abs", "ticks", "atr", "pct"];

const state = {
  meta: null,          // /api/meta
  params: {},          // aktuálne hodnoty formulára (v tvare pre IBSConfig.from_dict)
  base: {},            // hodnoty východiskového profilu (na zvýraznenie odchýlok)
  profile: null,
  pollTimer: null,
  detailId: null,
  activeGroup: null,
};

function currentUser() { return ($("#who").value || "").trim() || null; }

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try { const j = await r.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j); } catch (_) { /* text */ }
    throw new Error(msg);
  }
  const ct = r.headers.get("content-type") || "";
  return ct.includes("json") ? r.json() : r.text();
}

// --------------------------------------------------------------------------- //
// Hodnoty parametrov
// --------------------------------------------------------------------------- //

const metaByName = () => Object.fromEntries(state.meta.params.map(p => [p.name, p]));

/** SizeSpec: holé číslo = Pine jednotka. Na porovnanie normalizujeme na {value, unit}. */
function normSize(v, pineUnit) {
  if (v === null || v === undefined) return { value: 0, unit: pineUnit };
  if (typeof v === "object") return { value: Number(v.value), unit: v.unit || pineUnit };
  return { value: Number(v), unit: pineUnit };
}

function sameValue(meta, a, b) {
  if (meta.type === "size") {
    const x = normSize(a, meta.pine_unit), y = normSize(b, meta.pine_unit);
    return x.value === y.value && x.unit === y.unit;
  }
  if (a === null || a === undefined) return b === null || b === undefined;
  if (typeof a === "number" || typeof b === "number") return Number(a) === Number(b);
  return String(a) === String(b);
}

function setParams(values, asBase) {
  const m = metaByName();
  const out = {};
  for (const name of Object.keys(m)) {
    if (name in values) out[name] = values[name];
    else out[name] = state.meta.defaults[name];
  }
  state.params = JSON.parse(JSON.stringify(out));
  if (asBase) state.base = JSON.parse(JSON.stringify(out));
  renderParams();
}

// --------------------------------------------------------------------------- //
// Formulár parametrov
//
// Vľavo navigácia skupín (ako panel nastavení v TradingView), vpravo len aktívna
// skupina. Riadok = jeden parameter na jednom riadku; polia, ktoré Pine kreslí
// vedľa seba (`inline`, napr. hodina + minúta seansy), sú vedľa seba aj tu.
// Tooltip z Pine je na názve (dotted underline), identifikátor v ňom.
// --------------------------------------------------------------------------- //

function paramInput(meta) {
  const v = state.params[meta.name];
  const wrap = document.createElement("div");
  wrap.className = "ctl";
  const onChange = (val) => { state.params[meta.name] = val; refreshChanged(); };

  if (meta.type === "bool") {
    const i = document.createElement("input"); i.type = "checkbox"; i.checked = !!v;
    i.onchange = () => onChange(i.checked); wrap.append(i); return wrap;
  }
  if (meta.options) {
    const s = document.createElement("select");
    for (const o of meta.options) { const op = document.createElement("option"); op.value = o; op.textContent = o; s.append(op); }
    s.value = v ?? meta.default ?? meta.options[0];
    s.onchange = () => onChange(s.value); wrap.append(s); return wrap;
  }
  if (meta.type === "size") {
    const cur = normSize(v, meta.pine_unit);
    wrap.classList.add("size");
    const n = document.createElement("input"); n.type = "number"; n.step = "any"; n.value = cur.value;
    const u = document.createElement("select"); u.title = "jednotka: abs = cenové body, ticks = násobky ticku, atr = násobky ATR, pct = % ceny";
    for (const o of UNITS) { const op = document.createElement("option"); op.value = o; op.textContent = o; u.append(op); }
    u.value = cur.unit;
    const emit = () => {
      const val = Number(n.value);
      onChange(u.value === meta.pine_unit ? val : { value: val, unit: u.value });
    };
    n.oninput = emit; u.onchange = emit;
    wrap.append(n, u); return wrap;
  }
  if (meta.type === "color") {
    const i = document.createElement("input"); i.type = "color"; i.value = v || "#334155";
    i.oninput = () => onChange(i.value); wrap.append(i); return wrap;
  }
  if (meta.type === "int" || meta.type === "float") {
    const i = document.createElement("input"); i.type = "number";
    i.step = meta.type === "int" ? "1" : (meta.step ? String(meta.step) : "any");
    if (meta.min !== null && meta.min !== undefined) i.min = meta.min;
    if (meta.max !== null && meta.max !== undefined) i.max = meta.max;
    i.value = v === null || v === undefined ? "" : v;
    i.placeholder = v === null ? "—" : "";
    i.oninput = () => onChange(i.value === "" ? null : (meta.type === "int" ? parseInt(i.value, 10) : Number(i.value)));
    wrap.append(i); return wrap;
  }
  const i = document.createElement("input"); i.type = "text"; i.value = v ?? "";
  i.classList.add("text");
  i.oninput = () => onChange(i.value); wrap.append(i); return wrap;
}

function groupList() {
  const groups = [];
  for (const p of state.meta.params) if (!groups.includes(p.group)) groups.push(p.group);
  return groups;
}

/** Skupina -> riadky; parametre s rovnakým Pine `inline` kľúčom idú do jedného riadku. */
function groupRows(group) {
  const rows = [], byInline = {};
  for (const meta of state.meta.params.filter(p => p.group === group)) {
    if (meta.inline) {
      if (!byInline[meta.inline]) { byInline[meta.inline] = []; rows.push(byInline[meta.inline]); }
      byInline[meta.inline].push(meta);
    } else rows.push([meta]);
  }
  return rows;
}

function tooltipFor(meta) {
  const parts = [meta.tooltip || meta.title, "", `[${meta.name}]`];
  if (meta.min !== null && meta.min !== undefined) parts.push(`rozsah ${meta.min} – ${meta.max}`);
  if (meta.pine_unit) parts.push(`Pine jednotka: ${meta.pine_unit}`);
  if (meta.note) parts.push(meta.note);
  return parts.join("\n");
}

function renderParams() {
  const nav = $("#param-nav"), root = $("#param-groups");
  nav.innerHTML = ""; root.innerHTML = "";
  const groups = groupList();
  if (!state.activeGroup || !groups.includes(state.activeGroup)) state.activeGroup = groups[0];

  for (const g of groups) {
    const b = document.createElement("button"); b.className = "nav-item"; b.dataset.group = g;
    b.innerHTML = `<span class="nav-title">${esc(g)}</span><span class="nav-count" data-count></span>`;
    b.onclick = () => { state.activeGroup = g; $("#param-filter").value = ""; $("#only-changed").checked = false; applyParamFilter(); };
    nav.append(b);

    const sec = document.createElement("section"); sec.className = "pgroup"; sec.dataset.group = g;
    sec.innerHTML = `<h3 class="pgroup-title">${esc(g)} <span class="chip" data-count></span></h3>`;
    for (const metas of groupRows(g)) {
      const row = document.createElement("div"); row.className = "prow";
      row.dataset.names = metas.map(m => m.name).join(" ");
      row.dataset.search = metas.map(m => `${m.name} ${m.title} ${m.tooltip}`).join(" ").toLowerCase();
      const first = metas[0];
      const label = document.createElement("div"); label.className = "plabel";
      label.textContent = first.title; label.title = tooltipFor(first);
      if (first.note) label.classList.add("noted");
      const ctls = document.createElement("div"); ctls.className = "pctl";
      for (const meta of metas) {
        const ctl = paramInput(meta);
        ctl.dataset.name = meta.name;
        if (metas.length > 1 && meta !== first) {
          const cap = document.createElement("span"); cap.className = "cap"; cap.textContent = meta.title; cap.title = tooltipFor(meta);
          ctls.append(cap);
        }
        ctls.append(ctl);
      }
      const reset = document.createElement("button"); reset.className = "ghost reset"; reset.textContent = "↺";
      reset.title = "späť na hodnotu profilu";
      reset.onclick = () => { for (const m of metas) state.params[m.name] = JSON.parse(JSON.stringify(state.base[m.name] ?? null)); renderParams(); };
      row.append(label, ctls, reset);
      sec.append(row);
    }
    root.append(sec);
  }
  refreshChanged();
  applyParamFilter();
}

function refreshChanged() {
  const m = metaByName();
  let total = 0;
  const perGroup = {};
  for (const row of $$(".prow")) {
    let changed = false;
    for (const name of row.dataset.names.split(" ")) {
      const c = !sameValue(m[name], state.params[name], state.base[name]);
      const ctl = row.querySelector(`.ctl[data-name="${name}"]`);
      if (ctl) ctl.classList.toggle("changed", c);
      if (c) { changed = true; total++; perGroup[m[name].group] = (perGroup[m[name].group] || 0) + 1; }
    }
    row.classList.toggle("changed", changed);
  }
  $("#override-count").textContent = total ? `${total} zmenených` : "bez zmien";
  $("#override-count").className = total ? "chip warn" : "chip";
  for (const el of $$("[data-group]")) {
    const c = perGroup[el.dataset.group] || 0;
    const badge = el.querySelector("[data-count]");
    if (badge) { badge.textContent = c ? String(c) : ""; badge.classList.toggle("warn", c > 0); }
  }
  if ($("#only-changed").checked) applyParamFilter();
}

function applyParamFilter() {
  const q = $("#param-filter").value.trim().toLowerCase();
  const onlyChanged = $("#only-changed").checked;
  const browsing = !q && !onlyChanged;
  for (const b of $$(".nav-item")) b.classList.toggle("active", browsing && b.dataset.group === state.activeGroup);
  let shown = 0;
  for (const sec of $$(".pgroup")) {
    let visible = 0;
    for (const row of $$(".prow", sec)) {
      const hit = browsing
        ? sec.dataset.group === state.activeGroup
        : (!q || row.dataset.search.includes(q)) && (!onlyChanged || row.classList.contains("changed"));
      row.hidden = !hit; if (hit) visible++;
    }
    sec.hidden = visible === 0;
    sec.classList.toggle("titled", !browsing);
    shown += visible;
  }
  $("#param-empty").hidden = shown > 0;
}

// --------------------------------------------------------------------------- //
// Nastavenia behu
// --------------------------------------------------------------------------- //

function fillSettings() {
  const ps = $("#profile"); ps.innerHTML = `<option value="">(Pine defaulty)</option>`;
  for (const p of state.meta.profiles) { const o = document.createElement("option"); o.value = p; o.textContent = p; ps.append(o); }
  const pair = $("#pair"); pair.innerHTML = "";
  for (const p of state.meta.pairs) {
    const o = document.createElement("option"); o.value = p.pair;
    o.textContent = `${p.pair}${p.has_1m ? "" : " (bez 1m)"}`; o.dataset.from = p.from; o.dataset.to = p.to; pair.append(o);
  }
  pair.onchange = () => {
    const o = pair.selectedOptions[0]; if (!o) return;
    $("#pair-range").textContent = `dáta ${o.dataset.from} → ${o.dataset.to}`;
    $("#from").min = o.dataset.from; $("#from").max = o.dataset.to; $("#to").min = o.dataset.from; $("#to").max = o.dataset.to;
    if (!$("#to").value || $("#to").value > o.dataset.to) $("#to").value = o.dataset.to;
    if (!$("#from").value) { const d = new Date(o.dataset.to); d.setDate(d.getDate() - 365); $("#from").value = d.toISOString().slice(0, 10); }
  };
  pair.onchange();
  ps.onchange = () => loadProfile(ps.value);
  const who = $("#who");
  let saved = null;
  try { saved = localStorage.getItem("ibs.user"); } catch (_) { /* súkromný režim */ }
  who.value = saved || state.meta.user || "";
  who.onchange = () => { try { localStorage.setItem("ibs.user", who.value.trim()); } catch (_) { /* ignoruj */ } };
  $("#branch").textContent = state.meta.branch;
}

async function loadProfile(name) {
  state.profile = name || null;
  if (!name) { setParams({}, true); return; }
  const r = await api(`/api/profiles/${encodeURIComponent(name)}`);
  setParams(r.params, true);
  // profil určuje aj nástroj -> prepni pár, ak zodpovedá
  const inst = r.instrument;
  const pair = state.meta.pairs.find(p => p.instrument === inst);
  if (pair) { $("#pair").value = pair.pair; $("#pair").onchange(); }
}

function timerange() {
  const a = $("#from").value.replaceAll("-", ""), b = $("#to").value.replaceAll("-", "");
  return `${a}-${b}`;
}

async function submitRun() {
  const btn = $("#run"); btn.disabled = true; $("#run-error").hidden = true;
  try {
    const body = {
      params: state.params,
      pair: $("#pair").value,
      timerange: timerange(),
      fee: $("#fee").value === "" ? null : Number($("#fee").value) / 100,
      wallet: Number($("#wallet").value),
      timeframe_detail: $("#detail").checked ? "1m" : null,
      profile: state.profile,
      note: $("#note").value.trim(),
      user: currentUser(),
    };
    await api("/api/runs", { method: "POST", body: JSON.stringify(body) });
    await pollQueue();
  } catch (e) {
    $("#run-error").textContent = e.message; $("#run-error").hidden = false;
  } finally { btn.disabled = false; }
}

// --------------------------------------------------------------------------- //
// Fronta
// --------------------------------------------------------------------------- //

async function pollQueue() {
  const jobs = await api("/api/queue");
  const box = $("#queue");
  $("#queue-count").textContent = jobs.length ? String(jobs.length) : "";
  if (!jobs.length) {
    box.innerHTML = `<div class="muted">Nič nebeží.</div>`;
    if (state.pollTimer) { clearTimeout(state.pollTimer); state.pollTimer = null; if (!$("#view-history").hidden) loadRuns(); }
    return;
  }
  box.innerHTML = "";
  for (const j of jobs) {
    const el = document.createElement("div"); el.className = "job";
    el.innerHTML = `<div class="head"><span class="chip ${j.status === "running" ? "warn" : ""}">${j.status}</span>
      <b>${j.settings.pair}</b> <span class="muted">${j.settings.timerange}</span> <span class="spacer"></span>
      <span class="muted">${esc(j.note || "")}</span> <button class="ghost small" data-cancel="${j.id}">✕</button></div>
      ${j.status === "running" ? `<pre>${esc((j.log_tail || []).slice(-12).join("\n"))}</pre>` : ""}`;
    el.querySelector("[data-cancel]").onclick = async () => { await api(`/api/queue/${j.id}/cancel`, { method: "POST" }); pollQueue(); };
    box.append(el);
  }
  clearTimeout(state.pollTimer);
  state.pollTimer = setTimeout(pollQueue, 2000);
}

// --------------------------------------------------------------------------- //
// História
// --------------------------------------------------------------------------- //

const fmt = (v, d = 2) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toFixed(d);
const signed = (v, d = 2, suffix = "") => v === null || v === undefined ? "—" :
  `<span class="${v >= 0 ? "pos" : "neg"}">${v >= 0 ? "+" : ""}${Number(v).toFixed(d)}${suffix}</span>`;
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function fmtVal(v) { return typeof v === "object" && v !== null ? `${v.value} ${v.unit}` : String(v); }

async function loadRuns() {
  const q = $("#search").value.trim();
  const r = await api(`/api/runs?q=${encodeURIComponent(q)}`);
  $("#search-count").textContent = `${r.total} behov`;
  const tb = $("#runs-table tbody"); tb.innerHTML = "";
  for (const run of r.runs) {
    const res = run.result || {};
    const tr = document.createElement("tr");
    const ov = Object.entries(run.overrides || {}).map(([k, v]) => `<span class="kv">${k}=${esc(fmtVal(v))}</span>`).join("");
    const failed = run.status !== "done";
    tr.innerHTML = `<td><div>${run.id}</div><div class="muted small">${(run.created || "").replace("T", " ").slice(0, 16)} · ${esc(run.user || "")}</div></td>
      <td>${esc(run.settings?.pair || "")}</td><td>${esc(run.settings?.timerange || "")}<div class="muted small">fee ${run.settings?.fee != null ? (run.settings.fee * 100).toFixed(3) + " %" : "—"} · ${run.settings?.wallet ?? ""}</div></td>
      <td class="num">${failed ? `<span class="status-failed">${esc(run.status)}</span>` : res.trades ?? "—"}</td>
      <td class="num">${signed(res.pnl_pct, 2, " %")}</td><td class="num">${fmt(res.profit_factor, 3)}</td>
      <td class="num">${fmt(res.winrate, 1)}</td><td class="num">${fmt(res.max_drawdown_pct, 2)}</td>
      <td class="num">${res.break_even_pct != null ? fmt(res.break_even_pct, 4) : "—"}</td>
      <td class="ov">${ov || '<span class="muted">Pine defaulty</span>'}</td><td>${esc(run.note || "")}</td>`;
    tr.onclick = () => openRun(run.id);
    tb.append(tr);
  }
}

async function openRun(id) {
  const r = await api(`/api/runs/${id}`);
  const rec = r.record;
  state.detailId = id;
  $("#runs-table").parentElement.parentElement.hidden = true;
  $("#run-detail").hidden = false;
  $("#detail-title").textContent = `${rec.settings.pair} · ${rec.settings.timerange}`;
  $("#detail-meta").textContent = `${rec.id} · ${rec.user || ""} · ${(rec.created || "").replace("T", " ").slice(0, 16)} · profil ${rec.settings.profile || "(Pine)"} · poplatok ${rec.settings.fee != null ? (rec.settings.fee * 100).toFixed(3) + " %" : "—"} · peňaženka ${rec.settings.wallet} · detail ${rec.settings.timeframe_detail || "bez"}${rec.note ? " · " + rec.note : ""}`;
  $("#download-profile").href = `/api/runs/${id}/profile.json`;
  $("#detail-error").hidden = !rec.error; $("#detail-error").textContent = rec.error || "";

  const res = rec.result || {};
  const cur = res.stake_currency || "USDT";
  $("#cards").innerHTML = rec.status !== "done" ? "" : [
    card("Total PnL", signed(res.pnl_abs, 2, " " + cur), signed(res.pnl_pct, 2, " %")),
    card("Max drawdown", `${fmt(res.max_drawdown_abs)} ${cur}`, `${fmt(res.max_drawdown_pct)} %`),
    card("Profitable trades", `${fmt(res.winrate, 2)} %`, `${res.wins}/${res.trades}`),
    card("Profit factor", fmt(res.profit_factor, 3), ""),
    card("Break-even poplatok", res.break_even_pct != null ? `${fmt(res.break_even_pct, 4)} %` : "—", "na stranu; Binance taker 0,05 %"),
    card("Buy & hold", signed(res.market_change_pct, 2, " %"), `${res.duration_s ?? "?"} s výpočtu`),
  ].join("");

  drawChart(rec.series || { equity: [], market: [] }, res);

  const ov = rec.overrides || {};
  $("#detail-overrides").innerHTML = Object.keys(ov).length
    ? `<table class="runs"><tbody>${Object.entries(ov).map(([k, v]) => `<tr><td><code>${k}</code></td><td>${esc(fmtVal(v))}</td><td class="muted">Pine: ${esc(fmtVal(state.meta.defaults[k]))}</td></tr>`).join("")}</tbody></table>`
    : `<div class="muted">Pine defaulty bez zmeny.</div>`;
  const ex = res.exits || {};
  $("#detail-exits").innerHTML = Object.keys(ex).length
    ? `<table class="runs"><thead><tr><th>Dôvod</th><th class="num">n</th><th class="num">PnL ${cur}</th></tr></thead><tbody>${Object.entries(ex).map(([k, v]) => `<tr><td>${k}</td><td class="num">${v.n}</td><td class="num">${signed(v.pnl_abs)}</td></tr>`).join("")}</tbody></table>`
    : `<div class="muted">—</div>`;

  const trades = r.trades || [];
  $("#trade-count").textContent = trades.length;
  const cols = ["open_date", "close_date", "open_rate", "close_rate", "amount", "profit_abs", "profit_ratio", "exit_reason", "enter_tag"];
  $("#trades thead").innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>`;
  $("#trades tbody").innerHTML = trades.map(t => `<tr>${cols.map(c => {
    let v = t[c];
    if (c.endsWith("_date") && v) v = String(v).replace("T", " ").slice(0, 16);
    if (c === "profit_abs") return `<td class="num">${signed(v)}</td>`;
    if (c === "profit_ratio") return `<td class="num">${signed(v * 100, 2, " %")}</td>`;
    if (typeof v === "number") v = Number.isInteger(v) ? v : v.toFixed(4);
    return `<td>${esc(v ?? "")}</td>`;
  }).join("")}</tr>`).join("");

  $("#detail-params").innerHTML = `<table class="runs"><tbody>${Object.entries(rec.params || {}).filter(([k]) => !k.startsWith("_")).map(([k, v]) => `<tr><td><code>${k}</code></td><td>${esc(fmtVal(v))}</td></tr>`).join("")}</tbody></table>`;
  $("#detail-log").textContent = await api(`/api/runs/${id}/log`);
}

function card(k, v, s) { return `<div class="kcard"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`; }

/** Krivka ako v Strategy Testeri: stĺpce za obchod (vlastná skrytá os), kumulatívny PnL, buy and hold. */
function drawChart(series, res) {
  const eq = series.equity || [], mk = series.market || [];
  if (!eq.length) { $("#chart").innerHTML = `<div class="muted">Bez obchodov, nie je čo kresliť.</div>`; return; }
  const x = eq.map(e => e[0]), bar = eq.map(e => e[1]), cum = eq.map(e => e[2]);
  const span = new Date(x[x.length - 1]) - new Date(x[0]);
  const width = Math.max(span / Math.max(eq.length, 1) * 0.7, 60000);
  const traces = [
    { type: "bar", x, y: bar, name: "PnL obchodu", yaxis: "y2", width, opacity: 0.85,
      marker: { color: bar.map(v => v >= 0 ? GREEN : RED), line: { width: 0 } },
      hovertemplate: "%{x|%d.%m. %H:%M}<br>%{y:+.2f} %<extra></extra>" },
    { type: "scatter", x, y: cum, name: "Kumulatívny PnL", mode: "lines+markers", line: { color: GREEN, width: 2 },
      marker: { size: 4 }, fill: "tozeroy", fillcolor: "rgba(8,153,129,0.08)",
      hovertemplate: "%{x|%d.%m. %H:%M}<br>%{y:+.2f} %<extra></extra>" },
  ];
  let lo = Math.min(0, ...cum), hi = Math.max(0, ...cum);
  if (mk.length) {
    traces.push({ type: "scatter", x: mk.map(m => m[0]), y: mk.map(m => m[1]), name: "Buy and hold", mode: "lines",
      line: { color: BLUE, width: 1.2 }, hovertemplate: "%{x|%d.%m.}<br>%{y:+.2f} %<extra></extra>" });
    lo = Math.min(lo, ...mk.map(m => m[1])); hi = Math.max(hi, ...mk.map(m => m[1]));
  }
  const pad = (hi - lo) * 0.06 || 1; lo -= pad; hi += pad;
  const scale = (hi - lo) / Math.max(Math.max(...bar.map(Math.abs)) * 6, 1e-9);
  Plotly.newPlot("chart", traces, {
    height: 460, margin: { l: 10, r: 56, t: 10, b: 30 }, template: "plotly_white", hovermode: "x unified",
    legend: { orientation: "h", yanchor: "bottom", y: 1.0, x: 0 }, bargap: 0.2,
    yaxis: { ticksuffix: " %", range: [lo, hi], side: "right" },
    yaxis2: { overlaying: "y", range: [lo / scale, hi / scale], showgrid: false, showticklabels: false },
    xaxis: { showgrid: false },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  }, { displaylogo: false, responsive: true });
}

function closeDetail() {
  $("#run-detail").hidden = true;
  $("#runs-table").parentElement.parentElement.hidden = false;
  state.detailId = null;
}

async function loadDetailIntoForm() {
  const r = await api(`/api/runs/${state.detailId}`);
  const rec = r.record;
  $("#profile").value = rec.settings.profile || "";
  state.profile = rec.settings.profile || null;
  // základ = profil (aby sa zvýraznili odchýlky), hodnoty = beh
  if (state.profile) { const p = await api(`/api/profiles/${encodeURIComponent(state.profile)}`); setParams(p.params, true); }
  else setParams({}, true);
  setParams(rec.params, false);
  $("#pair").value = rec.settings.pair; $("#pair").onchange();
  const [a, b] = rec.settings.timerange.split("-");
  $("#from").value = `${a.slice(0, 4)}-${a.slice(4, 6)}-${a.slice(6)}`; $("#to").value = `${b.slice(0, 4)}-${b.slice(4, 6)}-${b.slice(6)}`;
  $("#fee").value = rec.settings.fee != null ? (rec.settings.fee * 100) : ""; $("#wallet").value = rec.settings.wallet;
  $("#detail").checked = !!rec.settings.timeframe_detail; $("#note").value = rec.note || "";
  showView("new");
}

// --------------------------------------------------------------------------- //
// Git
// --------------------------------------------------------------------------- //

async function gitStatus() {
  try {
    const s = await api("/api/git/status");
    const parts = [];
    if (s.uncommitted_runs) parts.push(`${s.uncommitted_runs} necommitnutých`);
    if (s.ahead) parts.push(`↑${s.ahead}`);
    if (s.behind) parts.push(`↓${s.behind}`);
    $("#git-status").textContent = parts.length ? parts.join(" · ") : "synchronizované";
  } catch (e) { $("#git-status").textContent = "git: " + e.message; }
}

async function gitAction(kind) {
  const out = $("#git-output"); out.hidden = false; out.textContent = `git ${kind} …`;
  try {
    const r = await api(`/api/git/${kind}`, { method: "POST", body: kind === "push" ? JSON.stringify({ author: currentUser() }) : undefined });
    out.textContent = (r.ok ? "OK\n" : "CHYBA\n") + r.output;
    $("#git-status").textContent = r.uncommitted_runs ? `${r.uncommitted_runs} necommitnutých` : "synchronizované";
    if (kind === "pull" && !$("#view-history").hidden) loadRuns();
  } catch (e) { out.textContent = e.message; }
}

// --------------------------------------------------------------------------- //
// Navigácia a štart
// --------------------------------------------------------------------------- //

function showView(name) {
  for (const b of $$(".tabs button")) b.classList.toggle("active", b.dataset.view === name);
  $("#view-new").hidden = name !== "new"; $("#view-history").hidden = name !== "history";
  if (name === "history") loadRuns();
}

async function init() {
  state.meta = await api("/api/meta");
  fillSettings();
  const preferred = ["btcusdt_3m_binance_ny_sl_risk1", "btcusdt_3m_binance_ny_sl", "btcusdt_3m_binance_ny"].find(p => state.meta.profiles.includes(p)) || "";
  $("#profile").value = preferred;
  await loadProfile(preferred);
  pollQueue();
  gitStatus();

  $$(".tabs button").forEach(b => b.onclick = () => showView(b.dataset.view));
  $("#run").onclick = submitRun;
  $("#param-filter").oninput = applyParamFilter;
  $("#only-changed").onchange = applyParamFilter;
  $("#reset-params").onclick = () => setParams(state.base, false);
  $("#search-btn").onclick = loadRuns;
  $("#search").onkeydown = e => { if (e.key === "Enter") loadRuns(); };
  $("#search-help-btn").onclick = () => $("#search-help").hidden = !$("#search-help").hidden;
  $("#back").onclick = closeDetail;
  $("#load-params").onclick = loadDetailIntoForm;
  $("#delete-run").onclick = async () => {
    if (!confirm("Zmazať tento beh z histórie? (zmaže adresár v runs/)")) return;
    await api(`/api/runs/${state.detailId}`, { method: "DELETE" }); closeDetail(); loadRuns();
  };
  $("#git-pull").onclick = () => gitAction("pull");
  $("#git-push").onclick = () => gitAction("push");
}

init().catch(e => { document.body.insertAdjacentHTML("afterbegin", `<div class="error">${esc(e.message)}</div>`); });
