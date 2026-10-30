/* TradeBot Backtester — karta Stratégie: katalóg stratégií s profilmi a najlepším behom.
 * Dáta z /api/catalog (stratégia → profily po skupinách + najlepší beh z histórie). C# porty
 * (`tksnet`, `tksneteod`) sa zlučujú do karty predlohy (`baseStrategyKey`), trh a typ je
 * `strategyClass` zo settings.js — ten istý, ktorý triedi výber stratégie vo formulári. */
"use strict";

const cat = { data: null, deployments: [], market: "", type: "", sort: "score", query: "", onlySmernica: false,
  onlyLive: false, drawer: null, tab: "all" };

const CAT_GROUPS = { smernica: "prešiel smernicou", repo: "repozitár", user: "vlastný" };
const CAT_GROUP_ORDER = { smernica: 0, repo: 1, user: 2 };

/** Zisk na jednotku drawdownu — to isté poradie, akým backend vyberá najlepší beh. */
const catScore = b => b ? (b.pnl_pct || 0) / Math.max(b.max_drawdown_pct || 0, 1) : -Infinity;
const catNum = (v, d = 1) => v === null || v === undefined || Number.isNaN(v) ? "—"
  : Number(v).toLocaleString("sk-SK", { minimumFractionDigits: d, maximumFractionDigits: d });
