/* TradeBot Backtester — Diverzifikácia: viac nastavení naraz na jednom účte. */
"use strict";

// --------------------------------------------------------------------------- //
// Diverzifikacia: nastavenia z roznych strategii, ktore by bezali naraz
// --------------------------------------------------------------------------- //
//
// Port obrazovky Diverzifikácia zo stránky výsledkov (tester/dashboard), len dáta nejdú
// z ručne vyrobeného JSON, ale z histórie: nastavenie a trh z /api/analytics/configs,
// obchody jeho behov z /api/diversify/trades (bez duplicít z prekrývajúcich sa okien).
// Všetko ostatné sa počíta tu - násobok veľkosti sa mení bez nového dopytu.

const DV_KEY = "tradebot.diversify";
const DV_MAX = 8;
const DV_OOS = "2025-09-04";
const DV_FROM = "2021-10-01", DV_TO = "2026-09-05";
const DV_YEARS = [["21/22", "2021-10-01", "2022-10-01"], ["22/23", "2022-10-01", "2023-10-01"],
                  ["23/24", "2023-10-01", "2024-10-01"], ["24/25", "2024-10-01", DV_OOS],
                  ["25/26 (odložený)", DV_OOS, DV_TO]];
const DV_WD = ["Po", "Ut", "St", "Št", "Pi", "So", "Ne"];
const DV_MONTHS = ["jan", "feb", "mar", "apr", "máj", "jún", "júl", "aug", "sep", "okt", "nov", "dec"];
const DV_COLORS = ["#2962ff", "#e8590c", "#9c36b5", "#0ca678", "#f08c00", "#1098ad", "#d6336c", "#5c940d"];

const dv = {
  items: null,          // [{strategy, setting, market, label, name, run_ids, mult}]
  configs: {},          // strategia -> nastavenia z /api/analytics/configs
  trades: {},           // run_ids.join(",") -> odpoved /api/diversify/trades
  open: {},
  all: false,           // aj stratégie a nastavenia, ktoré smernicou neprešli
  result: null,
  log: { view: "tr", item: "", year: "", res: "", page: 0, sort: null, dir: 1 },
};

const dvNfCache = {};
const dvNf = d => (dvNfCache[d] = dvNfCache[d] || new Intl.NumberFormat("sk-SK", { minimumFractionDigits: d, maximumFractionDigits: d }));
function dvNum(v, d = 0) { return v == null || !isFinite(v) ? "—" : dvNf(d).format(v); }
function dvMoney(v, d = 0) { return v == null || !isFinite(v) ? "—" : (v < 0 ? "−" : "") + dvNf(d).format(Math.abs(v)) + " $"; }
function dvCompact(v) {
  const a = Math.abs(v);
  return (v < 0 ? "−" : "") + (a >= 1000 ? dvNf(a >= 10000 ? 0 : 1).format(a / 1000) + "k" : dvNf(0).format(a));
}
function dvPf(v) { return v == null ? "—" : v === Infinity ? "∞" : dvNf(2).format(v); }
function dvCls(v) { return v > 0 ? "pos" : v < 0 ? "neg" : ""; }
function dvPfCls(v) { return v == null ? "" : v >= 1.3 ? "pos" : v < 1 ? "neg" : "warn"; }
function dvDate(d) { const [y, m, dd] = String(d).slice(0, 10).split("-"); return `${+dd}. ${+m}. ${y}`; }
function dvDateTime(iso) { return dvDate(iso) + " " + dvNyTime(iso); }
function dvColor(i) { return DV_COLORS[i % DV_COLORS.length]; }
function dvSw(i) { return `<span class="dv-sw" style="background:${dvColor(i)}"></span>`; }
function dvYear(d) { const y = DV_YEARS.find(y => d >= y[1] && d < y[2]); return y ? y[0] : ""; }
function dvKey(it) { return it.run_ids.join(","); }
function dvRuns(n) { return `${n} ${n === 1 ? "beh" : n < 5 ? "behy" : "behov"}`; }

const dvNyFmt = new Intl.DateTimeFormat("en-GB", { timeZone: "America/New_York", hour: "2-digit", minute: "2-digit", hour12: false });
function dvNyTime(iso) { return dvNyFmt.format(new Date(iso)); }
function dvNyHour(iso) { return +dvNyTime(iso).slice(0, 2) % 24; }

function dvLoad() {
  if (dv.items) return;
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(DV_KEY) || "null"); } catch (_) { /* súkromné okno */ }
  dv.items = (Array.isArray(saved) ? saved : []).filter(x => x && Array.isArray(x.run_ids) && x.run_ids.length).slice(0, DV_MAX);
}
function dvSave() { try { localStorage.setItem(DV_KEY, JSON.stringify(dv.items)); } catch (_) { /* nezapamätá sa */ } }

/** Krátke meno nastavenia: `IBS EZ 1 · PF 1,55 · …` → `IBS EZ 1`; bez `_title` meno súboru profilu. */
function dvSettingName(strategyTitle, n) {
  if (n.title) return String(n.title).split(" · ")[0];
  const file = String(n.profile || "").replace(/\\/g, "/").split("/").pop().replace(/\.json$/, "");
  const variant = Object.entries(n.variant || {}).map(([k, v]) => `${k}=${v}`).join(", ");
  return `${strategyTitle} · ${file}${variant ? " · " + variant : ""}`;
}

// ---------------------------------------------------------------- výpočet --- //

function dvStats(pnls) {
  let n = pnls.length, gw = 0, gl = 0, w = 0, eq = 0, peak = 0, dd = 0, cw = 0, cl = 0, ws = 0, ls = 0, best = null, worst = null;
  for (const p of pnls) {
    if (p > 0) { gw += p; w++; cw++; cl = 0; } else { if (p < 0) gl -= p; cl++; cw = 0; }
    ws = Math.max(ws, cw); ls = Math.max(ls, cl);
    eq += p; peak = Math.max(peak, eq); dd = Math.max(dd, peak - eq);
    if (best == null || p > best) best = p;
    if (worst == null || p < worst) worst = p;
  }
  return { n, wr: n ? 100 * w / n : null, pf: gl ? gw / gl : (gw ? Infinity : null), pnl: gw - gl, dd,
           avg: n ? (gw - gl) / n : null, avgWin: w ? gw / w : null, avgLoss: n - w ? -gl / (n - w) : null,
           winStreak: ws, lossStreak: ls, best, worst, retDd: dd ? (gw - gl) / dd : null };
}

