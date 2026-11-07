/* TradeBot Backtester — karta Stratégie: katalóg stratégií s profilmi a najlepším behom.
 * Dáta z /api/catalog (stratégia → profily po skupinách + najlepší beh z histórie). C# porty
 * (`tksnet`, `tksneteod`) sa zlučujú do karty predlohy (`baseStrategyKey`), trh a typ je
 * `strategyClass` zo settings.js — ten istý, ktorý triedi výber stratégie vo formulári. */
"use strict";

const cat = { data: null, deployments: [], market: "", type: "", sort: "audit", query: "", onlySmernica: false,
  state: "", drawer: null, tab: "all" };

/** Filter Stav: "" = všetky, run = len bežiace, stop = nasadené, ale zastavené. */
const CAT_STATES = { run: f => f.running.length > 0, stop: f => f.deps.length > 0 && !f.running.length };

const CAT_GROUPS = { smernica: "prešiel smernicou", repo: "repozitár", user: "vlastný" };
const CAT_GROUP_ORDER = { smernica: 0, repo: 1, user: 2 };

/** Zisk na jednotku drawdownu — to isté poradie, akým backend vyberá najlepší beh. */
const catScore = b => b ? (b.pnl_pct || 0) / Math.max(b.max_drawdown_pct || 0, 1) : -Infinity;
const catNum = (v, d = 1) => v === null || v === undefined || Number.isNaN(v) ? "—"
  : Number(v).toLocaleString("sk-SK", { minimumFractionDigits: d, maximumFractionDigits: d });
