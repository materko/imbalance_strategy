/* TradeBot Backtester — Hyperopt: zadanie, priebeh, výsledok a okolie víťaza. */
"use strict";

/** Hyperopt: jeden beh vo fronte, po ňom overenie na referenčných oknách. */
async function startHyperopt() {
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
      epochs: Number($("#hyper-epochs").value) || 200,
      verify: $("#hyper-verify").checked,
    };
    if (hubChecked()) {
      const job = await api("/api/hub/hyperopts", { method: "POST", body: JSON.stringify({ ...body, ...hubOptions() }) });
      $("#sweep-status").textContent = `hyperopt na hube: ${job.id} · ${job.status}${job.agent ? " · " + job.agent : ""} — sleduj kartu Hub`;
      return;
    }
    const r = await api("/api/hyperopts", { method: "POST", body: JSON.stringify(body) });
    hyper.id = r.id;
    try { localStorage.setItem(hyperKey(), r.id); } catch (e) { /* súkromné okno */ }
    $("#sweep-status").textContent = `${r.epochs} epoch vo fronte · ${r.goal_note}`;
    if (r.warn && r.warn.length) {
      $("#sweep-warn").hidden = false;
      $("#sweep-warn").textContent = r.warn.join(" ");
    }
    pollQueue();
    pollHyper();
    loadSweepHistory();
  } catch (e) {
    $("#sweep-status").textContent = e.message;
  } finally {
    refreshSweep();
  }
}

/** Slovencina pocita inak nez anglictina: 1 parameter, 2-4 parametre, 5+ parametrov. */
function slovom(n, jeden, malo, mnoho) {
  if (n === 1) return jeden;
  return n >= 2 && n <= 4 ? malo : mnoho;
}

const hyperKey = () => `hyperopt:${state.strategy}`;
const hyper = { id: null, timer: null };

async function pollHyper() {
  if (!hyper.id) return;
  try {
    const r = await api(`/api/hyperopts/${hyper.id}`);
    renderHyper(r);
    if (r.status === "queued" || r.status === "running"
        || (r.verify || []).some(v => v.status === "queued" || v.status === "running")) {
      clearTimeout(hyper.timer);
      hyper.timer = setTimeout(pollHyper, 4000);
    }
  } catch (e) {
    clearTimeout(hyper.timer);
    hyper.timer = setTimeout(pollHyper, 4000);
  }
}

/** „beží · 37/200 epoch · ešte ~12 min". Odhad až keď sú aspoň dve dávky hotové —
 *  pred prvou epochou Freqtrade len načítava dáta a tempo z nej by klamalo. */
function hyperProgress(r) {
  const p = r.progress;
  const spolu = r.hyperopt.epochs;
  if (!p || !p.done) {
    const uz = p ? ` · ${fmtMinutes(Math.round((p.elapsed_s || 0) / 60))} od štartu` : "";
    return `beží · pripravuje sa (${spolu} epoch)${uz}`;
  }
  const odhad = p.eta_s == null ? "odhad po ďalšej dávke"
    : `ešte ~${fmtMinutes(Math.max(1, Math.round(p.eta_s / 60)))}`;
  return `beží · ${p.done}/${p.total || spolu} epoch · ${odhad}`;
}