function dvDayPart(map) {
  const keys = Object.keys(map).sort(), vals = keys.map(k => map[k]);
  const pos = vals.filter(v => v > 0), neg = vals.filter(v => v < 0);
  const sum = a => a.reduce((s, v) => s + v, 0);
  let ls = 0, cl = 0;
  const months = {}, wd = {};
  keys.forEach((k, j) => {
    const v = vals[j]; cl = v < 0 ? cl + 1 : 0; ls = Math.max(ls, cl);
    months[k.slice(0, 7)] = (months[k.slice(0, 7)] || 0) + v;
    const w = (new Date(k + "T12:00:00Z").getUTCDay() + 6) % 7;
    (wd[w] = wd[w] || []).push(v);
  });
  const mk = Object.keys(months).sort(), mv = mk.map(k => months[k]);
  const sorted = vals.slice().sort((a, b) => a - b), h = sorted.length >> 1;
  const at = v => keys[vals.indexOf(v)];
  const mMin = Math.min(...mv), mMax = Math.max(...mv);
  return {
    days: vals.length, winPct: vals.length ? 100 * pos.length / vals.length : 0,
    avg: vals.length ? sum(vals) / vals.length : 0,
    median: sorted.length ? (sorted.length % 2 ? sorted[h] : (sorted[h - 1] + sorted[h]) / 2) : 0,
    avgWin: pos.length ? sum(pos) / pos.length : 0, avgLoss: neg.length ? sum(neg) / neg.length : 0,
    lossStreak: ls, months, monthsPos: mv.length ? 100 * mv.filter(v => v > 0).length / mv.length : 0,
    worstMonth: mk.length ? [mk[mv.indexOf(mMin)], mMin] : null, bestMonth: mk.length ? [mk[mv.indexOf(mMax)], mMax] : null,
    worstDay: sorted.length ? [at(sorted[0]), sorted[0]] : null,
    bestDay: sorted.length ? [at(sorted[sorted.length - 1]), sorted[sorted.length - 1]] : null,
    weekday: wd,
  };
}

function dvCompute() {
  return dvComputeParts(dv.items.map((it, i) => {
    const src = dv.trades[dvKey(it)], m = +it.mult || 1;
    const inside = src.trades.filter(t => t[0].slice(0, 10) >= DV_FROM && t[0].slice(0, 10) < DV_TO);
    const trades = inside.map(t => ({ i, open: t[0], close: t[1], dir: t[2] === "S" ? "short" : "long",
                                      entry: t[3], exit: t[4], pnl: t[5] * m, reason: t[6], day: t[7] }));
    const daily = {};
    for (const t of trades) daily[t.day] = (daily[t.day] || 0) + t.pnl;
    return { i, it, src, mult: m, trades, daily, name: it.name || it.label, outside: src.trades.length - inside.length };
  }));
}

/** Zlúčenie častí `{i (poradie), c (farba, inak i), name, trades [{i, open, close, dir, entry, exit, pnl, reason}], daily {deň: pnl}}`
 *  — to isté pre Diverzifikáciu (behy z histórie) aj kartu Naživo (obchody u brokera v $ alebo R). */
function dvComputeParts(parts) {
  const byClose = (a, b) => (a.close < b.close ? -1 : a.close > b.close ? 1 : 0);
  const all = parts.flatMap(p => p.trades).sort(byClose);
  const days = {};
  for (const p of parts) for (const d in p.daily) days[d] = (days[d] || 0) + p.daily[d];
  const dayKeys = Object.keys(days).sort();
  const yearly = trs => DV_YEARS.map(y => dvStats(trs.filter(t => t.open.slice(0, 10) >= y[1] && t.open.slice(0, 10) < y[2]).map(t => t.pnl)));
  // korelácia denných výsledkov (dni, keď obchodovali obe)
  const corr = [];
  for (let a = 0; a < parts.length; a++) for (let b = a + 1; b < parts.length; b++) {
    const ka = parts[a].daily, kb = parts[b].daily, common = Object.keys(ka).filter(d => d in kb);
    let r = null, both = 0;
    if (common.length > 10) {
      const xa = common.map(d => ka[d]), xb = common.map(d => kb[d]);
      const ma = xa.reduce((s, v) => s + v, 0) / xa.length, mb = xb.reduce((s, v) => s + v, 0) / xb.length;
      let cov = 0, va = 0, vb = 0;
      for (let j = 0; j < xa.length; j++) { cov += (xa[j] - ma) * (xb[j] - mb); va += (xa[j] - ma) ** 2; vb += (xb[j] - mb) ** 2; }
      r = va && vb ? cov / Math.sqrt(va * vb) : null;
      both = common.filter(d => ka[d] < 0 && kb[d] < 0).length;
    }
    corr.push({ a, b, common: common.length, r, both });
  }
  // súbežné pozície naprieč nastaveniami
  const ev = [];
  for (const t of all) { ev.push([t.open, 1]); ev.push([t.close, -1]); }
  ev.sort((x, y) => (x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : x[1] - y[1]));
  let cur = 0, maxConcurrent = 0;
  for (const e of ev) { cur += e[1]; maxConcurrent = Math.max(maxConcurrent, cur); }
  const hours = {};
  for (const p of parts) for (const t of p.trades) {
    const h = dvNyHour(t.open);
    ((hours[h] = hours[h] || {})[p.i] = hours[h][p.i] || []).push(t.pnl);
  }
  let eq = 0;
  const equity = dayKeys.map(d => [d, (eq += days[d])]);
  return {
    parts: parts.map(p => {
      let cum = 0;
      return { ...p, c: p.c ?? p.i, total: dvStats(p.trades.map(t => t.pnl)), yearly: yearly(p.trades), days: dvDayPart(p.daily),
               equity: Object.keys(p.daily).sort().map(d => [d, (cum += p.daily[d])]),
               reasons: ["take_profit", "stop_loss"].map(r => { const x = p.trades.filter(t => t.reason === r); return [r, x.length, x.reduce((s, t) => s + t.pnl, 0)]; }),
               dirs: ["long", "short"].map(d => [d, dvStats(p.trades.filter(t => t.dir === d).map(t => t.pnl))]) };
    }),
    all, total: dvStats(all.map(t => t.pnl)), yearly: yearly(all),
    dayStats: dvStats(dayKeys.map(d => days[d])), days: dvDayPart(days), dayMap: days,
    corr, maxConcurrent, hours, equity,
  };
}

