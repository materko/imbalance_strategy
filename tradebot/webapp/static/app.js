/* IBS Backtester — jednostránková aplikácia bez frameworku. */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const GREEN = "#089981", RED = "#f23645", BLUE = "#2962ff";
const UNITS = ["abs", "ticks", "atr", "pct"];

const state = {
  meta: null,          // /api/meta; params/defaults/profiles… sú vždy aktívnej stratégie (viď setStrategy)
  strategy: "ibs",     // kľúč aktívnej stratégie vo formulári
  params: {},          // aktuálne hodnoty formulára (v tvare pre config_cls.from_dict)
  base: {},            // hodnoty východiskového profilu (na zvýraznenie odchýlok)
  profile: null,
  pollTimer: null,
  detailId: null,
  activeGroup: null,
  profileInstrument: null,
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
// Vľavo navigácia skupín (ako panel nastavení v TradingView), vpravo všetky skupiny
// pod sebou v jednom dlhom zozname — klik vľavo naskroluje na skupinu a zvýraznenie
// sleduje, kde práve si. Riadok = jeden parameter na jednom riadku; polia, ktoré Pine kreslí
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
    i.onchange = () => { onChange(i.checked); if (meta.type === "bool") applyParamFilter(); };
    wrap.append(i); return wrap;
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

/**
 * Zrkadlo kresliaceho prepínača (napr. `showSR`) vedľa hlavného prepínača feature
 * (`enableSrTrading`), keď sú v Pine v rôznych skupinách. Je to ten istý parameter,
 * len na druhom mieste — zmena sa prejaví aj v jeho domovskej skupine.
 */
function showMirror(show) {
  const lab = document.createElement("label"); lab.className = "mirror";
  lab.title = `${show.tooltip || show.title}\n\n[${show.name}] — to isté pole ako v skupine „${show.group}“`;
  const i = document.createElement("input"); i.type = "checkbox"; i.checked = !!state.params[show.name];
  i.onchange = () => { state.params[show.name] = i.checked; renderParams(); };
  lab.append(i, document.createTextNode("kresliť"));
  lab.classList.toggle("changed", !sameValue(show, state.params[show.name], state.base[show.name]));
  return lab;
}

/** Riadok má zmysel, keď je zapnutý aspoň jeden z jeho prepínačov — a ten sám je viditeľný. */
function dependencyMet(row, seen = new Set()) {
  const deps = (row.dataset.dependsOn || "").split(" ").filter(Boolean);
  if (!deps.length) return true;
  return deps.some(name => {
    if (!state.params[name] || seen.has(name)) return false;
    const owner = $(`.prow[data-names~="${name}"]`);
    return !owner || dependencyMet(owner, new Set([...seen, name]));
  });
}

function renderParams() {
  const nav = $("#param-nav"), root = $("#param-groups");
  const m = metaByName();
  nav.innerHTML = ""; root.innerHTML = "";
  const groups = groupList();
  if (!state.activeGroup || !groups.includes(state.activeGroup)) state.activeGroup = groups[0];

  for (const g of groups) {
    const b = document.createElement("button"); b.className = "nav-item"; b.dataset.group = g;
    b.innerHTML = `<span class="nav-title">${esc(g)}</span><span class="nav-count" data-count></span>`;
    b.onclick = () => { $("#param-filter").value = ""; $("#only-changed").checked = false; applyParamFilter(); scrollToGroup(g); };
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
      const deps = metas.map(m => m.depends_on).find(d => d && d.length);
      if (deps) row.dataset.dependsOn = deps.join(" ");
      const ctls = document.createElement("div"); ctls.className = "pctl";
      for (const meta of metas) {
        const ctl = paramInput(meta);
        ctl.dataset.name = meta.name;
        if (metas.length > 1 && meta !== first) {
          const cap = document.createElement("span"); cap.className = "cap"; cap.textContent = meta.title; cap.title = tooltipFor(meta);
          ctls.append(cap);
        }
        ctls.append(ctl);
        const show = meta.show_param && m[meta.show_param];
        if (show && show.group !== meta.group) ctls.append(showMirror(show));
      }
      const hint = document.createElement("span"); hint.className = "dep-hint"; hint.hidden = true; ctls.append(hint);
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

/** Klik na skupinu vľavo: dlhý zoznam sa presunie na jej nadpis (pod prilepenú hlavičku). */
function scrollToGroup(g) {
  const sec = $$(".pgroup").find(s => s.dataset.group === g);
  if (!sec) return;
  state.activeGroup = g;
  for (const b of $$(".nav-item")) b.classList.toggle("active", b.dataset.group === g);
  state.spyLock = Date.now() + 300;  // spy nech neprepíše práve zvolenú skupinu
  // Skroluje sa len zoznam parametrov (má vlastné okno), stránka stojí — skupiny vľavo
  // ostávajú na mieste. Skok bez animácie, ako v paneli nastavení TradingView.
  $(".param-content").scrollTop = sec.offsetTop - 6;
}

/** Zvýraznenie v navigácii sleduje skupinu, ktorej nadpis je práve pri hornom okraji okna zoznamu. */
function spyGroups() {
  if (Date.now() < (state.spyLock || 0) || $("#view-new").hidden) return;
  const secs = $$(".pgroup").filter(s => !s.hidden);
  if (!secs.length) return;
  const box = $(".param-content");
  const line = box.getBoundingClientRect().top + 30;
  let cur = secs[0];
  for (const s of secs) if (s.getBoundingClientRect().top <= line) cur = s;
  if (box.scrollTop + box.clientHeight >= box.scrollHeight - 2) cur = secs[secs.length - 1];
  if (cur.dataset.group !== state.activeGroup) {
    state.activeGroup = cur.dataset.group;
    for (const b of $$(".nav-item")) b.classList.toggle("active", b.dataset.group === state.activeGroup);
  }
}
$(".param-content").addEventListener("scroll", spyGroups, { passive: true });

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
  for (const b of $$(".nav-item")) b.classList.toggle("active", b.dataset.group === state.activeGroup);
  let shown = 0;
  const collapsed = {};  // prepínač -> počet podnastavení, ktoré kvôli nemu nevidno
  for (const sec of $$(".pgroup")) {
    let visible = 0;
    for (const row of $$(".prow", sec)) {
      let hit = browsing || ((!q || row.dataset.search.includes(q)) && (!onlyChanged || row.classList.contains("changed")));
      // Podnastavenia vypnutej feature sa neukazujú (hľadanie a „len zmenené" ich ukážu vždy).
      if (hit && browsing && !dependencyMet(row)) {
        hit = false;
        for (const d of row.dataset.dependsOn.split(" ")) collapsed[d] = (collapsed[d] || 0) + 1;
      }
      row.hidden = !hit; if (hit) visible++;
    }
    sec.hidden = visible === 0;
    shown += visible;
  }
  for (const row of $$(".prow")) {
    const hint = row.querySelector(".dep-hint"); if (!hint) continue;
    const n = row.dataset.names.split(" ").reduce((s, name) => s + (collapsed[name] || 0), 0);
    hint.hidden = !n || row.hidden;
    hint.textContent = n ? `▸ ${n} ${n === 1 ? "nastavenie skryté" : n < 5 ? "nastavenia skryté" : "nastavení skrytých"}` : "";
    hint.title = "podnastavenia sa ukážu po zapnutí prepínača";
  }
  $("#param-empty").hidden = shown > 0;
}

// --------------------------------------------------------------------------- //
// Nastavenia behu
// --------------------------------------------------------------------------- //

/** Stratégia vo formulári: metadáta, defaulty a profily sú na najvyššej úrovni `state.meta`
 *  vždy tie aktívnej stratégie, takže formulár, profily a diff nič iné nepoznajú. */
function strategyMeta(key) { return (state.meta.strategy_meta || {})[key] || null; }
function strategySpec(key) { return (state.meta.strategies || []).find(s => s.key === key) || null; }

function setStrategy(key) {
  const sm = strategyMeta(key);
  if (!sm) return;
  state.strategy = key;
  Object.assign(state.meta, sm);
  state.activeGroup = null;
  $("#strategy").value = key;
  fillProfiles();
  const spec = strategySpec(key);
  if (spec && spec.default_timeframe) fillTimeframes($("#pair").value, spec.default_timeframe);
}

function fillProfiles() {
  const ps = $("#profile"); ps.innerHTML = `<option value="">(Pine defaulty)</option>`;
  for (const p of state.meta.profiles) {
    const o = document.createElement("option"); o.value = p;
    o.textContent = `${p} — ${(state.meta.profile_titles || {})[p] || ""}`; o.title = (state.meta.profile_titles || {})[p] || p; ps.append(o);
  }
}

function fillSettings() {
  const ss = $("#strategy"); ss.innerHTML = "";
  for (const s of state.meta.strategies) { const o = document.createElement("option"); o.value = s.key; o.textContent = s.title; ss.append(o); }
  ss.onchange = async () => { setStrategy(ss.value); $("#profile").value = ""; await loadProfile(""); };
  fillProfiles();
  const pair = $("#pair"); pair.innerHTML = "";
  for (const p of state.meta.pairs) {
    const o = document.createElement("option"); o.value = p.pair;
    o.textContent = `${p.pair}${p.has_1m ? "" : " (bez 1m)"}`; o.dataset.from = p.from; o.dataset.to = p.to; pair.append(o);
  }
  pair.onchange = () => {
    const o = pair.selectedOptions[0]; if (!o) return;
    checkPairProfile();
    $("#pair-range").textContent = `dáta ${o.dataset.from} → ${o.dataset.to}`;
    fillTimeframes(o.value);
    $("#from").min = o.dataset.from; $("#from").max = o.dataset.to; $("#to").min = o.dataset.from; $("#to").max = o.dataset.to;
    if (!$("#to").value || $("#to").value > o.dataset.to) $("#to").value = o.dataset.to;
    if (!$("#from").value) { const d = new Date(o.dataset.to); d.setDate(d.getDate() - 365); $("#from").value = d.toISOString().slice(0, 10); }
  };
  pair.onchange();
  $("#profile").onchange = () => loadProfile($("#profile").value);
  const who = $("#who");
  let saved = null;
  try { saved = localStorage.getItem("ibs.user"); } catch (_) { /* súkromný režim */ }
  who.value = saved || state.meta.user || "";
  who.onchange = () => { try { localStorage.setItem("ibs.user", who.value.trim()); } catch (_) { /* ignoruj */ } };
  $("#branch").textContent = state.meta.branch;
}

/** TF grafu pre beh: ponuka podľa stiahnutých dát páru, zachová voľbu, inak 3m. */
function fillTimeframes(pairName, wanted) {
  const sel = $("#tf");
  const keep = wanted || sel.value || "3m";
  const p = state.meta.pairs.find(x => x.pair === pairName);
  const tfs = ((p && p.timeframes) || ["3m"]).filter(t => t in TF_MINUTES);
  sel.innerHTML = "";
  for (const t of tfs) { const o = document.createElement("option"); o.value = t; o.textContent = t; sel.append(o); }
  sel.value = tfs.includes(keep) ? keep : (tfs.includes("3m") ? "3m" : tfs[0]);
}

async function loadProfile(name) {
  state.profile = name || null;
  state.profileInstrument = null;
  if (!name) { setParams({}, true); checkPairProfile(); return; }
  const r = await api(`/api/profiles/${encodeURIComponent(name)}?strategy=${encodeURIComponent(state.strategy)}`);
  state.profileInstrument = r.instrument;
  setParams(r.params, true);
  // profil určuje aj nástroj -> prepni pár, ak zodpovedá
  const inst = r.instrument;
  const pair = state.meta.pairs.find(p => p.instrument === inst);
  if (pair) { $("#pair").value = pair.pair; $("#pair").onchange(); }
}

/** Profil je ladený na konkrétny nástroj — BTC prahy v bodoch na ETH dajú stovky nezmyselných obchodov. */
function checkPairProfile() {
  const box = $("#pair-warn");
  const pair = state.meta.pairs.find(p => p.pair === $("#pair").value);
  if (!pair || !state.profileInstrument || pair.instrument === state.profileInstrument) { box.hidden = true; return; }
  const fit = state.meta.profiles.filter(p => (state.meta.profile_instruments || {})[p] === pair.instrument);
  box.textContent = `Profil ${state.profile} je pre iný nástroj (${state.profileInstrument}). Prahy v bodoch/tickoch na ${pair.pair} nesedia a výsledok nebude porovnateľný. Pre tento pár: ${fit.join(", ") || "(Pine defaulty) alebo profil z docs/profily_archiv/"}.`;
  box.hidden = false;
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
      strategy: state.strategy,
      pair: $("#pair").value,
      timeframe: $("#tf").value,
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
      <b>${j.settings.pair}</b> <span class="muted">${j.settings.timeframe || "3m"} · ${j.settings.timerange}</span> <span class="spacer"></span>
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
    const strat = run.settings?.strategy || "ibs";
    tr.innerHTML = `<td><div>${run.id}</div><div class="muted small">${(run.created || "").replace("T", " ").slice(0, 16)} · ${esc(run.user || "")}</div></td>
      <td title="${esc(strat)}">${esc((strategySpec(strat) || {}).title || strat)}</td>
      <td>${esc(run.settings?.pair || "")}<div class="muted small">${esc(run.settings?.timeframe || "3m")}</div></td><td>${esc(run.settings?.timerange || "")}<div class="muted small">fee ${run.settings?.fee != null ? (run.settings.fee * 100).toFixed(3) + " %" : "—"} · ${run.settings?.wallet ?? ""}</div></td>
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
  const runStrategy = rec.settings.strategy || "ibs";
  const runMeta = strategyMeta(runStrategy) || state.meta;
  $("#detail-title").textContent = `${(strategySpec(runStrategy) || {}).title || runStrategy} · ${rec.settings.pair} · ${rec.settings.timeframe || "3m"} · ${rec.settings.timerange}`;
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
    ? `<table class="runs"><tbody>${Object.entries(ov).map(([k, v]) => `<tr><td><code>${k}</code></td><td>${esc(fmtVal(v))}</td><td class="muted">Pine: ${esc(fmtVal(runMeta.defaults[k]))}</td></tr>`).join("")}</tbody></table>`
    : `<div class="muted">Pine defaulty bez zmeny.</div>`;
  const ex = res.exits || {};
  $("#detail-exits").innerHTML = Object.keys(ex).length
    ? `<table class="runs"><thead><tr><th>Dôvod</th><th class="num">n</th><th class="num">PnL ${cur}</th></tr></thead><tbody>${Object.entries(ex).map(([k, v]) => `<tr><td>${k}</td><td class="num">${v.n}</td><td class="num">${signed(v.pnl_abs)}</td></tr>`).join("")}</tbody></table>`
    : `<div class="muted">—</div>`;

  const trades = r.trades || [];
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

// --------------------------------------------------------------------------- //
// Graf páru s kresbami enginu
//
// Sviečky idú z feather súborov po oknách (/api/candles), kresby behu (zóny, TP/SL
// boxy, štítky…) z chart.json.gz orezané na okno (/api/runs/<id>/chart). Boxy a
// čiary sa kreslia ako scatter trace na skupinu štýlov (nie plotly shapes — tých
// by boli tisíce a graf by sa zasekával); pásy seáns sú shapes, tých je pár.
// Časy sú UTC: Plotly ignoruje časové pásmo v reťazci, tak mu dávame UTC text.
// --------------------------------------------------------------------------- //

// Vrstvy grafu (prepínače) a názvy druhov kresieb dodáva stratégia cez /api/meta
// (`strategies[].layers`, `kind_titles`); vrstva „Obchody Freqtrade" je spoločná.
const TRADES_LAYER = { id: "trades", title: "Obchody Freqtrade", kinds: [], sw: GREEN, hollow_kinds: [] };
function layersFor(strategyKey) {
  const spec = strategySpec(strategyKey);
  const layers = [...((spec && spec.layers) || []), TRADES_LAYER];
  return {
    layers,
    byKind: Object.fromEntries(layers.flatMap(l => l.kinds.map(k => [k, l.id]))),
    titles: (spec && spec.kind_titles) || {},
    hollow: new Set(layers.flatMap(l => l.hollow_kinds || [])),
  };
}
const TF_MINUTES = { "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60 };
const SPANS = [["4 h", 4 * 3600e3], ["12 h", 12 * 3600e3], ["1 deň", 86400e3], ["3 dni", 3 * 86400e3], ["1 týždeň", 7 * 86400e3]];
const MAX_CANDLES = 6000;  // rovnaké ako server (tradebot/webapp/chart.py)
const DASH = { dotted: "dot", dashed: "dash" };

const pc = { rec: null, trades: [], runFrom: 0, runTo: 0, from: 0, to: 0, tf: "auto", layers: {}, meta: null, last: null,
  seq: 0, bound: false, relayoutTimer: null, quietUntil: 0, strategy: "ibs", L: null };

const utc = ms => new Date(ms).toISOString().slice(0, 19).replace("T", " ");
const parseUtc = s => Date.parse(String(s).replace(" ", "T").replace(/(\.\d+)?$/, "Z"));
const fmtPrice = v => Number(v).toLocaleString("en-US", { maximumFractionDigits: 6 });

function layerPrefsKey() { return `tradebot.layers.${pc.strategy}`; }

function loadLayerPrefs() {
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(layerPrefsKey()) || "null"); } catch (_) { /* ignoruj */ }
  pc.layers = {};
  for (const l of pc.L.layers) pc.layers[l.id] = saved && l.id in saved ? !!saved[l.id] : true;
}

function tfOptions() {
  const p = state.meta.pairs.find(x => x.pair === pc.rec.settings.pair);
  const tfs = (p && p.timeframes && p.timeframes.length) ? p.timeframes : ["3m"];
  return tfs.filter(t => t in TF_MINUTES);
}

function initPairChart(rec, trades) {
  pc.rec = rec; pc.trades = trades; pc.meta = null; pc.last = null; pc.seq++;
  pc.strategy = rec.settings.strategy || "ibs";
  pc.L = layersFor(pc.strategy);
  const [a, b] = rec.settings.timerange.split("-");
  pc.runFrom = Date.parse(`${a.slice(0, 4)}-${a.slice(4, 6)}-${a.slice(6)}T00:00:00Z`);
  pc.runTo = Date.parse(`${b.slice(0, 4)}-${b.slice(4, 6)}-${b.slice(6)}T00:00:00Z`);
  loadLayerPrefs();
  $("#pc-title").textContent = `${rec.settings.pair} · beh na ${rec.settings.timeframe || "3m"} · UTC`;

  const span = $("#pc-span"); span.innerHTML = "";
  for (const [t, ms] of SPANS) { const o = document.createElement("option"); o.value = ms; o.textContent = t; span.append(o); }
  span.value = String(86400e3);
  span.onchange = () => setWindow(pc.from, pc.from + Number(span.value));

  const tf = $("#pc-tf"); tf.innerHTML = `<option value="auto">auto</option>`;
  for (const t of tfOptions()) { const o = document.createElement("option"); o.value = t; o.textContent = t; tf.append(o); }
  tf.value = "auto"; pc.tf = "auto";
  tf.onchange = () => { pc.tf = tf.value; loadPairChart(); };

  $("#pc-start").onclick = () => setWindow(pc.runFrom, pc.runFrom + spanMs());
  $("#pc-prev").onclick = () => setWindow(pc.from - spanMs(), pc.from);
  $("#pc-next").onclick = () => setWindow(pc.to, pc.to + spanMs());
  $("#pc-first-trade").onclick = () => { if (pc.trades.length) jumpToTrade(pc.trades[0]); };
  $("#pc-first-trade").disabled = !pc.trades.length;
  $("#pc-goto").onchange = () => { const v = $("#pc-goto").value; if (v) { const t0 = Date.parse(v + ":00Z"); setWindow(t0, t0 + spanMs()); } };

  $("#pc-note").textContent = rec.has_chart ? "" :
    "Tento beh nemá uložené kresby enginu (spustený staršou verziou) — graf ukáže sviečky a obchody bez zón a štítkov.";
  renderLayerToggles();

  if (pc.trades.length) jumpToTrade(pc.trades[0]);
  else setWindow(pc.runFrom, pc.runFrom + 86400e3);
}

function spanMs() { return Math.max(pc.to - pc.from, 15 * 60e3) || 86400e3; }

function chooseTf(span) {
  const opts = tfOptions();
  if (pc.tf !== "auto") return opts.includes(pc.tf) ? pc.tf : (opts[0] || "3m");
  const fine = opts.filter(t => span / (TF_MINUTES[t] * 60e3) <= MAX_CANDLES * 0.9);
  const idx = Math.max(opts.indexOf(pc.rec.settings.timeframe || "3m"), 0);  // jemnejšie než TF behu nemá zmysel
  const ok = fine.filter(t => opts.indexOf(t) >= idx);
  return ok[0] || fine[0] || opts[opts.length - 1] || "3m";
}

function setWindow(from, to) {
  if (!(to > from)) return;
  pc.from = Math.round(from); pc.to = Math.round(to);
  const preset = SPANS.find(([, ms]) => Math.abs(ms - (pc.to - pc.from)) < 60e3);
  $("#pc-span").value = preset ? String(preset[1]) : "";
  $("#pc-window").textContent = `${utc(pc.from).slice(0, 16)} → ${utc(pc.to).slice(0, 16)}`;
  loadPairChart();
}

function jumpToTrade(t) {
  const open = Date.parse(t.open_date), close = Date.parse(t.close_date || t.open_date);
  const dur = Math.max(close - open, 15 * 60e3);
  const pad = Math.max(dur * 0.6, 2 * 3600e3);
  for (const tr of $$("#trades tbody tr")) tr.classList.toggle("hl", pc.trades[Number(tr.dataset.trade)] === t);
  setWindow(open - pad, close + pad);
  $("#pair-chart").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderLayerToggles() {
  const box = $("#pc-layers"); box.innerHTML = "";
  const counts = (pc.meta && pc.meta.counts) || {};
  for (const l of pc.L.layers) {
    if (!pc.rec.has_chart && l.id !== "trades") continue;
    const n = l.id === "trades" ? pc.trades.length : l.kinds.reduce((s, k) => s + (counts[k] || 0), 0);
    const lab = document.createElement("label"); lab.classList.toggle("off", !pc.layers[l.id]);
    lab.innerHTML = `<input type="checkbox" ${pc.layers[l.id] ? "checked" : ""}> <span class="sw" style="background:${l.sw}"></span>${esc(l.title)} <span class="n">${pc.meta || l.id === "trades" ? n : ""}</span>`;
    lab.querySelector("input").onchange = e => {
      pc.layers[l.id] = e.target.checked; lab.classList.toggle("off", !e.target.checked);
      try { localStorage.setItem(layerPrefsKey(), JSON.stringify(pc.layers)); } catch (_) { /* ignoruj */ }
      if (pc.last) renderPairChart(pc.last.candles, pc.last.objects);
    };
    box.append(lab);
  }
}

async function loadPairChart() {
  const seq = ++pc.seq;
  const el = $("#pair-chart"); el.classList.add("loading");
  const tf = chooseTf(pc.to - pc.from);
  const q = `from=${pc.from}&to=${pc.to}`;
  try {
    const [candles, chart] = await Promise.all([
      api(`/api/candles?pair=${encodeURIComponent(pc.rec.settings.pair)}&tf=${tf}&${q}`),
      pc.rec.has_chart ? api(`/api/runs/${pc.rec.id}/chart?${q}`) : Promise.resolve({ meta: null, objects: [] }),
    ]);
    if (seq !== pc.seq) return;
    if (chart.meta && !pc.meta) { pc.meta = chart.meta; renderLayerToggles(); }
    pc.last = { candles, objects: chart.objects };
    $("#pc-status").textContent = `${tf} · ${candles.t.length} sviečok · ${chart.objects.length} objektov` +
      (candles.truncated ? " · okno orezané, zvoľ hrubší TF" : "");
    renderPairChart(candles, chart.objects);
  } catch (e) {
    if (seq !== pc.seq) return;
    el.innerHTML = `<div class="error">${esc(e.message)}</div>`;
  } finally { if (seq === pc.seq) el.classList.remove("loading"); }
}

function describe(o) {
  const head = `<b>${esc(pc.L.titles[o.k] || o.k)}</b>${o.tx ? " · " + esc(o.tx).replace(/\n/g, " ") : ""}${o.z != null ? ` · zóna #${o.z}` : ""}`;
  if (o.t === "label") return `${head}<br>${utc(o.x).slice(0, 16)} · ${fmtPrice(o.y)}`;
  const y = o.t === "bg" ? "" : `<br>${fmtPrice(Math.max(o.y1, o.y2))} – ${fmtPrice(Math.min(o.y1, o.y2))}`;
  return `${head}<br>${utc(o.x1).slice(0, 16)} → ${utc(o.x2).slice(0, 16)}${y}`;
}

function objectTraces(objects) {
  const groups = new Map(), shapes = [];
  const group = (key, init) => { let g = groups.get(key); if (!g) { g = init(); groups.set(key, g); } return g; };
  for (const o of objects) {
    const layer = pc.L.byKind[o.k];  // druh mimo vrstiev sa kreslí vždy
    if (layer && !pc.layers[layer]) continue;
    if (pc.L.hollow.has(o.k)) continue;  // kreslí sa ako dutá sviečka, viď candleTraces
    const name = (pc.L.layers.find(l => l.id === layer) || {}).title || o.k;
    const desc = describe(o);
    if (o.t === "bg") {
      shapes.push({ type: "rect", xref: "x", yref: "paper", layer: "below", x0: utc(o.x1), x1: utc(o.x2), y0: 0, y1: 1, fillcolor: o.c, line: { width: 0 } });
    } else if (o.t === "box") {
      const fill = o.fc || "rgba(0,0,0,0)", dash = DASH[o.bs] || "solid", w = o.bw ?? 1;
      const g = group(`box|${fill}|${o.bc}|${dash}|${w}`, () => ({ type: "scatter", mode: "lines", fill: "toself", fillcolor: fill,
        line: { color: o.bc, width: w, dash }, x: [], y: [], text: [], hoverinfo: "text", hoveron: "points", showlegend: false, name }));
      const x2 = o.er ? Math.max(o.x2, pc.to) : o.x2;
      g.x.push(utc(o.x1), utc(x2), utc(x2), utc(o.x1), utc(o.x1), null);
      g.y.push(o.y1, o.y1, o.y2, o.y2, o.y1, null);
      g.text.push(desc, desc, desc, desc, desc, "");
    } else if (o.t === "line") {
      const dash = DASH[o.s] || "solid", w = o.w ?? 1;
      const g = group(`line|${o.c}|${dash}|${w}`, () => ({ type: "scatter", mode: "lines", line: { color: o.c, width: w, dash },
        x: [], y: [], text: [], hoverinfo: "text", showlegend: false, name }));
      g.x.push(utc(o.x1), utc(o.x2), null); g.y.push(o.y1, o.y2, null); g.text.push(desc, desc, "");
    } else if (o.t === "label") {
      const bubble = !!o.bg;
      const g = group(`label|${o.ab ? 1 : 0}|${bubble ? 1 : 0}`, () => {
        const t = { type: "scatter", mode: bubble ? "markers+text" : "text",
          x: [], y: [], text: [], hovertext: [], hoverinfo: "text", showlegend: false, name,
          textposition: o.ab ? "top center" : "bottom center", textfont: { size: 10, color: [] } };
        // Plotly neznesie `marker: undefined` (validácia robí `"line" in marker`), tak kľúč len keď treba.
        if (bubble) t.marker = { symbol: o.ab ? "triangle-down" : "triangle-up", size: 8, color: [] };
        return t;
      });
      g.x.push(utc(o.x)); g.y.push(o.y); g.text.push(esc(o.tx || "").replace(/\n/g, "<br>"));
      g.textfont.color.push(bubble ? o.bg : o.c); g.hovertext.push(desc);
      if (bubble) g.marker.color.push(o.bg);
    }
  }
  return { traces: [...groups.values()], shapes };
}

/**
 * Sviečky. Imbalance sviečky (Pine ich vybledne a označí boxom na tele) idú do vlastného
 * trace s priehľadnou výplňou — dutá sviečka s obrysom vo farbe imbalance (zelená bull,
 * tehlová bear). Plotly počíta šírku sviečky naprieč všetkými candlestick trace na osi,
 * takže duté sviečky sú rovnako široké ako ostatné. Na hrubšom TF sa označí sviečka,
 * do ktorej imbalance 3m sviečka časovo patrí.
 */
function candleTraces(candles, objects) {
  const marks = new Map();  // index sviečky -> farba obrysu
  if (pc.L.hollow.size) {
    const t = candles.t;
    for (const o of objects) {
      if (!pc.L.hollow.has(o.k) || o.t !== "box") continue;
      const layer = pc.L.byKind[o.k];
      if (layer && !pc.layers[layer]) continue;
      let lo = 0, hi = t.length - 1, idx = -1;
      while (lo <= hi) { const m = (lo + hi) >> 1; if (t[m] <= o.x1) { idx = m; lo = m + 1; } else hi = m - 1; }
      if (idx >= 0 && (idx + 1 >= t.length || o.x1 < t[idx + 1])) marks.set(idx, o.bc);
    }
  }
  const base = (name, inc, dec, fill) => ({ type: "candlestick", x: [], open: [], high: [], low: [], close: [], name, showlegend: false, whiskerwidth: 0.3,
    increasing: { line: { color: inc, width: 1 }, fillcolor: fill || inc }, decreasing: { line: { color: dec, width: 1 }, fillcolor: fill || dec } });
  const normal = base(pc.rec.settings.pair, GREEN, RED);
  const hollow = new Map();
  for (let i = 0; i < candles.t.length; i++) {
    let tr = normal;
    const col = marks.get(i);
    if (col) {
      tr = hollow.get(col);
      if (!tr) { tr = base("Dutá sviečka", col, col, "rgba(0,0,0,0)"); hollow.set(col, tr); }
    }
    tr.x.push(utc(candles.t[i])); tr.open.push(candles.o[i]); tr.high.push(candles.h[i]); tr.low.push(candles.l[i]); tr.close.push(candles.c[i]);
  }
  return [normal, ...hollow.values()];
}

function tradeTraces() {
  if (!pc.layers.trades) return [];
  const inWin = pc.trades.filter(t => Date.parse(t.close_date || t.open_date) >= pc.from && Date.parse(t.open_date) <= pc.to);
  if (!inWin.length) return [];
  const cur = (pc.rec.result || {}).stake_currency || "USDT";
  const entry = { type: "scatter", mode: "markers", x: [], y: [], text: [], hoverinfo: "text", showlegend: false, name: "Vstup",
    marker: { symbol: [], size: 11, color: [], line: { color: "#fff", width: 1 } } };
  const exit = { type: "scatter", mode: "markers", x: [], y: [], text: [], hoverinfo: "text", showlegend: false, name: "Výstup",
    marker: { symbol: "x", size: 9, color: [], line: { width: 0 } } };
  const win = { type: "scatter", mode: "lines", x: [], y: [], hoverinfo: "skip", showlegend: false, line: { color: GREEN, width: 1.5, dash: "dot" } };
  const loss = { type: "scatter", mode: "lines", x: [], y: [], hoverinfo: "skip", showlegend: false, line: { color: RED, width: 1.5, dash: "dot" } };
  for (const t of inWin) {
    const long = !t.is_short, good = (t.profit_abs || 0) >= 0;
    const txt = `<b>${long ? "LONG" : "SHORT"}</b> ${esc(t.enter_tag || "")}<br>vstup ${fmtPrice(t.open_rate)} · ${utc(Date.parse(t.open_date)).slice(0, 16)}` +
      `<br>výstup ${fmtPrice(t.close_rate)} · ${utc(Date.parse(t.close_date)).slice(0, 16)} · ${esc(t.exit_reason || "")}` +
      `<br>PnL ${Number(t.profit_abs).toFixed(2)} ${cur} (${(t.profit_ratio * 100).toFixed(2)} %)`;
    entry.x.push(utc(Date.parse(t.open_date))); entry.y.push(t.open_rate); entry.text.push(txt);
    entry.marker.symbol.push(long ? "triangle-up" : "triangle-down"); entry.marker.color.push(long ? GREEN : RED);
    exit.x.push(utc(Date.parse(t.close_date))); exit.y.push(t.close_rate); exit.text.push(txt); exit.marker.color.push(good ? GREEN : RED);
    const ln = good ? win : loss;
    ln.x.push(utc(Date.parse(t.open_date)), utc(Date.parse(t.close_date)), null); ln.y.push(t.open_rate, t.close_rate, null);
  }
  return [win, loss, entry, exit];
}

function renderPairChart(candles, objects) {
  const el = $("#pair-chart");
  const { traces, shapes } = objectTraces(objects);
  let lo = Math.min(...candles.l), hi = Math.max(...candles.h);
  if (!Number.isFinite(lo)) { lo = 0; hi = 1; }
  const pad = (hi - lo) * 0.05 || 1;
  Plotly.react(el, [...traces, ...candleTraces(candles, objects), ...tradeTraces()], {
    height: 640, margin: { l: 10, r: 70, t: 8, b: 36 }, template: "plotly_white", dragmode: "pan", hovermode: "closest",
    showlegend: false, shapes,
    xaxis: { type: "date", range: [utc(pc.from), utc(pc.to)], rangeslider: { visible: false }, showgrid: true, gridcolor: "#f0f1f3" },
    yaxis: { side: "right", range: [lo - pad, hi + pad], showgrid: true, gridcolor: "#f0f1f3", fixedrange: false },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  }, { displaylogo: false, responsive: true, scrollZoom: true, modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"] });
  pc.quietUntil = Date.now() + 400;
  if (!pc.bound) {
    pc.bound = true;
    el.on("plotly_relayout", ev => {
      // Len skutočný pan/zoom používateľa: ten má vždy oba kraje osi x. Autosize,
      // dvojklik (autorange) a echo nášho vlastného rozsahu sa ignorujú, inak by sa
      // graf po každom vykreslení načítaval znova a okno by rástlo samo.
      if (Date.now() < pc.quietUntil || ev.autosize || !("xaxis.range[0]" in ev) || !("xaxis.range[1]" in ev)) return;
      const a = parseUtc(ev["xaxis.range[0]"]), b = parseUtc(ev["xaxis.range[1]"]);
      if (!Number.isFinite(a) || !Number.isFinite(b) || b <= a) return;
      if (Math.abs(a - pc.from) < 1000 && Math.abs(b - pc.to) < 1000) return;
      const cur = pc.to - pc.from, span = b - a;
      // Posun v rámci načítaného okna netreba načítavať; von z okna alebo výrazný zoom áno.
      if (a >= pc.from && b <= pc.to && span > cur * 0.45) return;
      // Jeden krok nesmie okno zväčšiť viac než 4× — poistka proti slučke.
      const limit = cur * 4;
      const mid = (a + b) / 2, half = Math.min(span, limit) / 2;
      clearTimeout(pc.relayoutTimer);
      pc.relayoutTimer = setTimeout(() => setWindow(mid - half, mid + half), 250);
    });
  }
}

function closeDetail() {
  $("#run-detail").hidden = true;
  $("#runs-table").parentElement.parentElement.hidden = false;
  state.detailId = null;
}

async function loadDetailIntoForm() {
  const r = await api(`/api/runs/${state.detailId}`);
  const rec = r.record;
  setStrategy(rec.settings.strategy || "ibs");  // formulár musí byť tej stratégie, ktorej sú parametre
  state.profile = rec.settings.profile || null;
  // základ = profil (aby sa zvýraznili odchýlky), hodnoty = beh. Profil behu už nemusí
  // existovať (archivované presety) — vtedy je základom Pine default a odchýlky sú voči nemu.
  let base = {};
  if (state.profile) {
    try { base = (await api(`/api/profiles/${state.profile.split("/").map(encodeURIComponent).join("/")}?strategy=${encodeURIComponent(state.strategy)}`)).params; }
    catch (_) { state.profile = null; }
  }
  $("#profile").value = state.profile && state.meta.profiles.includes(state.profile) ? state.profile : "";
  setParams(base, true);
  setParams(rec.params, false);
  $("#pair").value = rec.settings.pair; $("#pair").onchange();
  fillTimeframes(rec.settings.pair, rec.settings.timeframe || "3m");
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
  Object.assign(state.meta, strategyMeta(state.strategy) || {});
  fillSettings();
  $("#strategy").value = state.strategy;
  // Východisko sú Pine defaulty; referenčné profily (golden test, MultiCharts) sú na výber.
  const preferred = "";
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
