/* TradeBot Backtester — jednostránková aplikácia bez frameworku.
 * Skripty v static/js/ sú klasické (nie moduly) a zdieľajú globálny priestor;
 * poradie načítania je v index.html. Tento súbor ide prvý, main.js posledný. */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const GREEN = "#089981", RED = "#f23645", BLUE = "#2962ff";
const UNITS = ["abs", "ticks", "atr", "pct"];
/** Stratégia, keď ju záznam ani formulár nepovie — to isté ako `DEFAULT_STRATEGY` v `tradebot/core/config.py`
 *  (stráži `test_webapp_default_strategy.py`); inde v skriptoch sa ten kľúč ako default nepíše. */
const DEFAULT_STRATEGY = "ibs";

// --------------------------------------------------------------------------- //
// Téma (svetlá/tmavá/podľa systému). Atribút data-theme sa nastavuje aj inline
// skriptom v <head> (aby nebliklo svetlé pozadie pred načítaním app.js) — tu sa
// len drží v zhode s výberom v hlavičke a prekresľuje grafy, ktoré majú vlastné
// farby napevno v JS (Plotly layout, farby kresieb stratégie z backendu).
// --------------------------------------------------------------------------- //
const THEME_KEY = "tradebot.theme";
const systemDark = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

function loadThemePref() {
  try { return localStorage.getItem(THEME_KEY) || "dark"; } catch (_) { return "dark"; }
}
function saveThemePref(v) {
  try { localStorage.setItem(THEME_KEY, v); } catch (_) { /* ignoruj, len sa nezapamätá */ }
}
function isDarkTheme() { return document.documentElement.getAttribute("data-theme") === "dark"; }

function applyTheme(pref) {
  const dark = pref === "dark" || (pref === "auto" && !!(systemDark && systemDark.matches));
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  for (const b of $$("#theme-switch button")) b.classList.toggle("active", b.dataset.theme === pref);
  const t = $("#theme-toggle");
  if (t) t.title = `Téma: ${{ dark: "tmavá", light: "svetlá", auto: "podľa systému" }[pref] || pref} — klik prepne`;
  redrawThemedCharts();
}

function setTheme(pref) { saveThemePref(pref); applyTheme(pref); }

let lastEquityChart = null;  // { series, res } z posledného drawChart() — na prekreslenie pri zmene témy

/** Grafy majú farby (mriežka, šablóna, kresby stratégie) napevno v layoute pri
 *  vykreslení — pri prepnutí témy treba znova zavolať to, čo ich naposledy nakreslilo. */
function redrawThemedCharts() {
  if (pc.last) renderPairChart(pc.last.candles, pc.last.objects);
  if (lastEquityChart) drawChart(lastEquityChart.series, lastEquityChart.res);
  if (mc.lastBe) drawBeChart(mc.lastBe, mc.lastFeePct);
  if (mc.lastDd) drawDdChart(mc.lastDd);
  if (typeof dvCharts === "function") dvCharts();
}

const state = {
  meta: null,          // /api/meta; params/defaults/profiles… sú vždy aktívnej stratégie (viď setStrategy)
  strategy: DEFAULT_STRATEGY,   // kľúč aktívnej stratégie vo formulári
  params: {},          // aktuálne hodnoty formulára (v tvare pre config_cls.from_dict)
  base: {},            // hodnoty východiskového profilu (na zvýraznenie odchýlok)
  profile: null,
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

/** Riadok dlaždíc s číslami nad kartou (Hub, Live): `[{k: menovka, v: hodnota, s: podnadpis, cls}]`. */
function kpiRow(el, tiles) {
  el.innerHTML = tiles.map(t => `<div class="kpi-tile"><span>${t.k}</span><b class="${t.cls || ""}">${t.v}</b>${t.s ? `<small>${t.s}</small>` : ""}</div>`).join("");
  el.hidden = !tiles.length;
}

function currentUser() { return ($("#who").value || "").trim() || null; }

/** Text chyby z odpovede API: reťazec tak, ako je; zoznam chýb validácie (422 z Pydanticu) ako
 *  „pole: správa; …" namiesto surového JSON (audit N-FE-4); čokoľvek iné ako JSON. */
function apiErrorText(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map(x => {
      if (!x || typeof x.msg !== "string") return JSON.stringify(x);
      const pole = (Array.isArray(x.loc) ? x.loc : []).filter(c => c !== "body" && c !== "query").join(".");
      return pole ? `${pole}: ${x.msg}` : x.msg;
    }).join("; ");
  }
  return JSON.stringify(detail);
}

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try { const j = await r.json(); msg = apiErrorText(j.detail ?? j); } catch (_) { /* text */ }
    const err = new Error(msg);
    err.status = r.status;   // poller podľa neho rozozná „už neexistuje" (404) od výpadku
    throw err;
  }
  const ct = r.headers.get("content-type") || "";
  return ct.includes("json") ? r.json() : r.text();
}

/** Jeden spoločný poller pre frontu, mriežku, hyperopt a maticu (audit N-FE-4).
 *
 *  `step()` spraví jedno načítanie a vráti pravdu, kým má zmysel pýtať sa ďalej. `kick()` ho spustí hneď
 *  (a zruší naplánované kolo), `stop()` ho zastaví. Po chybe sa pauza zdvojuje až po `maxDelay`, 404 reťaz
 *  ukončí (vec už neexistuje — pýtať sa na ňu navždy nemá zmysel) a každú chybu dostane `onError(e, info)`,
 *  aby ju bolo vidno; `onOk()` hlásenie zruší. `idle` = pauza, kým `step` hovorí „netreba" (bez nej sa stojí),
 *  `forever` = ani 404 reťaz neukončí (fronta existuje vždy).
 *  Kolo, ktoré medzitým predbehol novší `kick`/`stop`, už nič neplánuje. */
function makePoller(opts) {
  const interval = opts.interval || 3000;
  const maxDelay = opts.maxDelay || 30000;
  let timer = null, gen = 0, failures = 0;
  const plan = (ms, mine) => {
    if (mine !== gen) return;
    clearTimeout(timer);
    timer = setTimeout(run, ms);
  };
  async function run() {
    const mine = ++gen;
    clearTimeout(timer);
    timer = null;
    let more = false;
    try {
      more = await opts.step();
    } catch (e) {
      if (mine !== gen) return;
      if (e && e.status === 404 && !opts.forever) {
        failures = 0;
        if (opts.onError) opts.onError(e, { fatal: true, delay: 0 });
        return;
      }
      failures += 1;
      const delay = Math.min(interval * 2 ** failures, maxDelay);
      if (opts.onError) opts.onError(e, { fatal: false, delay });
      plan(delay, mine);
      return;
    }
    if (mine !== gen) return;
    failures = 0;
    if (opts.onOk) opts.onOk();
    if (more) plan(interval, mine);
    else if (opts.idle) plan(opts.idle, mine);
  }
  return {
    kick: run,
    stop() { gen += 1; clearTimeout(timer); timer = null; failures = 0; },
  };
}