// ------------------------------------------------------------------ výber --- //

async function dvConfigs(strategy) {
  if (!dv.configs[strategy]) {
    dv.configs[strategy] = (await api(`/api/analytics/configs?strategy=${encodeURIComponent(strategy)}`)).settings || [];
  }
  return dv.configs[strategy];
}

/** Nastavenie, ktoré prešlo smernicou: profil s prefixom zo smernice (`PRESIEL_SMERNICAMI_`,
 *  `SMERNICE_CS_`) alebo súbor z rannej kontroly (`…/checkup/vwaporb_PRESIEL_SMERNICAMI_…json`,
 *  `ibsentry_presiel1_…json`) - meno súboru je tam s kľúčom stratégie vpredu. */
function dvIsSmernice(n) {
  const file = String(n.profile || "").replace(/\\/g, "/").split("/").pop();
  return isSmerniceProfile(file) || /presiel|smernic/i.test(file);
}
/** Nastavenia stratégie v ponuke: predvolene len tie, ktoré prešli smernicou. */
function dvShown(cfg) { return dv.all ? cfg : cfg.filter(dvIsSmernice); }

function dvPickerHtml() {
  const picked = new Set(dv.items.map(dvKey)), full = dv.items.length >= DV_MAX;
  // Stratégia, ktorej nastavenia zo smernice v histórii nemajú beh, sa v ponuke len plietla.
  const strategies = (state.meta.strategies || []).filter(s => dv.all
    || (inSmernice(s.key) && !(dv.configs[s.key] && !dvShown(dv.configs[s.key]).length)));
  if (!strategies.length) return `<p class="hint">Žiadna stratégia zatiaľ neprešla smernicou.</p>`;
  return strategies.map(s => {
    const cfg = dv.configs[s.key] && dvShown(dv.configs[s.key]);
    let body = `<p class="hint">Načítavam nastavenia z histórie…</p>`;
    if (cfg) {
      const rows = [];
      for (const n of cfg) for (const m of n.markets) {
        const key = m.run_ids.join(","), on = picked.has(key);
        rows.push(`<div class="dv-set"><span class="lbl">${esc(dvSettingName(s.title, n))}
            <small>${esc(pairShort(m.pair))} ${esc(m.timeframe)} · ${dvRuns(m.runs)} · ${dvNum(m.trades)} obch.</small></span>
          <button type="button" class="ghost" data-dv-add="${esc(s.key)}" data-dv-setting="${esc(n.key)}" data-dv-market="${esc(m.key)}"${on || full ? " disabled" : ""}>${on ? "Pridané" : "Pridať"}</button></div>`);
      }
      body = rows.join("") || `<p class="hint">${dv.all ? "V histórii nie je dobehnutý beh s obchodmi."
        : "V histórii nie je beh nastavenia, ktoré prešlo smernicou."}</p>`;
    }
    return `<details class="dv-strat" data-key="${esc(s.key)}"${dv.open[s.key] ? " open" : ""}>
      <summary><span>${esc(s.title)}</span><span class="hint">${cfg ? cfg.length + " nast." : ""}</span></summary>${body}</details>`;
  }).join("");
}

function dvSelectedHtml() {
  if (!dv.items.length) return `<p class="hint">Zatiaľ nič. Pri nastavení vľavo klikni na <b>Pridať</b>; prepočet má zmysel od dvoch nastavení.</p>`;
  return dv.items.map((it, i) => `<div class="dv-item"><span class="dv-sw" style="background:${dvColor(i)}"></span>
      <span class="lbl"><input type="text" value="${esc(it.name || it.label)}" data-dv-name="${i}" aria-label="Krátke meno nastavenia">
        <small>${esc(it.label)}</small></span>
      <label class="hint">× <input type="text" inputmode="decimal" value="${esc(String(it.mult).replace(".", ","))}" data-dv-mult="${i}" aria-label="Násobok veľkosti (napr. 0,5)"></label>
      <button type="button" class="ghost" data-dv-del="${i}" aria-label="Odobrať">✕</button></div>`).join("");
}

function renderDiversify() {
  dvLoad();
  const root = $("#dv-root");
  $("#dv-picker").innerHTML = dvPickerHtml();
  $("#dv-selected").innerHTML = dvSelectedHtml();
  $("#dv-count").textContent = `${dv.items.length} / ${DV_MAX}`;
  $("#dv-run").disabled = !dv.items.length;
  $("#dv-clear").hidden = !dv.items.length;
  for (const d of $$("details.dv-strat", root)) {
    d.addEventListener("toggle", () => {
      dv.open[d.dataset.key] = d.open;
      if (d.open && !dv.configs[d.dataset.key]) {
        dvConfigs(d.dataset.key).then(renderDiversify).catch(e => { d.querySelector(".hint").textContent = e.message; });
      }
    });
  }
  for (const b of $$("[data-dv-add]", root)) b.onclick = () => {
    const sk = b.dataset.dvAdd, nk = b.dataset.dvSetting, mk = b.dataset.dvMarket;
    const s = (state.meta.strategies || []).find(x => x.key === sk);
    const n = dv.configs[sk].find(x => x.key === nk), m = n.markets.find(x => x.key === mk);
    const name = dvSettingName(s.title, n);
    // Krátke meno do tabuliek: `_title` profilu po prvú bodku, inak názov stratégie;
    // druhé nastavenie tej istej stratégie dostane poradové číslo. Dá sa prepísať.
    const base = n.title ? name : s.title;
    let short = base;
    for (let k = 2; dv.items.some(x => x.name === short); k++) short = `${base} (${k})`;
    dv.items.push({ strategy: sk, setting: nk, market: mk, run_ids: m.run_ids, mult: 1, name: short,
                    label: `${s.title} · ${name} · ${pairShort(m.pair)} ${m.timeframe}` });
    dvSave(); renderDiversify();
  };
  for (const b of $$("[data-dv-del]", root)) b.onclick = () => { dv.items.splice(+b.dataset.dvDel, 1); dvSave(); renderDiversify(); };
  for (const inp of $$("[data-dv-mult]", root)) inp.onchange = () => {
    let v = parseFloat(String(inp.value).replace(",", "."));
    if (!(v > 0)) v = 1;
    dv.items[+inp.dataset.dvMult].mult = v; dvSave(); inp.value = String(v).replace(".", ",");
  };
  for (const inp of $$("[data-dv-name]", root)) inp.onchange = () => {
    dv.items[+inp.dataset.dvName].name = inp.value.trim() || dv.items[+inp.dataset.dvName].label; dvSave();
  };
}