const catSigned = (v, d = 1) => v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${catNum(v, d)}`;

/** Nasadenie naozaj beží: je aktívne a jeho inštancia v spoole žije (ping alebo udalosť nedávno, aj keď trh stojí). */
const catDepRunning = d => !!(d.active && d.live && d.live.alive);

/** Jedno nasadenie do tooltipu: účet · stratégia · profil — stav. */
function catDepLine(d) {
  const why = catDepRunning(d) ? (d.live.state === "closed" ? "beží, trh stojí" : "beží")
    : !d.active ? (d.mode === "paused" ? "pozastavené" : "vypnuté") : "aktívne, ale inštancia mlčí";
  return `${d.account || "účet"} · ${d.strategy} · ${d.profile || "—"} — ${why}`;
}

/** Štítky rodiny: ● BEŽÍ / ■ ZASTAVENÁ (nasadenia na účtoch, tooltip po jednom) a C# port.
 *  Tie isté na karte katalógu aj v hlavičke okna Hodnotenie. */
function catLiveBadges(f) {
  const n = a => a.length > 1 ? ` · ${a.length}` : "";
  return [
    f.running.length ? `<span class="cat-badge on" title="${esc(f.running.map(catDepLine).join("\n"))}">● BEŽÍ${n(f.running)}</span>` : "",
    f.stopped.length ? `<span class="cat-badge off" title="${esc(f.stopped.map(catDepLine).join("\n"))}">■ ZASTAVENÁ${n(f.stopped)}</span>` : "",
    f.live ? '<span class="cat-badge port" title="má C# port — pripravená na NinjaTrader 8 a MetaTrader 5">C#</span>' : "",
  ].join("");
}

/** Stratégie zlúčené do rodín: predloha + jej C# porty. Profily rodiny sú spolu (s kľúčom
 *  stratégie, ku ktorej patria), najlepší beh je najlepší z celej rodiny. */
function catFamilies(rows) {
  const keys = new Set(rows.map(r => r.key));
  const fam = new Map();
  for (const r of rows) {
    const base = keys.has(baseStrategyKey(r.key)) ? baseStrategyKey(r.key) : r.key;
    if (!fam.has(base)) fam.set(base, { key: base, members: [] });
    fam.get(base).members.push(r);
  }
  return [...fam.values()].map(f => {
    const head = f.members.find(m => m.key === f.key) || f.members[0];
    const ports = f.members.filter(m => m.key !== f.key);
    const profiles = f.members.flatMap(m => m.profiles.map(p => ({ ...p, strategy: m.key })));
    const best = f.members.map(m => m.best && { ...m.best, strategy: m.key })
      .filter(Boolean).sort((a, b) => catScore(b) - catScore(a))[0] || null;
    const [market, type] = strategyClass(f.key);
    const counts = { smernica: 0, repo: 0, user: 0 };
    for (const p of profiles) counts[p.group] = (counts[p.group] || 0) + 1;
    const memberKeys = new Set(f.members.map(m => m.key));
    // všetky nasadenia rodiny na účtoch (aj pozastavené), z nich bežiace = aktívne a inštancia žije
    const deps = cat.deployments.filter(d => memberKeys.has(d.strategy));
    const running = deps.filter(catDepRunning), stopped = deps.filter(d => !catDepRunning(d));
    for (const p of profiles) {
      const mine = deps.filter(d => d.profile === p.name && d.strategy === p.strategy);
      p.deployed = mine.length; p.running = mine.filter(catDepRunning).length;
    }
    return {
      deps, running, stopped,
      key: f.key, title: head.title, lead: head.lead || "", hasExplainer: !!head.has_explainer,
      ports, profiles, best, counts, market, type,
      live: ports.some(p => p.csharp) || head.csharp,
      runs: f.members.reduce((s, m) => s + (m.runs || 0), 0),
      lastRun: f.members.map(m => m.last_run || "").sort().pop() || "",
      isNew: NOVE_STRATEGIE.has(f.key),
    };
  });
}

/** Poradie profilov v karte aj v paneli: smernica, potom s behom (od najlepšieho), potom zvyšok. */
function catProfileSort(a, b) {
  const g = CAT_GROUP_ORDER[a.group] - CAT_GROUP_ORDER[b.group];
  if (g) return g;
  const pa = a.claimed?.pf ?? a.best_run?.profit_factor ?? -1, pb = b.claimed?.pf ?? b.best_run?.profit_factor ?? -1;
  return pb - pa || a.name.localeCompare(b.name);
}

/** PF / WR profilu: smernica má čísla z posudku (`_title`), ostatné z najlepšieho behu. */
function catProfileStats(p) {
  const c = p.claimed || {};
  if (p.group === "smernica" && c.pf != null) {
    const extra = [c.trades_year != null && `${catNum(c.trades_year, 0)} obch/rok`,
      c.max_dd_usd != null && `max DD ${catNum(c.max_dd_usd, 0)} $`,
      c.pf_last_year != null && `posl. rok PF ${catNum(c.pf_last_year, 2)}`].filter(Boolean).join(" · ");
    return { pf: c.pf, wr: c.winrate, extra, src: "posudok smernice" };
  }
  const r = p.best_run;
  if (r) return { pf: r.profit_factor, wr: r.winrate, extra: `${catSigned(r.pnl_pct)} %`, src: `beh ${r.id}` };
  return null;
}

function catSpark(eq) {
  if (!eq || eq.length < 2) return '<div class="cat-spark empty muted small">bez krivky</div>';
  const w = 240, h = 46, min = Math.min(0, ...eq), max = Math.max(0, ...eq), span = max - min || 1;
  const pts = eq.map((v, i) => `${(i / (eq.length - 1) * w).toFixed(1)},${(h - (v - min) / span * h).toFixed(1)}`);
  const zero = (h - (0 - min) / span * h).toFixed(1);
  const cls = eq[eq.length - 1] >= 0 ? "pos" : "neg";
  return `<svg class="cat-spark ${cls}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
    <line x1="0" x2="${w}" y1="${zero}" y2="${zero}" class="zero"/>
    <polygon points="0,${zero} ${pts.join(" ")} ${w},${zero}" class="area"/>
    <polyline points="${pts.join(" ")}" class="line"/></svg>`;
}

/** Krátke meno profilu. Popis smernice nesie aj čísla („NOA 1 C# · PF 1,82 · WR 40 % · …"),
 *  tie sú v karte a v paneli zvlášť, takže z neho ostane len prvý úsek. */
function catProfileName(p) {
  const t = p.title || p.name.replace(/^(PRESIEL_SMERNICAMI_|SMERNICE_CS_)/, "").replace(/_/g, " ");
  return p.group === "smernica" ? t.split(" · ")[0] : t;
}

/** Jeden profil rodiny — „naj": nasadený naživo, potom zo smernice, potom s najlepším behom (zisk / DD).
 *  Ten istý ukazuje karta aj okno hodnotenia, keď sa otvorí bez výberu. */
function catTopProfile(f) {
  const rank = p => [p.running > 0, p.deployed > 0, p.group === "smernica", !!p.best_run,
    p.group === "smernica" ? (p.claimed?.pf ?? 0) : catScore(p.best_run)];
  const better = (x, y) => { const a = rank(x), b = rank(y); for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return b[i] > a[i] ? 1 : -1; return 0; };
  return [...f.profiles].sort(better)[0] || null;
}

function catCard(f) {
  const b = f.best, n = f.profiles.length;
  const seg = g => n ? (f.counts[g] / n * 100).toFixed(1) : 0;
  const top = [catTopProfile(f)].filter(Boolean);
  const kpi = (label, val, cls = "") => `<div class="cat-kpi"><span>${label}</span><b class="${cls}">${val}</b></div>`;
  const badges = catLiveBadges(f) + (f.isNew ? '<span class="cat-badge new">nová</span>' : "");
  const ports = f.ports.length ? `<div class="cat-ports small muted">C# porty: ${f.ports.map(p =>
    `<button type="button" class="linkish" data-cat-open="${esc(p.key)}">${esc(p.key)}</button>`).join(", ")}</div>` : "";
  return `<article class="cat-card card" data-key="${esc(f.key)}" title="klik otvorí hodnotenie stratégie">
    <div class="cat-head">
      <div><h3 class="cat-title">${auditBadges(f.key)}${esc(f.title)}</h3>
        <div class="cat-tags"><span class="chip">${esc(f.market)}</span>${f.type ? `<span class="chip">${esc(f.type)}</span>` : ""}${badges}</div></div>
      <code class="muted small">${esc(f.key)}</code>
    </div>
    ${f.lead || f.hasExplainer ? `<p class="cat-lead small">${esc(f.lead)}${f.hasExplainer
      ? ` <button type="button" class="linkish" data-cat-explain="${esc(f.key)}" title="vysvetlivka: myšlienka, kedy vstupuje, stop a cieľ, hlavné nastavenia">Ako funguje?</button>` : ""}</p>` : ""}
    ${b ? `${catSpark(b.equity)}
    <div class="cat-best small muted">najlepší beh: ${esc(b.pair || "")} ${esc(b.timeframe || "")} · ${esc(b.timerange || "")}${b.strategy !== f.key ? ` · ${esc(b.strategy)}` : ""}</div>
    <div class="cat-kpis">
      ${kpi("Zisk", `${catSigned(b.pnl_pct)} %`, (b.pnl_pct || 0) >= 0 ? "pos" : "neg")}
      ${kpi("PF", catNum(b.profit_factor, 2))}
      ${kpi("RR", b.rr != null ? catNum(b.rr, 2) : "—")}
      ${kpi("Win", `${catNum(b.winrate)} %`)}
      ${kpi("DD", `${catNum(b.max_drawdown_pct)} %`)}
      ${kpi("BE", b.break_even_pct != null ? `${catNum(b.break_even_pct, 4)} %` : "—")}
    </div>
    ${b.r_n ? `<div class="cat-rline small" title="kde obchody najlepšieho behu v priemere zatvoria, v násobkoch rizika (vzdialenosti stopu); ${b.r_n} obchodov">
      Ø zatvára: zisk <b class="pos">${b.r_win != null ? `${catSigned(b.r_win, 2)} R` : "—"}</b> · strata <b class="neg">${b.r_loss != null ? `${catSigned(b.r_loss, 2)} R` : "—"}</b>
      · obchod <b>${catSigned(b.r_avg, 2)} R</b></div>` : ""}` : `<div class="cat-nobest muted small">Žiadny beh v histórii neprešiel sitom (aspoň 40 obchodov, PF &gt; 1, DD pod 35 %).
      Behov spolu: ${f.runs}.</div>`}
    <section class="cat-prof">
      <div class="cat-prof-head"><b>${n} ${n === 1 ? "profil" : n < 5 && n > 0 ? "profily" : "profilov"}</b>
        <span class="small muted">${f.counts.smernica} smernica · ${f.counts.repo} repo · ${f.counts.user} vlastné</span></div>
      <div class="cat-bar" aria-hidden="true"><i class="g-smernica" style="width:${seg("smernica")}%"></i><i class="g-repo" style="width:${seg("repo")}%"></i><i class="g-user" style="width:${seg("user")}%"></i></div>
      <ul class="cat-top">${top.map(p => { const s = catProfileStats(p); return `<li>
        <span class="small muted">naj</span><span class="cat-dot g-${p.group}" title="${CAT_GROUPS[p.group]}"></span>
        <button type="button" class="linkish cat-pname" data-cat-open="${esc(p.strategy)}" data-cat-profile="${esc(p.name)}" title="${esc(p.name)} — otvoriť v Novom behu">${esc(catProfileName(p))}</button>
        ${p.running ? '<span class="cat-badge on" title="tento profil beží naživo">beží</span>'
          : p.deployed ? '<span class="cat-badge off" title="tento profil je nasadený, ale nebeží">zastavený</span>' : ""}
        <span class="small muted num">${s ? `PF ${catNum(s.pf, 2)} · WR ${catNum(s.wr, 0)} %` : "bez behu"}</span></li>`; }).join("") || '<li class="muted small">žiadny profil — len Pine defaulty</li>'}</ul>
    </section>
    ${ports}
    <div class="cat-actions">
      <button type="button" class="ghost small" data-cat-report="${esc(f.key)}" title="výkon, analytika, posudok, nastavenie a behy — aj klik kamkoľvek na kartu">Hodnotenie</button>
      <button type="button" class="ghost small" data-cat-drawer="${esc(f.key)}"${n ? "" : " disabled"}>Profily (${n})</button>
      ${b ? `<button type="button" class="ghost small" data-cat-run="${esc(b.id)}" title="detail najlepšieho behu v Histórii">Najlepší beh</button>` : ""}
      <span class="spacer"></span>
      <button type="button" class="primary small" data-cat-open="${esc(f.key)}">Otestovať</button>
    </div>
    ${f.ports.length || (auditOf(f.key) && auditOf(f.key).csharp) ? "" : '<div class="cat-nocs" title="stratégia nemá C# jadro — na NinjaTrader 8 / MetaTrader 5 (live) ju treba najprv prepísať do jadra (docs/STRATEGIE.md, „Stratégia s jadrom v C#“)">⚙ treba prepísať do jadra (C#)</div>'}
  </article>`;
}

/** Skupina auditu rodiny: 0 = AS, 1 = A, 2 = BS, 3 = B, 4 = C, 5 = bez hodnotenia (tester/audit.json). */
const CAT_AUDIT_GROUPS = ["AS — funguje a prešiel Sortino", "A — funguje, Sortino neprešiel", "BS — s výhradou, prešiel Sortino",
  "B — s výhradou, Sortino neprešiel", "C — nefunguje (zatiaľ)", "Bez hodnotenia auditu"];
function catAuditRank(f) {
  const a = auditOf(f.key);
  if (!a) return 5;
  return a.cls === "A" ? (a.sortino_ok ? 0 : 1) : a.cls === "B" ? (a.sortino_ok ? 2 : 3) : 4;
}

function catFiltered() {
  const q = cat.query.trim().toLowerCase();
  const list = catFamilies(cat.data).filter(f =>
    (!cat.market || f.market === cat.market)
    && (!cat.type || (cat.type === "LIVE" ? f.deps.length > 0 : f.type === cat.type))
    && (!cat.onlySmernica || f.counts.smernica > 0)
    && (!cat.state || CAT_STATES[cat.state](f))
    && (!q || [f.key, f.title, ...f.ports.map(p => p.key), ...f.profiles.map(p => p.name + " " + p.title)]
      .some(s => String(s).toLowerCase().includes(q))));
  const val = (f, k) => f.best && f.best[k] != null ? f.best[k] : -Infinity;
  const by = {
    audit: (a, b) => catAuditRank(a) - catAuditRank(b) || ((auditOf(b.key) || {}).sortino ?? -99) - ((auditOf(a.key) || {}).sortino ?? -99)
      || catScore(b.best) - catScore(a.best),
    score: (a, b) => catScore(b.best) - catScore(a.best),
    pnl: (a, b) => val(b, "pnl_pct") - val(a, "pnl_pct"),
    rr: (a, b) => val(b, "rr") - val(a, "rr"),
    live: (a, b) => b.running.length - a.running.length || b.deps.length - a.deps.length || (b.live - a.live) || catScore(b.best) - catScore(a.best),
    profiles: (a, b) => b.profiles.length - a.profiles.length,
    smernica: (a, b) => b.counts.smernica - a.counts.smernica || catScore(b.best) - catScore(a.best),
    recent: (a, b) => b.lastRun.localeCompare(a.lastRun),
    title: (a, b) => a.title.localeCompare(b.title, "sk"),
  }[cat.sort];
  // typ LIVE = nasadené na účtoch: najprv bežiace, potom zastavené, v rámci nich zvolené poradie
  if (cat.type === "LIVE") return list.sort((a, b) => (b.running.length > 0) - (a.running.length > 0) || by(a, b));
  return list.sort(by);
}

function catPills(el, values, current, attr) {
  el.innerHTML = ["", ...values].map(v =>
    `<button type="button" class="chip-btn${v === current ? " active" : ""}" data-${attr}="${esc(v)}">${esc(v || "Všetky")}</button>`).join("");
}

function renderCatalog() {
  if (!cat.data) return;
  const all = catFamilies(cat.data);
  const markets = [...TRHY, ...(all.some(f => f.market === "OSTATNÉ") ? ["OSTATNÉ"] : [])];
  catPills($("#cat-markets"), markets, cat.market, "cat-market");
  catPills($("#cat-types"), [...TYPY, "LIVE"], cat.type, "cat-type");
  $("#cat-states").innerHTML = [["", "Všetky"], ["run", "● Bežiace"], ["stop", "■ Zastavené"]].map(([v, t]) =>
    `<button type="button" class="chip-btn${v === cat.state ? " active" : ""}" data-cat-state="${v}">${t}${v
      ? ` (${all.filter(CAT_STATES[v]).length})` : ""}</button>`).join("");
  const list = catFiltered();
  // stratégie bez dobrého behu a bez profilu zo smernice idú do zbaleného bloku na koniec
  // (pri LIVE nie: nasadená stratégia sa nesmie schovať do zbaleného bloku)
  const weak = f => cat.type !== "LIVE" && !cat.state && !f.best && !f.counts.smernica;
  const shown = list.filter(f => !weak(f)), rest = list.filter(weak);
  const nProf = all.reduce((s, f) => s + f.profiles.length, 0);
  const nRun = all.filter(f => f.running.length).length, nStop = all.filter(f => f.deps.length && !f.running.length).length;
  $("#cat-summary").textContent = `${list.length} z ${all.length} stratégií · ${nProf} profilov · ${all.filter(f => f.live).length} s C# portom`
    + (nRun ? ` · ${nRun} beží` : "") + (nStop ? ` · ${nStop} zastavených` : "");
  // pri poradí podľa hodnotenia nadpis pred každou skupinou (AS, A, BS, B, C, bez hodnotenia)
  let lastGroup = -1;
  $("#cat-grid").innerHTML = shown.map(f => {
    if (cat.sort !== "audit") return catCard(f);
    const g = catAuditRank(f), head = g !== lastGroup
      ? `<h3 class="cat-group-head">${esc(CAT_AUDIT_GROUPS[g])} <span class="muted small">(${shown.filter(x => catAuditRank(x) === g).length})</span></h3>` : "";
    lastGroup = g;
    return head + catCard(f);
  }).join("")
    || (rest.length ? "" : '<div class="muted">Filtru nezodpovedá žiadna stratégia.</div>');
  const restEl = $("#cat-rest");
  restEl.hidden = !rest.length;
  $("#cat-rest-count").textContent = rest.length;
  $("#cat-rest-grid").innerHTML = rest.map(catCard).join("");
}

