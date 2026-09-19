/* TradeBot Backtester — Monte Carlo v detaile behu. */
"use strict";

// --------------------------------------------------------------------------- //
// Monte Carlo — aký široký je interval okolo nameraného čísla
//
// Bootstrap obchodov behu; ráta server (/api/runs/<id>/montecarlo, tester/montecarlo.py).
// Až po rozbalení sekcie: pri behu s tisíckami obchodov to trvá jednotky sekúnd.
// --------------------------------------------------------------------------- //

const mc = { key: null, busy: false, lastBe: null, lastDd: null, lastFeePct: null };

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
  mc.lastBe = be; mc.lastDd = dd; mc.lastFeePct = r.fee_pct;
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

/** Šablóna Plotly grafu podľa aktuálnej témy — pozadie je vždy priehľadné (karta pod
 *  grafom je už tokenizovaná v CSS), len mriežka/písmo/hover potrebujú tmavý variant. */
function plotlyTemplate() { return isDarkTheme() ? "plotly_dark" : "plotly_white"; }
function chartGridColor() { return isDarkTheme() ? "#30454d" : "#f0f1f3"; }

function histLayout(title, suffix, extra) {
  return Object.assign({
    height: 280, margin: { l: 48, r: 16, t: 18, b: 40 }, template: plotlyTemplate(), bargap: 0.02,
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
  lastEquityChart = { series, res };
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
    height: 460, margin: { l: 10, r: 56, t: 10, b: 30 }, template: plotlyTemplate(), hovermode: "x unified",
    legend: { orientation: "h", yanchor: "bottom", y: 1.0, x: 0 }, bargap: 0.2,
    yaxis: { ticksuffix: " %", range: [lo, hi], side: "right" },
    yaxis2: { overlaying: "y", range: [lo / scale, hi / scale], showgrid: false, showticklabels: false },
    xaxis: { showgrid: false },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  }, { displaylogo: false, responsive: true });
}