function setupDiversify() {
  $("#dv-run").onclick = dvRun;
  $("#dv-rerun").onclick = dvRun;
  $("#dv-edit").onclick = () => dvCollapse(false);
  $("#dv-all").onchange = e => { dv.all = e.target.checked; renderDiversify(); };
  $("#dv-clear").onclick = () => { dv.items = []; dvSave(); dv.result = null; $("#dv-out").innerHTML = ""; renderDiversify(); };
}

/** Po Prepočítať sa výber zbalí do jedného riadka - výsledok je hneď pod ním, nie
 *  o dve obrazovky nižšie, kde by ho tester nenašiel. „Upraviť výber" ho rozbalí. */
function dvCollapse(on) {
  $("#dv-pick").hidden = on;
  $("#dv-bar").hidden = !on;
  $("#dv-bar-items").innerHTML = dv.items.map((it, i) =>
    `<span class="dv-bar-item">${dvSw(i)}${esc(it.name || it.label)}${+it.mult !== 1 ? ` <span class="hint">× ${dvNum(+it.mult, 2)}</span>` : ""}</span>`).join("");
  if (!on) $("#dv-pick").scrollIntoView({ behavior: "smooth", block: "start" });
}

/** Pri otvorení karty: ponuka nastavení; stratégie vybraných nastavení sa rovno načítajú. */
async function loadDiversify() {
  dvLoad();
  for (const it of dv.items) dv.open[it.strategy] = true;
  renderDiversify();
  // Nastavenia stratégií zo smernice hneď všetky - až potom je jasné, ktoré majú čo ponúknuť.
  const keys = new Set([...dv.items.map(it => it.strategy),
                        ...(state.meta.strategies || []).filter(s => inSmernice(s.key)).map(s => s.key)]);
  await Promise.all([...keys].map(s => dvConfigs(s).catch(() => null)));
  renderDiversify();
}

async function dvRun() {
  if (!dv.items.length) return;
  const status = $("#dv-status"), out = $("#dv-out");
  const busy = on => { for (const id of ["#dv-run", "#dv-rerun", "#dv-edit"]) $(id).disabled = on; };
  busy(true);
  status.textContent = "";
  dvCollapse(true);
  const steps = dv.items.length;
  let done = dv.items.filter(it => dv.trades[dvKey(it)]).length;
  const progress = text => { out.innerHTML = `<div class="card dv-busy"><span class="dv-spinner"></span><span>${text}</span></div>`; };
  progress(`Načítavam obchody z histórie… ${done} / ${steps}`);
  $("#dv-bar").scrollIntoView({ behavior: "smooth", block: "start" });
  try {
    await Promise.all(dv.items.map(async it => {
      if (dv.trades[dvKey(it)]) return;
      dv.trades[dvKey(it)] = await api(`/api/diversify/trades?runs=${encodeURIComponent(dvKey(it))}`);
      progress(`Načítavam obchody z histórie… ${++done} / ${steps}`);
    }));
    progress("Počítam roky, mesiace, dni a korelácie…");
    await new Promise(r => setTimeout(r, 30));   // nech sa text vykreslí pred výpočtom
    dv.log = { view: "tr", item: "", year: "", res: "", page: 0, sort: null, dir: 1 };
    dv.result = dvCompute();
    dvRenderOut();
  } catch (e) {
    out.innerHTML = `<div class="card dv-busy neg">Prepočet zlyhal: ${esc(e.message)}</div>`;
  } finally {
    busy(false);
  }
}

// ---------------------------------------------------------------- výstup --- //

function dvSumRow(name, oos, all, cl = "") {
  return `<tr class="${cl}"><td class="l">${name}</td>
    <td>${oos.n}</td><td>${dvNum(oos.wr, 1)} %</td><td class="${dvPfCls(oos.pf)}">${dvPf(oos.pf)}</td><td class="${dvCls(oos.pnl)}">${dvMoney(oos.pnl)}</td><td>${dvMoney(-oos.dd)}</td>
    <td>${all.n}</td><td>${dvNum(all.wr, 1)} %</td><td class="${dvPfCls(all.pf)}">${dvPf(all.pf)}</td><td class="${dvCls(all.pnl)}">${dvMoney(all.pnl)}</td><td>${dvMoney(-all.dd)}</td><td>${all.retDd == null ? "—" : dvNum(all.retDd, 1)}</td></tr>`;
}