function renderCatDrawer() {
  const f = catFamilies(cat.data).find(x => x.key === cat.drawer);
  if (!f) { $("#cat-drawer").hidden = true; return; }
  $("#cat-drawer-title").textContent = `${f.title} — profily`;
  const tabs = [["all", "Všetky", f.profiles.length], ...Object.entries(CAT_GROUPS).map(([g, t]) => [g, t, f.counts[g]])];
  $("#cat-drawer-tabs").innerHTML = tabs.map(([k, t, n]) =>
    `<button type="button" class="chip-btn${k === cat.tab ? " active" : ""}" data-cat-tab="${k}">${esc(t)} (${n})</button>`).join("");
  const rows = f.profiles.filter(p => cat.tab === "all" || p.group === cat.tab).sort(catProfileSort);
  $("#cat-drawer-rows").innerHTML = rows.map(p => {
    const s = catProfileStats(p);
    return `<tr>
      <td><span class="cat-dot g-${p.group}" title="${CAT_GROUPS[p.group]}"></span></td>
      <td><b>${esc(catProfileName(p))}</b><div class="small muted">${esc(p.name)}${p.strategy !== f.key ? ` · ${esc(p.strategy)}` : ""}</div></td>
      <td>${esc(p.pair)} ${esc(p.timeframe)}</td>
      <td class="num">${s ? catNum(s.pf, 2) : "—"}</td><td class="num">${s && s.wr != null ? `${catNum(s.wr, 0)} %` : "—"}</td>
      <td class="small muted">${s ? esc(s.extra) : "bez behu"}${s ? `<div title="odkiaľ sú čísla">${esc(s.src)}</div>` : ""}</td>
      <td><button type="button" class="ghost small" data-cat-open="${esc(p.strategy)}" data-cat-profile="${esc(p.name)}">Otestovať</button></td>
    </tr>`;
  }).join("") || '<tr><td colspan="7" class="muted">V tejto skupine nie je žiadny profil.</td></tr>';
  $("#cat-drawer").hidden = false;
}

