/* TradeBot Backtester — Live diverzifikácia (karta „Naživo“ v kóde): ako sa darí stratégiám nasadeným naživo (Diverzifikácia nad obchodmi u brokera). */
"use strict";

// --------------------------------------------------------------------------- //
// Naživo: tie isté rozbory ako Diverzifikácia, len z obchodov naživo
// --------------------------------------------------------------------------- //
//
// Obchody, otvorené pozície, signály a varovania sú z /api/diversify/live (sekcia `live` stránky
// výsledkov zo zrkadla webapp). Spoločný výpočet a sekcie sú z diversify.js (dvComputeParts, dvDaysHtml…).
// Navyše: pásmo naživo vs. test (Monte Carlo z obchodov behov toho istého profilu v histórii,
// v bodoch indexu) a kvalita plnenia (sklz proti plánu enginu, oneskorenie Market príkazu).

const NZ_KEY = "tradebot.livediv";
const NZ_PLAT = { ninjatrader: "NinjaTrader", mt5: "MT5" };
const nz = {
  data: null, off: {}, open: new Set(), unit: "$", band: "", bt: {}, R: null, loaded: false,
  log: { view: "tr", inst: "", page: 0 },
};

function nzPrefs() {
  if (nz.loaded) return;
  nz.loaded = true;
  try { const s = JSON.parse(localStorage.getItem(NZ_KEY) || "null"); if (s) { nz.off = s.off || {}; nz.open = new Set(s.open || []); nz.unit = s.unit === "R" ? "R" : "$"; } } catch (_) { /* súkromné okno */ }
}
// účty vo výbere sú predvolene zbalené; rozbalené si pamätá prehliadač, nový účet tak príde zbalený
function nzSave() { try { localStorage.setItem(NZ_KEY, JSON.stringify({ off: nz.off, open: [...nz.open], unit: nz.unit })); } catch (_) { /* nezapamätá sa */ } }