function dvFindings(R) {
  const out = [], P = R.parts;
  const negYear = P.filter(p => p.yearly.some(y => y.n && y.pnl < 0));
  const cy = R.yearly.filter(y => y.n && y.pnl < 0);
  out.push(cy.length ? ["bad", `Spolu prerobené roky: ${cy.length} z 5.`]
    : ["ok", "Spolu zarobili všetky roky (5 z 5)" + (negYear.length ? "; samostatne mali stratový rok: " + negYear.map(p => esc(p.name)).join(", ") + "." : ", aj každé nastavenie samo.")]);
  const rs = R.corr.filter(c => c.r != null);
  if (rs.length) {
    const hi = rs.filter(c => c.r >= 0.5);
    out.push(hi.length
      ? ["warn", "Niektoré nastavenia sa hýbu spolu (korelácia ≥ 0,5): " + hi.map(c => esc(P[c.a].name) + " × " + esc(P[c.b].name)).join(", ") + ". Ich súčet sa správa skôr ako väčšia pozícia než ako diverzifikácia."]
      : ["ok", "Korelácia denných výsledkov je nízka (" + rs.map(c => esc(P[c.a].name) + " × " + esc(P[c.b].name) + " " + dvNum(c.r, 2)).join(", ") + "), takže sa navzájom vyrovnávajú."]);
  }
  const best = Math.max(...P.map(p => p.days.monthsPos));
  out.push([R.days.monthsPos >= best ? "ok" : "warn", `Spolu je v pluse ${dvNum(R.days.monthsPos)} % mesiacov; samostatne ` + P.map(p => esc(p.name) + " " + dvNum(p.days.monthsPos) + " %").join(", ") + "."]);
  const sumDd = P.reduce((s, p) => s + p.total.dd, 0);
  out.push(["", `Max. prepad spolu ${dvMoney(-R.total.dd)} oproti súčtu samostatných prepadov ${dvMoney(-sumDd)} — ` + (R.total.dd < sumDd ? "prepady neprichádzajú naraz." : "prepady prichádzajú naraz.")]);
  if (R.total.pnl > 0) out.push(["", "Podiel na zisku: " + P.map(p => esc(p.name) + " " + dvNum(100 * p.total.pnl / R.total.pnl) + " %").join(", ") + "."]);
  out.push(["", "Najhorší deň spolu " + (R.days.worstDay ? dvDate(R.days.worstDay[0]) + " " + dvMoney(R.days.worstDay[1]) : "—") +
    `, najviac stratových dní po sebe ${R.days.lossStreak}, naraz v trhu najviac ${R.maxConcurrent} pozície.`]);
  const tag = { ok: "v poriadku", warn: "pozor", bad: "pozor", "": "dobré vedieť" };
  return `<ul class="dv-find">${out.map(x => `<li><span class="chip ${x[0]}">${tag[x[0]]}</span><span>${x[1]}</span></li>`).join("")}</ul>`;
}

/** Kontrola dát: z ktorých behov obchody sú a čo sa zahodilo - nech je vidieť, že súčet sedí. */
function dvAuditHtml(R) {
  const rows = R.parts.map(p => {
    const s = p.src, used = s.windows.filter(w => w.trades);
    const ok = !s.overlapping && !s.skipped.length;
    const what = [
      `${dvRuns(used.length)} s obchodmi: ` + used.map(w => `<span title="${esc(w.run_id)}">${esc(fmtWindow(w.timerange))} (${w.trades})</span>`).join(", "),
      s.duplicates ? `${s.duplicates} duplicít z prekrývajúcich sa okien zahodených` : "",
      s.skipped.length ? `vynechané behy s iným poplatkom: ` + s.skipped.map(w => `${esc(w.run_id)} (${esc(fmtWindow(w.timerange))}, poplatok ${w.fee})`).join(", ") : "",
      p.outside ? `${p.outside} obchodov mimo obdobia 10/2021 – 9/2026 sa nepočíta` : "",
      s.overlapping ? `<b class="neg">${s.overlapping} pozícií sa prekrýva v čase</b>` : "",
    ].filter(Boolean).join(" · ");
    return `<tr><td class="l">${dvSw(p.i)}${esc(p.name)}</td><td>${p.trades.length}</td><td>${Object.keys(p.daily).length}</td>
      <td>${s.fee ?? "—"}</td><td><span class="chip ${ok ? "ok" : "warn"}">${ok ? "v poriadku" : "pozri"}</span></td><td class="l dv-audit">${what}</td></tr>`;
  }).join("");
  return `<div class="card"><h2>Kontrola dát</h2><div class="table-wrap"><table class="dv-table"><thead><tr><th class="l">Nastavenie</th><th>Obchody</th><th>Dni</th><th>Poplatok</th><th>Stav</th><th class="l">Z čoho</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="hint">Obchod, ktorý je v dvoch behoch (okná 23/24 a 24/25 sa prekrývajú o september 2024, celé obdobie prekrýva všetky okná), sa počíta raz. Deň = dátum zatvorenia v UTC (ako na stránke výsledkov); časy v denníku sú newyorské.</p></div>`;
}

