/* TradeBot Backtester — okno „Hodnotenie stratégie" z karty Stratégie.
 * Dáta z /api/catalog/<kľúč>/report?profile=… (catalog_report.py): výkon z behov piatich
 * referenčných okien (krivka, roky, mesiace, okná), analytika a posudok z ANALYTIKA.md,
 * parametre profilu odlišné od defaultov, posledné behy a dokumenty. Profil sa prepína
 * v okne — rodina stratégie (predloha + C# porty) má profily spolu, ako karta. */
"use strict";

const srep = { family: null, key: "", profile: "", data: null, tab: "perf", cache: new Map() };

const SREP_TABS = [["perf", "Výkon"], ["analytika", "Analytika"], ["posudok", "Posudok"],
  ["setup", "Nastavenie"], ["runs", "Behy a dokumenty"], ["explain", "Ako funguje"]];
const SREP_MONTHS = ["jan", "feb", "mar", "apr", "máj", "jún", "júl", "aug", "sep", "okt", "nov", "dec"];

// ------------------------------------------------------------------ Markdown (ANALYTIKA, posudok, merania)

function srepInline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])_(\S.*?)_(?=[\s).,;:]|$)/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<span class="srep-ref" title="$2">$1</span>');
}

/** Markdown generovaných dokumentov: nadpisy, odrážky, číslovanie, tabuľky, citácie, bloky kódu. */
function srepMd(md) {
  const out = [], lines = String(md || "").split("\n");
  let list = null, para = [], table = null, code = null;
  const flushPara = () => { if (para.length) { out.push(`<p>${srepInline(para.join(" "))}</p>`); para = []; } };
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  const flushTable = () => {
    if (!table) return;
    const cells = r => r.replace(/^\||\|$/g, "").split("|").map(c => c.trim());
    const [head, ...body] = table.filter(r => !/^\|?\s*:?-{2,}/.test(r));
    const num = c => /^[+\-−]?[\d\s.,]+ ?%?$/.test(c);
    out.push(`<div class="scroll"><table class="srep-md-table"><thead><tr>${cells(head).map(c => `<th>${srepInline(c)}</th>`).join("")}</tr></thead><tbody>${
      body.map(r => `<tr>${cells(r).map(c => `<td${num(c) ? ' class="num"' : ""}>${srepInline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
    table = null;
  };
  for (const raw of lines) {
    const line = raw.replace(/\s+$/, "");
    if (code !== null) {
      if (/^```/.test(line)) { out.push(`<pre class="srep-code">${esc(code.join("\n"))}</pre>`); code = null; } else code.push(raw);
      continue;
    }
    let m;
    if (/^```/.test(line)) { flushPara(); closeList(); flushTable(); code = []; continue; }
    if (/^<!--/.test(line)) continue;
    if (/^\|/.test(line)) { flushPara(); closeList(); (table = table || []).push(line); continue; }
    flushTable();
    if (!line.trim()) { flushPara(); closeList(); continue; }
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) {
      flushPara(); closeList();
      const lvl = Math.min(m[1].length + 1, 5);
      out.push(`<h${lvl}>${srepInline(m[2])}</h${lvl}>`);
    } else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) {
      flushPara();
      if (list !== "ul") { closeList(); out.push("<ul>"); list = "ul"; }
      out.push(`<li>${srepInline(m[1])}</li>`);
    } else if ((m = line.match(/^\s*(\d+)\.\s+(.*)$/))) {
      flushPara();
      if (list !== "ol") { closeList(); out.push(`<ol start="${m[1]}">`); list = "ol"; }
      out.push(`<li>${srepInline(m[2])}</li>`);
    } else if ((m = line.match(/^>\s?(.*)$/))) {
      flushPara(); closeList();
      out.push(`<p class="xp-lead">${srepInline(m[1])}</p>`);
    } else if (list && /^\s{2,}\S/.test(raw)) {
      out[out.length - 1] = out[out.length - 1].replace(/<\/li>$/, " " + srepInline(line.trim()) + "</li>");
    } else {
      closeList(); para.push(line.trim());
    }
  }
  flushPara(); closeList(); flushTable();
  if (code !== null) out.push(`<pre class="srep-code">${esc(code.join("\n"))}</pre>`);
  return out.join("\n");
}

// ------------------------------------------------------------------ výkon

const srepPct = (v, d = 2) => v == null ? "—" : `${catSigned(v, d)} %`;
const srepCls = v => v == null ? "" : v > 0 ? "pos" : v < 0 ? "neg" : "";

function srepKpis(s, perf) {
  const k = (label, val, cls = "", tip = "") => `<div class="cat-kpi"${tip ? ` title="${esc(tip)}"` : ""}><span>${label}</span><b class="${cls}">${val}</b></div>`;
  return `<div class="srep-kpis">
    ${k("Zisk spolu", srepPct(s.pnl_pct), srepCls(s.pnl_pct), "súčet ziskov obchodov v % účtu (bez zloženého úroku)")}
    ${k("Zisk / rok", srepPct(s.pnl_year), srepCls(s.pnl_year))}
    ${k("PF", catNum(s.profit_factor, 2), "", "hrubý zisk / hrubá strata")}
    ${k("RR", catNum(s.rr, 2), "", "priemerný zisk / priemerná strata")}
    ${s.r_n ? k("Ø zisk zatvára", s.r_win != null ? `${catSigned(s.r_win, 2)} R` : "—", "pos", `kde ziskové obchody v priemere zatvoria — v násobkoch rizika (vzdialenosti stopu); ${s.r_n} obchodov so stopom`) : ""}
    ${s.r_n ? k("Ø strata zatvára", s.r_loss != null ? `${catSigned(s.r_loss, 2)} R` : "—", "neg", "kde stratové obchody v priemere zatvoria; −1 R = plný stop") : ""}
    ${s.r_n ? k("Ø R / obchod", `${catSigned(s.r_avg, 3)} R`, srepCls(s.r_avg), "priemerný výsledok obchodu v R (očakávanie v násobkoch rizika)") : ""}
    ${k("Winrate", `${catNum(s.winrate)} %`)}
    ${k("Max DD", `${catNum(s.max_dd_pct)} %`, "", "najväčší pokles spojenej krivky v % účtu")}
    ${k("Zisk / DD", catNum(s.recovery, 1), "", "recovery factor — zisk spolu / max drawdown")}
    ${k("Obchodov / rok", catNum(s.trades_year, 0), "", `${s.trades} obchodov spolu`)}
    ${k("Očakávanie", srepPct(s.expectancy, 3), srepCls(s.expectancy), "priemerný zisk na obchod")}
    ${perf ? k("Ziskové okná", `${perf.positive_windows} / ${perf.windows.length}`, perf.positive_windows === perf.windows.length ? "pos" : "", "referenčné okná so ziskom") : ""}
    ${k("Séria strát", s.loss_streak ?? "—", "", "najdlhšia séria strát za sebou")}
    ${k("Najhorší obchod", srepPct(s.worst), "neg")}
  </div>`;
}

function srepVerdicts(a) {
  if (!a?.exists || (!a.good?.length && !a.bad?.length)) return "";
  const li = xs => xs.map(x => `<li>${srepInline(x)}</li>`).join("");
  return `<div class="srep-verdicts">
    <div class="srep-good"><h4>V čom je dobrá</h4><ul>${li(a.good || []) || '<li class="muted">—</li>'}</ul></div>
    <div class="srep-bad"><h4>Kde má chyby</h4><ul>${li(a.bad || []) || '<li class="muted">—</li>'}</ul></div>
  </div>`;
}

function srepWindowsTable(perf) {
  const byWin = Object.fromEntries(perf.windows.map(w => [w.timerange, w]));
  return `<div class="scroll"><table class="runs srep-table"><thead><tr><th>Okno</th><th class="num">Obch.</th><th class="num">Zisk</th>
    <th class="num">PF</th><th class="num">RR</th><th class="num">WR</th><th class="num">DD</th><th class="num">Break-even</th><th>Beh</th></tr></thead><tbody>${
    perf.expected_windows.map(t => { const w = byWin[t]; return w ? `<tr data-srep-run="${esc(w.id)}" title="detail behu v Histórii">
      <td>${esc(t)}</td><td class="num">${w.trades ?? "—"}</td><td class="num ${srepCls(w.pnl_pct)}">${srepPct(w.pnl_pct)}</td>
      <td class="num">${catNum(w.profit_factor, 2)}</td><td class="num">${catNum(w.rr, 2)}</td><td class="num">${catNum(w.winrate)} %</td>
      <td class="num">${catNum(w.max_drawdown_pct)} %</td><td class="num">${w.break_even_pct != null ? `${catNum(w.break_even_pct, 4)} %` : "—"}</td>
      <td><code class="small">${esc(w.id)}</code></td></tr>`
      : `<tr class="muted"><td>${esc(t)}</td><td colspan="8">beh tohto okna v histórii nie je</td></tr>`; }).join("")}</tbody></table></div>`;
}

function srepYearsTable(years) {
  if (!years?.length) return "";
  return `<div class="scroll"><table class="runs srep-table"><thead><tr><th>Rok</th><th class="num">Obch.</th><th class="num">Zisk</th>
    <th class="num">PF</th><th class="num">RR</th><th class="num">WR</th><th class="num">DD</th></tr></thead><tbody>${
    years.map(y => `<tr><td>${esc(y.year)}</td><td class="num">${y.trades}</td><td class="num ${srepCls(y.pnl_pct)}">${srepPct(y.pnl_pct)}</td>
      <td class="num">${catNum(y.profit_factor, 2)}</td><td class="num">${catNum(y.rr, 2)}</td><td class="num">${catNum(y.winrate)} %</td>
      <td class="num">${catNum(y.max_dd_pct)} %</td></tr>`).join("")}</tbody></table></div>`;
}

/** Mesačné výnosy rok × mesiac; sýtosť farby podľa najväčšieho mesiaca. */
function srepMonths(months) {
  const years = Object.keys(months || {}).sort();
  if (!years.length) return "";
  const vals = years.flatMap(y => Object.values(months[y]));
  const top = Math.max(...vals.map(Math.abs), 0.01);
  const cell = v => {
    if (v == null) return '<td class="srep-m empty"></td>';
    const a = (0.12 + 0.68 * Math.min(Math.abs(v) / top, 1)).toFixed(2);
    return `<td class="srep-m num" style="--a:${a}" data-sign="${v >= 0 ? "pos" : "neg"}" title="${catSigned(v, 2)} %">${catNum(v, 1)}</td>`;
  };
  const sum = y => Object.values(months[y]).reduce((s, v) => s + v, 0);
  const pos = vals.filter(v => v > 0).length;
  return `<div class="scroll"><table class="srep-months"><thead><tr><th></th>${SREP_MONTHS.map(m => `<th>${m}</th>`).join("")}<th>rok</th></tr></thead><tbody>${
    years.map(y => `<tr><th>${y}</th>${Array.from({ length: 12 }, (_, i) => cell(months[y][String(i + 1).padStart(2, "0")])).join("")}
      <td class="num srep-ysum ${srepCls(sum(y))}">${catSigned(sum(y), 1)}</td></tr>`).join("")}</tbody></table></div>
    <p class="small muted">Ziskových mesiacov ${pos} z ${vals.length} (${catNum(vals.length ? pos / vals.length * 100 : 0, 0)} %). Hodnoty sú % účtu.</p>`;
}

function srepCharts(perf) {
  const el = $("#srep-eq");
  if (!el || typeof Plotly === "undefined" || !perf.curve?.length) return;
  const x = perf.curve.map(p => p[0]), y = perf.curve.map(p => p[1]);
  let peak = -Infinity;
  const dd = y.map(v => { peak = Math.max(peak, v); return +(v - peak).toFixed(3); });
  const pos = getComputedStyle(document.documentElement).getPropertyValue("--pos").trim() || "#089981";
  const neg = getComputedStyle(document.documentElement).getPropertyValue("--neg").trim() || "#f23645";
  const base = { template: plotlyTemplate(), paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", showlegend: false };
  const cfg = { displaylogo: false, responsive: true };
  // hranice referenčných okien — krivka je z nich poskladaná
  const shapes = (perf.windows || []).slice(1).map(w => {
    const t = `${w.timerange.slice(0, 4)}-${w.timerange.slice(4, 6)}-${w.timerange.slice(6, 8)}`;
    return { type: "line", xref: "x", yref: "paper", y0: 0, y1: 1, x0: t, x1: t, line: { color: chartGridColor(), width: 1, dash: "dot" } };
  });
  Plotly.newPlot(el, [
    { type: "scatter", mode: "lines", x, y, line: { color: pos, width: 2 }, fill: "tozeroy", fillcolor: pos + "22", name: "zisk", hovertemplate: "%{x|%d. %m. %Y}<br>%{y:.2f} %<extra></extra>" },
    { type: "scatter", mode: "lines", x, y: dd, yaxis: "y2", line: { color: neg, width: 1 }, fill: "tozeroy", fillcolor: neg + "33", name: "drawdown", hovertemplate: "DD %{y:.2f} %<extra></extra>" },
  ], { ...base, height: 330, margin: { l: 10, r: 52, t: 8, b: 28 }, shapes, hovermode: "x unified",
    xaxis: { showgrid: false }, yaxis: { domain: [0.3, 1], side: "right", ticksuffix: " %", gridcolor: chartGridColor() },
    yaxis2: { domain: [0, 0.24], side: "right", ticksuffix: " %", gridcolor: chartGridColor() } }, cfg);
  const wb = $("#srep-win-bars");
  if (wb && perf.windows?.length) {
    const wx = perf.windows.map(w => w.timerange.replace(/^(\d{4})\d{4}-(\d{4})\d{4}$/, "$1/$2"));
    Plotly.newPlot(wb, [
      { type: "bar", x: wx, y: perf.windows.map(w => w.pnl_pct), marker: { color: perf.windows.map(w => (w.pnl_pct || 0) >= 0 ? pos : neg) },
        text: perf.windows.map(w => `${catSigned(w.pnl_pct, 1)} %`), textposition: "outside", cliponaxis: false, hovertemplate: "%{x}: %{y:.2f} %<extra></extra>" },
    ], { ...base, height: 210, margin: { l: 10, r: 40, t: 18, b: 28 }, yaxis: { side: "right", ticksuffix: " %", gridcolor: chartGridColor(), zeroline: true },
      xaxis: { type: "category" } }, cfg);
  }
}

function srepPerf(d) {
  const perf = d.performance, single = d.single, p = d.profile;
  const claimed = p?.claimed && Object.keys(p.claimed).length ? `<p class="small muted srep-claimed">Posudok smernice (z názvu profilu):
    ${[p.claimed.pf != null && `PF ${catNum(p.claimed.pf, 2)}`, p.claimed.winrate != null && `WR ${catNum(p.claimed.winrate, 0)} %`,
      p.claimed.trades_year != null && `${catNum(p.claimed.trades_year, 0)} obch/rok`, p.claimed.max_dd_usd != null && `max DD ${catNum(p.claimed.max_dd_usd, 0)} $`,
      p.claimed.pf_last_year != null && `posl. rok PF ${catNum(p.claimed.pf_last_year, 2)}`].filter(Boolean).join(" · ")}</p>` : "";
  const verd = d.analytika?.matches_profile ? srepVerdicts(d.analytika) : "";
  if (perf) {
    const src = [perf.checkup_id ? `checkup <code>${esc(perf.checkup_id)}</code>` : "najnovšie behy profilu po oknách",
      `${esc(perf.pair || "")} ${esc(perf.timeframe || "")}`, perf.engine && esc(perf.engine),
      perf.fee != null && `poplatok ${catNum(perf.fee * 100, 4)} %/stranu`, perf.wallet && `účet ${catNum(perf.wallet, 0)}`].filter(Boolean).join(" · ");
    const nw = perf.windows.length, okien = nw === perf.expected_windows.length ? "piatich referenčných okien"
      : `${nw} z ${perf.expected_windows.length} referenčných okien (ostatné v histórii nie sú)`;
    return `${claimed}<p class="small muted">Spojené obchody z ${okien} (${esc(perf.stats.first?.slice(0, 10) || "")} – ${esc(perf.stats.last?.slice(0, 10) || "")}) · ${src}</p>
      ${srepKpis(perf.stats, perf)}
      ${verd}
      <h4>Krivka zisku a drawdown</h4><div id="srep-eq" class="srep-chart"></div>
      <div class="srep-two">
        <section><h4>Referenčné okná</h4><div id="srep-win-bars" class="srep-chart"></div></section>
        <section><h4>Po rokoch</h4>${srepYearsTable(perf.years)}</section>
      </div>
      ${srepWindowsTable(perf)}
      <h4>Po mesiacoch</h4>${srepMonths(perf.months)}`;
  }
  if (single?.stats && Object.keys(single.stats).length) {
    return `${claimed}<p class="notice small">Behy tohto profilu na piatich referenčných oknách v histórii nie sú — čísla sú z posledného behu
      <button type="button" class="linkish" data-srep-run="${esc(single.id)}">${esc(single.id)}</button> (${esc(single.pair || "")} ${esc(single.timeframe || "")} · ${esc(single.timerange || "")}).
      Celé hodnotenie dá <code>cli checkup --strategy ${esc(d.key)}${p ? ` --profile ${esc(p.name)}` : ""}</code>.</p>
      ${srepKpis(single.stats, null)}${verd}
      <h4>Krivka zisku a drawdown</h4><div id="srep-eq" class="srep-chart"></div>
      <h4>Po rokoch</h4>${srepYearsTable(single.years)}<h4>Po mesiacoch</h4>${srepMonths(single.months)}`;
  }
  return `${claimed}<p class="notice">K tomuto ${p ? "profilu" : "výberu"} nie je v histórii žiadny hotový beh. Výkon sa zmeria
    behmi na piatich oknách: <code>python -m tester.webapp.cli checkup --strategy ${esc(d.key)}${p ? ` --profile ${esc(p.name)}` : ""}</code>.</p>${verd}`;
}

// ------------------------------------------------------------------ ostatné záložky

function srepAnalytika(d) {
  const a = d.analytika;
  if (!a?.exists) return `<p class="notice">Stratégia <code>${esc(d.key)}</code> zatiaľ nemá základnú analytiku (ANALYTIKA.md).
    Vyrobí ju <code>python -m tester.webapp.cli checkup --strategy ${esc(d.key)} …</code>.</p>`;
  const warn = a.matches_profile ? "" : `<p class="notice small">Analytika je zmeraná na profile <code>${esc(a.profile || "?")}</code>,
    nie na zvolenom${d.profile ? ` <code>${esc(d.profile.name)}</code>` : ""} — čísla nižšie platia pre ten profil.</p>`;
  return `${warn}<p class="small muted">${srepInline(a.measured || "")}</p>
    ${a.character ? `<p class="srep-char"><span class="muted small">Charakter</span> <b>${esc(a.character)}</b></p>` : ""}
    ${a.matches_profile ? "" : srepVerdicts(a)}
    <div class="srep-md">${(a.sections || []).map(s => `<details class="srep-sec"${/Charakter|náhody|Slabne|Interval/.test(s.title) ? " open" : ""}>
      <summary>${esc(s.title)}</summary>${srepMd(s.markdown)}</details>`).join("")}</div>`;
}

function srepPosudok(d) {
  const a = d.analytika;
  if (!a?.exists) return '<p class="notice">Bez analytiky nie je ani posudok — najprv <code>cli checkup</code>.</p>';
  const warn = a.matches_profile ? "" : `<p class="notice small">Posudok patrí profilu <code>${esc(a.profile || "?")}</code>.</p>`;
  return a.posudok ? `${warn}<div class="srep-md srep-posudok">${srepMd(a.posudok)}</div>`
    : `${warn}<p class="notice">Posudok (AI) k analytike ešte nie je napísaný — šesť otázok v ANALYTIKA.md doplní AI
      (<a href="#" data-srep-goto="analytics">karta Analytika</a> alebo Claude nad dokumentom).</p>`;
}

function srepSetup(d) {
  const p = d.profile, f = srep.family;
  const { market, type } = f;          // trh a typ rodiny — C# port by mal typ „LIVE"
  const deps = (cat.deployments || []).filter(x => x.strategy === d.key && (!p || x.profile === p.name))
    .sort((a, b) => catDepRunning(b) - catDepRunning(a));
  const chips = [market, type, d.csharp && "C# jadro · NinjaTrader 8 / MetaTrader 5"].filter(Boolean)
    .map(c => `<span class="chip">${esc(c)}</span>`).join("");
  const typeNote = { "TRENDOVÉ": "Trendová — zarába na pokračovaní pohybu: nižší winrate a dlhé série strát sú normálne, rozhoduje RR.",
    "SKALPOVACIE": "Skalpovacia — veľa krátkych obchodov: rozhoduje poplatok a sklz, break-even musí byť jasne nad nimi.",
    "RANGEOVÉ": "Rangeová — obchoduje návrat do rozsahu: vysoký winrate, malé RR, nebezpečný je silný trend." }[type] || "";
  const params = p?.params || [];
  const groups = [...new Set(params.map(x => x.group || ""))];
  const fmt = v => typeof v === "boolean" ? (v ? "áno" : "nie") : esc(String(v ?? "—"));
  return `<div class="srep-tags">${chips}</div>${typeNote ? `<p class="small">${esc(typeNote)} <span class="muted">(docs/TYPY_STRATEGII.md)</span></p>` : ""}
    ${f && f.ports.length ? `<p class="small muted">Rodina: <code>${esc(f.key)}</code> + C# porty ${f.ports.map(x => `<code>${esc(x.key)}</code>`).join(", ")}.</p>` : ""}
    ${p ? `<table class="srep-kv">
      <tr><th>Profil</th><td><b>${esc(catProfileName(p))}</b> <code class="small">${esc(p.name)}</code></td></tr>
      <tr><th>Skupina</th><td>${esc(CAT_GROUPS[p.group] || p.group)}</td></tr>
      <tr><th>Trh</th><td>${esc(p.pair || "—")} ${esc(p.timeframe || "")}</td></tr>
      ${p.created ? `<tr><th>Vznikol</th><td>${esc(p.created.slice(0, 10))}</td></tr>` : ""}
      ${p.title ? `<tr><th>Popis</th><td class="small">${esc(p.title)}</td></tr>` : ""}
      <tr><th>Naživo</th><td>${deps.length ? deps.map(x => `<span class="cat-badge ${catDepRunning(x) ? "on" : "off"}" title="${esc(catDepLine(x))}">${catDepRunning(x) ? "● beží" : "■ zastavená"} · ${esc(x.account || x.akey || "účet")}</span>`).join(" ") : '<span class="muted">nenasadený</span>'}</td></tr>
    </table>
    <h4>Parametre odlišné od defaultov stratégie (${params.length})</h4>
    ${params.length ? `<div class="scroll"><table class="runs srep-table"><thead><tr><th>Parameter</th><th>Hodnota</th><th>Default</th></tr></thead><tbody>${
      groups.map(g => `${g ? `<tr class="srep-group"><td colspan="3">${esc(g)}</td></tr>` : ""}${params.filter(x => (x.group || "") === g).map(x =>
        `<tr><td>${esc(x.title || x.name)}<div class="small muted">${esc(x.name)}</div></td><td><b>${fmt(x.value)}</b></td><td class="muted">${fmt(x.default)}</td></tr>`).join("")}`).join("")}
      </tbody></table></div>` : '<p class="muted small">Profil nemení nič — beží s defaultmi z Pine.</p>'}`
    : '<p class="muted">Bez profilu — Pine defaulty stratégie.</p>'}
    <div class="srep-actions"><button type="button" class="primary small" data-srep-test>Otestovať v Novom behu</button></div>`;
}

function srepRuns(d) {
  const r = d.runs;
  const rows = r.recent.map(x => `<tr data-srep-run="${esc(x.id)}" title="${esc(x.note || "detail v Histórii")}">
    <td><code class="small">${esc(x.id)}</code></td><td>${esc(x.pair || "")} ${esc(x.timeframe || "")}</td><td>${esc(x.timerange || "")}</td>
    <td class="num">${x.trades ?? "—"}</td><td class="num ${srepCls(x.pnl_pct)}">${srepPct(x.pnl_pct)}</td><td class="num">${catNum(x.profit_factor, 2)}</td>
    <td class="num">${catNum(x.winrate)} %</td><td class="num">${catNum(x.max_drawdown_pct)} %</td><td class="small muted srep-note">${esc(x.note)}</td></tr>`).join("");
  const docs = d.docs.map(x => `<li><button type="button" class="linkish" data-srep-doc="${esc(x.id)}">${esc(x.title)}</button>
    <span class="small muted">· ${esc(x.kind)}</span></li>`).join("");
  return `<p class="small muted">Hotových behov stratégie <code>${esc(d.key)}</code> v histórii: ${r.strategy_total}${d.profile ? `, s týmto profilom ${r.profile_total}` : ""}.</p>
    ${rows ? `<h4>Posledné behy profilu</h4><div class="scroll"><table class="runs srep-table"><thead><tr><th>Beh</th><th>Trh</th><th>Obdobie</th><th class="num">Obch.</th>
      <th class="num">Zisk</th><th class="num">PF</th><th class="num">WR</th><th class="num">DD</th><th>Poznámka</th></tr></thead><tbody>${rows}</tbody></table></div>` : ""}
    <h4>Dokumenty a merania (${d.docs.length})</h4>
    ${docs ? `<ul class="srep-docs">${docs}</ul><div id="srep-doc" class="srep-md"></div>` : '<p class="muted small">K stratégii nie sú ďalšie dokumenty ani merania.</p>'}`;
}

async function srepExplain(d) {
  const body = $("#srep-body");
  if (!d.has_explainer) { body.innerHTML = '<p class="muted">Táto stratégia zatiaľ vysvetlivku nemá.</p>'; return; }
  body.innerHTML = '<p class="muted">Načítavam…</p>';
  try {
    const x = await api(`/api/strategies/${encodeURIComponent(d.key)}/explainer`);
    if (srep.tab === "explain") body.innerHTML = `<div class="xp-body">${explainerHtml(x.markdown || "")}</div>`;
  } catch (e) { body.innerHTML = `<p class="error">Vysvetlivku sa nepodarilo načítať: ${esc(e.message)}</p>`; }
}

// ------------------------------------------------------------------ okno

function srepRenderBody() {
  const d = srep.data, body = $("#srep-body");
  $("#srep-tabs").innerHTML = SREP_TABS.map(([k, t]) =>
    `<button type="button" class="chip-btn${k === srep.tab ? " active" : ""}" data-srep-tab="${k}">${t}</button>`).join("");
  if (!d) return;
  if (srep.tab === "explain") { srepExplain(d); return; }
  body.innerHTML = { perf: srepPerf, analytika: srepAnalytika, posudok: srepPosudok, setup: srepSetup, runs: srepRuns }[srep.tab](d);
  if (srep.tab === "perf") srepCharts(d.performance || d.single || {});
}

function srepRenderHead() {
  const f = srep.family, d = srep.data;
  const [market, type] = strategyClass(f.key);
  const ch = d?.analytika?.character;
  $("#srep-head").innerHTML = `<h2 id="srep-title">${esc(f.title)} <code class="muted small">${esc(srep.key)}</code></h2>
    <div class="cat-tags"><span class="chip">${esc(market)}</span>${type ? `<span class="chip">${esc(type)}</span>` : ""}
      ${catLiveBadges(f)}
      ${ch ? `<span class="chip" title="charakter z analytiky">${esc(ch)}</span>` : ""}</div>
    ${f.lead ? `<p class="cat-lead small">${esc(f.lead)}</p>` : ""}`;
}

function srepProfileOptions() {
  const f = srep.family;
  const members = [f.key, ...f.ports.map(p => p.key)];
  return members.map(k => {
    const ps = f.profiles.filter(p => p.strategy === k).sort(catProfileSort);
    return `<optgroup label="${esc(k === f.key ? k : `${k} (C# port)`)}">
      <option value="${esc(k)}|">— profil analytiky ${esc(k)}</option>
      ${ps.map(p => `<option value="${esc(k)}|${esc(p.name)}">${p.running ? "● " : p.deployed ? "■ " : ""}${esc(catProfileName(p))} · ${esc(CAT_GROUPS[p.group])}</option>`).join("")}</optgroup>`;
  }).join("");
}

async function srepLoad(key, profile) {
  srep.key = key; srep.profile = profile;
  const sel = $("#srep-profile");
  $("#srep-body").innerHTML = '<p class="muted">Skladám hodnotenie z histórie behov a analytiky…</p>';
  const ck = `${key}|${profile}`;
  try {
    const d = srep.cache.get(ck) || await api(`/api/catalog/${encodeURIComponent(key)}/report?profile=${encodeURIComponent(profile)}`);
    srep.cache.set(ck, d);
    if (srep.key !== key || srep.profile !== profile) return;     // medzitým iný výber
    srep.data = d;
    // „profil analytiky" sa rozvinie na konkrétny profil, aby výber ukazoval, čo sa naozaj zobrazuje
    const real = `${key}|${d.profile?.name || ""}`;
    if ([...sel.options].some(o => o.value === real)) sel.value = real; else sel.value = `${key}|`;
    srepRenderHead();
    srepRenderBody();
  } catch (e) {
    $("#srep-body").innerHTML = `<p class="error">Hodnotenie sa nepodarilo načítať: ${esc(e.message)}</p>`;
  }
}

/** Otvorí hodnotenie rodiny stratégie; bez profilu ten, ktorý karta ukazuje ako „naj". */
function strategyReportOpen(familyKey, profile = "", strategy = "") {
  const f = catFamilies(cat.data || []).find(x => x.key === familyKey);
  if (!f) return;
  srep.family = f; srep.data = null; srep.tab = "perf";
  $("#srep-profile").innerHTML = srepProfileOptions();
  srepRenderHead();
  srepRenderBody();
  $("#srep").hidden = false;
  if (!profile) {
    const top = catTopProfile(f);
    if (top) { profile = top.name; strategy = top.strategy; }
  }
  srepLoad(strategy || f.key, profile);
}

function srepClose() {
  $("#srep").hidden = true;
  if (typeof Plotly !== "undefined") for (const id of ["#srep-eq", "#srep-win-bars"]) if ($(id)) Plotly.purge($(id));
}

function initStrategyReport() {
  const box = $("#srep");
  $("#srep-close").onclick = srepClose;
  box.addEventListener("click", async e => {
    if (e.target.id === "srep") { srepClose(); return; }
    const t = e.target.closest("[data-srep-tab],[data-srep-run],[data-srep-doc],[data-srep-test],[data-srep-goto]");
    if (!t) return;
    if (t.dataset.srepTab) { srep.tab = t.dataset.srepTab; srepRenderBody(); }
    else if (t.dataset.srepRun) { srepClose(); showView("history"); openRun(t.dataset.srepRun); }
    else if (t.dataset.srepGoto) { e.preventDefault(); srepClose(); showView(t.dataset.srepGoto); }
    else if (t.dataset.srepTest !== undefined) { srepClose(); catalogOpen(srep.key, srep.data?.profile?.name || ""); }
    else if (t.dataset.srepDoc) {
      const el = $("#srep-doc");
      el.innerHTML = '<p class="muted">Načítavam…</p>';
      try {
        const x = await api(`/api/catalog/${encodeURIComponent(srep.key)}/doc?id=${encodeURIComponent(t.dataset.srepDoc)}`);
        el.innerHTML = srepMd(x.markdown);
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (err) { el.innerHTML = `<p class="error">${esc(err.message)}</p>`; }
    }
  });
  $("#srep-profile").onchange = e => { const [k, p] = e.target.value.split("|"); srepLoad(k, p || ""); };
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !box.hidden) srepClose(); });
}
