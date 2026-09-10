/* TradeBot Backtester — jednostránková aplikácia bez frameworku. */
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
  liveLog: null,       // id behu, ktorého log je otvorený v plnej šírke
  detailId: null,
  activeGroup: null,
  profileInstrument: null,
  paramMode: "basic",
  hyperMeta: {},
  propMeta: null,
  posudokId: null,     // uložená analytika, ku ktorej sa píše posudok
  propAfterRun: null,   // beh, ktoreho prop vyzva sa spocita, ked dobehne
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
  enforceSpotParams();
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
      const sessionTime = /^sess[123](Zone|Trade)(Start|End)H$/.test(first.name)
        && metas.length === 2 && metas[1].name === first.name.slice(0, -1) + "M";
      if (sessionTime) {
        const minute = metas[1];
        label.textContent = first.name.includes("Zone") ? "Vznik zón" : "Obchodovanie";
        label.textContent += first.name.includes("Start") ? " · od" : " · do";
        const wrap = document.createElement("div"); wrap.className = "ctl"; wrap.dataset.name = first.name;
        const input = document.createElement("input"); input.type = "time"; input.step = "60";
        input.setAttribute("aria-label", `${g}: ${label.textContent}`);
        input.value = `${String(state.params[first.name]).padStart(2, "0")}:${String(state.params[minute.name]).padStart(2, "0")}`;
        input.onchange = () => {
          if (!input.value) { renderParams(); return; }
          const [hour, min] = input.value.split(":").map(Number);
          state.params[first.name] = hour; state.params[minute.name] = min; refreshChanged();
        };
        wrap.append(input); ctls.append(wrap);
      }
      for (const meta of sessionTime ? [] : metas) {
        const ctl = paramInput(meta);
        ctl.dataset.name = meta.name;
        for (const input of ctl.querySelectorAll("input, select")) input.setAttribute("aria-label", `${g}: ${meta.title}${input.title ? " — " + input.title : ""}`);
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
  lockSpotParams();
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

/** Vypnuté `enableTrading` je Pine dedičstvo (tam vypínalo posielanie ordrov na burzu).
 *  V backteste znamená beh bez jediného obchodu, čo si tester všimne až vo výsledku. */
function checkTradingSwitch() {
  const box = $("#trading-warn");
  const off = state.params.enableTrading === false;
  if (off) box.textContent = "Obchodovanie je vypnuté (Základné nastavenia) — beh dobehne, ale neurobí ani jeden obchod. "
    + "Reálne vs. papierové obchodovanie sa vo Freqtrade rieši v configu (dry_run), nie týmto poľom.";
  box.hidden = !off;
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
  checkTradingSwitch();
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
  const basic = browsing && state.paramMode === "basic";
  $(".params-card").classList.toggle("basic-mode", basic);
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
      if (hit && basic && state.strategy === "ibs") {
        hit = row.dataset.names.split(" ").some(name => BASIC_PARAMS.has(name) || /^sess[123]/.test(name));
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

const BASIC_PARAMS = new Set(["tradeDirection", "rrRatio", "enableImbEntry", "enablePinBarEntry",
  "enableEngulfingEntry", "enableTrailing", "trailActivationR", "trailOffsetR", "maxLossDollar",
  "legacyPineSizing", "leverage", "minSlDistance", "slLookback", "slBufferTicks", "maxDailyWins",
  "useStructureFilter", "zoneDetectionTF", "enableTrading", "closeAtSessionEnd", "weekdaysOnly"]);

function setParamMode(mode) {
  state.paramMode = mode;
  for (const name of ["basic", "all"]) {
    const button = $(`#mode-${name}`);
    button.classList.toggle("active", mode === name);
    button.setAttribute("aria-pressed", String(mode === name));
  }
  $("#mode-hint").textContent = mode === "basic"
    ? "Najčastejšie nastavenia. Ostatné hodnoty zostávajú podľa zvoleného profilu. Hľadanie prechádza všetky parametre."
    : "Úplné nastavenia stratégie vrátane vizualizácie a pokročilých filtrov.";
  applyParamFilter();
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
  fillProfiles("");
  const spec = strategySpec(key);
  if (spec && spec.default_timeframe) fillTimeframes($("#pair").value, spec.default_timeframe);
  // Sekcia sweepu ponúkala parametre stratégie, z ktorej sa prepínalo, a históriu všetkých.
  if ($("#sweep-rows")) resetSweepForStrategy();
}

function fillSettings() {
  fillHistoryFilters();
  const ss = $("#strategy"); ss.innerHTML = "";
  for (const s of state.meta.strategies) { const o = document.createElement("option"); o.value = s.key; o.textContent = s.title; ss.append(o); }
  ss.onchange = async () => {
    setStrategy(ss.value);
    const f = $("#filter-strategy");
    if (f && f.value) { f.value = ss.value; historyPage.offset = 0; }
    loadAnalyticsHistory();
    $("#profile").value = "";
    await loadProfile("");
  };
  fillProfiles();
  const pair = $("#pair"); pair.innerHTML = "";
  // z jedného riadku má byť vidno, odkiaľ sviečky sú, aký je to trh a ako sa pár volá
  // na burze (BTCUSDT.P je perpetual, BTCUSDT spot) — aj keď je select zavretý
  for (const source of [...new Set(state.meta.pairs.map(p => p.source || "?"))].sort()) {
    const list = state.meta.pairs.filter(p => (p.source || "?") === source);
    if (!list.length) continue;
    const g = document.createElement("optgroup"); g.label = source;
    for (const p of list.sort((a, b) => (a.kind || a.market || "").localeCompare(b.kind || b.market || "")
        || (a.exchange_symbol || a.pair).localeCompare(b.exchange_symbol || b.pair))) {
      const o = document.createElement("option"); o.value = p.pair;
      o.textContent = `${source} · ${p.kind || p.market || "futures"} · ${p.exchange_symbol || p.pair}`
        + (p.has_1m ? "" : " (bez 1m)");
      o.title = p.pair;
      o.dataset.from = p.from; o.dataset.to = p.to;
      g.append(o);
    }
    pair.append(g);
  }
  pair.onchange = () => {
    const o = pair.selectedOptions[0]; if (!o) return;
    checkPairProfile();
    showMarket();
    if (enforceSpotParams()) renderParams(); else lockSpotParams();
    $("#pair-range").textContent = `dáta ${o.dataset.from} → ${o.dataset.to}`;
    fillEngines(o.value);
    fillExchanges(o.value);
    fillTimeframes(o.value);
    $("#from").min = o.dataset.from; $("#from").max = o.dataset.to; $("#to").min = o.dataset.from; $("#to").max = o.dataset.to;
    if (!$("#to").value || $("#to").value > o.dataset.to) $("#to").value = o.dataset.to;
    if (!$("#from").value) { const d = new Date(o.dataset.to); d.setDate(d.getDate() - 365); $("#from").value = d.toISOString().slice(0, 10); }
  };
  pair.onchange();
  $("#profile").onchange = e => loadProfile(e.target.value);
  const who = $("#who");
  let saved = null;
  try { saved = localStorage.getItem("ibs.user"); } catch (_) { /* súkromný režim */ }
  who.value = saved || state.meta.user || "";
  who.onchange = () => { try { localStorage.setItem("ibs.user", who.value.trim()); } catch (_) { /* ignoruj */ } };
  $("#branch").textContent = state.meta.branch;
}

const ENGINE_TITLES = { freqtrade: "Freqtrade", multicharts: "MultiCharts (emulátor)" };
const ENGINE_NOTES = {
  freqtrade: "backtest Freqtradu — jeho fill model, hyperopt a FreqAI",
  multicharts: "emulátor MultiCharts — ten istý runner, čo beží v štúdii; referencia pre MultiCharts",
};

/** Engine pre beh: ponuka podľa toho, pre ktorý sú na disku dáta. */
function fillEngines(pairName, wanted) {
  const sel = $("#engine");
  const p = state.meta.pairs.find(x => x.pair === pairName);
  const list = (p && p.engines && p.engines.length) ? p.engines : ["freqtrade"];
  const keep = wanted || sel.value;
  sel.innerHTML = "";
  for (const e of list) {
    const o = document.createElement("option"); o.value = e; o.textContent = ENGINE_TITLES[e] || e; sel.append(o);
  }
  sel.value = list.includes(keep) ? keep : ((p && p.default_engine) || list[0]);
  sel.onchange = () => { showEngineNote(); fillExchanges($("#pair").value); };
  showEngineNote();
}

function showEngineNote() {
  const e = $("#engine").value;
  $("#engine-note").textContent = ENGINE_NOTES[e] || "";
}

/** Burza pre Freqtrade beh: naša fiktívna Tester a tá, odkiaľ sviečky naozaj sú.
 *  Emulátor MultiCharts burzu nepotrebuje — vtedy je pole zamknuté. */
function fillExchanges(pairName, wanted) {
  const sel = $("#exchange");
  const p = state.meta.pairs.find(x => x.pair === pairName);
  const list = (p && p.exchanges && p.exchanges.length) ? p.exchanges : [state.meta.default_exchange];
  const titles = Object.fromEntries((state.meta.exchanges || []).map(e => [e.key, e.title]));
  const keep = wanted || sel.value;
  sel.innerHTML = "";
  for (const e of list) {
    const o = document.createElement("option");
    o.value = e; o.textContent = titles[e] || e;
    sel.append(o);
  }
  sel.value = list.includes(keep) ? keep : (list.includes(state.meta.default_exchange)
    ? state.meta.default_exchange : list[0]);
  const emulator = $("#engine").value === "multicharts";
  sel.disabled = emulator;
  $("#exchange-note").textContent = emulator
    ? "emulátor MultiCharts burzu nepotrebuje — číta priamo 1m sviečky"
    : (sel.value === state.meta.default_exchange
      ? "fiktívna burza: pozná všetky naše timeframy, poplatok zadáva beh"
      : "skutočná burza: platia jej timeframy a pravidlá trhu");
  sel.onchange = () => fillExchanges(pairName, sel.value);
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

/** Ponuka profilov: z repozitára (nemenné) a vlastné (premenovať/zmazať sa dajú len tie). */
function fillProfiles(selected) {
  const ps = $("#profile");
  const keep = selected !== undefined ? selected : ps.value;
  const own = new Set(state.meta.user_profiles || []);
  ps.innerHTML = `<option value="">(Pine defaulty)</option>`;
  for (const [label, names] of [["Profily repozitára", state.meta.profiles.filter(p => !own.has(p))],
                                ["Vlastné profily", state.meta.profiles.filter(p => own.has(p))]]) {
    if (!names.length) continue;
    const g = document.createElement("optgroup"); g.label = label;
    const titles = state.meta.profile_titles || {};
    for (const p of names) {
      const o = document.createElement("option"); o.value = p;
      o.textContent = titles[p] && titles[p] !== p ? `${p} — ${titles[p]}` : p;
      o.title = titles[p] || p;
      g.append(o);
    }
    ps.append(g);
  }
  ps.value = state.meta.profiles.includes(keep) ? keep : "";
  updateProfileActions();
}

function updateProfileActions() {
  const name = $("#profile").value;
  const own = (state.meta.user_profiles || []).includes(name);
  const why = !name ? "Vyber vlastný profil." : "Profily repozitára sa z webapp nemenia — ulož si vlastný cez „Uložiť ako profil“ v detaile behu.";
  for (const id of ["#profile-rename", "#profile-delete"]) {
    const b = $(id); b.disabled = !own; b.title = own ? "" : why;
  }
}

/** Odpoveď API o profiloch nesie aktuálny zoznam — prekresli ponuku a načítaj `pick`.
 *
 * Načítanie musí ísť cez `loadProfile`, nie len prestaviť `value`: inak by v ponuke
 * svietil jeden profil, vo formulári by boli iné hodnoty a beh by sa uložil s iným
 * (alebo žiadnym) profilom, než tester vidí. */
async function applyProfileList(r, pick) {
  // zoznam patrí stratégii — zapíš ho aj do strategy_meta, aby po prepnutí a návrate nezmizol
  for (const target of [state.meta, strategyMeta(r.strategy || state.strategy) || {}]) {
    target.profiles = r.profiles; target.user_profiles = r.user_profiles;
    if (r.profile_titles) target.profile_titles = r.profile_titles;
    if (r.profile_instruments) target.profile_instruments = r.profile_instruments;
  }
  fillProfiles(pick);
  if (pick !== undefined) await loadProfile($("#profile").value);
}

function profileMsg(text, isError) {
  const el = $("#profile-msg");
  el.textContent = text; el.classList.toggle("err", !!isError);
}

/** Meno súboru: medzera je podtržník, diakritika a zvyšné znaky pryč — inak by ho
 *  server odmietol a tester by si všimol až to, že sa nič neuložilo. */
function slugProfileName(raw) {
  return (raw || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .trim().replace(/\s+/g, "_").replace(/[^A-Za-z0-9._-]/g, "_")
    .replace(/_{2,}/g, "_").replace(/^[^A-Za-z0-9]+/, "");
}

/** Meno z promptu: očistí, a keď z neho po očistení nič nezostane, povie to nahlas. */
function askProfileName(question, preset) {
  const raw = prompt(question, preset || "");
  if (raw === null) return null;
  const name = slugProfileName(raw);
  if (!name) { alert(`„${raw}" sa ako meno profilu použiť nedá — treba aspoň jedno písmeno bez diakritiky alebo číslicu.`); return null; }
  return name;
}

/** Chyba od servera musí byť vidno: popup aj červený text vedľa ponuky. */
function profileFailed(e, el) {
  alert(`Profil: ${e.message}`);
  if (el) { el.textContent = e.message; el.classList.add("err"); }
}

async function renameProfile() {
  const cur = $("#profile").value;
  const name = askProfileName("Nové meno profilu:", cur);
  if (!name || name === cur) return;
  try {
    const r = await api(`/api/profiles/${encodeURIComponent(cur)}?strategy=${encodeURIComponent(state.strategy)}`, { method: "PATCH", body: JSON.stringify({ name }) });
    await applyProfileList(r, r.name);
    profileMsg(`premenované na ${r.name} — nezabudni na Push`);
  } catch (e) { profileFailed(e, $("#profile-msg")); }
}

async function deleteProfile() {
  const cur = $("#profile").value;
  if (!cur || !confirm(`Zmazať vlastný profil ${cur}? (zmaže súbor v tester/profiles/)`)) return;
  try {
    const r = await api(`/api/profiles/${encodeURIComponent(cur)}?strategy=${encodeURIComponent(state.strategy)}`, { method: "DELETE" });
    await applyProfileList(r, "");
    profileMsg(`${cur} zmazaný — nezabudni na Push`);
  } catch (e) { profileFailed(e, $("#profile-msg")); }
}

/** Uloženie profilu — `what` je buď {from_run}, alebo {params, instrument, timeframe}. */
async function saveProfile(what, msg) {
  const name = askProfileName("Meno profilu (medzera sa zmení na podtržník):", "");
  if (!name) return;
  const note = (prompt("Krátky popis, čo profil je (nepovinné):", "") || "").trim();
  const body = { name, note, strategy: state.strategy, ...what };
  msg.classList.remove("err"); msg.textContent = "ukladám…";
  try {
    let r;
    try {
      r = await api("/api/profiles", { method: "POST", body: JSON.stringify(body) });
    } catch (e) {
      if (!/už existuje/.test(e.message) || !confirm(`${e.message}. Prepísať ho?`)) throw e;
      r = await api("/api/profiles", { method: "POST", body: JSON.stringify({ ...body, overwrite: true }) });
    }
    if (r.strategy && r.strategy !== state.strategy) { setStrategy(r.strategy); }
    await applyProfileList(r, r.name);
    msg.textContent = `uložené ako ${r.name} — formulár teraz vychádza z neho, do gitu ide cez Push`;
  } catch (e) { msg.textContent = ""; profileFailed(e, msg); }
}

/** Beh z histórie ako východiskový profil pod vlastným menom. */
async function saveRunAsProfile() {
  if (!state.detailId) return;
  const rec = state.detailRecord;
  await saveProfile({ from_run: state.detailId, strategy: (rec && rec.settings && rec.settings.strategy) || state.strategy }, $("#save-profile-msg"));
}

/** Aktuálny formulár (vrátane zmeneného TF) ako vlastný profil. */
async function saveFormAsProfile() {
  const pair = state.meta.pairs.find(p => p.pair === $("#pair").value);
  if (!pair) { alert("Najprv vyber pár."); return; }
  await saveProfile({
    params: state.params, instrument: pair.instrument, timeframe: $("#tf").value,
    base: state.profile || null,
    timerange: timerange(), fee: $("#fee").value === "" ? null : Number($("#fee").value) / 100,
    wallet: Number($("#wallet").value), timeframe_detail: $("#detail").checked ? "1m" : null,
  }, $("#profile-msg"));
}

async function loadProfile(name) {
  state.profile = name || null;
  state.profileInstrument = null;
  updateProfileActions();
  $("#profile-base").textContent = "";
  if (!name) { setParams({}, true); checkPairProfile(); return; }
  const r = await api(`/api/profiles/${encodeURIComponent(name)}?strategy=${encodeURIComponent(state.strategy)}`);
  state.profileInstrument = r.instrument;
  setParams(r.params, true);
  // profil určuje aj nástroj -> prepni pár, ak zodpovedá
  const inst = r.instrument;
  const pair = state.meta.pairs.find(p => p.instrument === inst);
  if (pair) { $("#pair").value = pair.pair; $("#pair").onchange(); }
  // limity *MaxBars sú v baroch, takže k profilu patrí aj TF, na ktorom bol ladený;
  // profil bez `_timeframe` (tie z repozitára) znamená 3m, nie „nechaj, čo tam bolo"
  fillEngines($("#pair").value, r.engine);
  fillExchanges($("#pair").value, r.exchange);
  fillTimeframes($("#pair").value, r.timeframe || "3m");
  applyProfileSettings(r.settings || {});
  $("#profile-base").textContent = r.base ? `vychádza z profilu ${r.base}` : "";
}

function currentPair() {
  return state.meta.pairs.find(p => p.pair === $("#pair").value) || null;
}

function isSpotPair() {
  const p = currentPair();
  return !!p && (p.market || "futures") === "spot";
}

function showMarket() {
  const p = currentPair();
  const el = $("#pair-market");
  if (!p) { el.textContent = ""; return; }
  const src = p.source || "?";
  const kind = p.kind || p.market || "futures";
  const popis = {spot: "spot — len longy, bez páky", futures: "futures perpetual",
                 cfd: "CFD (mimo burzy)"}[kind] || kind;
  el.textContent = `${src} ${p.exchange_symbol} · ${popis} (${p.pair})`;
}

/** Na spote nie sú shorty ani páka — hodnoty sa nastavia natvrdo, nech beh zodpovedá
 *  tomu, čo sa dá naozaj obchodovať. Vracia `true`, keď niečo zmenil. */
function enforceSpotParams() {
  if (!isSpotPair()) return false;
  let changed = false;
  if ("tradeDirection" in (state.meta.defaults || {}) && state.params.tradeDirection !== "Long only") { state.params.tradeDirection = "Long only"; changed = true; }
  if ("leverage" in (state.meta.defaults || {}) && Number(state.params.leverage) > 1) { state.params.leverage = 1; changed = true; }
  return changed;
}

/** Zamkne polia, ktoré na spote nemajú význam (a povie prečo). */
function lockSpotParams() {
  const spot = isSpotPair();
  for (const name of ["tradeDirection", "leverage"]) {
    const ctl = $(`.ctl[data-name="${name}"]`);
    if (!ctl) continue;
    ctl.classList.toggle("locked", spot);
    for (const el of ctl.querySelectorAll("input, select")) {
      el.disabled = spot;
      el.title = spot ? "Spotový pár: na spote sa nedá shortovať ani páčiť." : "";
    }
  }
}

/** Obdobie, poplatok, peňaženka a 1m detail uložené v profile — čo profil nemá,
 *  ostane tak, ako to má tester nastavené. Obdobie sa oreže na stiahnuté dáta páru. */
function applyProfileSettings(setup) {
  if (setup.timerange) {
    const o = $("#pair").selectedOptions[0];
    const [a, b] = setup.timerange.split("-").map(d => `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6)}`);
    const lo = (o && o.dataset.from) || a, hi = (o && o.dataset.to) || b;
    $("#from").value = a < lo ? lo : (a > hi ? hi : a);
    $("#to").value = b > hi ? hi : (b < lo ? lo : b);
  }
  if (setup.fee !== undefined) $("#fee").value = setup.fee * 100;
  if (setup.wallet !== undefined) $("#wallet").value = setup.wallet;
  if (setup.detail !== undefined) $("#detail").checked = !!setup.detail;
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

/** Profil, s ktorým sa beh uloží do histórie — vždy ten, čo tester vidí v ponuke.
 *
 * Archívny profil („Načítať do formulára" z behu, ktorého profil už v `ibs/configs`
 * nie je) je cesta a v ponuke nie je — vtedy platí `state.profile`. */
function profileForRun() {
  const shown = $("#profile").value;
  if (shown) return shown;
  return state.profile && !state.meta.profiles.includes(state.profile) ? state.profile : null;
}

/** Rýchly rozsah obdobia: posledný rok, dva roky alebo celé dáta páru.
 *  Koniec je vždy koniec dát — na nedávnom okne testuje človek najčastejšie. */
function setQuickRange(years) {
  const o = $("#pair").selectedOptions[0];
  if (!o) return;
  const first = o.dataset.from, last = o.dataset.to;
  $("#to").value = last;
  if (years === "max") { $("#from").value = first; return; }
  const d = new Date(last + "T00:00:00Z");
  d.setUTCFullYear(d.getUTCFullYear() - Number(years));
  const want = d.toISOString().slice(0, 10);
  $("#from").value = want < first ? first : want;
}

function timerange() {
  const a = $("#from").value.replaceAll("-", ""), b = $("#to").value.replaceAll("-", "");
  return `${a}-${b}`;
}


// --------------------------------------------------------------------------- //
// Sweep: mriežka behov cez hodnoty parametra
//
// Každý bod je obyčajný beh vo fronte, takže sa dá otvoriť ako ktorýkoľvek iný.
// Formulár len povie, ktoré parametre a aké hodnoty, a podľa čoho vybrať najlepší.
// --------------------------------------------------------------------------- //

const sweep = { id: null, timer: null };

const GOAL_TITLES = {
  break_even: "najvyšší break-even poplatok",
  profit: "najvyšší zisk",
  winrate: "najvyšší podiel ziskových",
  drawdown: "najnižší drawdown",
};

/** Prednastavené hodnoty pre parameter: rozsah z Pine, krok podľa typu. */
function defaultSpec(meta) {
  if (!meta) return "";
  if (meta.type === "bool") return "true,false";
  if (meta.options) return meta.options.join(",");
  const lo = meta.min ?? 0, hi = meta.max ?? 10;
  const span = hi - lo;
  const step = meta.type === "int" ? Math.max(1, Math.round(span / 5)) : Number((span / 5).toPrecision(1));
  return `${lo}:${hi}:${step}`;
}

function sweepParamOptions() {
  const groups = {};
  for (const m of state.meta.params) {
    if (m.type === "color" || m.type === "string") continue;
    (groups[m.group] = groups[m.group] || []).push(m);
  }
  return groups;
}

function addSweepRow(name) {
  const wrap = document.createElement("div");
  wrap.className = "sweep-row";
  const sel = document.createElement("select");
  for (const [group, metas] of Object.entries(sweepParamOptions())) {
    const g = document.createElement("optgroup"); g.label = group;
    for (const m of metas) {
      const o = document.createElement("option");
      o.value = m.name;
      o.textContent = (m.breaks_parity ? "⚠ " : "") + m.title;
      o.title = m.name + (m.breaks_parity ? " — mení sizing/časovanie prevzaté z Pine" : "");
      g.append(o);
    }
    sel.append(g);
  }
  const spec = document.createElement("input");
  spec.type = "text"; spec.className = "spec"; spec.title = "od:do:krok alebo zoznam a,b,c";
  const del = document.createElement("button");
  del.type = "button"; del.className = "ghost small"; del.textContent = "✕";
  del.onclick = () => { wrap.remove(); refreshSweep(); };

  sel.value = name || sel.options[0].value;
  spec.value = defaultSpec(metaByName()[sel.value]);
  sel.onchange = () => { spec.value = defaultSpec(metaByName()[sel.value]); refreshSweep(); };
  spec.oninput = refreshSweep;

  wrap.append(sel, spec, del);
  $("#sweep-rows").append(wrap);
  refreshSweep();
}

/** Rozbalí zadanie tak, ako to spraví server — len aby sa dal ukázať počet behov. */
function sweepPoints(specText) {
  const text = (specText || "").trim();
  if (!text) return 0;
  if (text.includes(":") && !text.includes(",")) {
    const [lo, hi, step] = text.split(":").map(Number);
    if (!isFinite(lo) || !isFinite(hi) || !(step > 0)) return 0;
    return Math.floor((hi - lo) / step + 1e-9) + 1;
  }
  return text.split(",").filter(v => v.trim()).length;
}

function sweepSpace() {
  const space = {};
  for (const row of $$("#sweep-rows .sweep-row")) {
    const name = row.querySelector("select").value;
    const spec = row.querySelector("input.spec").value.trim();
    if (name && spec) space[name] = spec;
  }
  return space;
}

/** Bod mriežky ako veta: „rrRatio 4, trailActivationR 2,5". */
function sweepPointText(params, values) {
  return params.map(n => `${n} ${fmtVal(values[n])}`).join(", ");
}

/** Odhad, ako dlho mriežka pobeží — behy idú za sebou, jeden po druhom. */
function sweepMinutes(total) {
  const a = $("#from").value, b = $("#to").value;
  const days = (new Date(b) - new Date(a)) / 86400000;
  if (!(days > 0)) return 0;
  const perYear = state.meta.sweep_seconds_per_year || 30;
  return Math.max(1, Math.round(total * (days / 365) * perYear / 60));
}

function fmtMinutes(min) {
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60), m = min % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}

function refreshSweep() {
  const space = sweepSpace();
  const count = Object.values(space).reduce((n, spec) => n * (sweepPoints(spec) || 0), 1);
  const total = Object.keys(space).length ? count : 0;
  const cap = state.meta.max_sweep_runs || 0;      // 0 = bez stropu (predvolené)
  const min = total ? sweepMinutes(total) : 0;
  if (isMatrix()) {
    const pocet = matrixPairs().length * matrixTimeframes().length;
    const min = pocet ? sweepMinutes(pocet) : 0;
    $("#sweep-run").textContent = pocet
      ? `▶ Prejsť trhy (${pocet} ${slovom(pocet, "beh", "behy", "behov")}${min ? ` ≈ ${fmtMinutes(min)}` : ""})`
      : "▶ Prejsť trhy";
    $("#sweep-run").disabled = !pocet;
    matrixWalletCheck();
  } else if (isHyper()) {
    // Hyperopt nemá mriežku: počet behov je počet epoch a ten si tester zadáva sám.
    const epoch = Number($("#hyper-epochs").value) || 0;
    const pocet = Object.keys(space).length;
    $("#sweep-run").textContent = epoch
      ? `▶ Hľadať (${epoch} epoch, ${pocet} ${slovom(pocet, "parameter", "parametre", "parametrov")})`
      : "▶ Hľadať";
    $("#sweep-run").disabled = !pocet || !epoch;
  } else {
    $("#sweep-run").textContent = total
      ? `▶ Spustiť sweep (${total} behov${min ? ` ≈ ${fmtMinutes(min)}` : ""})`
      : "▶ Spustiť sweep";
    $("#sweep-run").disabled = !total || (cap && total > cap);
  }

  const meta = metaByName();
  const risky = Object.keys(space).filter(n => meta[n] && meta[n].breaks_parity);
  const warn = $("#sweep-warn");
  const parts = [];
  const varovania = (state.hyperMeta.warn || {});
  if (isMatrix()) {
    const pocet = matrixPairs().length * matrixTimeframes().length;
    const min = pocet ? sweepMinutes(pocet) : 0;
    $("#sweep-run").textContent = pocet
      ? `▶ Prejsť trhy (${pocet} ${slovom(pocet, "beh", "behy", "behov")}${min ? ` ≈ ${fmtMinutes(min)}` : ""})`
      : "▶ Prejsť trhy";
    $("#sweep-run").disabled = !pocet;
    matrixWalletCheck();
  } else if (isHyper()) {
    const rizikove = Object.keys(space).filter(n => varovania[n]);
    for (const n of rizikove) parts.push(`${n}: ${varovania[n]}.`);
    if (Object.keys(space).length < 3) {
      parts.push("Na jeden–dva parametre je čitateľnejšia mriežka — hyperopt sa oplatí od troch.");
    }
  } else if (cap && total > cap) {
    parts.push(`Mriežka má ${total} behov, strop je ${cap} (TRADEBOT_MAX_SWEEP_RUNS).`);
  } else if (min >= 120) {
    // Nie zákaz, len číslo: dlhá mriežka je legitímna, púšťa sa cez noc.
    parts.push(`${total} behov je odhadom ${fmtMinutes(min)} — behy idú za sebou, takže`
      + " sa to hodí nechať bežať cez noc. Mriežku sa dá kedykoľvek zrušiť celú.");
  }
  if (risky.length) {
    parts.push(`${risky.map(n => meta[n].title).join(", ")}: mení sizing alebo časovanie prevzaté `
      + "z TradingView. Ladiť sa dá, ale výsledok sa už nedá porovnať s Pine ani s golden testami.");
  }
  warn.hidden = !parts.length;
  warn.textContent = parts.join(" ");
}

async function startSearch() {
  if (isMatrix()) return startMatrix();
  return isHyper() ? startHyperopt() : startSweep();
}

/** Hyperopt: jeden beh vo fronte, po ňom overenie na referenčných oknách. */
async function startHyperopt() {
  const space = sweepSpace();
  if (!Object.keys(space).length) return;
  const btn = $("#sweep-run");
  btn.disabled = true;
  $("#sweep-status").textContent = "zaraďujem do fronty…";
  try {
    const body = {
      ...runBody(),
      space,
      goal: $("#sweep-goal").value,
      max_dd: $("#sweep-maxdd").value === "" ? null : Number($("#sweep-maxdd").value),
      min_trades: $("#sweep-mintrades").value === "" ? null : Number($("#sweep-mintrades").value),
      epochs: Number($("#hyper-epochs").value) || 200,
      verify: $("#hyper-verify").checked,
    };
    const r = await api("/api/hyperopts", { method: "POST", body: JSON.stringify(body) });
    hyper.id = r.id;
    try { localStorage.setItem(hyperKey(), r.id); } catch (e) { /* súkromné okno */ }
    $("#sweep-status").textContent = `${r.epochs} epoch vo fronte · ${r.goal_note}`;
    if (r.warn && r.warn.length) {
      $("#sweep-warn").hidden = false;
      $("#sweep-warn").textContent = r.warn.join(" ");
    }
    pollQueue();
    pollHyper();
    loadSweepHistory();
  } catch (e) {
    $("#sweep-status").textContent = e.message;
  } finally {
    refreshSweep();
  }
}

/** Slovencina pocita inak nez anglictina: 1 parameter, 2-4 parametre, 5+ parametrov. */
function slovom(n, jeden, malo, mnoho) {
  if (n === 1) return jeden;
  return n >= 2 && n <= 4 ? malo : mnoho;
}

const hyperKey = () => `hyperopt:${state.strategy}`;
const hyper = { id: null, timer: null };

async function pollHyper() {
  if (!hyper.id) return;
  try {
    const r = await api(`/api/hyperopts/${hyper.id}`);
    renderHyper(r);
    if (r.status === "queued" || r.status === "running"
        || (r.verify || []).some(v => v.status === "queued" || v.status === "running")) {
      clearTimeout(hyper.timer);
      hyper.timer = setTimeout(pollHyper, 4000);
    }
  } catch (e) {
    clearTimeout(hyper.timer);
    hyper.timer = setTimeout(pollHyper, 4000);
  }
}

function renderHyper(r) {
  const casti = [];
  if (r.status === "queued") casti.push("čaká vo fronte");
  else if (r.status === "running") casti.push(`beží · ${r.hyperopt.epochs} epoch`);
  else if (r.status === "failed") casti.push("zlyhalo");
  else casti.push(`hotovo · ${r.hyperopt.epochs_done || 0} epoch`);
  casti.push(r.goal_note);
  $("#sweep-status").textContent = casti.join(" · ");
  $("#sweep-cancel").hidden = !(r.status === "queued" || r.status === "running");

  const box = $("#sweep-result");
  if (r.status === "failed") { box.innerHTML = `<div class="error">${esc(r.error || "beh zlyhal")}</div>`; return; }
  const casti_html = [];

  if ((r.epochs || []).length) {
    const head = [...r.params, "obch.", "PnL %", "WR %", "DD %", "skóre"];
    const rows = r.epochs.slice(0, 20).map((e, i) => {
      const cls = !e.usable ? "out" : (i === 0 ? "best" : "");
      const cells = [
        ...r.params.map(n => esc(fmtVal(e.params["hp_" + n]))),
        e.trades ?? "—", fmt(e.pnl_pct, 2), fmt(e.winrate, 1),
        fmt(e.max_drawdown_pct, 2), fmt(-e.loss, 4),
      ];
      const title = e.usable ? "" : "mimo mantinelov (počet obchodov alebo drawdown)";
      return `<tr class="${cls}" title="${esc(title)}">` + cells.map(c => `<td>${c}</td>`).join("") + "</tr>";
    }).join("");
    casti_html.push(`<table><thead><tr>${head.map(h => `<th>${esc(h)}</th>`).join("")}`
      + `</tr></thead><tbody>${rows}</tbody></table>`);
  }

  if (r.overrides) {
    const zoznam = Object.entries(r.overrides).map(([k, v]) => `${k} = ${esc(fmtVal(v))}`).join(", ");
    casti_html.push(`<p class="mode-hint">Najlepšia epocha: ${zoznam}</p>`);
  }

  if ((r.verify || []).length) {
    const rows = r.verify.map(v => {
      const res = v.result || {};
      const cells = [v.timerange + (v.tuned ? " (ladené)" : ""), v.status,
        res.trades ?? "—", fmt(res.pnl_pct, 2), fmt(res.break_even_pct, 4)];
      return `<tr class="${v.tuned ? "tuned" : ""}" data-run="${v.id}" title="klikni pre detail behu">`
        + cells.map(c => `<td>${c}</td>`).join("") + "</tr>";
    }).join("");
    casti_html.push('<table class="verify-table"><thead><tr><th>okno</th><th>stav</th>'
      + "<th>obch.</th><th>PnL %</th><th>break-even</th></tr></thead>"
      + `<tbody>${rows}</tbody></table>`);
  }

  if (r.verdict) {
    const trieda = r.verdict.startsWith("VITAZ PREZIL") ? "good"
      : (r.verdict.startsWith("PRETRENOVANE") ? "bad" : "unsure");
    casti_html.push(`<div class="verdict ${trieda}">${esc(r.verdict)}</div>`);
  }
  casti_html.push(plateauHtml(r));
  box.innerHTML = casti_html.join("");
  for (const tr of $$("#sweep-result tr[data-run]")) {
    tr.onclick = () => { showView("history"); openRun(tr.dataset.run); };
  }
  const tlacidlo = $("#plateau-run");
  if (tlacidlo) tlacidlo.onclick = () => startPlateau(r.id);
}

/** Okolie víťaza: plató, alebo osamelá špička? */
function plateauHtml(r) {
  if (!r.overrides) return "";
  const p = r.plateau;
  if (!p) {
    return `<p class="an-note"><button id="plateau-run" class="ghost small" type="button"
        title="Pustí susedov víťaza — o krok a o dva kroky na každom ladenom parametri.">
        Preveriť okolie víťaza</button>
      Hyperopt vrátil jedno číslo; susedia povedia, či je to stred niečoho, alebo náhodná
      diera v šume.</p>`;
  }
  const rows = (p.rows || []).map(x => {
    const znak = x.step > 0 ? "+" : "";
    return `<tr class="${x.holds ? "" : "out"}" data-run="${x.id}" title="klikni pre detail behu">`
      + `<td>${esc(x.param)} ${znak}${x.step}</td><td>${esc(fmtVal(x.value))}</td>`
      + `<td>${x.trades ?? "—"}</td><td>${fmt(x.break_even_pct, 4)}</td>`
      + `<td>${x.holds ? "áno" : "NIE"}</td></tr>`;
  }).join("");
  const trieda = p.verdict.startsWith("PLATO") ? "good"
    : (p.verdict.startsWith("SPICKA") ? "bad" : "unsure");
  const hlavicka = p.ci_lo !== null && p.ci_lo !== undefined
    ? `<p class="an-note">Interval víťaza (Monte Carlo): ${fmt(p.ci_lo, 4)} až ${fmt(p.ci_hi, 4)} %`
      + (p.spread !== null ? ` · rozptyl okolia ${fmt(p.spread, 4)} %` : "") + "</p>"
    : "";
  return `<div class="ch-box">
      <div class="ch-head"><h3>Okolie víťaza</h3>
        ${p.pending ? `<span class="chip warn">${p.pending} beží</span>` : ""}</div>
      <p class="an-note">${esc(p.note || "")}</p>
      ${hlavicka}
      ${rows ? `<table class="mx-table"><thead><tr><th>sused</th><th>hodnota</th>
        <th>obch.</th><th>break-even</th><th>drží</th></tr></thead>
        <tbody>${rows}</tbody></table>` : ""}
      <div class="verdict ${trieda}">${esc(p.verdict)}</div>
    </div>`;
}

/** Zaradí susedov víťaza do fronty. */
async function startPlateau(id) {
  const btn = $("#plateau-run");
  if (btn) btn.disabled = true;
  try {
    const r = await api(`/api/hyperopts/${id}/plateau`, { method: "POST" });
    $("#sweep-status").textContent = `${r.neighbours} susedov vo fronte`;
    pollQueue();
    pollHyper();
  } catch (e) {
    $("#sweep-status").textContent = e.message;
    if (btn) btn.disabled = false;
  }
}

async function startSweep() {
  const space = sweepSpace();
  if (!Object.keys(space).length) return;
  const btn = $("#sweep-run");
  btn.disabled = true;
  $("#sweep-status").textContent = "zaraďujem do fronty…";
  try {
    const body = {
      ...runBody(),
      space,
      goal: $("#sweep-goal").value,
      max_dd: $("#sweep-maxdd").value === "" ? null : Number($("#sweep-maxdd").value),
      min_trades: $("#sweep-mintrades").value === "" ? null : Number($("#sweep-mintrades").value),
    };
    const r = await api("/api/sweeps", { method: "POST", body: JSON.stringify(body) });
    sweep.id = r.id;
    try { localStorage.setItem(sweepKey(), r.id); } catch (e) { /* súkromné okno */ }
    $("#sweep-status").textContent = `${r.points} behov vo fronte`
      + (r.minutes ? ` · odhadom ${fmtMinutes(r.minutes)}` : "") + ` · ${r.goal_note}`;
    // Fronta sa prestane obtáčať, keď raz dobehne do prázdna; sweep ju musí zobudiť
    // rovnako ako ▶ Spustiť backtest, inak karta Fronta tvrdí „Nič nebeží".
    pollQueue();
    pollSweep();
    loadSweepHistory();
  } catch (e) {
    $("#sweep-status").textContent = e.message;
  } finally {
    refreshSweep();
  }
}

async function pollSweep() {
  if (!sweep.id) return;
  try {
    const r = await api(`/api/sweeps/${sweep.id}`);
    renderSweep(r);
    if (r.running) {
      clearTimeout(sweep.timer);
      sweep.timer = setTimeout(pollSweep, 3000);
    } else {
      loadSweepHistory();          // dobehnutá mriežka už nesie konečné počty
    }
  } catch (e) { /* beh ešte nič neuložil */ clearTimeout(sweep.timer); sweep.timer = setTimeout(pollSweep, 3000); }
}

function renderSweep(r) {
  const casti = [`hotových ${r.done} z ${r.done + r.running}`];
  if (r.running_values) casti.push(`beží ${sweepPointText(r.params, r.running_values)}`);
  else if (r.ahead) casti.push(`čaká, pred ňou je vo fronte ${r.ahead} behov`);
  casti.push(r.goal_note);
  $("#sweep-status").textContent = casti.join(" · ");
  $("#sweep-cancel").hidden = !r.running;
  if (!r.rows.length) { $("#sweep-result").innerHTML = ""; return; }
  const head = [...r.params, "obch.", "PnL %", "WR %", "DD %", "break-even"];
  const ceka = row => row.status === "queued" || row.status === "running";
  const rows = r.rows.map((row, i) => {
    const hodnoty = r.params.map(n => `<td>${esc(fmtVal(row.values[n]))}</td>`).join("");
    if (ceka(row)) {
      // Body, ktoré ešte len čakajú, sú v tabuľke od začiatku — inak sekcia vyzerá
      // po zaradení mriežky prázdna a nie je vidieť, že sa niečo deje.
      return `<tr class="pending" title="beh ešte nedobehol">${hodnoty}`
        + `<td colspan="5" class="muted">${row.status === "running" ? "beží…" : "čaká vo fronte"}</td></tr>`;
    }
    const cls = !row.ok ? "out" : (i === 0 ? "best" : "");
    const cells = [
      row.result.trades ?? "—",
      fmt(row.result.pnl_pct, 2), fmt(row.result.winrate, 1),
      fmt(row.result.max_drawdown_pct, 2), fmt(row.result.break_even_pct, 4),
    ].map(c => `<td>${c}</td>`).join("");
    const title = row.why ? `mimo mantinelov: ${row.why}` : "klikni pre detail behu";
    return `<tr class="${cls}" data-run="${row.id}" title="${esc(title)}">${hodnoty}${cells}</tr>`;
  }).join("");
  $("#sweep-result").innerHTML = `<table><thead><tr>${head.map(h => `<th>${esc(h)}</th>`).join("")}`
    + `</tr></thead><tbody>${rows}</tbody></table>`;
  for (const tr of $$("#sweep-result tr[data-run]")) {
    tr.onclick = () => { showView("history"); openRun(tr.dataset.run); };
  }
}

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

/** Naplní výber trhov a timeframov; zvýrazní trhy, kde sa nezmestí jeden kontrakt. */
async function initMatrixPick() {
  const sel = $("#matrix-pairs");
  if (!sel.options.length) {
    for (const p of state.meta.pairs || []) {
      const o = document.createElement("option");
      o.value = p.pair;
      o.textContent = `${p.source || "?"} · ${p.kind || ""} · ${p.pair}`;
      if (p.pair === $("#pair").value) o.selected = true;
      sel.append(o);
    }
  }
  const box = $("#matrix-tfs");
  if (!box.children.length) {
    // Timeframy sú vlastnosť páru (nie všetky trhy majú všetky), takže tu je zjednotenie
    // toho, čo je aspoň na jednom trhu — čo na konkrétnom páre nie je, sa preskočí.
    const vsetky = [...new Set((state.meta.pairs || []).flatMap(p => p.timeframes || []))]
      .sort((a, b) => (tfMinutes(a) || 0) - (tfMinutes(b) || 0));
    for (const tf of (vsetky.length ? vsetky : ["3m"])) {
      const label = document.createElement("label");
      label.innerHTML = `<input type="checkbox" value="${tf}"${tf === $("#tf").value ? " checked" : ""}> ${tf}`;
      label.querySelector("input").onchange = refreshSweep;
      box.append(label);
    }
  }
  await matrixWalletCheck();
}

/** Jeden lot EURUSD je ~112 000 — s peňaženkou 10 000 sa nezmestí a bunka dá nula obchodov. */
async function matrixWalletCheck() {
  const box = $("#matrix-warn");
  try {
    const tf = matrixTimeframes()[0] || "3m";
    const r = await api(`/api/matrix/meta?wallet=${encodeURIComponent($("#wallet").value || 10000)}`
      + `&timeframe=${encodeURIComponent(tf)}&strategy=${encodeURIComponent(state.strategy)}`);
    const male = Object.entries(r.small_wallet || {})
      .filter(([pair]) => matrixPairs().includes(pair))
      .sort((a, b) => b[1] - a[1]);
    if (!male.length) { box.hidden = true; return; }
    box.hidden = false;
    box.textContent = `Peňaženka ${$("#wallet").value} nestačí na jeden kontrakt na `
      + `${male.length} vybraných trhoch (${male.slice(0, 3).map(([p, n]) =>
        `${p} ${Math.round(n).toLocaleString("sk")}`).join(", ")}…). `
      + `Tie bunky skončia s nula obchodmi. Break-even od peňaženky nezávisí, tak ju zvýš `
      + `na ${Math.round(male[0][1] * 2).toLocaleString("sk")}.`;
  } catch (e) { box.hidden = true; }
}

/** `3m` -> 3, `1h` -> 60. Na zoradenie timeframov podľa dĺžky, nie abecedy. */
function tfMinutes(tf) {
  const m = /^(\d+)([mhdw])$/.exec(String(tf || ""));
  if (!m) return 0;
  const n = Number(m[1]);
  return n * { m: 1, h: 60, d: 1440, w: 10080 }[m[2]];
}

const matrixPairs = () => [...$("#matrix-pairs").selectedOptions].map(o => o.value);
const matrixTimeframes = () => [...$$("#matrix-tfs input:checked")].map(i => i.value);

/** Matica: každá bunka je obyčajný beh s tou istou značkou. */
async function startMatrix() {
  const pairs = matrixPairs(), timeframes = matrixTimeframes();
  if (!pairs.length || !timeframes.length) return;
  const btn = $("#sweep-run");
  btn.disabled = true;
  $("#sweep-status").textContent = "zaraďujem do fronty…";
  try {
    const r = await api("/api/matrices", {
      method: "POST",
      body: JSON.stringify({
        ...runBody(), pairs, timeframes,
        goal: $("#sweep-goal").value,
        min_trades: $("#sweep-mintrades").value === "" ? 10 : Number($("#sweep-mintrades").value),
        relative: $("#matrix-relative").checked,
      }),
    });
    matrixState.id = r.id;
    try { localStorage.setItem(matrixKey(), r.id); } catch (e) { /* súkromné okno */ }
    const preskocene = Object.keys(r.skipped || {}).length;
    $("#sweep-status").textContent = `${r.cells} buniek vo fronte`
      + (preskocene ? ` · ${preskocene} preskočených` : "");
    if ((r.converted || []).length) {
      $("#sweep-warn").hidden = false;
      $("#sweep-warn").textContent = "Prahy prepočítané: " + r.converted.join("; ");
    }
    pollQueue();
    pollMatrix();
    loadSweepHistory();
  } catch (e) {
    $("#sweep-status").textContent = e.message;
  } finally { refreshSweep(); }
}

const matrixKey = () => `matrix:${state.strategy}`;
const matrixState = { id: null, timer: null };

async function pollMatrix() {
  if (!matrixState.id) return;
  try {
    const r = await api(`/api/matrices/${matrixState.id}`);
    renderMatrix(r);
    if (r.pending) {
      clearTimeout(matrixState.timer);
      matrixState.timer = setTimeout(pollMatrix, 4000);
    }
  } catch (e) {
    clearTimeout(matrixState.timer);
    matrixState.timer = setTimeout(pollMatrix, 4000);
  }
}

function renderMatrix(r) {
  $("#sweep-status").textContent = `hotových ${r.done} z ${r.done + r.pending}`
    + ` · ${r.goal_note}` + (r.relative ? " · prahy v ATR" : " · prahy nezmenené (!)");
  const t = r.table || {};
  const casti = [];
  if ((t.pairs || []).length) {
    const head = ["trh", ...t.timeframes].map(h => `<th>${esc(h)}</th>`).join("");
    const rows = t.pairs.map(pair => {
      const cells = t.timeframes.map(tf => {
        const b = (t.cells[pair] || {})[tf];
        if (!b) return `<td class="wait">.</td>`;
        if (b.status !== "done") return `<td class="wait">${esc(b.status || "…")}</td>`;
        if (b.value === null || b.value === undefined) {
          // Rozdiel je zásadný: „0 setupov" je vlastnosť stratégie na tom trhu,
          // „odmietnuté" je náš problém s peňaženkou alebo sizingom.
          const text = b.empty === "bez setupu" ? "0 setupov"
            : b.empty === "odmietnute" ? "odmietnuté" : "—";
          return `<td class="wait" title="${esc(b.warning || "")}">${text}</td>`;
        }
        const cls = !b.ok ? "noise" : (b.value > 0 ? "pos" : "neg");
        const title = b.ok ? `${b.trades} obchodov` : esc(b.why || "mimo mantinelov");
        return `<td class="${cls}" data-run="${b.id}" title="${title}">${fmt(b.value, 4)}</td>`;
      }).join("");
      return `<tr><td>${esc(pair)}</td>${cells}</tr>`;
    }).join("");
    casti.push(`<table class="mx-table"><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`);
    casti.push('<p class="an-note">Čísla sú break-even poplatok v % na stranu. Kurzívou sú bunky'
      + " s málo obchodmi — číslo tam je, ale záver z neho nie. PnL % nie je medzi trhmi"
      + " porovnateľné (závisí od peňaženky), break-even áno.</p>");
  }
  if (r.verdict) {
    const trieda = r.verdict.startsWith("MYSLIENKA DRZI") ? "good"
      : (r.verdict.includes("LEN NA JEDNOM") || r.verdict.startsWith("SLABE") ? "bad" : "unsure");
    casti.push(`<div class="verdict ${trieda}">${esc(r.verdict)}</div>`);
  }
  $("#sweep-result").innerHTML = casti.join("");
  for (const td of $$("#sweep-result td[data-run]")) {
    td.onclick = () => { showView("history"); openRun(td.dataset.run); };
  }
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
  };
}

async function submitRun() {
  const btn = $("#run"); btn.disabled = true; $("#run-error").hidden = true;
  try {
    const job = await api("/api/runs", { method: "POST", body: JSON.stringify(runBody()) });
    // Vyzva sa pocita az z hotovych obchodov, takze si beh zapamatame a pockame naň.
    state.propAfterRun = ($("#nprop-after")?.checked && job?.id) ? job.id : null;
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
      <td class="ov">${ov || '<span class="muted">Pine defaulty</span>'}</td><td>${esc(run.note || "")}</td>`;
    tr.tabIndex = 0;
    tr.onclick = () => openRun(run.id);
    tr.onkeydown = e => { if (e.key === "Enter") openRun(run.id); };
    fragment.append(tr);
  }
  tb.replaceChildren(fragment);
  if (!r.runs.length) tb.innerHTML = '<tr><td colspan="12" class="empty muted">Žiadne behy nezodpovedajú hľadaniu.</td></tr>';
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
  $("#save-profile-msg").textContent = ""; $("#save-profile-msg").classList.remove("err");
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
  initMonteCarlo(rec);

  $("#detail-params").innerHTML = `<table class="runs"><tbody>${Object.entries(rec.params || {}).filter(([k]) => !k.startsWith("_")).map(([k, v]) => `<tr><td><code>${k}</code></td><td>${esc(fmtVal(v))}</td></tr>`).join("")}</tbody></table>`;
  $("#detail-log").textContent = await api(`/api/runs/${id}/log`);
}

function card(k, v, s) { return `<div class="kcard"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`; }

// --------------------------------------------------------------------------- //
// Monte Carlo — aký široký je interval okolo nameraného čísla
//
// Bootstrap obchodov behu; ráta server (/api/runs/<id>/montecarlo, tester/montecarlo.py).
// Až po rozbalení sekcie: pri behu s tisíckami obchodov to trvá jednotky sekúnd.
// --------------------------------------------------------------------------- //

const mc = { key: null, busy: false };

const mcInputs = () => ["#mc-fee", "#mc-account", "#mc-risk", "#mc-block", "#mc-iter"].map(s => $(s).value);
function mcKey() { return [state.detailId, ...mcInputs()].join("|"); }

function initMonteCarlo(rec) {
  $("#mc-box").open = false;
  mc.key = null;
  for (const id of ["#mc-cards", "#mc-chart", "#mc-dd-chart", "#mc-hits"]) $(id).innerHTML = "";
  $("#mc-note").textContent = "";
  // predvolený poplatok je ten, s ktorým beh bežal (rovnako ako v CLI) — aj keď je nulový;
  // vymyslieť burzovú sadzbu behu na CFD by bolo horšie než ukázať čistý edge
  $("#mc-fee").value = (rec.settings.fee != null ? rec.settings.fee * 100 : 0.05).toFixed(3);
  $("#mc-account").value = rec.settings.wallet || 10000;
  // riziko na obchod sa dá meniť len tam, kde je sizing rizikový; pri legacyPineSizing
  // je veľkosť pozície pevný počet kontraktov a prepočet na iný účet nedáva zmysel
  const risk = (rec.params || {}).legacyPineSizing ? null : (rec.params || {}).maxLossDollar;
  $("#mc-risk").value = risk || "";
  $("#mc-risk").disabled = !risk;
  $("#mc-risk").title = risk ? "maxLossDollar z profilu behu" : "beh má pevný počet kontraktov, nie dolárové riziko";
  const n = (rec.result || {}).trades || 0;
  $("#mc-run").disabled = !n;
  $("#mc-status").textContent = n ? "" : "Beh nemá obchody, nie je čo premiešavať.";
}

async function loadMonteCarlo(force = false) {
  const id = state.detailId;
  if (!id || mc.busy || !((state.detailRecord || {}).result || {}).trades) return;
  const key = mcKey();
  if (key === mc.key && !force) return;
  mc.busy = true;
  $("#mc-status").textContent = "počítam…";
  try {
    const q = new URLSearchParams({ fee: $("#mc-fee").value, account: $("#mc-account").value,
      block: $("#mc-block").value, iterations: $("#mc-iter").value });
    if ($("#mc-risk").value && !$("#mc-risk").disabled) q.set("risk", $("#mc-risk").value);
    const r = await api(`/api/runs/${id}/montecarlo?${q}`);
    if (state.detailId !== id) return;          // medzitým sa otvoril iný beh
    mc.key = key;
    renderMonteCarlo(r);
    $("#mc-status").textContent = `${r.n} obchodov · ${r.iterations.toLocaleString("sk-SK")} opakovaní`;
  } catch (e) {
    $("#mc-status").textContent = e.message;
  } finally { mc.busy = false; }
}

function renderMonteCarlo(r) {
  const cur = ((state.detailRecord || {}).result || {}).stake_currency || "USDT";
  const be = r.break_even, net = r.net, acc = r.account;
  const dd = acc.drawdown_pct, st = acc.losing_streak, wt = acc.wait_for_high, fin = acc.final_pct;
  $("#mc-cards").innerHTML = [
    card("Break-even poplatok", `${fmt(be.median, 4)} %`, `nameraný ${fmt(be.observed, 4)} %`),
    card(`${fmt(r.ci, 0)} % interval`, `${fmt(be.lo, 4)} – ${fmt(be.hi, 4)}`, "% na stranu"),
    card("P(edge > poplatok)", `${fmt(100 * be.p_above_fee, 1)} %`, `pri ${fmt(r.fee_pct, 4)} % = P(zisk > 0)`),
    card(`Čistý PnL (${cur})`, signed(net.median, 0), `${signed(net.lo, 0)} … ${signed(net.hi, 0)}`),
    card("Max drawdown", `${fmt(dd.median, 1)} %`, `95. p. ${fmt(dd.p95, 1)} % · nameraný ${fmt(dd.observed, 1)} %`),
    card("Séria strát", `${fmt(st.median, 0)}`, `95. p. ${fmt(st.p95, 0)} · najdlhšia ${fmt(st.max, 0)} obchodov`),
    card("Čakanie na nové max", `${fmt(wt.median, 0)}`, `95. p. ${fmt(wt.p95, 0)} obchodov`),
    card("Konečný zostatok", signed(fin.median, 1, " %"), `${signed(fin.lo, 1, " %")} … ${signed(fin.hi, 1, " %")}`),
  ].join("");
  drawBeChart(be, r.fee_pct);
  drawDdChart(dd);

  const sizing = acc.risk_pct ? `riziko ${acc.risk_pct} % z equity (zložené úročenie)`
    : acc.risk ? `riziko ${money(acc.risk)} ${cur} na obchod`
    : "veľkosť pozície z behu (pevný počet kontraktov, nedá sa preškálovať)";
  $("#mc-hits").innerHTML = `<h4>Účet ${money(acc.start)} ${cur}, ${esc(sizing)}</h4>`
    + `<table class="runs"><thead><tr><th>pokles účtu pod počiatočný zostatok</th>`
    + acc.hits.map(h => `<th class="num">−${fmt(h.limit, 0)} %</th>`).join("")
    + `<th class="num">ruina (0)</th></tr></thead><tbody><tr><td>stane sa v … % ciest</td>`
    + acc.hits.map(h => `<td class="num">${fmt(100 * h.p, 1)} %</td>`).join("")
    + `<td class="num">${fmt(100 * acc.p_ruin, 1)} %</td></tr></tbody></table>`;

  const notes = [];
  if (acc.advice) {
    notes.push(`Aby 95 % ciest zostalo nad −${fmt(acc.advice.limit, 0)} %, riskuj najviac `
      + `${money(acc.advice.risk)} ${cur} na obchod (teraz ${money(acc.risk)}).`);
  }
  if (r.n < r.min_trades) {
    notes.push(`${r.n} obchodov je pod hranicou ${r.min_trades} — interval je taký široký, že o stratégii nehovorí nič.`);
  }
  if (r.fee_pct > 0 && be.p_above_fee < 0.95) {
    notes.push(`V ${fmt(100 * (1 - be.p_above_fee), 0)} % vzoriek by burza zobrala viac, než stratégia zarobí.`);
  }
  notes.push(`Losuje sa po blokoch ${r.block} obchodov, aby sa série strát nerozsypali. Bootstrap meria `
    + "rozptyl vzorky, nie pretrénovanie — či nastavenie prežije, ukážu až dáta, ktoré optimalizátor nevidel. "
    + "Účet sa počíta z uzavretých obchodov: priebeh otvorenej pozície (a teda margin) v tom nie je, "
    + "rovnako ako denné limity strát.");
  $("#mc-note").innerHTML = notes.map(esc).join("<br>");
}

const money = v => Number(v).toLocaleString("sk-SK", { maximumFractionDigits: 0 });

const vline = (x, color, dash) => ({ type: "line", x0: x, x1: x, yref: "paper", y0: 0, y1: 1,
  line: { color, width: 2, dash } });
const vlabel = (x, text, color) => ({ x, y: 1, yref: "paper", text, showarrow: false, yanchor: "bottom",
  font: { size: 11, color } });

function histLayout(title, suffix, extra) {
  return Object.assign({
    height: 280, margin: { l: 48, r: 16, t: 18, b: 40 }, template: "plotly_white", bargap: 0.02,
    showlegend: false,
    xaxis: { title, ticksuffix: suffix },
    yaxis: { title: "vzoriek", showgrid: true },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  }, extra);
}

/** Rozdelenie break-even poplatku; zvýraznený je interval, zvislice sú poplatok a nameraná hodnota. */
function drawBeChart(be, feePct) {
  const h = be.hist;
  const color = h.centers.map(c => (c >= be.lo && c <= be.hi) ? "rgba(41,98,255,0.55)" : "rgba(41,98,255,0.16)");
  Plotly.newPlot("mc-chart", [{
    type: "bar", x: h.centers, y: h.counts, marker: { color, line: { width: 0 } },
    hovertemplate: "%{x:.4f} %<br>%{y} vzoriek<extra></extra>",
  }], histLayout("break-even poplatok (% na stranu)", " %", {
    shapes: [vline(feePct, RED, "solid"), vline(be.observed, GREEN, "dash")],
    annotations: [vlabel(feePct, "poplatok", RED), vlabel(be.observed, "nameraný", GREEN)],
  }), { displaylogo: false, responsive: true });
}

/** Rozdelenie max drawdownu v % z vrcholu; zvislice sú nameraný a 95. percentil. */
function drawDdChart(dd) {
  const h = dd.hist;
  const color = h.centers.map(c => c <= dd.p95 ? "rgba(242,54,69,0.45)" : "rgba(242,54,69,0.8)");
  Plotly.newPlot("mc-dd-chart", [{
    type: "bar", x: h.centers, y: h.counts, marker: { color, line: { width: 0 } },
    hovertemplate: "%{x:.1f} %<br>%{y} vzoriek<extra></extra>",
  }], histLayout("max drawdown (% z vrcholu)", " %", {
    shapes: [vline(dd.p95, RED, "solid"), vline(dd.observed, GREEN, "dash")],
    annotations: [vlabel(dd.p95, "95. p.", RED), vlabel(dd.observed, "nameraný", GREEN)],
  }), { displaylogo: false, responsive: true });
}

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
// Minúty na timeframe; ponuku dáva server (/api/meta → pair.timeframes, tester/timeframes.json),
// tu musí byť aspoň to, čo je v nej, inak graf taký TF ticho preskočí.
const TF_MINUTES = { "1m": 1, "2m": 2, "3m": 3, "4m": 4, "5m": 5, "15m": 15, "30m": 30,
  "1h": 60, "2h": 120, "4h": 240, "1d": 1440, "1w": 10080 };
const SPANS = [["4 h", 4 * 3600e3], ["12 h", 12 * 3600e3], ["1 deň", 86400e3], ["3 dni", 3 * 86400e3],
  ["1 týždeň", 7 * 86400e3], ["1 mesiac", 30 * 86400e3], ["1 rok", 365 * 86400e3]];
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
    // história ide vždy do `main` — keď klon stojí inde, nech je to vidno v hlavičke
    if (s.target && s.branch && s.target !== s.branch) {
      $("#branch").textContent = `${s.branch} → ${s.target}`;
      $("#branch").title = `klon je na vetve ${s.branch}, história behov ide do ${s.target}`;
    } else if (s.target) {
      $("#branch").textContent = s.target; $("#branch").title = "";
    }
    const parts = [];
    if (s.uncommitted) parts.push(`${s.uncommitted} necommitnutých`);
    if (s.ahead) parts.push(`↑${s.ahead}`);
    if (s.behind) parts.push(`↓${s.behind}`);
    $("#git-status").textContent = parts.length ? parts.join(" · ") : "synchronizované";
  } catch (e) { $("#git-status").textContent = "git: " + e.message; }
}

async function gitAction(kind) {
  const box = $("#git-box"), out = $("#git-output"), close = $("#git-close");
  box.hidden = false; close.disabled = true; out.textContent = `git ${kind} …`;
  $("#git-title").textContent = `git ${kind}`;
  try {
    const r = await api(`/api/git/${kind}`, { method: "POST", body: kind === "push" ? JSON.stringify({ author: currentUser() }) : undefined });
    out.textContent = (r.ok ? "OK\n" : "CHYBA\n") + r.output;
    $("#git-title").textContent = `git ${kind} — ${r.ok ? "hotovo" : "chyba"}`;
    $("#git-status").textContent = r.uncommitted ? `${r.uncommitted} necommitnutých` : "synchronizované";
    if (kind === "pull" && !$("#view-history").hidden) loadRuns();
  } catch (e) { out.textContent = e.message; $("#git-title").textContent = `git ${kind} — chyba`; }
  // zavrieť sa dá až po dobehnutí — inak by výstup zmizol uprostred behu
  close.disabled = false;
}

// --------------------------------------------------------------------------- //
// Navigácia a štart
// --------------------------------------------------------------------------- //

// --------------------------------------------------------------------------- //
// Analytika: ktora skupina obchodov kazi vysledok
// --------------------------------------------------------------------------- //

async function loadAnalytics() {
  const btn = $("#an-run");
  btn.disabled = true;
  $("#an-status").textContent = "počítam…";
  const params = new URLSearchParams({
    q: $("#an-query").value.trim(),
    strategy: state.strategy,
    quantiles: $("#an-quantiles").value,
    min_bucket: $("#an-minbucket").value || 8,
    limit_runs: $("#an-limit").value || 40,
  });
  try {
    const r = await api(`/api/analytics?${params}`);
    renderAnalytics(r);
    // Meranie sa pise z tych istych behov, takze tlacidlo ma zmysel az teraz.
    state.analytics = r;
    $("#an-paper").disabled = false;
    $("#an-save").disabled = false;
    $("#an-history").value = "";
    showPosudok(null);          // cerstva analytika este nie je v historii
    $("#an-status").textContent = "";
  } catch (e) {
    $("#an-status").textContent = e.message;
    $("#an-summary").innerHTML = "";
    $("#an-result").innerHTML = "";
    $("#an-paper").disabled = true;
    $("#an-save").disabled = true;
  } finally { btn.disabled = false; }
}

/** Zapíše meranie do docs/merania/ z tých istých behov, aké sú na stránke. */
async function writePaper() {
  const r = state.analytics;
  if (!r) return;
  const btn = $("#an-paper");
  btn.disabled = true;
  $("#an-status").textContent = "píšem meranie…";
  try {
    const out = await api("/api/paper", {
      method: "POST",
      body: JSON.stringify({
        runs: (r.runs || []).map(x => x.id),
        strategy: r.strategy || state.strategy,
        limit: Number($("#an-limit").value) || 40,
      }),
    });
    const chyby = (out.sections || []).filter(s => s.gap);
    $("#an-status").innerHTML = `zapísané: <code>${esc(out.path)}</code>`
      + (chyby.length ? ` · ${chyby.length} ${slovom(chyby.length, "sekcia nemá dosť dát",
          "sekcie nemajú dosť dát", "sekcií nemá dosť dát")}` : "");
  } catch (e) {
    $("#an-status").textContent = e.message;
  } finally { btn.disabled = false; }
}

// --------------------------------------------------------------------------- //
// Historia analytiky — per strategia, rovnako ako mriezky a matice
// --------------------------------------------------------------------------- //

/** Naplni ponuku ulozenych analytik. Per strategia: vlastnosti aj parametre su pri
 *  kazdej ine, takze zliate v jednom zozname by sa neporovnavali. */
async function loadAnalyticsHistory(vybrat = "") {
  const sel = $("#an-history");
  if (!sel) return;
  try {
    const r = await api(`/api/analytics/history?strategy=${encodeURIComponent(state.strategy)}`);
    sel.innerHTML = '<option value="">— nová analytika —</option>'
      + (r.items || []).map(x => {
        const be = x.break_even_pct === null || x.break_even_pct === undefined
          ? "" : ` · break-even ${fmt(x.break_even_pct, 4)} %`;
        const popis = `${anStamp(x.created)} · ${x.trades} obch. z ${x.runs} behov${be}`
          + (x.note ? ` · ${x.note}` : "");
        return `<option value="${esc(x.id)}">${esc(popis)}</option>`;
      }).join("");
    sel.value = vybrat;
  } catch (e) {
    sel.innerHTML = `<option value="">história sa nenačítala: ${esc(e.message)}</option>`;
  }
}

function anStamp(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? String(iso).slice(0, 16)
    : d.toLocaleString("sk-SK", { dateStyle: "short", timeStyle: "short" });
}

/** Posudok patrí k uloženej analytike — čerstvá ho ešte nemá kam pripísať. */
function showPosudok(zaznam) {
  const box = $("#posudok-box");
  if (!zaznam) { box.hidden = true; state.posudokId = null; return; }
  state.posudokId = zaznam.id;
  box.hidden = false;
  $("#posudok-text").value = zaznam.posudok || "";
  // Posudok napísaný k iným číslam nie je nepravdivý, len starý — a to musí byť vidieť.
  const stary = zaznam.posudok && zaznam.posudok_stamp !== zaznam.numbers;
  const chip = $("#posudok-stav");
  chip.className = "chip" + (stary ? " stale" : "");
  chip.textContent = !zaznam.posudok ? "zatiaľ nenapísaný"
    : (stary ? "starý — čísla sa medzitým zmenili" : `napísaný ${anStamp(zaznam.posudok_at)}`);
  box.open = !zaznam.posudok;
  $("#posudok-status").textContent = "";
}

async function copyZadanie() {
  if (!state.posudokId) return;
  try {
    const r = await api(`/api/analytics/history/${encodeURIComponent(state.posudokId)}/zadanie`);
    await navigator.clipboard.writeText(r.text);
    $("#posudok-status").textContent = "zadanie je v schránke — vlož ho AI";
  } catch (e) {
    $("#posudok-status").textContent = e.message;
  }
}

async function savePosudok() {
  if (!state.posudokId) return;
  const btn = $("#posudok-save");
  btn.disabled = true;
  $("#posudok-status").textContent = "ukladám…";
  try {
    const out = await api(`/api/analytics/history/${encodeURIComponent(state.posudokId)}/posudok`, {
      method: "POST",
      body: JSON.stringify({ text: $("#posudok-text").value, user: currentUser() || "" }),
    });
    $("#posudok-status").textContent = "uložené";
    $("#posudok-stav").className = "chip";
    $("#posudok-stav").textContent = `napísaný ${anStamp(out.posudok_at)}`;
    await loadAnalyticsHistory(state.posudokId);
  } catch (e) {
    $("#posudok-status").textContent = e.message;
  } finally { btn.disabled = false; }
}

/** Otvori ulozenu analytiku — vykresli sa tym istym kodom ako cerstva. */
async function openAnalyticsHistory(id) {
  if (!id) return;
  $("#an-status").textContent = "načítavam…";
  try {
    const z = await api(`/api/analytics/history/${encodeURIComponent(id)}`);
    state.analytics = z.report;
    renderAnalytics(z.report);
    $("#an-paper").disabled = false;
    $("#an-save").disabled = true;      // ulozene sa neuklada druhykrat
    showPosudok(z);
    $("#an-status").innerHTML = `uložená ${esc(anStamp(z.created))}`
      + (z.note ? ` · ${esc(z.note)}` : "");
  } catch (e) {
    $("#an-status").textContent = e.message;
  }
}

/** Ulozi zaver do historie. Obchody sa neukladaju - tie su v behoch. */
async function saveAnalytics() {
  const r = state.analytics;
  if (!r) return;
  const note = prompt("Čo si tým zisťoval? (poznámka do histórie)", "") ?? "";
  const btn = $("#an-save");
  btn.disabled = true;
  $("#an-status").textContent = "ukladám…";
  try {
    const out = await api("/api/analytics/history", {
      method: "POST",
      body: JSON.stringify({ report: r, note, user: currentUser() || "" }),
    });
    await loadAnalyticsHistory(out.id);
    showPosudok({ ...out, posudok: "" });
    $("#an-status").textContent = `uložené ako ${out.id}`;
  } catch (e) {
    $("#an-status").textContent = e.message;
    btn.disabled = false;
  }
}

// --------------------------------------------------------------------------- //
// Prop vyzva: dostanes sa k vyplate skor, nez ucet zhori?
// --------------------------------------------------------------------------- //
//
// Formular je jeden a montuje sa na dve miesta: do Analytiky (nad vybranymi behmi) a
// k Novemu behu (nad tym jednym, ked dobehne). Preto vsetky id nesu prefix - dve kopie
// s rovnakymi id by boli chyba, ktoru prehliadac nenahlasi, len prestane fungovat.

/** Markup formulára pravidiel. `p` je prefix id (`prop` alebo `nprop`). */
function propFormHtml(p) {
  return `<div class="form-grid an-form">
      <label class="field span2">Pravidlá
        <select id="${p}-preset"></select>
      </label>
      <label class="field">Účet
        <input type="number" id="${p}-account" min="1000" step="1000">
      </label>
      <label class="field">Ciele fáz (% oddelené čiarkou)
        <input type="text" id="${p}-targets" placeholder="10,5">
      </label>
      <label class="field">Denný limit % <span class="hint">0 = firma ho nemá</span>
        <input type="number" id="${p}-daily" min="0" step="0.1">
      </label>
      <label class="field">Celkový limit %
        <input type="number" id="${p}-maxloss" min="0.1" step="0.1">
      </label>
      <label class="field">Od čoho sa počíta celkový limit
        <select id="${p}-trailing"></select>
      </label>
      <label class="field inline small"><input type="checkbox" id="${p}-freeze">
        hranica sa zastaví na počiatočnom zostatku</label>
      <label class="field">Minimum dní
        <input type="number" id="${p}-mindays" min="0" step="1">
      </label>
      <label class="field">Najlepší deň max % zisku <span class="hint">0 = bez pravidla</span>
        <input type="number" id="${p}-dayshare" min="0" max="100" step="5">
      </label>
      <label class="field">Cena výzvy
        <input type="number" id="${p}-cost" min="0" step="10">
      </label>
      <label class="field">Podiel zo zisku %
        <input type="number" id="${p}-payout" min="1" max="100" step="5">
      </label>
      <label class="field inline small"><input type="checkbox" id="${p}-refund">
        cena sa vracia pri prvej výplate</label>
      <label class="field">Horizont v dňoch <span class="hint">0 = bez limitu</span>
        <input type="number" id="${p}-horizon" min="0" step="10">
      </label>
      <div class="an-actions span2">
        <button id="${p}-run" class="primary" type="button">Spočítať výzvu</button>
        <span id="${p}-status" class="hint"></span>
      </div>
    </div>
    <p id="${p}-source" class="an-note"></p>
    <div id="${p}-result"></div>`;
}

/** Predlohy pravidiel firiem; nacitaju sa raz a drzia sa v state. */
async function loadPropMeta(p) {
  const box = $(`#${p}-form`);
  if (!box) return null;
  if (!box.dataset.ready) { box.innerHTML = propFormHtml(p); box.dataset.ready = "1"; }
  state.propMeta = state.propMeta || await api("/api/prop/meta");
  const sel = $(`#${p}-preset`);
  if (!sel.options.length) {
    sel.innerHTML = Object.entries(state.propMeta.presets)
      .map(([k, v]) => `<option value="${esc(k)}">${esc(v.name)}</option>`).join("");
    $(`#${p}-trailing`).innerHTML = Object.entries(state.propMeta.trailing)
      .map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join("");
    sel.onchange = () => fillPropForm(p, sel.value);
    $(`#${p}-run`).onclick = () => runProp(p);
    fillPropForm(p, sel.value);
  }
  return state.propMeta;
}

/** Predloha do formulara. Kazde pole sa da prepisat - firmy pravidla menia. */
function fillPropForm(p, key) {
  const r = (state.propMeta.presets || {})[key];
  if (!r) return;
  $(`#${p}-account`).value = r.account;
  $(`#${p}-targets`).value = (r.targets || []).join(",");
  $(`#${p}-daily`).value = r.max_daily_loss_pct;
  $(`#${p}-maxloss`).value = r.max_loss_pct;
  $(`#${p}-trailing`).value = r.trailing;
  $(`#${p}-freeze`).checked = !!r.trailing_freeze_at_start;
  $(`#${p}-mindays`).value = r.min_days;
  $(`#${p}-dayshare`).value = r.max_day_share_pct;
  $(`#${p}-cost`).value = r.cost;
  $(`#${p}-payout`).value = r.payout_pct;
  $(`#${p}-refund`).checked = !!r.refund;
  $(`#${p}-horizon`).value = r.horizon_days;
  $(`#${p}-source`).innerHTML = r.source
    ? `Zdroj čísel: ${esc(r.source)}<br><b>Firmy pravidlá menia často — over si ich`
      + " podľa svojej zmluvy.</b>"
    : "";
}

/** Pravidla z formulara ako telo requestu. */
function propBody(p) {
  const ciele = $(`#${p}-targets`).value.split(",").map(x => Number(x.trim()))
    .filter(x => Number.isFinite(x) && x > 0);
  return {
    rules: $(`#${p}-preset`).value,
    account: Number($(`#${p}-account`).value),
    targets: ciele.length ? ciele : null,
    max_daily_loss_pct: Number($(`#${p}-daily`).value),
    max_loss_pct: Number($(`#${p}-maxloss`).value),
    trailing: $(`#${p}-trailing`).value,
    trailing_freeze_at_start: $(`#${p}-freeze`).checked,
    min_days: Number($(`#${p}-mindays`).value),
    max_day_share_pct: Number($(`#${p}-dayshare`).value),
    cost: Number($(`#${p}-cost`).value),
    payout_pct: Number($(`#${p}-payout`).value),
    refund: $(`#${p}-refund`).checked,
    horizon_days: Number($(`#${p}-horizon`).value),
  };
}

/** Spusti simulaciu. V Analytike nad vybranymi behmi, pri Novom behu nad `runIds`. */
async function runProp(p, runIds = null) {
  const behy = runIds || ((state.analytics || {}).runs || []).map(x => x.id);
  if (!behy.length) { $(`#${p}-status`).textContent = "najprv spočítaj analytiku"; return; }
  const btn = $(`#${p}-run`);
  btn.disabled = true;
  $(`#${p}-status`).textContent = "počítam…";
  try {
    const out = await api("/api/prop", {
      method: "POST",
      body: JSON.stringify({
        ...propBody(p),
        runs: behy,
        strategy: (state.analytics || {}).strategy || state.strategy,
        limit: Math.max(behy.length, Number($("#an-limit")?.value) || 40),
      }),
    });
    renderProp(p, out);
    $(`#${p}-status`).textContent = "";
  } catch (e) {
    $(`#${p}-status`).textContent = e.message;
    $(`#${p}-result`).innerHTML = "";
  } finally { btn.disabled = false; }
}

function renderProp(p, out) {
  const najlepsi = out.best_risk;
  const rows = (out.results || []).map(x => {
    const dni = x.median_days === null || x.median_days === undefined ? "—" : fmt(x.median_days, 0);
    const ev = x.ev === null || x.ev === undefined ? "—"
      : `<span class="${x.ev > 0 ? "good" : "bad"}">${x.ev > 0 ? "+" : ""}${fmt(x.ev, 0)}</span>`;
    return `<tr class="${x.risk_pct === najlepsi ? "best" : ""}">
        <td>${fmt(x.risk_pct, 2)} %</td><td>${x.attempts}</td><td>${x.passed}</td>
        <td>${x.burned}</td><td>${x.unfinished}</td>
        <td>${fmt(x.p_pass * 100, 1)} %</td><td>${dni}</td><td>${ev}</td></tr>`;
  }).join("");
  // Preco pokusy koncia je casto dolezitejsie nez samotna pravdepodobnost: iny dovod
  // znamena iny zasah (ine riziko vs. viac trhov vs. ina firma).
  const naj = (out.results || []).find(x => x.risk_pct === najlepsi) || {};
  const dovody = Object.entries(naj.reasons || {}).sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `${esc(k)} ${v}×`).join(" · ");
  const trieda = (naj.ev || 0) > 0 ? "good" : "bad";
  $(`#${p}-result`).innerHTML = `<div class="ch-box">
      ${configHtml(out.config)}
      <p class="an-note">${out.trades} obchodov z ${out.runs} behov ·
        ${esc((out.pairs || []).join(", "))} ·
        ${out.rules.phases} ${out.rules.phases === 1 ? "fáza" : "fázy"} ·
        ciele ${(out.rules.targets || []).map(x => fmt(x, 2) + " %").join(" + ")}</p>
      <table class="mx-table"><thead><tr><th>riziko</th><th>pokusov</th><th>prešiel</th>
        <th>spálený</th><th>nedobehol</th><th>P(výplata)</th><th>dní</th><th>EV</th></tr></thead>
        <tbody>${rows}</tbody></table>
      ${dovody ? `<p class="an-note">prečo pokusy končia (pri ${fmt(najlepsi, 2)} %): ${dovody}</p>` : ""}
      <div class="verdict ${trieda}">${esc(out.verdict || "")}</div>
    </div>`;
}

/** Po dobehnutí behu z karty Nový beh: spočítať výzvu z jeho obchodov. */
async function runPropForRun(runId) {
  if (!runId) return;
  $("#nprop-box").open = true;
  await loadPropMeta("nprop");
  await runProp("nprop", [runId]);
}

/** Z akej konfigurácie tie obchody sú. Bez toho sa nedá vedieť, o čom čísla hovoria. */
function configHtml(c) {
  if (!c || !c.note) return "";
  const zoznam = Object.entries(c.differing || {}).map(([k, v]) =>
    `<li><b>${esc(k)}</b>: ${v.map(x => esc(typeof x === "object" && x
      ? `${x.value} ${x.unit || ""}`.trim() : String(x))).join(" · ")}</li>`).join("");
  const detail = zoznam
    ? `<details class="cfg-diff"><summary>v čom sa behy líšia</summary><ul>${zoznam}</ul></details>`
    : "";
  // Rozne profily su chyba (zliate rozne strategie), rozne cisla jedneho profilu su
  // zvycajne zamer (--set, prepocet na ATR) - preto dva stupne, nie jeden.
  if (c.severity === "chyba") return `<div class="warnbox">${esc(c.note)}${detail}</div>`;
  return `<p class="an-note${c.severity === "pozor" ? " warn" : ""}">`
    + `<b>Konfigurácia:</b> ${esc(c.note)}</p>${detail}`;
}

/** Slabne edge? Obdobia proti intervalu, ktorý stratégia vyrobí sama od seba. */
function decayHtml(d) {
  if (!d || !d.periods || !d.periods.length) return "";
  const trieda = { "DRZI": "good", "ZLEPSUJE SA": "good", "SLABNE": "bad" }[d.verdict] || "unsure";
  const posledny = d.periods.length - 1;
  const riadky = d.periods.map((p, i) => {
    // Percentil je test len pre posledne obdobie - ostatne su opis, nech to je vidiet.
    const cls = i === posledny ? "best" : "";
    const pc = p.percentile === null || p.percentile === undefined ? "—"
      : `${fmt(p.percentile, 0)}${i === posledny ? "" : "<span class=\"muted\"> (opis)</span>"}`;
    return `<tr class="${cls}"><td>${esc(p.label)}</td><td>${p.trades}</td>`
      + `<td>${fmt(p.per_month, 1)}</td><td>${fmt(p.winrate, 1)}</td>`
      + `<td>${fmt(p.break_even_pct, 4)}</td><td>${pc}</td></tr>`;
  }).join("");
  const pasmo = d.lo === null || d.lo === undefined ? ""
    : `<p class="an-note">Úsek takej dĺžky, akú má posledné obdobie, vyjde tej istej
        stratégii medzi <b>${fmt(d.lo, 4)}</b> a <b>${fmt(d.hi, 4)} %</b> už len
        preskladaním vlastných obchodov. Preto sa posledné obdobie neporovnáva s celkom:
        je kratšie, teda aj prirodzene rozkolísanejšie.</p>`;
  return `<div class="ch-box">
      <div class="ch-head"><h3>Slabne edge?</h3></div>
      ${pasmo}
      <table class="mx-table"><thead><tr><th>obdobie</th><th>obch.</th><th>/mes.</th>
        <th>WR %</th><th>break-even</th><th>percentil</th></tr></thead>
        <tbody>${riadky}</tbody></table>
      <div class="verdict ${trieda}">${esc(d.note || d.verdict)}</div>
    </div>`;
}

/** Portfólio: koľko sa dá zarobiť a za aký drawdown. */
function portfolioHtml(p) {
  if (!p || !p.risks) return "";
  const risks = p.risks.map(r => `<tr><td>${fmt(r.risk_pct, 2)} %</td>`
    + `<td>${fmt(r.return_pct, 1)} %</td><td>${fmt(r.cagr_pct, 1)} %</td>`
    + `<td class="${r.max_drawdown_pct > 30 ? "neg" : ""}">${fmt(r.max_drawdown_pct, 1)} %</td>`
    + `<td>${r.ruin ? "RUINA" : r.trades}</td></tr>`).join("");
  const roky = (p.by_year || []).map(r => `<tr><td>${esc(r.year)}</td>`
    + `<td class="${r.return_pct < 0 ? "neg" : "pos"}">${fmt(r.return_pct, 1)} %</td>`
    + `<td>${r.trades}</td></tr>`).join("");
  const dvojice = ((p.correlations || {}).pairs || []).slice(0, 5).map(
    ([a, b, r, m]) => `<tr><td class="${r >= 0.7 ? "neg" : ""}">${fmt(r, 2)}</td>`
      + `<td>${esc(a)}</td><td>${esc(b)}</td><td>${m} mes.</td></tr>`).join("");
  const trieda = p.verdict.startsWith("TO NIE JE PORTFOLIO") ? "bad"
    : (p.verdict.startsWith("CLENOVIA SU MALO") ? "good" : "unsure");
  return `<div class="ch-box">
      <div class="ch-head"><h3>Portfólio</h3>
        <span class="chip">${p.members.length} členov · ${p.trades} obchodov</span></div>
      <p class="an-note">Vybrané behy prehraté cez jeden účet. Veľkosť pozície sa prepočíta
        na zvolené riziko — bez toho by sa sčítavali veľkosti z rôznych behov a výsledok by
        hovoril o peňaženkách, nie o stratégii.</p>
      <table class="mx-table"><thead><tr><th>riziko/obchod</th><th>zhodnotenie</th>
        <th>ročne (CAGR)</th><th>max drawdown</th><th>obchodov</th></tr></thead>
        <tbody>${risks}</tbody></table>
      ${roky ? `<p class="an-note">Rok po roku (pri ${fmt(p.risks.find(r => r.risk_pct === 1)
        ? 1 : p.risks[0].risk_pct, 2)} % na obchod) — nesie to jeden rok, alebo je to rozložené?</p>
        <table class="mx-table"><thead><tr><th>rok</th><th>zhodnotenie</th><th>obchodov</th>
        </tr></thead><tbody>${roky}</tbody></table>` : ""}
      ${dvojice ? `<p class="an-note">Najkorelovanejšie dvojice — nad +0,70 sa členovia
        nediverzifikujú, len zväčšujú pozíciu.</p>
        <table class="mx-table"><thead><tr><th>r</th><th>člen</th><th>člen</th>
        <th>prekryv</th></tr></thead><tbody>${dvojice}</tbody></table>` : ""}
      <div class="verdict ${trieda}">${esc(p.verdict)}</div>
    </div>`;
}

/** Test proti náhode: je ten edge odlíšiteľný od hodu mincou? */
function nullHtml(nt) {
  if (!nt || !nt.nulls) return "";
  const riadky = Object.entries(nt.nulls).map(([kluc, v]) => {
    const trieda = v.sigma >= 2 ? "pos" : (v.sigma <= -1 ? "neg" : "noise");
    return `<tr><td>${esc(v.null_note || kluc)}</td>`
      + `<td>${fmt(v.observed, 4)}</td>`
      + `<td>${fmt(v.mean, 4)} ± ${fmt(v.sd, 4)}</td>`
      + `<td class="${trieda}">${v.sigma > 0 ? "+" : ""}${fmt(v.sigma, 2)} σ</td>`
      + `<td>${fmt(v.percentile, 1)}</td></tr>`;
  }).join("");
  const prvy = Object.values(nt.nulls)[0] || {};
  const trieda = prvy.sigma >= 2 ? "good" : (prvy.sigma <= -1 ? "bad" : "unsure");
  return `<div class="ch-box">
      <div class="ch-head"><h3>Je to odlíšiteľné od náhody?</h3></div>
      <p class="an-note">Tá istá stratégia, ktorá obchoduje rovnako často, rovnakým smerom
        a s rovnakým stopom aj take profitom — len si nevyberá, kedy vstúpiť. Rozdiel je
        presne to, čo výber vstupu prináša.</p>
      <table class="mx-table"><thead><tr><th>náhoda</th><th>stratégia</th>
        <th>náhoda</th><th>rozdiel</th><th>percentil</th></tr></thead>
        <tbody>${riadky}</tbody></table>
      <div class="verdict ${trieda}">${esc(prvy.verdict || "")}</div>
      ${nt.note ? `<p class="an-note">${esc(nt.note)}</p>` : ""}
    </div>`;
}

/** Syntetický trh: nevyrába tú výhodu náš backtest? */
function syntheticHtml(v) {
  if (!v || !v.rows || !v.rows.length) {
    if (!v || !v.verdict) return "";
    // Chýbajúce behy sa nezamlčia — je pri nich rovno príkaz, ktorým vzniknú.
    return `<div class="ch-box"><div class="ch-head"><h3>Nevyrába to náš backtest?</h3></div>
        <p class="an-note">${esc(v.verdict)}</p>
        ${v.command ? `<pre class="cmd">${esc(v.command)}</pre>` : ""}</div>`;
  }
  const cely = x => (x === null || x === undefined) ? "—" : fmt(x, 0) + " %";
  const riadky = v.rows.map(r => {
    const s2 = r.synth;
    return `<tr class="${s2 ? "" : "muted"}"><td>${esc(r.timerange)}</td>
        <td>${fmt(r.real.break_even_pct, 4)}</td><td>${r.real.trades}</td>
        <td>${cely(r.real.fill_pct)}</td>
        <td>${s2 ? fmt(s2.break_even_pct, 4) : "—"}</td>
        <td>${s2 ? s2.trades : "—"}</td><td>${s2 ? cely(s2.fill_pct) : "—"}</td></tr>`;
  }).join("");
  const trieda = { ok: "good", chyba: "bad" }[v.severity] || "unsure";
  return `<div class="ch-box">
      <div class="ch-head"><h3>Nevyrába to náš backtest?</h3>
        <span class="chip ${v.severity === "chyba" ? "warn" : ""}">${esc(v.severity || "")}</span></div>
      <p class="an-note">Tá istá konfigurácia na <b>premiešanom</b> trhu: rozdelenie výnosov
        aj celkový drift sú tie isté, zmizlo len poradie. Edge tam nemá z čoho vzniknúť —
        a keď predsa vznikne, vyrobil ho backtest.</p>
      <table class="mx-table"><thead><tr><th>okno</th><th>break-even</th><th>obch.</th>
        <th>vyplnené</th><th>synt. break-even</th><th>obch.</th><th>vyplnené</th></tr></thead>
        <tbody>${riadky}</tbody></table>
      <div class="verdict ${trieda}">${esc(v.verdict || "")}</div>
      ${v.command && (v.missing || []).length
        ? `<p class="an-note">Bez syntetického behu: ${v.missing.map(esc).join(", ")}</p>
           <pre class="cmd">${esc(v.command)}</pre>` : ""}
    </div>`;
}

/** Charakter stratégie: čísla, dôkazy a čo z toho vyplýva pre ladenie. */
function characterHtml(ch) {
  if (!ch || !ch.title) return "";
  const cisla = [
    ["winrate", ch.winrate, "%"],
    ["payoff (zisk / strata)", ch.payoff, ""],
    ["očakávanie na obchod", ch.expectancy_pct, "%"],
    ["medián držania", ch.median_bars, "barov"],
    ["obchodov za deň", ch.trades_per_day, ""],
    ["šikmosť výnosov", ch.skew, ""],
    ["pohyb pred vstupom", ch.pre_entry_atr, "ATR"],
    ["vstupov po pohybe", ch.momentum_share, "%"],
    ["teplo pred ziskom", ch.heat_ratio, "MAE/MFE"],
  ].filter(([, v]) => v !== null && v !== undefined);

  const vystupy = Object.entries(ch.exits || {})
    .map(([k, v]) => `${esc(k)} ${fmt(v, 1)} %`).join(" · ");

  return `<div class="ch-box">
      <div class="ch-head"><h3>${esc(ch.title)}</h3>
        <span class="chip ${ch.confidence === "dobrá" ? "" : "warn"}">istota ${esc(ch.confidence)}</span></div>
      <ul class="ch-evidence">${(ch.evidence || []).map(e => `<li>${esc(e)}</li>`).join("")}</ul>
      <div class="ch-grid">${cisla.map(([meno, v, u]) =>
        `<div><span>${esc(meno)}</span><b>${fmt(v, 2)}${u ? " " + esc(u) : ""}</b></div>`).join("")}</div>
      ${vystupy ? `<p class="an-note">výstupy: ${vystupy}</p>` : ""}
      <dl class="ch-advice">
        <dt>Čo je pri tomto type normálne</dt><dd>${esc(ch.normal || "")}</dd>
        <dt>Na čo pozor</dt><dd>${esc(ch.watch || "")}</dd>
        <dt>Čo ladiť</dt><dd>${esc(ch.tune || "")}</dd>
      </dl>
    </div>`;
}

/** Ostatné typy — aby bolo vidieť, do čoho sa stratégia zaradila a čo je vedľa. */
function archetypesHtml(list, aktivny) {
  if (!list || !list.length) return "";
  const rows = list.map(a => `<tr class="${a.key === aktivny ? "tuned" : ""}">
      <td>${esc(a.title)}</td><td class="wide">${esc(a.signature)}</td></tr>`).join("");
  return `<details class="ch-types"><summary>Aké typy stratégií rozoznávame</summary>
      <table class="verify-table"><tbody>${rows}</tbody></table>
      <p class="an-note">Zaradenie je pravidlá nad zmeranými číslami, nie model — vidno,
        prečo to vyšlo. Podrobne: docs/TYPY_STRATEGII.md</p></details>`;
}

function renderAnalytics(r) {
  const zhrnutie = [
    `<div class="headline">${esc(r.headline)}</div>`,
    `<p class="an-note"><b>${r.trades}</b> obchodov z <b>${r.runs.length}</b> behov`
      + ` · break-even <b>${fmt(r.break_even_pct, 4)} %</b> · winrate ${fmt(r.winrate, 1)} %`
      + ` · ${esc(r.pairs.join(", "))}</p>`,
  ];
  zhrnutie.push(configHtml(r.config));
  if (r.mixed_pairs) {
    zhrnutie.push('<div class="warnbox">Zliate sú obchody z viacerých párov. Vzdialenosť'
      + " stopu ani prahy v cenových bodoch medzi nimi porovnateľné nie sú — pozeraj hlavne"
      + " hodinu, deň a smer, alebo si vyber jeden pár.</div>");
  }
  zhrnutie.push(portfolioHtml(r.portfolio));
  zhrnutie.push(decayHtml(r.decay));
  zhrnutie.push(nullHtml(r.nulltest));
  zhrnutie.push(syntheticHtml(r.synthetic));
  zhrnutie.push(characterHtml(r.character));
  zhrnutie.push(archetypesHtml(r.archetypes, (r.character || {}).archetype));
  zhrnutie.push(`<div class="an-runs">${r.runs.map(x =>
    `<span title="${esc(x.note)}">${esc(x.id)} (${x.trades})</span>`).join(" · ")}</div>`);
  $("#an-summary").innerHTML = zhrnutie.join("");

  const sekcia = (s, neskor) => {
    const posledny = s.buckets.length - 1;
    const rows = s.buckets.map((b, i) => {
      const cls = i === 0 ? "worst" : (i === posledny ? "best" : "");
      return `<tr class="${cls}"><td>${esc(b.label)}</td>`
        + `<td>${b.trades}</td><td>${fmt(b.share_pct, 1)} %</td>`
        + `<td>${fmt(b.winrate, 1)}</td><td>${fmt(b.break_even_pct, 4)}</td>`
        + `<td>${fmt(b.without_pct, 4)}</td>`
        + `<td>${b.impact === null ? "—" : (b.impact > 0 ? "+" : "") + fmt(b.impact, 4)}</td></tr>`;
    }).join("");
    // Parameter, ktory vlastnost riadi, je vedomost strategie - klik z neho spravi zadanie.
    const gate = s.param
      ? `<button class="ghost small param" data-param="${esc(s.param)}"
           title="Nachystá hľadanie tohto parametra na karte Nový beh">preladiť ${esc(s.param)}</button>`
      : "";
    return `<div class="an-split ${neskor ? "an-later" : ""}">
        <div class="an-head"><h3>${esc(s.title)}</h3>${gate}</div>
        <p class="an-note">${esc(s.note)}</p>
        <table><thead><tr><th>skupina</th><th>obch.</th><th>podiel</th><th>WR %</th>
          <th>break-even</th><th>bez nej</th><th>zmena</th></tr></thead>
        <tbody>${rows}</tbody></table>
      </div>`;
  };

  const casti = ["<h3>Vopred známe — podľa toho sa dá filtrovať</h3>"];
  casti.push(...r.splits.map(s => sekcia(s, false)));
  if ((r.descriptive || []).length) {
    casti.push("<h3>Známe až po obchode — len opis</h3>");
    casti.push('<p class="an-note">Tieto vlastnosti sa pri vstupe nedajú poznať, takže'
      + " „bez nej by break-even bol" + '" tu nie je príležitosť, ale pohľad dozadu.'
      + " Užitočné sú na to, aby bolo vidieť, kde obchody končia.</p>");
    casti.push(...r.descriptive.map(s => sekcia(s, true)));
  }
  $("#an-result").innerHTML = casti.join("");

  for (const b of $$("#an-result [data-param]")) {
    b.onclick = () => prepareTuning(b.dataset.param);
  }
}

/** Z analytiky rovno do hľadania: nachystá riadok parametra a prepne na formulár. */
async function prepareTuning(name) {
  showView("new");
  $("#sweep-box").open = true;
  const meta = metaByName()[name];
  $("#sweep-rows").innerHTML = "";
  addSweepRow(name);
  const row = $$("#sweep-rows .sweep-row").at(-1);
  if (isMatrix()) {
    const pocet = matrixPairs().length * matrixTimeframes().length;
    const min = pocet ? sweepMinutes(pocet) : 0;
    $("#sweep-run").textContent = pocet
      ? `▶ Prejsť trhy (${pocet} ${slovom(pocet, "beh", "behy", "behov")}${min ? ` ≈ ${fmtMinutes(min)}` : ""})`
      : "▶ Prejsť trhy";
    $("#sweep-run").disabled = !pocet;
    matrixWalletCheck();
  } else if (isHyper()) {
    const odporucane = (state.hyperMeta.suggested || {})[name];
    if (odporucane) row.querySelector("input.spec").value = odporucane;
  } else if (meta) {
    row.querySelector("input.spec").value = defaultSpec(meta);
  }
  refreshSweep();
  $("#sweep-status").textContent = `nachystané z analytiky: ${name}`;
  row.querySelector("input.spec").focus();
}

function showView(name) {
  for (const b of $$(".tabs button")) b.classList.toggle("active", b.dataset.view === name);
  $("#view-new").hidden = name !== "new"; $("#view-history").hidden = name !== "history";
  $("#view-analytics").hidden = name !== "analytics";
  // karta História je vždy celý zoznam — otvorený detail behu sa zavrie, nech neprekrýva tabuľku
  if (name === "history") { closeDetail(); loadRuns(); }
  // Historia analytiky je per strategia, takze sa nacita az pri otvoreni karty - vtedy
  // uz je jasne, ktora strategia je zvolena.
  if (name === "analytics") loadAnalyticsHistory();
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
  initSweep();
  $("#an-run").onclick = loadAnalytics;
  $("#an-paper").onclick = writePaper;
  $("#an-save").onclick = saveAnalytics;
  $("#posudok-save").onclick = savePosudok;
  $("#posudok-zadanie").onclick = copyZadanie;
  $("#an-history").onchange = () => openAnalyticsHistory($("#an-history").value);
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