function dvRenderOut() {
  const R = dv.result, P = R.parts, multi = P.length > 1;
  let h = `<div class="card"><h2>Súhrn</h2><div class="table-wrap"><table class="dv-table"><thead><tr><th></th><th colspan="5">Posledný rok (odložený)</th><th colspan="6">Celé obdobie</th></tr>
    <tr><th class="l">Nastavenie</th><th>Obch.</th><th>WR</th><th>PF</th><th>Zisk</th><th>Max. DD</th><th>Obch.</th><th>WR</th><th>PF</th><th>Zisk</th><th>Max. DD</th><th>Zisk / DD</th></tr></thead><tbody>` +
    P.map(p => dvSumRow(dvSw(p.i) + esc(p.name) + (p.mult !== 1 ? ` <span class="hint">× ${dvNum(p.mult, 2)}</span>` : ""), p.yearly[4], p.total)).join("") +
    (multi ? dvSumRow("Spolu", R.yearly[4], R.total, "sum") : "") + "</tbody></table></div></div>";
  if (multi) h += `<div class="card"><h2>Čo z toho vyplýva</h2>${dvFindings(R)}</div>`;
  h += `<div class="card"><h2>Krivka kapitálu <span class="hint">kumulatívny PnL podľa dní; žltá čiara = začiatok odloženého roka</span></h2><div id="dv-eq" class="dv-chart"></div></div>`;
  if (multi) h += `<div class="card"><h2>Spolu: kapitál a prepad</h2><div id="dv-dd" class="dv-chart sm"></div></div>`;
  // po rokoch
  h += `<div class="card"><h2>Po rokoch</h2><div class="table-wrap"><table class="dv-table"><thead><tr><th class="l">Rok</th><th class="l">Nastavenie</th><th>Obch.</th><th>WR</th><th>PF</th><th>Zisk</th><th>Max. DD</th><th>Priem. zisk</th><th>Priem. strata</th><th>Séria strát</th></tr></thead><tbody>`;
  const yRow = (y, name, r, cl = "") => `<tr class="${cl}"><td class="l">${y}</td><td class="l">${name}</td><td>${r.n}</td><td>${dvNum(r.wr, 1)} %</td><td class="${dvPfCls(r.pf)}">${dvPf(r.pf)}</td><td class="${dvCls(r.pnl)}">${dvMoney(r.pnl)}</td><td>${dvMoney(-r.dd)}</td><td>${dvMoney(r.avgWin)}</td><td>${dvMoney(r.avgLoss)}</td><td>${r.lossStreak}</td></tr>`;
  DV_YEARS.forEach((y, yi) => {
    P.forEach((p, k) => { h += yRow(k ? "" : y[0], dvSw(p.i) + esc(p.name), p.yearly[yi]); });
    if (multi) h += yRow("", "Spolu", R.yearly[yi], "sum");
  });
  h += `</tbody></table></div><p class="hint">Roky od októbra do septembra; 24/25 končí ${dvDate(DV_OOS)}, kde začína odložený rok. Max. DD je najväčší prepad v rámci roka v dolároch.</p></div>`;
  // mesiace
  const M = R.days.months, mx = Math.max(1, ...Object.values(M).map(Math.abs));
  h += `<div class="card"><h2>Mesiace${multi ? " spolu" : ""}</h2><div class="table-wrap"><table class="dv-table dv-months"><thead><tr><th class="l">Rok</th>${DV_MONTHS.map(m => `<th>${m}</th>`).join("")}<th>Rok spolu</th></tr></thead><tbody>`;
  for (let yr = +DV_FROM.slice(0, 4); yr <= +DV_TO.slice(0, 4); yr++) {
    let row = `<tr><th class="l">${yr}</th>`, tot = 0, any = false;
    for (let mo = 1; mo <= 12; mo++) {
      const v = M[`${yr}-${String(mo).padStart(2, "0")}`];
      if (v == null) { row += "<td></td>"; continue; }
      any = true; tot += v;
      const al = Math.round(14 + 56 * Math.min(1, Math.abs(v) / mx));
      row += `<td title="${DV_MONTHS[mo - 1]} ${yr}: ${dvMoney(v)}" style="background:color-mix(in srgb, var(${v >= 0 ? "--pos" : "--neg"}) ${al}%, var(--card));">${dvCompact(v)}</td>`;
    }
    if (any) h += row + `<td class="${dvCls(tot)}">${dvMoney(tot)}</td></tr>`;
  }
  h += `</tbody></table></div><p class="hint">Intenzita farby podľa veľkosti sumy.</p></div>`;
  h += dvDaysHtml(R, P) + dvWeekdayHtml(R, P) + dvTradeCardsHtml(P) + dvHoursHtml(R, P) + dvCorrHtml(R, P);
  h += dvAuditHtml(R);
  // denník
  // Denník je zbalený - bežne ho nikto nečíta, je to na dohľadanie konkrétneho obchodu či dňa.
  h += `<details class="card dv-log-box"><summary><h2>Denník <span class="hint">${R.all.length} obchodov, ${Object.keys(R.dayMap).length} dní — rozbaľ</span></h2></summary>
    <div class="dv-filters"><span class="mode-switch dv-seg" id="dv-view"><button type="button" data-v="tr">Obchody</button><button type="button" data-v="dy">Dni</button></span><label>Nastavenie <select id="dv-f-item"><option value="">všetky</option>${P.map(p => `<option value="${p.i}">${esc(p.name)}</option>`).join("")}</select></label>
      <label>Rok <select id="dv-f-year"><option value="">všetky</option>${DV_YEARS.map(y => `<option>${y[0]}</option>`).join("")}</select></label>
      <label>Výsledok <select id="dv-f-res"><option value="">všetky</option><option value="+">v zisku</option><option value="-">v strate</option></select></label></div>
    <div class="table-wrap"><table class="dv-table" id="dv-log"></table></div>
    <div class="dv-pager"><button type="button" class="ghost" id="dv-prev">‹ Späť</button><span id="dv-info" class="hint"></span><button type="button" class="ghost" id="dv-next">Ďalej ›</button></div></details>`;
  $("#dv-out").innerHTML = h;
  dvCharts();
  dvBindLog();
}

