/* TradeBot Backtester — Sweep: mriežka behov cez hodnoty parametra. */
"use strict";

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
  const casti = [`hotových ${r.done} z ${r.total ?? (r.done + r.running)}`];
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
    tr.onclick = () => openPoint(tr.dataset.run);
  }
}

/**
 * Bod mriežky, bunka matice, overenie alebo sused víťaza. Do histórie sa neukladajú —
 * v `tester/sweeps/` je len ich výsledok s celým configom. Starý bod, ktorý v histórii
 * ešte je, sa otvorí; ostatné sa po potvrdení prehrajú ako obyčajný beh (s obchodmi
 * a grafom), ktorý už do histórie pribudne.
 */
async function openPoint(id) {
  let det = null;
  try { det = await api(`/api/runs/${id}`); } catch (e) { det = null; }
  if (det && !det.batch) { showView("history"); openRun(id); return; }
  const r = (det && det.record && det.record.result) || {};
  const popis = det ? ` (obchodov ${r.trades ?? "—"}, break-even ${fmt(r.break_even_pct, 4)})` : "";
  if (!confirm(`Bod${popis} nie je v histórii — z mriežky sa ukladá len jeho výsledok. `
    + "Prehrať ho ako obyčajný beh? Pribudne do fronty a potom do histórie s obchodmi a grafom.")) return;
  try {
    const job = await api(`/api/points/${id}/replay`, { method: "POST", body: JSON.stringify({ user: currentUser() || null }) });
    pollQueue();
    showView("history");
    openRun(job.id);
  } catch (e) {
    alert(`Bod sa prehrať nedá: ${e.message}`);
  }
}