const catSigned = (v, d = 1) => v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${catNum(v, d)}`;

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
    const deployed = cat.deployments.filter(d => d.active && memberKeys.has(d.strategy));
    const deployedProfiles = new Set(deployed.map(d => d.profile));
    for (const p of profiles) p.deployed = deployed.filter(d => d.profile === p.name && d.strategy === p.strategy).length;
    return {
      deployed, deployedProfiles,
      key: f.key, title: head.title, ports, profiles, best, counts, market, type,
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

function catCard(f) {
  const b = f.best, n = f.profiles.length;
  const seg = g => n ? (f.counts[g] / n * 100).toFixed(1) : 0;
  // jeden profil — naj: nasadený naživo, potom zo smernice, potom s najlepším behom (zisk / DD)
  const rank = p => [p.deployed > 0, p.group === "smernica", !!p.best_run,
    p.group === "smernica" ? (p.claimed?.pf ?? 0) : catScore(p.best_run)];
  const better = (x, y) => { const a = rank(x), b = rank(y); for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return b[i] > a[i] ? 1 : -1; return 0; };
  const top = [...f.profiles].sort(better).slice(0, 1);
  const kpi = (label, val, cls = "") => `<div class="cat-kpi"><span>${label}</span><b class="${cls}">${val}</b></div>`;
  const badges = [
    f.live ? '<span class="cat-badge live" title="má C# port — beží v NinjaTrader 8 a MetaTrader 5">LIVE · C#</span>' : "",
    f.deployed.length ? `<span class="cat-badge run" title="aktívne nasadenia na účtoch (karta Live)">NAŽIVO · ${f.deployed.length}</span>` : "",
    f.isNew ? '<span class="cat-badge new">nová</span>' : "",
  ].join("");
  const ports = f.ports.length ? `<div class="cat-ports small muted">C# porty: ${f.ports.map(p =>
    `<button type="button" class="linkish" data-cat-open="${esc(p.key)}">${esc(p.key)}</button>`).join(", ")}</div>` : "";
  return `<article class="cat-card card" data-key="${esc(f.key)}">
    <div class="cat-head">
      <div><h3 class="cat-title">${esc(f.title)}</h3>
        <div class="cat-tags"><span class="chip">${esc(f.market)}</span>${f.type ? `<span class="chip">${esc(f.type)}</span>` : ""}${badges}</div></div>
      <code class="muted small">${esc(f.key)}</code>
    </div>
    ${b ? `${catSpark(b.equity)}
    <div class="cat-best small muted">najlepší beh: ${esc(b.pair || "")} ${esc(b.timeframe || "")} · ${esc(b.timerange || "")}${b.strategy !== f.key ? ` · ${esc(b.strategy)}` : ""}</div>
    <div class="cat-kpis">
      ${kpi("Zisk", `${catSigned(b.pnl_pct)} %`, (b.pnl_pct || 0) >= 0 ? "pos" : "neg")}
      ${kpi("PF", catNum(b.profit_factor, 2))}
      ${kpi("RR", b.rr != null ? catNum(b.rr, 2) : "—")}
      ${kpi("Win", `${catNum(b.winrate)} %`)}
      ${kpi("DD", `${catNum(b.max_drawdown_pct)} %`)}
      ${kpi("BE", b.break_even_pct != null ? `${catNum(b.break_even_pct, 4)} %` : "—")}
    </div>` : `<div class="cat-nobest muted small">Žiadny beh v histórii neprešiel sitom (aspoň 40 obchodov, PF &gt; 1, DD pod 35 %).
      Behov spolu: ${f.runs}.</div>`}
    <section class="cat-prof">
      <div class="cat-prof-head"><b>${n} ${n === 1 ? "profil" : n < 5 && n > 0 ? "profily" : "profilov"}</b>
        <span class="small muted">${f.counts.smernica} smernica · ${f.counts.repo} repo · ${f.counts.user} vlastné</span></div>
      <div class="cat-bar" aria-hidden="true"><i class="g-smernica" style="width:${seg("smernica")}%"></i><i class="g-repo" style="width:${seg("repo")}%"></i><i class="g-user" style="width:${seg("user")}%"></i></div>
      <ul class="cat-top">${top.map(p => { const s = catProfileStats(p); return `<li>
        <span class="small muted">naj</span><span class="cat-dot g-${p.group}" title="${CAT_GROUPS[p.group]}"></span>
        <button type="button" class="linkish cat-pname" data-cat-open="${esc(p.strategy)}" data-cat-profile="${esc(p.name)}" title="${esc(p.name)} — otvoriť v Novom behu">${esc(catProfileName(p))}</button>
        ${p.deployed ? '<span class="cat-badge run" title="tento profil beží naživo">naživo</span>' : ""}
        <span class="small muted num">${s ? `PF ${catNum(s.pf, 2)} · WR ${catNum(s.wr, 0)} %` : "bez behu"}</span></li>`; }).join("") || '<li class="muted small">žiadny profil — len Pine defaulty</li>'}</ul>
    </section>
    ${ports}
    <div class="cat-actions">
      <button type="button" class="ghost small" data-cat-drawer="${esc(f.key)}"${n ? "" : " disabled"}>Profily (${n})</button>
      ${b ? `<button type="button" class="ghost small" data-cat-run="${esc(b.id)}" title="detail najlepšieho behu v Histórii">Najlepší beh</button>` : ""}
      <span class="spacer"></span>
      <button type="button" class="primary small" data-cat-open="${esc(f.key)}">Otestovať</button>
    </div>
  </article>`;
}

function catFiltered() {
  const q = cat.query.trim().toLowerCase();
  const list = catFamilies(cat.data).filter(f =>
    (!cat.market || f.market === cat.market)
    && (!cat.type || (cat.type === "LIVE" ? f.live : f.type === cat.type))
    && (!cat.onlySmernica || f.counts.smernica > 0)
    && (!cat.onlyLive || f.deployed.length > 0)
    && (!q || [f.key, f.title, ...f.ports.map(p => p.key), ...f.profiles.map(p => p.name + " " + p.title)]
      .some(s => String(s).toLowerCase().includes(q))));
  const val = (f, k) => f.best && f.best[k] != null ? f.best[k] : -Infinity;
  const by = {
    score: (a, b) => catScore(b.best) - catScore(a.best),
    pnl: (a, b) => val(b, "pnl_pct") - val(a, "pnl_pct"),
    rr: (a, b) => val(b, "rr") - val(a, "rr"),
    live: (a, b) => b.deployed.length - a.deployed.length || (b.live - a.live) || catScore(b.best) - catScore(a.best),
    profiles: (a, b) => b.profiles.length - a.profiles.length,
    smernica: (a, b) => b.counts.smernica - a.counts.smernica || catScore(b.best) - catScore(a.best),
    recent: (a, b) => b.lastRun.localeCompare(a.lastRun),
    title: (a, b) => a.title.localeCompare(b.title, "sk"),
  }[cat.sort];
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
  const list = catFiltered();
  // stratégie bez dobrého behu a bez profilu zo smernice idú do zbaleného bloku na koniec
  const weak = f => !f.best && !f.counts.smernica;
  const shown = list.filter(f => !weak(f)), rest = list.filter(weak);
  const nProf = all.reduce((s, f) => s + f.profiles.length, 0);
  const nLive = all.filter(f => f.deployed.length).length;
  $("#cat-summary").textContent = `${list.length} z ${all.length} stratégií · ${nProf} profilov · ${all.filter(f => f.live).length} s C# portom`
    + (nLive ? ` · ${nLive} naživo` : "");
  $("#cat-grid").innerHTML = shown.map(catCard).join("")
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
  $("#cat-only-live").onchange = e => { cat.onlyLive = e.target.checked; renderCatalog(); };
  $("#cat-refresh").onclick = () => loadCatalog(true);
  const onClick = e => {
    const t = e.target.closest("button");
    if (!t) return;
    if (t.dataset.catMarket !== undefined) { cat.market = t.dataset.catMarket; renderCatalog(); }
    else if (t.dataset.catType !== undefined) { cat.type = t.dataset.catType; renderCatalog(); }
    else if (t.dataset.catDrawer) { cat.drawer = t.dataset.catDrawer; cat.tab = "all"; renderCatDrawer(); }
    else if (t.dataset.catTab) { cat.tab = t.dataset.catTab; renderCatDrawer(); }
    else if (t.dataset.catRun) { showView("history"); openRun(t.dataset.catRun); }
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