// Sekcie spoločné s kartou Naživo; fm = formát hodnoty (doláre, alebo R na karte Naživo), farba = p.c.
function dvDayCard(title, d, sw, fm = dvMoney) {
  return `<div class="card"><h2>${sw}${esc(title)}</h2><dl class="dv-kv">
      <dt>Obchodných dní</dt><dd>${d.days}</dd><dt>Dni v zisku</dt><dd>${dvNum(d.winPct, 1)} %</dd>
      <dt>Priemerný deň</dt><dd>${fm(d.avg)}</dd><dt>Medián dňa</dt><dd>${fm(d.median)}</dd>
      <dt>Priemerný ziskový / stratový deň</dt><dd>${fm(d.avgWin)} / ${fm(d.avgLoss)}</dd>
      <dt>Najviac stratových dní po sebe</dt><dd>${d.lossStreak}</dd><dt>Mesiace v zisku</dt><dd>${dvNum(d.monthsPos, 1)} %</dd>
      <dt>Najhorší mesiac</dt><dd>${d.worstMonth ? d.worstMonth[0] + " " + fm(d.worstMonth[1]) : "—"}</dd>
      <dt>Najlepší mesiac</dt><dd>${d.bestMonth ? d.bestMonth[0] + " " + fm(d.bestMonth[1]) : "—"}</dd>
      <dt>Najhorší deň</dt><dd>${d.worstDay ? dvDate(d.worstDay[0]) + " " + fm(d.worstDay[1]) : "—"}</dd>
      <dt>Najlepší deň</dt><dd>${d.bestDay ? dvDate(d.bestDay[0]) + " " + fm(d.bestDay[1]) : "—"}</dd></dl></div>`;
}
function dvDaysHtml(R, P, fm = dvMoney) {
  return `<h2 class="dv-section">Dni</h2><div class="dv-cards">${P.map(p => dvDayCard(p.name, p.days, dvSw(p.c), fm)).join("")}${P.length > 1 ? dvDayCard("Spolu", R.days, "", fm) : ""}</div>`;
}
function dvWeekdayHtml(R, P, fm = dvMoney) {
  const multi = P.length > 1;
  let h = `<div class="card"><h2>Dni v týždni</h2><div class="table-wrap"><table class="dv-table"><thead><tr><th class="l">Deň</th>` +
    P.map(p => `<th>${dvSw(p.c)}${esc(p.name)}</th><th>dni v zisku</th>`).join("") + (multi ? "<th>Spolu</th>" : "") + "</tr></thead><tbody>";
  for (const w of [0, 1, 2, 3, 4, 6]) {
    let tr = `<tr><td class="l">${DV_WD[w]}${w === 6 ? " (večer)" : ""}</td>`, any = false;
    for (const p of P) {
      const v = p.days.weekday[w];
      if (v && v.length) {
        any = true; const s2 = v.reduce((a, b) => a + b, 0);
        tr += `<td class="${dvCls(s2)}">${fm(s2)}</td><td>${dvNum(100 * v.filter(x => x > 0).length / v.length, 1)} %</td>`;
      } else tr += `<td class="hint">—</td><td class="hint">—</td>`;
    }
    if (multi) { const cv = R.days.weekday[w] || [], cs = cv.reduce((a, b) => a + b, 0); tr += `<td class="${dvCls(cs)}">${cv.length ? fm(cs) : "—"}</td>`; }
    if (any) h += tr + "</tr>";
  }
  return h + "</tbody></table></div></div>";
}
function dvTradeCardsHtml(P, fm = dvMoney) {
  return `<h2 class="dv-section">Obchody</h2><div class="dv-cards">` + P.map(p => {
    const t = p.total;
    return `<div class="card"><h2>${dvSw(p.c)}${esc(p.name)}</h2><dl class="dv-kv">
      <dt>Obchodov</dt><dd>${t.n}</dd><dt>Priemerný obchod</dt><dd>${fm(t.avg, 1)}</dd><dt>Priemerný zisk / strata</dt><dd>${fm(t.avgWin)} / ${fm(t.avgLoss)}</dd>
      <dt>Najviac výhier / strát po sebe</dt><dd>${t.winStreak} / ${t.lossStreak}</dd>` +
      p.reasons.map(r => `<dt>${r[0] === "take_profit" ? "Take profit" : "Stop loss"}</dt><dd>${r[1]} · ${fm(r[2])}</dd>`).join("") +
      p.dirs.filter(d => d[1].n).map(d => `<dt>${d[0] === "long" ? "Long" : "Short"} (${d[1].n}), PF</dt><dd>${dvPf(d[1].pf)} · ${fm(d[1].pnl)}</dd>`).join("") +
      `<dt>Najlepší / najhorší obchod</dt><dd>${fm(t.best)} / ${fm(t.worst)}</dd></dl></div>`;
  }).join("") + "</div>";
}
function dvHoursHtml(R, P, fm = dvMoney) {
  const hrs = Object.keys(R.hours).map(Number).sort((a, b) => a - b);
  return `<div class="card"><h2>Hodina vstupu (New York)</h2><div class="table-wrap"><table class="dv-table"><thead><tr><th class="l">Hodina</th>` +
    P.map(p => `<th>${dvSw(p.c)}${esc(p.name)}</th><th>PF</th><th>zisk</th>`).join("") + "</tr></thead><tbody>" +
    hrs.map(hh => `<tr><td class="l">${String(hh).padStart(2, "0")}:00</td>` + P.map(p => {
      const v = R.hours[hh][p.i];
      if (!v) return `<td class="hint">—</td><td class="hint">—</td><td class="hint">—</td>`;
      const s3 = dvStats(v);
      return `<td>${s3.n}</td><td class="${dvPfCls(s3.pf)}">${dvPf(s3.pf)}</td><td class="${dvCls(s3.pnl)}">${fm(s3.pnl)}</td>`;
    }).join("") + "</tr>").join("") +
    `</tbody></table></div><p class="hint">Riadok je len pre hodinu, v ktorej obchoduje aspoň jedno nastavenie.</p></div>`;
}
function dvCorrHtml(R, P, note = "") {
  if (!R.corr.length) return "";
  return `<div class="card"><h2>Korelácia denných výsledkov</h2><div class="table-wrap"><table class="dv-table"><thead><tr><th class="l">Dvojica</th><th>Spoločných dní</th><th>Korelácia</th><th>Dni, keď obe prerobili</th></tr></thead><tbody>` +
    R.corr.map(c => `<tr><td class="l">${dvSw(P[c.a].c)}${esc(P[c.a].name)} × ${dvSw(P[c.b].c)}${esc(P[c.b].name)}</td><td>${c.common}</td><td class="${c.r != null && c.r >= 0.5 ? "neg" : ""}">${c.r == null ? "—" : dvNum(c.r, 2)}</td><td>${c.both}</td></tr>`).join("") +
    `</tbody></table></div><p class="hint">Korelácia blízko 0 = nastavenia sa navzájom nehýbu (dobrá diverzifikácia), blízko 1 = správajú sa ako jedna väčšia pozícia.${note ? " " + note : ""}</p></div>`;
}

