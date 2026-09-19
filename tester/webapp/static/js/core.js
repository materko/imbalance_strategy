/* TradeBot Backtester — jednostránková aplikácia bez frameworku.
 * Skripty v static/js/ sú klasické (nie moduly) a zdieľajú globálny priestor;
 * poradie načítania je v index.html. Tento súbor ide prvý, main.js posledný. */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const GREEN = "#089981", RED = "#f23645", BLUE = "#2962ff";
const UNITS = ["abs", "ticks", "atr", "pct"];

// --------------------------------------------------------------------------- //
// Téma (svetlá/tmavá/podľa systému). Atribút data-theme sa nastavuje aj inline
// skriptom v <head> (aby nebliklo svetlé pozadie pred načítaním app.js) — tu sa
// len drží v zhode s výberom v hlavičke a prekresľuje grafy, ktoré majú vlastné
// farby napevno v JS (Plotly layout, farby kresieb stratégie z backendu).
// --------------------------------------------------------------------------- //
const THEME_KEY = "tradebot.theme";
const systemDark = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

function loadThemePref() {
  try { return localStorage.getItem(THEME_KEY) || "auto"; } catch (_) { return "auto"; }
}
function saveThemePref(v) {
  try { localStorage.setItem(THEME_KEY, v); } catch (_) { /* ignoruj, len sa nezapamätá */ }
}
function isDarkTheme() { return document.documentElement.getAttribute("data-theme") === "dark"; }

function applyTheme(pref) {
  const dark = pref === "dark" || (pref === "auto" && !!(systemDark && systemDark.matches));
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  for (const b of $$("#theme-switch button")) b.classList.toggle("active", b.dataset.theme === pref);
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
}

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