function renderHyper(r) {
  const casti = [];
  if (r.status === "queued") casti.push("čaká vo fronte");
  else if (r.status === "running") casti.push(hyperProgress(r));
  else if (r.status === "failed") casti.push("zlyhalo");
  else casti.push(`hotovo · ${r.hyperopt.epochs_done || 0} epoch`);
  casti.push(r.goal_note);
  $("#sweep-status").textContent = casti.join(" · ");
  $("#sweep-cancel").hidden = !(r.status === "queued" || r.status === "running");

  const box = $("#sweep-result");
  if (r.status === "failed") { box.innerHTML = `<div class="error">${esc(r.error || "beh zlyhal")}</div>`; return; }
  const casti_html = [];
  // Zadanie nech je vidiet vzdy - bez neho sa tabulka nul neda ani len zacat riesit.
  const st = r.settings || {};
  casti_html.push(`<p class="an-note">${esc(st.pair || "")} ${esc(st.timeframe || "")} · ${esc(st.timerange || "")}`
    + ` · peňaženka ${esc(String(st.wallet ?? ""))} · profil ${esc(st.profile || "Pine defaulty")}</p>`);
  if (r.zero_trades) casti_html.push(`<div class="warnbox">${esc(r.zero_trades)}</div>`);

  if ((r.epochs || []).length) {
    const head = [...r.params, "obch.", "PnL %", "WR %", "DD %", "skóre"];
    const rows = r.epochs.slice(0, 20).map((e, i) => {
      const cls = !e.usable ? "out" : (i === 0 ? "best" : "");
      const cells = [
        ...r.params.map(n => esc(fmtVal(e.params["hp_" + n]))),
        e.trades ?? "—", fmt(e.pnl_pct, 2), fmt(e.winrate, 1),
        fmt(e.max_drawdown_pct, 2), fmt(-e.loss, 4),
      ];
      const title = e.usable ? "" : "mimo mantinelov (počet obchodov alebo drawdown)";
      return `<tr class="${cls}" title="${esc(title)}">` + cells.map(c => `<td>${c}</td>`).join("") + "</tr>";
    }).join("");
    casti_html.push(`<table><thead><tr>${head.map(h => `<th>${esc(h)}</th>`).join("")}`
      + `</tr></thead><tbody>${rows}</tbody></table>`);
  }

  if (r.overrides) {
    const zoznam = Object.entries(r.overrides).map(([k, v]) => `${k} = ${esc(fmtVal(v))}`).join(", ");
    casti_html.push(`<p class="mode-hint">Najlepšia epocha: ${zoznam}</p>`);
  }

  if ((r.verify || []).length) {
    const rows = r.verify.map(v => {
      const res = v.result || {};
      const cells = [v.timerange + (v.tuned ? " (ladené)" : ""), v.status,
        res.trades ?? "—", fmt(res.pnl_pct, 2), fmt(res.break_even_pct, 4)];
      return `<tr class="${v.tuned ? "tuned" : ""}" data-run="${v.id}" title="klikni pre detail behu">`
        + cells.map(c => `<td>${c}</td>`).join("") + "</tr>";
    }).join("");
    casti_html.push('<table class="verify-table"><thead><tr><th>okno</th><th>stav</th>'
      + "<th>obch.</th><th>PnL %</th><th>break-even</th></tr></thead>"
      + `<tbody>${rows}</tbody></table>`);
  }

  if (r.verdict) {
    const trieda = r.verdict.startsWith("VITAZ PREZIL") ? "good"
      : (r.verdict.startsWith("PRETRENOVANE") ? "bad" : "unsure");
    casti_html.push(`<div class="verdict ${trieda}">${esc(r.verdict)}</div>`);
  }
  casti_html.push(plateauHtml(r));
  box.innerHTML = casti_html.join("");
  for (const tr of $$("#sweep-result tr[data-run]")) {
    tr.onclick = () => openPoint(tr.dataset.run);
  }
  const tlacidlo = $("#plateau-run");
  if (tlacidlo) tlacidlo.onclick = () => startPlateau(r.id);
}

/** Okolie víťaza: plató, alebo osamelá špička? */
function plateauHtml(r) {
  if (!r.overrides) return "";
  const p = r.plateau;
  if (!p) {
    return `<p class="an-note"><button id="plateau-run" class="ghost small" type="button"
        title="Pustí susedov víťaza — o krok a o dva kroky na každom ladenom parametri.">
        Preveriť okolie víťaza</button>
      Hyperopt vrátil jedno číslo; susedia povedia, či je to stred niečoho, alebo náhodná
      diera v šume.</p>`;
  }
  const rows = (p.rows || []).map(x => {
    const znak = x.step > 0 ? "+" : "";
    return `<tr class="${x.holds ? "" : "out"}" data-run="${x.id}" title="klikni pre detail behu">`
      + `<td>${esc(x.param)} ${znak}${x.step}</td><td>${esc(fmtVal(x.value))}</td>`
      + `<td>${x.trades ?? "—"}</td><td>${fmt(x.break_even_pct, 4)}</td>`
      + `<td>${x.holds ? "áno" : "NIE"}</td></tr>`;
  }).join("");
  const trieda = p.verdict.startsWith("PLATO") ? "good"
    : (p.verdict.startsWith("SPICKA") ? "bad" : "unsure");
  const hlavicka = p.ci_lo !== null && p.ci_lo !== undefined
    ? `<p class="an-note">Interval víťaza (Monte Carlo): ${fmt(p.ci_lo, 4)} až ${fmt(p.ci_hi, 4)} %`
      + (p.spread !== null ? ` · rozptyl okolia ${fmt(p.spread, 4)} %` : "") + "</p>"
    : "";
  return `<div class="ch-box">
      <div class="ch-head"><h3>Okolie víťaza</h3>
        ${p.pending ? `<span class="chip warn">${p.pending} beží</span>` : ""}</div>
      <p class="an-note">${esc(p.note || "")}</p>
      ${hlavicka}
      ${rows ? `<table class="mx-table"><thead><tr><th>sused</th><th>hodnota</th>
        <th>obch.</th><th>break-even</th><th>drží</th></tr></thead>
        <tbody>${rows}</tbody></table>` : ""}
      <div class="verdict ${trieda}">${esc(p.verdict)}</div>
    </div>`;
}

/** Zaradí susedov víťaza do fronty. */
async function startPlateau(id) {
  const btn = $("#plateau-run");
  if (btn) btn.disabled = true;
  try {
    const r = await api(`/api/hyperopts/${id}/plateau`, { method: "POST" });
    $("#sweep-status").textContent = `${r.neighbours} susedov vo fronte`;
    pollQueue();
    pollHyper();
  } catch (e) {
    $("#sweep-status").textContent = e.message;
    if (btn) btn.disabled = false;
  }
}