function dvCharts() {
  const R = dv.result;
  if (!R || !$("#dv-eq") || typeof Plotly === "undefined") return;
  const P = R.parts, multi = P.length > 1;
  const oos = { type: "line", xref: "x", yref: "paper", x0: DV_OOS, x1: DV_OOS, y0: 0, y1: 1, line: { color: "#f5a524", width: 1.5, dash: "dot" } };
  const layout = extra => ({
    margin: { l: 10, r: 60, t: 10, b: 30 }, template: plotlyTemplate(), hovermode: "x unified",
    legend: { orientation: "h", yanchor: "bottom", y: 1.0, x: 0 }, shapes: [oos],
    yaxis: { side: "right", ticksuffix: " $", zeroline: true }, xaxis: { showgrid: false },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", ...extra,
  });
  const cfg = { displaylogo: false, responsive: true };
  const traces = P.map(p => ({ type: "scatter", mode: "lines", name: p.name, x: p.equity.map(e => e[0]), y: p.equity.map(e => e[1]),
                               line: { color: dvColor(p.i), width: 1.8, shape: "hv" }, hovertemplate: "%{y:,.0f} $" }));
  if (multi) traces.push({ type: "scatter", mode: "lines", name: "Spolu", x: R.equity.map(e => e[0]), y: R.equity.map(e => e[1]),
                           line: { color: isDarkTheme() ? "#e6edf0" : "#142c36", width: 2.6, shape: "hv" }, hovertemplate: "%{y:,.0f} $" });
  Plotly.newPlot("dv-eq", traces, layout({ height: 420 }), cfg);
  if (multi && $("#dv-dd")) {
    let peak = 0;
    const x = R.equity.map(e => e[0]), eq = R.equity.map(e => e[1]), dd = eq.map(v => { peak = Math.max(peak, v); return v - peak; });
    Plotly.newPlot("dv-dd", [
      { type: "scatter", mode: "lines", name: "kapitál", x, y: eq, line: { color: GREEN, width: 2 }, hovertemplate: "%{y:,.0f} $" },
      { type: "scatter", mode: "lines", name: "prepad", x, y: dd, line: { color: RED, width: 1 }, fill: "tozeroy", fillcolor: "rgba(242,54,69,0.15)", hovertemplate: "%{y:,.0f} $" },
    ], layout({ height: 260 }), cfg);
  }
}

function dvLogRows() {
  const L = dv.log, R = dv.result;
  let rows;
  if (L.view === "tr") {
    rows = R.all.filter(t => (L.item === "" || t.i === +L.item) && (!L.year || dvYear(t.open.slice(0, 10)) === L.year)
                             && (!L.res || (L.res === "+" ? t.pnl > 0 : t.pnl <= 0))).map(t => ({ k: t.open, t }));
  } else {
    rows = Object.keys(R.dayMap).filter(d => (!L.year || dvYear(d) === L.year) && (L.item === "" || d in R.parts[+L.item].daily))
      .map(d => ({ k: d, d, v: L.item === "" ? R.dayMap[d] : R.parts[+L.item].daily[d] }))
      .filter(x => !L.res || (L.res === "+" ? x.v > 0 : x.v <= 0));
  }
  const key = L.sort || "k", val = r => (key === "k" ? r.k : (r.t ? r.t.pnl : r.v));
  rows.sort((a, b) => (val(a) < val(b) ? -1 : val(a) > val(b) ? 1 : 0) * L.dir);
  return rows;
}

function dvRenderLog() {
  const L = dv.log, R = dv.result, P = R.parts, rows = dvLogRows(), n = 50, pages = Math.max(1, Math.ceil(rows.length / n));
  L.page = Math.min(L.page, pages - 1);
  const part = rows.slice(L.page * n, L.page * n + n);
  const reason = r => (r === "take_profit" ? "take profit" : r === "stop_loss" ? "stop loss" : esc(r));
  let h;
  if (L.view === "tr") {
    h = `<thead><tr><th class="l sort" data-k="k">Otvorenie (NY)</th><th class="l">Zatvorenie (NY)</th><th class="l">Nastavenie</th><th class="l">Smer</th><th>Vstup</th><th>Výstup</th><th class="l">Dôvod</th><th class="sort" data-k="v">PnL</th></tr></thead><tbody>` +
      part.map(({ t }) => `<tr><td class="l">${dvDateTime(t.open)}</td><td class="l">${dvDateTime(t.close)}</td><td class="l">${dvSw(t.i)}${esc(P[t.i].name)}</td>
        <td class="l">${t.dir}</td><td>${dvNum(t.entry, 2)}</td><td>${dvNum(t.exit, 2)}</td><td class="l">${reason(t.reason)}</td><td class="${dvCls(t.pnl)}">${dvMoney(t.pnl, 2)}</td></tr>`).join("");
  } else {
    h = `<thead><tr><th class="l sort" data-k="k">Deň</th>${P.map(p => `<th>${dvSw(p.i)}${esc(p.name)}</th>`).join("")}${P.length > 1 ? `<th class="sort" data-k="v">Spolu</th>` : ""}</tr></thead><tbody>` +
      part.map(r => `<tr><td class="l">${dvDate(r.d)}</td>` + P.map(p => { const v = p.daily[r.d]; return v == null ? `<td class="hint">—</td>` : `<td class="${dvCls(v)}">${dvMoney(v)}</td>`; }).join("") +
        (P.length > 1 ? `<td class="${dvCls(R.dayMap[r.d])}">${dvMoney(R.dayMap[r.d])}</td>` : "") + "</tr>").join("");
  }
  $("#dv-log").innerHTML = h + "</tbody>";
  const tot = rows.reduce((s, r) => s + (r.t ? r.t.pnl : r.v), 0);
  $("#dv-info").textContent = `${rows.length} ${L.view === "tr" ? "obchodov" : "dní"} · spolu ${dvMoney(tot)} · strana ${L.page + 1} z ${pages}`;
  $("#dv-prev").disabled = L.page === 0; $("#dv-next").disabled = L.page >= pages - 1;
  for (const b of $$("#dv-view button")) b.classList.toggle("active", b.dataset.v === L.view);
  for (const th of $$("#dv-log th.sort")) th.onclick = () => {
    const k = th.dataset.k; L.dir = L.sort === k ? -L.dir : (k === "v" ? 1 : -1); L.sort = k; L.page = 0; dvRenderLog();
  };
}

function dvBindLog() {
  const L = dv.log;
  for (const b of $$("#dv-view button")) b.onclick = () => { L.view = b.dataset.v; L.sort = null; L.dir = 1; L.page = 0; dvRenderLog(); };
  for (const [id, k] of [["#dv-f-item", "item"], ["#dv-f-year", "year"], ["#dv-f-res", "res"]]) $(id).onchange = e => { L[k] = e.target.value; L.page = 0; dvRenderLog(); };
  $("#dv-prev").onclick = () => { L.page--; dvRenderLog(); };
  $("#dv-next").onclick = () => { L.page++; dvRenderLog(); };
  dvRenderLog();
}