/** Aktívne inštancie (nie staré); `_c` = stála farba, aby sa pri výbere nemenila. */
function nzActive() {
  const a = ((nz.data && nz.data.instances) || []).filter(x => !x.stale);
  a.forEach((x, i) => { x._c = i; });
  return a;
}
function nzList() { return nzActive().filter(x => !nz.off[x.id]); }
function nzPlat(x) { return `${NZ_PLAT[x.platform] || x.platform} · ${x.symbol}`; }
function nzName(x) { return `${x.name} · ${NZ_PLAT[x.platform] || x.platform}`; }
function nzTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d) ? esc(iso) : `${d.getDate()}. ${d.getMonth() + 1}. ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
function nzDayKey(iso) { const d = new Date(iso); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; }

// R obchodu: z telemetrie, inak body / vzdialenosť stopu
function nzR(t) {
  if (t.r != null) return +t.r;
  const sd = t.sd || (t.sl != null && t.entry != null ? Math.abs(t.entry - t.sl) : 0);
  return sd && t.pts != null ? t.pts / sd : null;
}
function nzV(t) { return nz.unit === "R" ? (nzR(t) || 0) : (+t.pnl || 0); }
function nzFmtR(v, d = 2) { return v == null || !isFinite(v) ? "—" : (v < 0 ? "−" : v > 0 ? "+" : "") + dvNum(Math.abs(v), d) + " R"; }
function nzFm() { return nz.unit === "R" ? nzFmtR : dvMoney; }
function nzPts(v) { return v == null || !isFinite(v) ? "—" : (v < 0 ? "−" : v > 0 ? "+" : "") + dvNum(Math.abs(v), 1) + " b"; }
function nzAvg(a) { return a.length ? a.reduce((s, v) => s + v, 0) / a.length : null; }
function nzMedian(a) { if (!a.length) return null; const s = a.slice().sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }
function nzSecs(v) { return v == null ? "—" : v < 60 ? dvNum(v, 1) + " s" : dvNum(v / 60, 1) + " min"; }

// ------------------------------------------------- párovanie s históriou --- //

/** Spoločné meno profilu naprieč C# portom, Python predlohou, súbormi rannej kontroly a variantmi
 *  živého účtu: `vwaporb_PRESIEL_SMERNICAMI_VWAP_ORB_1_2026-10-11.json`, `PRESIEL_SMERNICAMI_VWAP_ORB_CS_1_SL500`
 *  → `VWAP_ORB_1`. */
function nzNorm(p) {
  let s = String(p || "").replace(/\\/g, "/").split("/").pop().replace(/\.json$/i, "");
  s = s.replace(/^[a-z0-9]+_(?=[A-Z])/, "").replace(/_\d{4}-\d{2}-\d{2}$/, "").toUpperCase();
  s = s.replace(/_SL\d+$/, "").replace(/^PRESIEL_SMERNICAMI_|^SMERNICE_/, "").replace(/(^|_)CS(?=_|$)/g, "$1");
  return s.replace(/_+/g, "_").replace(/^_|_$/g, "");
}
function nzStem(p) { return String(p || "").replace(/\\/g, "/").split("/").pop().replace(/\.json$/i, ""); }

/** Beh v histórii k živej inštancii: nastavenie s tým istým profilom (C# port alebo Python predloha, aj súbor
 *  rannej kontroly), trh radšej MNQ a ten istý TF. Presne ten istý súbor profilu má prednosť, len keď má aspoň
 *  150 obchodov — inak vyhrá kandidát s najviac obchodmi (jeden krátky beh je na pásmo málo). */
async function nzMatch(x) {
  const known = new Set((state.meta.strategies || []).map(s => s.key));
  const keys = [...new Set([x.engine, x.strategy])].filter(k => k && known.has(k));
  const want = nzNorm(x.profile), stem = nzStem(x.profile).replace(/_SL\d+$/i, "");
  const score = m => (String(m.pair).startsWith("MNQ") ? 2 : 0) + (m.timeframe === `${x.tf}m` ? 1 : 0);
  const cands = [];
  for (const key of keys) {
    const cfg = await dvConfigs(key).catch(() => []);
    for (const n of cfg) {
      if (!n.markets.length || nzNorm(n.profile) !== want) continue;
      const m = n.markets.slice().sort((a, b) => score(b) - score(a) || b.trades - a.trades)[0];
      cands.push({ key, n, m, exact: nzStem(n.profile) === stem && m.trades >= 150 });
    }
  }
  if (!cands.length) return null;
  cands.sort((a, b) => (b.exact - a.exact) || (score(b.m) - score(a.m)) || (b.m.trades - a.m.trades));
  const { key, n, m } = cands[0], meta = (state.meta.strategies || []).find(s => s.key === key);
  return { strategy: key, setting: n, market: m, title: dvSettingName(meta ? meta.title : key, n), profile: nzStem(n.profile) };
}

async function nzBacktests(list) {
  await Promise.all(list.map(async x => {
    if (nz.bt[x.id]) return;
    const match = await nzMatch(x).catch(() => null);
    if (!match) { nz.bt[x.id] = { none: true }; return; }
    const key = match.market.run_ids.join(",");
    if (!dv.trades[key]) dv.trades[key] = await api(`/api/diversify/trades?runs=${encodeURIComponent(key)}`);
    nz.bt[x.id] = { match, trades: dv.trades[key].trades };
  }));
}

// ---------------------------------------- naživo vs. test: pásmo (body) --- //
// Body, nie doláre: MNQ aj US100.cash idú po tom istom indexe, takže body z behu na MNQ sa dajú porovnať
// s bodmi na oboch platformách bez ohľadu na veľkosť kontraktu. Z obchodov testu sa 2000-krát (pevné
// semienko) vytiahne toľko obchodov, koľko je naživo.

const nzBandCache = {};
function nzRng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function nzHash(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h; }
function nzMaxDd(arr) { let eq = 0, pk = 0, dd = 0; for (const v of arr) { eq += v; pk = Math.max(pk, eq); dd = Math.max(dd, pk - eq); } return dd; }

function nzBand(x) {
  const bt = nz.bt[x.id];
  if (!bt || bt.none) return null;
  const live = (x.trades || []).filter(t => t.pts != null).sort((a, b) => (a.close < b.close ? -1 : 1)).map(t => +t.pts);
  const key = `${x.id}:${live.length}`;
  if (nzBandCache[key]) return nzBandCache[key];
  const all = bt.trades.filter(t => t[3] != null && t[4] != null);
  const last = all.filter(t => t[0].slice(0, 10) >= DV_OOS);
  const src = last.length >= 40 ? last : all;
  const pts = src.map(t => (t[4] - t[3]) * (t[2] === "S" ? -1 : 1));
  const st = dvStats(src.map(t => t[5]));
  const span = src.length > 1 ? Math.max(7, (Date.parse(src[src.length - 1][1]) - Date.parse(src[0][0])) / 864e5) : null;
  const n = live.length, K = Math.max(n, 20), S = 2000, rnd = nzRng(nzHash(x.id));
  const res = { n, src: last.length >= 40 ? "posledný rok" : "celý test", btN: pts.length, wr: st.wr, pf: st.pf,
                perWeek: span ? src.length / (span / 7) : null, sum: live.reduce((a, v) => a + v, 0),
                dd: nzMaxDd(live), btDd: nzMaxDd(pts), live, steps: [] };
  if (pts.length < 20) { res.noData = true; return (nzBandCache[key] = res); }
  const cols = Array.from({ length: K + 1 }, () => new Float64Array(S));
  let below = 0, ties = 0, ddWorse = 0;
  for (let s = 0; s < S; s++) {
    let c = 0, pk = 0, dd = 0;
    for (let k = 1; k <= K; k++) {
      c += pts[Math.floor(rnd() * pts.length)];
      cols[k][s] = c;
      if (k <= n) { pk = Math.max(pk, c); dd = Math.max(dd, pk - c); }
    }
    if (n) { const v = cols[n][s]; if (v < res.sum) below++; else if (v === res.sum) ties++; if (dd >= res.dd) ddWorse++; }
  }
  const q = (a, p) => a[Math.min(a.length - 1, Math.floor(p * a.length))];
  for (let k = 0; k <= K; k++) { const a = Array.from(cols[k]).sort((x1, x2) => x1 - x2); res.steps.push([q(a, 0.05), q(a, 0.5), q(a, 0.95)]); }
  if (n) Object.assign(res, { pct: 100 * (below + ties / 2) / S, ddWorse: 100 * ddWorse / S, lo: res.steps[n][0], mid: res.steps[n][1], hi: res.steps[n][2] });
  return (nzBandCache[key] = res);
}
function nzVerdict(b) {
  if (!b || b.noData) return ["", "bez testu"];
  if (b.n < 5) return ["", "málo obchodov"];
  if (b.pct < 5) return ["bad", "pod pásmom"];
  if (b.pct < 20) return ["warn", "spodok pásma"];
  if (b.pct > 95) return ["ok", "nad pásmom"];
  return ["ok", "v pásme"];
}

// --------------------------------------------------- kvalita plnenia --- //
// Sklz = o koľko horšia cena ako plán enginu (kladný = horšie): vstup proti plánovanej cene príkazu,
// výstup na stope proti SL, na take profite proti TP. Oneskorenie len pri Market príkaze (limitka čaká zámerne).
function nzFill(x) {
  const pv = +x.point_value || 1, out = { n: 0, ent: [], stop: [], tp: [], usd: 0, r: 0, lat: [], types: new Set() };
  for (const t of x.trades || []) {
    if (t.plan == null || t.entry == null) continue;
    const g = t.dir === "short" ? -1 : 1, q = +t.qty || 0, sd = t.sd || (t.sl != null ? Math.abs(t.entry - t.sl) : 0);
    const es = (t.entry - t.plan) * g;
    let xs = 0;
    if (t.reason === "stop_loss" && t.sl != null && t.exit != null) { xs = (t.sl - t.exit) * g; out.stop.push(xs); }
    else if (t.reason === "take_profit" && t.tp != null && t.exit != null) { xs = (t.tp - t.exit) * g; out.tp.push(xs); }
    out.n++; out.ent.push(es);
    out.usd += (es + xs) * q * pv;
    if (sd) out.r += (es + xs) / sd;
    if (t.order_type) out.types.add(t.order_type);
    const a = Date.parse(t.sent), b = Date.parse(t.open);
    if (isFinite(a) && isFinite(b) && /market/i.test(t.order_type || "")) out.lat.push(Math.max(0, (b - a) / 1000));
  }
  return out;
}

// --------------------------------------------------------- výpočet --- //

/** Inštancie ako časti pre dvComputeParts — pnl v zvolenej jednotke, deň = miestny deň zatvorenia. */
function nzCompute(list) {
  const parts = list.filter(x => (x.trades || []).length).map((x, k) => {
    const trades = x.trades.map(t => ({ i: k, open: t.open, close: t.close, dir: t.dir, entry: t.entry, exit: t.exit, reason: t.reason, pnl: nzV(t) }))
      .sort((a, b) => (a.open < b.open ? -1 : a.open > b.open ? 1 : 0));
    const daily = {};
    for (const t of trades) { const d = nzDayKey(t.close); daily[d] = (daily[d] || 0) + t.pnl; }
    return { i: k, c: x._c, x, mult: 1, trades, daily, name: nzName(x) };
  });
  return parts.length ? dvComputeParts(parts) : null;
}

function nzFindings(list, R) {
  const out = [], who = x => `${esc(x.name)} na ${esc(nzPlat(x))}`;
  for (const x of list) {
    const miss = (x.signals || []).filter(s => s.result === "bez vyplnenia");
    if (miss.length) out.push(["bad", `${who(x)}: ${miss.length} ${miss.length === 1 ? "signál ostal" : "signály ostali"} bez vyplnenia u brokera (posledný ${nzTime(miss[miss.length - 1].t)}). Skontroluj terminál a log platformy.`]);
    if (x.orphan_fills) out.push(["warn", `${who(x)}: ${x.orphan_fills} výstup(y) bez zaznamenaného vstupu — obchod mohol začať pred zapnutím telemetrie.`]);
    if (x.status !== "beží") out.push([x.status === "zastavená" ? "bad" : "warn", `${who(x)} ${x.status === "zastavená" ? "je zastavená" : "neposlala nič od " + nzTime(x.last_event)}.`]);
    const b = nzBand(x), v = nzVerdict(b);
    if (b && !b.noData && b.n >= 5 && (v[0] === "bad" || v[0] === "warn"))
      out.push([v[0], `${who(x)}: ${b.n} obchodov naživo ${nzPts(b.sum)}, test pri rovnakom počte čaká ${nzPts(b.lo)} až ${nzPts(b.hi)} (medián ${nzPts(b.mid)}) — horšie dopadlo len ${dvNum(b.pct)} % náhodných výberov z testu.` +
        (v[0] === "bad" ? " Over, či beží rovnako ako v teste (profil, dáta, plnenia)." : "")]);
    if (b && !b.noData && b.n >= 3 && b.btDd && b.dd > b.btDd) out.push(["bad", `${who(x)}: prepad naživo ${nzPts(-b.dd)} je väčší ako najhorší prepad v teste (${nzPts(-b.btDd)}).`]);
    const F = nzFill(x), ea = nzAvg(F.ent), sd = nzAvg((x.trades || []).map(t => t.sd || 0).filter(Boolean));
    if (F.n >= 3 && ea != null && sd && ea / sd > 0.05) out.push(["warn", `${who(x)}: priemerný sklz vstupu ${nzPts(ea)} (${nzFmtR(ea / sd)} na obchod), plnenia spolu ${dvMoney(-F.usd)} oproti plánu.`]);
    const lm = nzMedian(F.lat);
    if (lm != null && lm > 5) out.push(["warn", `${who(x)}: od odoslania Market príkazu po vyplnenie prejde v mediáne ${nzSecs(lm)}.`]);
  }
  const ok = list.filter(x => { const b = nzBand(x); return b && !b.noData && b.n >= 5 && nzVerdict(b)[0] === "ok"; });
  if (ok.length) out.push(["ok", "V pásme testu alebo nad ním (pri rovnakom počte obchodov): " + ok.map(x => `${esc(nzName(x))} ${dvNum(nzBand(x).pct)}. percentil`).join(", ") + "."]);
  // tá istá stratégia (profil) na dvoch platformách: dáva tie isté signály, odkedy bežia obe?
  const byProfile = {};
  for (const x of list) (byProfile[`${x.strategy}:${nzNorm(x.profile)}`] = byProfile[`${x.strategy}:${nzNorm(x.profile)}`] || []).push(x);
  for (const g of Object.values(byProfile)) {
    if (g.length < 2) continue;
    const from = g.reduce((m, x) => (x.since > m ? x.since : m), "");
    const keyOf = s => s.t.slice(0, 16) + s.dir;
    const sets = g.map(x => new Set((x.signals || []).filter(s => s.t >= from).map(keyOf)));
    const all = new Set(sets.flatMap(m => [...m]));
    const both = [...all].filter(q => sets.every(m => m.has(q))).length;
    if (all.size) out.push([both === all.size ? "ok" : "warn", `${esc(g[0].name)}: ${g.map(nzPlat).join(" a ")} — ${both} z ${all.size} signálov od ${nzTime(from)} (odkedy bežia obe) majú obe platformy v tej istej sviečke` +
      (both === all.size ? "." : " (rozdiel môže byť v dátach brokera: CFD vs. futures, iné sviečky).")]);
  }
  if (R && R.parts.length > 1) {
    const P = R.parts, fm = nzFm(), rs = R.corr.filter(c => c.r != null);
    if (!rs.length) out.push(["", `Korelácia denných výsledkov sa počíta od 11 spoločných obchodných dní dvojice; zatiaľ ich má najviac ${Math.max(0, ...R.corr.map(c => c.common))}.`]);
    else {
      const hi = rs.filter(c => c.r >= 0.5);
      out.push(hi.length ? ["warn", "Niektoré stratégie sa naživo hýbu spolu (korelácia ≥ 0,5): " + hi.map(c => `${esc(P[c.a].name)} × ${esc(P[c.b].name)} ${dvNum(c.r, 2)}`).join(", ") + ". Ich súčet sa správa skôr ako väčšia pozícia."]
        : ["ok", `Korelácia denných výsledkov naživo je nízka (najviac ${dvNum(Math.max(...rs.map(c => c.r)), 2)}), stratégie sa navzájom vyrovnávajú.`]);
    }
    const sumDd = P.reduce((s, p) => s + p.total.dd, 0);
    if (sumDd > 0) out.push(["", `Prepad spolu ${fm(-R.total.dd)} oproti súčtu samostatných prepadov ${fm(-sumDd)} — ${R.total.dd < sumDd ? "prepady neprišli naraz." : "prepady prišli naraz."}`]);
    out.push(["", `Najhorší deň spolu ${R.days.worstDay ? dvDate(R.days.worstDay[0]) + " " + fm(R.days.worstDay[1]) : "—"}, najviac stratových dní po sebe ${R.days.lossStreak}, naraz v trhu najviac ${R.maxConcurrent} pozície.`]);
  }
  const n = list.reduce((s, x) => s + (x.trades || []).length, 0);
  if (n < 20) out.push(["", `Uzavretých obchodov je zatiaľ ${n}. WR a PF sú pri tak málo obchodoch náhodné; pásmo testu malý počet zohľadňuje — sleduj hlavne to a či signály a vyplnenia sedia.`]);
  const tag = { ok: "v poriadku", warn: "pozor", bad: "pozor", "": "dobré vedieť" };
  return `<ul class="dv-find">${out.map(x => `<li><span class="chip ${x[0]}">${tag[x[0]]}</span><span>${x[1]}</span></li>`).join("")}</ul>`;
}

// ------------------------------------------------------------ výstup --- //

function nzStatus(x) {
  const c = x.status === "beží" ? "ok" : x.status === "zastavená" ? "bad" : "warn";
  return `<span class="chip ${c}">${esc(x.status)}</span>`;
}

/** Inštancie po účtoch (platforma + účet, ako tabuľka Nasadenia na karte Live), v poradí prvej inštancie. */
function nzGroups(all) {
  const g = new Map();
  for (const x of all) {
    const k = `${x.platform || ""}|${x.account || ""}`;
    if (!g.has(k)) g.set(k, []);
    g.get(k).push(x);
  }
  return [...g];
}

function nzPickHtml(all) {
  return `<div class="dv-head"><h2>Ktoré stratégie <span class="hint">výber platí pre celú kartu</span></h2>
      <span class="mode-switch dv-seg" id="nz-unit"><button type="button" data-u="$"${nz.unit === "$" ? ' class="active"' : ""}>$</button><button type="button" data-u="R"${nz.unit === "R" ? ' class="active"' : ""}>R</button></span></div>
    ${nzGroups(all).map(([key, xs]) => {
      const on = xs.filter(x => !nz.off[x.id]).length, x0 = xs[0], label = typeof liveAccountLabel === "function" ? liveAccountLabel(x0) : "";
      const open = nz.open.has(key);
      return `<div class="nz-acct"><div class="nz-acct-head"><input type="checkbox" data-nz-acct="${esc(key)}" title="všetky stratégie účtu"${on === xs.length ? " checked" : ""}${on && on < xs.length ? " data-mixed" : ""}>
          <span class="nz-acct-tog" data-nz-tog="${esc(key)}" title="${open ? "zbaliť" : "rozbaliť"}"><span class="live-caret">${open ? "▾" : "▸"}</span><b>${esc(label || x0.account || "—")}</b>
          <small>${esc(NZ_PLAT[x0.platform] || x0.platform)}${label ? " · " + esc(x0.account) : ""} · ${on} / ${xs.length}</small></span></div>
        ${open ? `<div class="nz-pick">${xs.map(x => `<label class="nz-chip"><input type="checkbox" data-nz-inst="${esc(x.id)}"${nz.off[x.id] ? "" : " checked"}>${dvSw(x._c)}${esc(x.name)} <small>${esc(nzPlat(x))}</small></label>`).join("")}</div>` : ""}</div>`;
    }).join("")}
    <p class="hint">$ = skutočný zisk u brokera, hrubý bez poplatkov (MT5 CFD má inú veľkosť kontraktu ako MNQ); R = zisk vo veľkostiach stopu — porovnateľné medzi stratégiami aj platformami.</p>`;
}

function nzSummaryHtml(list, R) {
  const fm = nzFm();
  const row = (x, p) => {
    const t = x.trades || [], st = dvStats(t.map(nzV)), rs = t.reduce((s, o) => s + (nzR(o) || 0), 0), xs = x.signals || [];
    const weeks = Math.max((Date.parse(nz.data.generated) - Date.parse(x.since)) / 6048e5, 1 / 7);
    return `<tr><td class="l nz-wrap">${dvSw(x._c)}${esc(x.name)}<br><small class="hint">${esc(x.profile)}</small></td>
      <td class="l">${esc(nzPlat(x))}<br><small class="hint">${esc(x.account)}</small></td><td class="l">${nzStatus(x)}<br><small class="hint">od ${dvDate(nzDayKey(x.since))}</small></td>
      <td>${st.n}${(x.open || []).length ? ` <small class="hint">+${x.open.length} otv.</small>` : ""}</td><td>${st.n ? dvNum(st.wr) + " %" : "—"}</td>
      <td class="${dvPfCls(st.pf)}">${st.n ? dvPf(st.pf) : "—"}</td><td class="${dvCls(st.pnl)}">${fm(st.pnl)}</td><td class="${dvCls(rs)}">${st.n ? nzFmtR(rs) : "—"}</td>
      <td>${st.n ? fm(-st.dd) : "—"}</td><td>${dvNum(st.n / weeks, 1)}</td><td>${xs.filter(s => s.result === "vyplnený").length} / ${xs.length}</td></tr>`;
  };
  let sum = "";
  if (R && R.parts.length > 1) {
    const all = list.flatMap(x => x.trades || []), rs = all.reduce((s, o) => s + (nzR(o) || 0), 0), sig = list.flatMap(x => x.signals || []);
    sum = `<tr class="sum"><td class="l">Spolu</td><td></td><td></td><td>${R.total.n}</td><td>${dvNum(R.total.wr)} %</td><td class="${dvPfCls(R.total.pf)}">${dvPf(R.total.pf)}</td>
      <td class="${dvCls(R.total.pnl)}">${fm(R.total.pnl)}</td><td class="${dvCls(rs)}">${nzFmtR(rs)}</td><td>${fm(-R.dayStats.dd)}</td><td></td><td>${sig.filter(s => s.result === "vyplnený").length} / ${sig.length}</td></tr>`;
  }
  return `<div class="card"><h2>Súhrn <span class="hint">stav k ${nzTime(nz.data.generated)}</span></h2><div class="table-wrap"><table class="dv-table"><thead><tr>
      <th class="l">Stratégia</th><th class="l">Platforma</th><th class="l">Stav</th><th>Obch.</th><th>WR</th><th>PF</th><th>Zisk</th><th>R</th><th>Max. DD</th><th>Obch./týž.</th><th>Signály vypl.</th></tr></thead>
      <tbody>${list.map(x => row(x)).join("")}${sum}</tbody></table></div>
      <p class="hint">Max. DD spolu je z denných súčtov (ako v Diverzifikácii). Otvorené pozície sú v denníku nižšie.</p></div>`;
}

function nzVsTestHtml(list) {
  const rows = list.map(x => {
    const bt = nz.bt[x.id], name = `${dvSw(x._c)}${esc(x.name)} <small class="hint">${esc(nzPlat(x))}</small>`;
    if (!bt) return `<tr><td class="l">${name}</td><td class="l hint" colspan="9">načítavam beh z histórie…</td></tr>`;
    if (bt.none) return `<tr><td class="l">${name}</td><td class="l hint" colspan="9">v histórii nie je beh profilu ${esc(x.profile)} — nie je s čím porovnať</td></tr>`;
    const b = nzBand(x), v = nzVerdict(b), st = dvStats((x.trades || []).map(t => +t.pnl || 0));
    const weeks = Math.max((Date.parse(nz.data.generated) - Date.parse(x.since)) / 6048e5, 1 / 7);
    const same = nzStem(x.profile) === bt.match.profile;
    return `<tr><td class="l nz-wrap">${name}</td>
      <td class="l nz-wrap" title="profil v histórii: ${esc(bt.match.profile)}${same ? "" : `\nprofil naživo: ${esc(x.profile)}`}">${esc(String(bt.match.title).split(" · ")[0])}${same ? "" : ` <span class="hint">≈</span>`}<br><small class="hint">${esc(pairShort(bt.match.market.pair))} ${esc(bt.match.market.timeframe)} · ${b ? b.src + ", " + b.btN + " obch." : ""}</small></td>
      <td>${st.n ? dvNum(st.wr) : "—"} / ${dvNum(b && b.wr)} %</td><td>${st.n ? dvPf(st.pf) : "—"} / ${dvPf(b && b.pf)}</td><td>${dvNum(st.n / weeks, 1)} / ${dvNum(b && b.perWeek, 1)}</td>
      <td class="${dvCls(b && b.sum)}">${b && b.n ? nzPts(b.sum) : "—"}</td>
      <td>${!b || b.noData || !b.n ? "—" : `${nzPts(b.mid)}<br><small class="hint">${nzPts(b.lo)} … ${nzPts(b.hi)}</small>`}</td><td>${b && b.pct != null ? dvNum(b.pct) + ". perc." : "—"}</td>
      <td>${b && b.n ? `${nzPts(-b.dd)}<br><small class="hint">test ${nzPts(-b.btDd)}${b.btDd ? " · " + dvNum(100 * b.dd / b.btDd) + " %" : ""}</small>` : "—"}</td>
      <td class="l"><span class="chip ${v[0]}">${v[1]}</span></td></tr>`;
  }).join("");
  const withBand = list.filter(x => { const b = nzBand(x); return b && !b.noData; });
  if (!withBand.some(x => x.id === nz.band)) nz.band = withBand.length ? withBand[0].id : "";
  return `<div class="card"><h2>Naživo vs. test <span class="hint">WR, PF a obchody za týždeň: naživo / test; pásmo v bodoch indexu pri rovnakom počte obchodov</span></h2>
    <div class="table-wrap"><table class="dv-table"><thead><tr><th class="l">Stratégia</th><th class="l">Beh v histórii</th><th>WR</th><th>PF</th><th>Obch./týž.</th><th>Naživo</th><th>Test medián<br><small>pásmo 5 – 95 %</small></th><th>Percentil</th><th>Prepad naživo<br><small>najhorší v teste</small></th><th class="l">Verdikt</th></tr></thead>
    <tbody>${rows || `<tr><td class="l hint" colspan="10">—</td></tr>`}</tbody></table></div>
    ${withBand.length ? `<div class="dv-head" style="margin-top:14px"><h2>Cesta naživo v pásme testu</h2><label class="hint">Stratégia <select id="nz-band-inst">${withBand.map(x => `<option value="${esc(x.id)}"${x.id === nz.band ? " selected" : ""}>${esc(nzName(x))}</option>`).join("")}</select></label></div><div id="nz-band" class="dv-chart sm"></div>` : ""}
    <p class="hint">Beh v histórii = nastavenie s tým istým profilom (C# port alebo Python predloha), trh radšej MNQ a ten istý TF. Z jeho obchodov (posledný rok, ak ich je aspoň 40, inak celý test) sa 2000-krát náhodne vytiahne toľko obchodov, koľko je naživo:
      pásmo 5 – 95 % ukazuje, kam padne 90 % výberov, percentil, koľko z nich dopadlo horšie ako živý účet. Body sú spoločná miera pre MNQ aj US100.cash (ten istý index). ≈ = naživo beží iný variant toho istého profilu (C# port, _SL500 …); mená oboch profilov sú v tooltipe.</p></div>`;
}

function nzFillHtml(list) {
  const rows = list.map(x => {
    const F = nzFill(x), n = (x.trades || []).length, name = `${dvSw(x._c)}${esc(x.name)} <small class="hint">${esc(nzPlat(x))}</small>`;
    if (!n) return "";
    if (!F.n) return `<tr><td class="l">${name}</td><td>0 / ${n}</td><td class="l hint" colspan="5">bez plánovanej ceny</td></tr>`;
    const cell = a => (a.length ? `${nzPts(nzAvg(a))} <small class="hint">(${a.length})</small>` : "—");
    return `<tr><td class="l">${name}<br><small class="hint">${esc([...F.types].join(", "))}</small></td><td>${F.n} / ${n}</td>
      <td class="${dvCls(-(nzAvg(F.ent) || 0))}">${nzPts(nzAvg(F.ent))}</td><td class="${dvCls(-(nzAvg(F.stop) || 0))}">${cell(F.stop)}</td><td class="${dvCls(-(nzAvg(F.tp) || 0))}">${cell(F.tp)}</td>
      <td class="${dvCls(-F.usd)}">${dvMoney(-F.usd)} <small class="hint">${nzFmtR(-F.r)}</small></td>
      <td>${nzSecs(nzMedian(F.lat))} <small class="hint">/ ${nzSecs(F.lat.length ? Math.max(...F.lat) : null)}</small></td></tr>`;
  }).join("");
  if (!rows) return "";
  return `<div class="card"><h2>Kvalita plnenia <span class="hint">sklz = horšia cena ako plán enginu</span></h2><div class="table-wrap"><table class="dv-table"><thead><tr>
      <th class="l">Stratégia</th><th>Obch. s plánom</th><th>Sklz vstupu (priem.)</th><th>Sklz na stope</th><th>Sklz na TP</th><th>Plnenia vs. plán</th><th>Oneskorenie Market medián / max.</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="hint">Kladný sklz (červený) = horšia cena: vstup proti cene, ktorú engine plánoval pri signáli, výstup na stope proti SL a na take profite proti TP. „Plnenia vs. plán“ = súčet sklzov × množstvo × hodnota bodu (a v R voči stopu);
      mínus = plnenia stáli peniaze. Oneskorenie = od odoslania Market príkazu po vyplnenie u brokera (limitka čaká na cenu zámerne).</p></div>`;
}

/** Dni v týždni otočené: riadok = stratégia, stĺpec = deň; v bunke súčet, v tooltipe dni a % v zisku. */
function nzWeekdayHtml(R, P, fm) {
  const days = [0, 1, 2, 3, 4, 6].filter(w => P.some(p => (p.days.weekday[w] || []).length));
  const cell = v => {
    if (!v || !v.length) return `<td class="hint">—</td>`;
    const s = v.reduce((a, b) => a + b, 0);
    return `<td class="${dvCls(s)}" title="${v.length} dní, ${dvNum(100 * v.filter(x => x > 0).length / v.length)} % v zisku">${fm(s)}</td>`;
  };
  return `<div class="card"><h2>Dni v týždni <span class="hint">súčet za deň; dni a % v zisku v tooltipe</span></h2><div class="table-wrap"><table class="dv-table"><thead><tr><th class="l">Stratégia</th>${days.map(w => `<th>${DV_WD[w]}${w === 6 ? " (večer)" : ""}</th>`).join("")}</tr></thead><tbody>` +
    P.map(p => `<tr><td class="l nz-wrap">${dvSw(p.c)}${esc(p.name)}</td>${days.map(w => cell(p.days.weekday[w])).join("")}</tr>`).join("") +
    (P.length > 1 ? `<tr class="sum"><td class="l">Spolu</td>${days.map(w => cell(R.days.weekday[w])).join("")}</tr>` : "") + "</tbody></table></div></div>";
}
/** Hodina vstupu (New York) otočená: riadok = stratégia, stĺpec = hodina; v bunke zisk, v tooltipe obchody a PF. */
function nzHoursHtml(R, P, fm) {
  const hrs = Object.keys(R.hours).map(Number).sort((a, b) => a - b);
  const cell = v => {
    if (!v || !v.length) return `<td class="hint">—</td>`;
    const s = dvStats(v);
    return `<td class="${dvCls(s.pnl)}" title="${s.n} obch., PF ${dvPf(s.pf)}">${fm(s.pnl)} <small class="hint">${s.n}</small></td>`;
  };
  return `<div class="card"><h2>Hodina vstupu (New York) <span class="hint">zisk a počet obchodov; PF v tooltipe</span></h2><div class="table-wrap"><table class="dv-table"><thead><tr><th class="l">Stratégia</th>${hrs.map(hh => `<th>${String(hh).padStart(2, "0")}:00</th>`).join("")}</tr></thead><tbody>` +
    P.map(p => `<tr><td class="l nz-wrap">${dvSw(p.c)}${esc(p.name)}</td>${hrs.map(hh => cell((R.hours[hh] || {})[p.i])).join("")}</tr>`).join("") +
    (P.length > 1 ? `<tr class="sum"><td class="l">Spolu</td>${hrs.map(hh => cell(Object.values(R.hours[hh] || {}).flat())).join("")}</tr>` : "") + "</tbody></table></div></div>";
}

function nzLogHtml(list) {
  return `<details class="card dv-log-box"${nz.log.open ? " open" : ""} id="nz-log-box"><summary><h2>Denník <span class="hint">obchody, signály, otvorené pozície a varovania platformy — rozbaľ</span></h2></summary>
    <div class="dv-filters"><span class="mode-switch dv-seg" id="nz-view"><button type="button" data-v="tr">Obchody</button><button type="button" data-v="sig">Signály</button><button type="button" data-v="open">Otvorené</button><button type="button" data-v="note">Varovania</button></span>
      <label>Stratégia <select id="nz-f-inst"><option value="">všetky</option>${list.map(x => `<option value="${esc(x.id)}">${esc(nzName(x))}</option>`).join("")}</select></label></div>
    <div class="table-wrap"><table class="dv-table" id="nz-log"></table></div>
    <div class="dv-pager"><button type="button" class="ghost" id="nz-prev">‹ Späť</button><span id="nz-info" class="hint"></span><button type="button" class="ghost" id="nz-next">Ďalej ›</button></div></details>`;
}

function nzRenderLog() {
  const L = nz.log, list = nzList().filter(x => !L.inst || x.id === L.inst), n = 50;
  const who = x => `${dvSw(x._c)}${esc(x.name)} <small class="hint">${esc(nzPlat(x))}</small>`;
  const num = (v, d = 2) => dvNum(v, d);
  let head, rows = [];
  if (L.view === "tr") {
    head = `<th class="l">Otvorenie</th><th class="l">Zatvorenie</th><th class="l">Stratégia</th><th class="l">Smer</th><th>Množ.</th><th>Vstup</th><th>Výstup</th><th>SL</th><th>TP</th><th class="l">Dôvod</th><th>R</th><th>PnL</th>`;
    for (const x of list) for (const t of x.trades || []) rows.push([t.close, `<td class="l">${nzTime(t.open)}</td><td class="l">${nzTime(t.close)}</td><td class="l">${who(x)}</td><td class="l">${t.dir}</td><td>${num(t.qty, t.qty % 1 ? 2 : 0)}</td>
      <td>${num(t.entry)}</td><td>${num(t.exit)}</td><td>${num(t.sl)}</td><td>${num(t.tp)}</td><td class="l">${t.reason === "take_profit" ? "take profit" : t.reason === "stop_loss" ? "stop loss" : esc(t.reason || "—")}</td>
      <td class="${dvCls(nzR(t))}">${nzFmtR(nzR(t))}</td><td class="${dvCls(t.pnl)}">${dvMoney(t.pnl, 2)}</td>`]);
  } else if (L.view === "sig") {
    head = `<th class="l">Signál (sviečka)</th><th class="l">Stratégia</th><th class="l">Smer</th><th class="l">Typ</th><th>Vstup</th><th>SL</th><th>TP</th><th>Množ.</th><th class="l">Výsledok</th>`;
    for (const x of list) for (const s of x.signals || []) {
      const c = s.result === "vyplnený" ? "ok" : s.result === "bez vyplnenia" ? "bad" : s.result === "čaká" ? "warn" : "";
      rows.push([s.t, `<td class="l">${nzTime(s.t)}</td><td class="l">${who(x)}</td><td class="l">${s.dir}</td><td class="l">${esc(s.type)}</td><td>${num(s.entry)}</td><td>${num(s.sl)}</td><td>${num(s.tp)}</td>
        <td>${s.qty == null ? "—" : num(s.qty, s.qty % 1 ? 2 : 0)}</td><td class="l"><span class="chip ${c}">${esc(s.result)}</span></td>`]);
    }
  } else if (L.view === "open") {
    head = `<th class="l">Otvorenie</th><th class="l">Stratégia</th><th class="l">Smer</th><th>Množ.</th><th>Vstup</th><th>SL</th><th>TP</th>`;
    for (const x of list) for (const t of x.open || []) rows.push([t.open, `<td class="l">${nzTime(t.open)}</td><td class="l">${who(x)}</td><td class="l">${t.dir}</td><td>${num(t.qty, t.qty % 1 ? 2 : 0)}</td><td>${num(t.entry)}</td><td>${num(t.sl)}</td><td>${num(t.tp)}</td>`]);
  } else {
    head = `<th class="l">Čas</th><th class="l">Stratégia</th><th class="l">Text</th>`;
    for (const x of list) for (const m of x.notes || []) rows.push([m.t, `<td class="l">${nzTime(m.t)}</td><td class="l">${who(x)}</td><td class="l" style="white-space:normal">${esc(m.text)}</td>`]);
  }
  rows.sort((a, b) => (a[0] < b[0] ? 1 : -1));
  const pages = Math.max(1, Math.ceil(rows.length / n));
  L.page = Math.min(L.page, pages - 1);
  const cols = (head.match(/<th/g) || []).length;
  $("#nz-log").innerHTML = `<thead><tr>${head}</tr></thead><tbody>${rows.slice(L.page * n, L.page * n + n).map(r => `<tr>${r[1]}</tr>`).join("") || `<tr><td class="l hint" colspan="${cols}">Nič.</td></tr>`}</tbody>`;
  $("#nz-info").textContent = `${rows.length} riadkov · strana ${L.page + 1} z ${pages}`;
  $("#nz-prev").disabled = L.page === 0; $("#nz-next").disabled = L.page >= pages - 1;
  for (const b of $$("#nz-view button")) b.classList.toggle("active", b.dataset.v === L.view);
}

function nzRender() {
  const out = $("#nz-out");
  if (!nz.data) return;
  const all = nzActive(), list = nzList(), stale = (nz.data.instances || []).filter(x => x.stale);
  const R = nzCompute(list), fm = nzFm();
  nz.R = R;
  $("#nz-pick").innerHTML = all.length ? nzPickHtml(all) : `<p class="hint">Žiadna živá inštancia v zrkadle. ${esc(nz.data.error || "")}</p>`;
  let h = "";
  if (!list.length) h = all.length ? `<div class="card"><p class="hint">Nie je vybraná žiadna stratégia.</p></div>` : "";
  else {
    const P = R ? R.parts : [];
    h += nzSummaryHtml(list, R);
    h += `<div class="card"><h2>Čo z toho vyplýva</h2>${nzFindings(list, R)}</div>`;
    h += nzVsTestHtml(list);
    if (R) {
      h += `<div class="card"><h2>Krivka zisku naživo <span class="hint">stĺpce = zisk dňa spolu, krivky = súčet${nz.unit === "R" ? " · v R" : ""}</span></h2><div id="nz-eq" class="dv-chart"></div></div>`;
      if (P.length > 1) h += `<div class="card"><h2>Spolu: kapitál a prepad</h2><div id="nz-dd" class="dv-chart sm"></div></div>`;
      if (P.length > 1) {
        const pos = P.filter(p => p.total.pnl > 0).sort((a, b) => b.total.pnl - a.total.pnl), tot = pos.reduce((s, p) => s + p.total.pnl, 0);
        const neg = P.filter(p => p.total.pnl <= 0).sort((a, b) => a.total.pnl - b.total.pnl);
        h += `<div class="card"><h2>Podiel na zisku <span class="hint">${nz.unit === "R" ? "zo súčtu R" : "z čistého zisku"} stratégií v pluse</span></h2><div class="nz-pie">${pos.length ? `<div id="nz-pie" class="nz-pie-box"></div>` : ""}
          <table class="dv-table"><tbody>${pos.map(p => `<tr><td class="l">${dvSw(p.c)}${esc(p.name)}</td><td><b>${dvNum(100 * p.total.pnl / tot, 1)} %</b></td><td class="pos">${fm(p.total.pnl)}</td></tr>`).join("")}
          ${neg.map(p => `<tr><td class="l hint">${dvSw(p.c)}${esc(p.name)}</td><td class="hint">v strate</td><td class="${dvCls(p.total.pnl)}">${fm(p.total.pnl)}</td></tr>`).join("")}</tbody></table></div></div>`;
      }
    }
    h += nzFillHtml(list);
    if (R) h += dvDaysHtml(R, P, fm) + nzWeekdayHtml(R, P, fm) + dvTradeCardsHtml(P, fm) + nzHoursHtml(R, P, fm) + dvCorrHtml(R, P, "Naživo sa počíta od 11 spoločných obchodných dní dvojice.");
    h += nzLogHtml(list);
  }
  if (stale.length) h += `<details class="card dv-log-box"><summary><h2>Staré a testovacie inštancie <span class="hint">${stale.length} — bez obchodu a bez správy viac ako 7 dní</span></h2></summary>
    <div class="table-wrap"><table class="dv-table"><tbody>${stale.map(x => `<tr><td class="l">${esc(x.name)}</td><td class="l">${esc(nzPlat(x))} · ${esc(x.account)}</td><td class="l hint">${esc(x.profile || "—")}</td><td>${nzStatus(x)}</td><td>${nzTime(x.last_event)}</td></tr>`).join("")}</tbody></table></div></details>`;
  out.innerHTML = h;
  nzBind();
  nzCharts();
}

function nzBind() {
  for (const cb of $$("[data-nz-inst]")) cb.onchange = () => { if (cb.checked) delete nz.off[cb.dataset.nzInst]; else nz.off[cb.dataset.nzInst] = 1; nz.log.inst = ""; nzSave(); nzRender(); };
  // celý účet: zaškrtnúť = všetky jeho stratégie, odškrtnúť = žiadnu; čiastočný výber ukáže pomlčku
  const groups = new Map(nzGroups(nzActive()));
  for (const cb of $$("[data-nz-acct]")) {
    cb.indeterminate = cb.hasAttribute("data-mixed");
    cb.onchange = () => {
      for (const x of groups.get(cb.dataset.nzAcct) || []) { if (cb.checked) delete nz.off[x.id]; else nz.off[x.id] = 1; }
      nz.log.inst = ""; nzSave(); nzRender();
    };
  }
  for (const t of $$("[data-nz-tog]")) t.onclick = () => {
    const k = t.dataset.nzTog;
    if (nz.open.has(k)) nz.open.delete(k); else nz.open.add(k);
    nzSave();
    $("#nz-pick").innerHTML = nzPickHtml(nzActive());
    nzBind();
  };
  for (const b of $$("#nz-unit button")) b.onclick = () => { if (b.dataset.u === nz.unit) return; nz.unit = b.dataset.u; nzSave(); nzRender(); };
  if ($("#nz-band-inst")) $("#nz-band-inst").onchange = e => { nz.band = e.target.value; nzBandChart(); };
  if (!$("#nz-log")) return;
  const L = nz.log;
  $("#nz-log-box").ontoggle = e => { L.open = e.target.open; };
  for (const b of $$("#nz-view button")) b.onclick = () => { L.view = b.dataset.v; L.page = 0; nzRenderLog(); };
  $("#nz-f-inst").value = L.inst;
  $("#nz-f-inst").onchange = e => { L.inst = e.target.value; L.page = 0; nzRenderLog(); };
  $("#nz-prev").onclick = () => { L.page--; nzRenderLog(); };
  $("#nz-next").onclick = () => { L.page++; nzRenderLog(); };
  nzRenderLog();
}

function nzLayout(extra) {
  return { margin: { l: 10, r: 60, t: 10, b: 30 }, template: plotlyTemplate(), hovermode: "x unified",
           legend: { orientation: "h", yanchor: "bottom", y: 1.0, x: 0 },
           yaxis: { side: "right", ticksuffix: nz.unit === "R" ? " R" : " $", zeroline: true }, xaxis: { showgrid: false },
           paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", ...extra };
}

function nzCharts() {
  const R = nz.R;
  if (typeof Plotly === "undefined") return;
  nzBandChart();
  if (!R || !$("#nz-eq")) return;
  const P = R.parts, cfg = { displaylogo: false, responsive: true }, hv = nz.unit === "R" ? "%{y:.2f} R" : "%{y:,.0f} $";
  const days = R.equity.map(e => e[0]);
  const bars = days.map(d => R.dayMap[d]);
  const traces = [{ type: "bar", name: "zisk dňa", x: days, y: bars, marker: { color: bars.map(v => (v >= 0 ? "rgba(8,153,129,0.55)" : "rgba(242,54,69,0.55)")) }, hovertemplate: hv }];
  for (const p of P) traces.push({ type: "scatter", mode: "lines+markers", name: p.name, x: p.equity.map(e => e[0]), y: p.equity.map(e => e[1]),
                                    line: { color: dvColor(p.c), width: 1.8 }, marker: { size: 5 }, hovertemplate: hv });
  if (P.length > 1) traces.push({ type: "scatter", mode: "lines+markers", name: "Spolu", x: days, y: R.equity.map(e => e[1]),
                                  line: { color: isDarkTheme() ? "#e6edf0" : "#142c36", width: 2.8 }, marker: { size: 6 }, hovertemplate: hv });
  Plotly.newPlot("nz-eq", traces, nzLayout({ height: 420, barmode: "relative" }), cfg);
  if ($("#nz-dd")) {
    let peak = 0;
    const eq = R.equity.map(e => e[1]), dd = eq.map(v => { peak = Math.max(peak, v); return v - peak; });
    Plotly.newPlot("nz-dd", [
      { type: "scatter", mode: "lines+markers", name: "kapitál", x: days, y: eq, line: { color: GREEN, width: 2 }, hovertemplate: hv },
      { type: "scatter", mode: "lines", name: "prepad", x: days, y: dd, line: { color: RED, width: 1 }, fill: "tozeroy", fillcolor: "rgba(242,54,69,0.15)", hovertemplate: hv },
    ], nzLayout({ height: 260 }), cfg);
  }
  if ($("#nz-pie")) {
    const pos = P.filter(p => p.total.pnl > 0).sort((a, b) => b.total.pnl - a.total.pnl);
    Plotly.newPlot("nz-pie", [{ type: "pie", hole: 0.55, sort: false, labels: pos.map(p => p.name), values: pos.map(p => p.total.pnl),
      marker: { colors: pos.map(p => dvColor(p.c)), line: { color: isDarkTheme() ? "#0f1a1f" : "#fff", width: 2 } }, textinfo: "percent", hoverinfo: "label+percent" }],
      { margin: { l: 0, r: 0, t: 0, b: 0 }, height: 240, showlegend: false, template: plotlyTemplate(), paper_bgcolor: "rgba(0,0,0,0)" }, cfg);
  }
}

/** Pásmo testu (5 – 95 %, medián) a cesta naživo po obchodoch, v bodoch. */
function nzBandChart() {
  const el = $("#nz-band");
  if (!el || typeof Plotly === "undefined") return;
  const x = nzList().find(q => q.id === nz.band), b = x && nzBand(x);
  if (!b || b.noData) return;
  const k = b.steps.map((_, i) => i), band = "rgba(41,98,255,", col = dvColor(x._c);
  let c = 0;
  const live = [0, ...b.live.map(v => (c += v))];
  Plotly.newPlot("nz-band", [
    { type: "scatter", mode: "lines", name: "test 95 %", x: k, y: b.steps.map(s => s[2]), line: { color: band + "0.35)", width: 1 }, hovertemplate: "%{y:.1f} b" },
    { type: "scatter", mode: "lines", name: "test 5 %", x: k, y: b.steps.map(s => s[0]), line: { color: band + "0.35)", width: 1 }, fill: "tonexty", fillcolor: band + "0.12)", hovertemplate: "%{y:.1f} b" },
    { type: "scatter", mode: "lines", name: "test medián", x: k, y: b.steps.map(s => s[1]), line: { color: band + "0.8)", width: 1.5, dash: "dash" }, hovertemplate: "%{y:.1f} b" },
    { type: "scatter", mode: "lines+markers", name: "naživo", x: live.map((_, i) => i), y: live, line: { color: col, width: 2.5 }, marker: { size: 6 }, hovertemplate: "%{y:.1f} b" },
  ], { ...nzLayout({ height: 280 }), yaxis: { side: "right", ticksuffix: " b", zeroline: true }, xaxis: { title: { text: "obchod č." }, showgrid: false, dtick: 5 } },
  { displaylogo: false, responsive: true });
}

async function loadLiveDiv(fresh = false) {
  nzPrefs();
  const status = $("#nz-status");
  status.textContent = "Načítavam obchody naživo…";
  try {
    nz.data = await api(`/api/diversify/live${fresh ? "?fresh=1" : ""}`);
    status.textContent = "";
  } catch (e) {
    status.textContent = `Načítanie zlyhalo: ${e.message}`;
    return;
  }
  nzRender();
  // behy z histórie na porovnanie s testom — dotiahnu sa na pozadí a karta sa prekreslí
  const missing = nzActive().filter(x => !nz.bt[x.id]);
  if (missing.length) {
    status.textContent = "Hľadám behy toho istého profilu v histórii…";
    await nzBacktests(missing).catch(e => { status.textContent = `Behy z histórie: ${e.message}`; });
    if (status.textContent.startsWith("Hľadám")) status.textContent = "";
    nzRender();
  }
}

function setupLiveDiv() {
  $("#nz-refresh").onclick = () => loadLiveDiv(true);
}