/** Otvorí Nový beh so stratégiou (a profilom) — to isté, čo ručný výber vo formulári. */
async function catalogOpen(key, profile) {
  showView("new");
  const ss = $("#strategy");
  if (ss.value !== key) { ss.value = key; await ss.onchange(); }
  if (profile) { $("#profile").value = profile; await loadProfile(profile); }
}

async function loadCatalog(force = false) {
  if (cat.data && !force) { renderCatalog(); return; }
  $("#cat-grid").innerHTML = '<div class="muted">Načítavam stratégie, profily a históriu…</div>';
  try {
    // nasadenia naživo sú z hubu — bez hubu ostane katalóg bez nich
    const [c, deps] = await Promise.all([api("/api/catalog"), api("/api/live/deployments").catch(() => [])]);
    cat.data = c.strategies;
    cat.deployments = Array.isArray(deps) ? deps : [];
    renderCatalog();
  } catch (e) {
    $("#cat-grid").innerHTML = `<div class="error">Katalóg sa nepodarilo načítať: ${esc(e.message)}</div>`;
  }
}

function initCatalog() {
  const view = $("#view-catalog");
  $("#cat-search").addEventListener("input", e => { cat.query = e.target.value; renderCatalog(); });
  $("#cat-sort").onchange = e => { cat.sort = e.target.value; renderCatalog(); };
  $("#cat-only-smernica").onchange = e => { cat.onlySmernica = e.target.checked; renderCatalog(); };
  $("#cat-refresh").onclick = () => loadCatalog(true);
  const onClick = e => {
    const t = e.target.closest("button");
    // klik mimo tlačidla (a mimo odkazu či výberu textu) kamkoľvek na kartu otvorí hodnotenie
    if (!t) {
      const card = e.target.closest(".cat-card");
      if (card && !e.target.closest("a, #cat-drawer") && !String(window.getSelection?.() || "")) strategyReportOpen(card.dataset.key);
      return;
    }
    if (t.dataset.catMarket !== undefined) { cat.market = t.dataset.catMarket; renderCatalog(); }
    else if (t.dataset.catType !== undefined) { cat.type = t.dataset.catType; renderCatalog(); }
    else if (t.dataset.catState !== undefined) { cat.state = t.dataset.catState; renderCatalog(); }
    else if (t.dataset.catReport) { strategyReportOpen(t.dataset.catReport); }
    else if (t.dataset.catDrawer) { cat.drawer = t.dataset.catDrawer; cat.tab = "all"; renderCatDrawer(); }
    else if (t.dataset.catTab) { cat.tab = t.dataset.catTab; renderCatDrawer(); }
    else if (t.dataset.catRun) { showView("history"); openRun(t.dataset.catRun); }
    else if (t.dataset.catExplain) { explainerOpen(t.dataset.catExplain); }
    else if (t.dataset.catOpen) { $("#cat-drawer").hidden = true; catalogOpen(t.dataset.catOpen, t.dataset.catProfile || ""); }
  };
  // panel profilov je vnútri karty, takže jeho tlačidlá obslúži ten istý poslucháč
  view.addEventListener("click", onClick);
  $("#cat-drawer").addEventListener("click", e => { if (e.target.id === "cat-drawer") $("#cat-drawer").hidden = true; });
  $("#cat-drawer-close").onclick = () => { $("#cat-drawer").hidden = true; };
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && !$("#cat-drawer").hidden) $("#cat-drawer").hidden = true;
    // „/" skočí do hľadania, keď je katalóg otvorený a píše sa mimo poľa
    if (e.key === "/" && !view.hidden && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
      e.preventDefault(); $("#cat-search").focus();
    }
  });
}
