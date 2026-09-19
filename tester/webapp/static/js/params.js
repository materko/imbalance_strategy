/* TradeBot Backtester — Hodnoty parametrov a formulár parametrov stratégie. */
"use strict";

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
    const x = normSize(a, meta.base_unit), y = normSize(b, meta.base_unit);
    return x.value === y.value && x.unit === y.unit;
  }
  if (a === null || a === undefined) return b === null || b === undefined;
  if (typeof a === "number" || typeof b === "number") return Number(a) === Number(b);
  return String(a) === String(b);
}

function setParams(values, asBase) {
  const m = metaByName();
  const out = {};
  // Všetky polia configu, nie len tie vo formulári: inertné Pine vstupy formulár neukazuje,
  // ale hodnota z profilu má s behom odísť celá (beh si ukladá úplný config).
  for (const name of new Set([...Object.keys(m), ...Object.keys(state.meta.defaults || {})])) {
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
    s.onchange = () => { onChange(s.value); applyParamFilter(); }; wrap.append(s); return wrap;
  }
  if (meta.type === "size") {
    const cur = normSize(v, meta.base_unit);
    wrap.classList.add("size");
    const n = document.createElement("input"); n.type = "number"; n.step = "any"; n.value = cur.value;
    const u = document.createElement("select"); u.title = "jednotka: abs = cenové body, ticks = násobky ticku, atr = násobky ATR, pct = % ceny";
    for (const o of UNITS) { const op = document.createElement("option"); op.value = o; op.textContent = o; u.append(op); }
    u.value = cur.unit;
    const emit = () => {
      const val = Number(n.value);
      onChange(u.value === meta.base_unit ? val : { value: val, unit: u.value });
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

function displayGroup(meta) {
  if (state.paramMode !== "basic" || state.strategy !== "ibs") return meta.group;
  const name = meta.name;
  const session = /^sess([123])/.exec(name);
  if (session) return `0${Number(session[1]) + 3} · Seansa ${session[1]}`;
  if (["maxLossDollar", "legacyPineSizing", "leverage", "maxDailyWins", "tickDollarValue"].includes(name)) return "03 · Veľkosť pozície";
  if (/^(rrRatio|sl|trail|enableTrailing|minSlDistance)/.test(name)) return "02 · Zisk a ochrana";
  if (BASIC_PARAMS.has(name) || (meta.depends_on || []).some(n => BASIC_PARAMS.has(n))) return "01 · Vstupy a smer";
  return "07 · Ďalšie nastavenia";
}

function groupList() {
  const groups = [];
  for (const p of state.meta.params) { const group = displayGroup(p); if (!groups.includes(group)) groups.push(group); }
  return state.paramMode === "basic" && state.strategy === "ibs" ? groups.sort() : groups;
}

/** Skupina -> riadky; parametre s rovnakým Pine `inline` kľúčom idú do jedného riadku. */
function groupRows(group) {
  const rows = [], byInline = {};
  for (const meta of state.meta.params.filter(p => displayGroup(p) === group)) {
    if (meta.inline) {
      const inlineKey = `${meta.group}:${meta.inline}`;
      if (!byInline[inlineKey]) { byInline[inlineKey] = []; rows.push(byInline[inlineKey]); }
      byInline[inlineKey].push(meta);
    } else rows.push([meta]);
  }
  // Riadky s `depends_when` (smer podľa indikátorov) a všetko, čo od nich závisí, idú v pôvodnom
  // poradí hneď pod prepínač, ktorý ich otvára — sú to rozšírenia portu a inak by boli o kus nižšie.
  const block = [];
  const inBlock = name => block.some(r => r.some(m => m.name === name));
  for (let grew = true; grew;) {
    grew = false;
    for (const r of rows) {
      if (block.includes(r)) continue;
      if (r[0].depends_when || (r[0].depends_on || []).some(inBlock)) { block.push(r); grew = true; }
    }
  }
  const anchorName = block.flatMap(r => r[0].depends_on || []).find(n => !inBlock(n));
  const anchor = rows.find(r => r.some(m => m.name === anchorName));
  if (block.length && anchor) {
    const rest = rows.filter(r => !block.includes(r));
    const ordered = rows.filter(r => block.includes(r));
    rest.splice(rest.indexOf(anchor) + 1, 0, ...ordered);
    return rest;
  }
  return rows;
}

function tooltipFor(meta) {
  const parts = [meta.tooltip || meta.title, "", `[${meta.name}]`];
  if (meta.min !== null && meta.min !== undefined) parts.push(`rozsah ${meta.min} – ${meta.max}`);
  if (meta.base_unit) parts.push(`Základná jednotka: ${meta.base_unit}`);
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

/** Riadok má zmysel, keď je zapnutý aspoň jeden z jeho prepínačov (pri `depends_all` všetky)
 *  — a ten sám je viditeľný. Prepínač s hodnotami (`depends_when`) je „zapnutý", keď má jednu z nich. */
function dependencyMet(row, seen = new Set()) {
  const deps = (row.dataset.dependsOn || "").split(" ").filter(Boolean);
  if (!deps.length) return true;
  const when = row.dataset.dependsWhen ? JSON.parse(row.dataset.dependsWhen) : {};
  const check = name => {
    const on = name in when ? when[name].includes(state.params[name]) : !!state.params[name];
    if (!on || seen.has(name)) return false;
    const owner = $(`.prow[data-names~="${name}"]`);
    return !owner || dependencyMet(owner, new Set([...seen, name]));
  };
  return row.dataset.dependsAll ? deps.every(check) : deps.some(check);
}

/** Ukáže skrytý riadok prepnutie tohto checkboxu? Pravidlá pre inú kombináciu indikátorov
 *  sa tak nepočítajú do „N nastavení skrytých" pri checkboxe, ktorý je už zapnutý.
 *  Prepínač so zoznamom hodnôt sa počíta vždy. */
function revealedBy(row, name) {
  const value = state.params[name];
  if (typeof value !== "boolean") return true;
  state.params[name] = !value;
  const shown = dependencyMet(row);
  state.params[name] = value;
  return shown;
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
      const when = metas.map(m => m.depends_when).find(Boolean);
      if (when) row.dataset.dependsWhen = JSON.stringify(when);
      if (metas.some(m => m.depends_all)) row.dataset.dependsAll = "1";
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
      if (c) { changed = true; total++; const group = displayGroup(m[name]); perGroup[group] = (perGroup[group] || 0) + 1; }
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
        for (const d of row.dataset.dependsOn.split(" ")) {
          if (revealedBy(row, d)) collapsed[d] = (collapsed[d] || 0) + 1;
        }
      }
      if (hit && basic && state.strategy === "ibs") {
        hit = row.dataset.names.split(" ").some(name => BASIC_PARAMS.has(name) || /^sess[123]/.test(name))
          || (row.dataset.dependsOn || "").split(" ").some(name => BASIC_PARAMS.has(name));
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
  "useStructureFilter", "indSupertrend", "indAdx", "zoneDetectionTF", "enableTrading", "closeAtSessionEnd", "weekdaysOnly"]);

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
  renderParams();
}
