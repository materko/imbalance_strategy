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
      sampler: $("#hyper-sampler").value || null,
      ...nativeBody(),
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

/** Voľby natívneho hyperoptu z formulára — server ich odmietne, keď engine nie je emulátor MultiCharts. */
function nativeBody() {
  if ($("#hyper-native").hidden) return {};
  const windows = $$("#hyper-windows input:checked").map(i => i.value);
  return {
    mode: $("#hyper-mode").value,
    windows: windows.length ? windows : null,
    aggregate: $("#hyper-aggregate").value,
    select: $("#hyper-select").value,
    anchored: $("#hyper-anchored").checked,
    objectives: $$(".hyper-obj:checked").map(i => i.value),
  };
}

/** Ukáže rozšírené voľby (vedia ich oba enginy) a naplní referenčné okná. */
function setupNativeOptions(meta) {
  const box = $("#hyper-native");
  if (!box) return;
  box.hidden = !meta || searchMode !== "hyper";
  const host = $("#hyper-windows");
  if (host && !host.dataset.ready && meta && meta.windows) {
    host.innerHTML = meta.windows.map(w => `<label class="inline small"><input type="checkbox" value="${esc(w)}"> `
      + `${esc(w.slice(0, 4))}/${esc(w.slice(11, 13))}</label>`).join("");
    host.dataset.ready = "1";
  }
}

/** Ďalšie epochy natívneho hyperoptu — nový záznam so starými aj novými epochami. */
async function continueHyperopt(id) {
  const n = Number(($("#hyper-continue-n") || {}).value) || 200;
  try {
    const r = await api(`/api/hyperopts/${id}/continue`, { method: "POST", body: JSON.stringify({ epochs: n, user: currentUser() }) });
    hyper.id = r.id;
    try { localStorage.setItem(hyperKey(), r.id); } catch (e) { /* súkromné okno */ }
    $("#sweep-status").textContent = `pokračovanie vo fronte: +${r.epochs} epoch k ${r.previous}`;
    pollQueue();
    pollHyper();
    loadSweepHistory();
  } catch (e) {
    $("#sweep-status").textContent = e.message;
  }
}

/** Walk-forward: foldy, ich test na nevidenom okne a verdikt. */
function walkForwardHtml(wf) {
  const rows = (wf.folds || []).map(f => {
    const r = f.result || {};
    const params = f.params ? Object.entries(f.params).map(([k, v]) => `${k}=${fmtVal(v)}`).join(", ") : "—";
    return `<tr class="${(f.edge || 0) > 0 ? "" : "out"}"><td>${f.fold + 1}</td><td>${esc((f.train || []).join(" + "))}</td>`
      + `<td>${esc(f.test)}</td><td>${f.train_score == null ? "—" : fmt(f.train_score, 4)}</td>`
      + `<td>${r.trades ?? "—"}</td><td>${fmt(r.break_even_pct, 4)}</td><td>${f.edge == null ? "—" : fmt(f.edge, 4)}</td>`
      + `<td class="muted small">${esc(params)}</td></tr>`;
  }).join("");
  const trieda = wf.verdict.startsWith("WALK-FORWARD DRZI") ? "good"
    : (wf.verdict.startsWith("WALK-FORWARD NEDRZI") ? "bad" : "unsure");
  return `<div class="ch-box"><div class="ch-head"><h3>Walk-forward${wf.anchored ? " (rastúce okno)" : ""}</h3></div>
    <p class="an-note">Každý fold ladí na ľavom okne a víťaza zmeria na pravom, ktoré optimalizátor nevidel.
      „Nad poplatkom" = break-even mínus poplatok behu.</p>
    <table class="mx-table ho-wf-table"><thead><tr><th>fold</th><th>ladené</th><th>test</th><th>ladené skóre</th>
      <th>obch.</th><th>test break-even</th><th>nad poplatkom</th><th>parametre</th></tr></thead><tbody>${rows}</tbody></table>
    <div class="verdict ${trieda}">${esc(wf.verdict)}</div></div>`;
}

/** Výber víťaza podľa okolia: kandidáti a priemer ich susedov. */
function plateauSelectHtml(info) {
  const rows = (info.candidates || []).map(c => `<tr class="${c.epoch === info.chosen ? "best" : ""}">`
    + `<td>${c.epoch}</td><td>${fmt(-c.loss, 4)}</td><td>${fmt(-c.robust, 4)}</td><td>${fmt(-c.worst, 4)}</td>`
    + `<td>${c.neighbours}</td></tr>`).join("");
  return `<div class="ch-box"><div class="ch-head"><h3>Výber podľa okolia</h3></div>
    <p class="an-note">Z najlepších epoch vyhrala tá, ktorej susedia (±1 krok na každom parametri) držia v priemere
      najlepšie${info.chosen !== info.best_epoch ? ` — nie najlepšia epocha ${info.best_epoch}, tá stojí na užšej špičke` : ""}.</p>
    <table class="mx-table"><thead><tr><th>epocha</th><th>skóre</th><th>priemer s okolím</th><th>najhorší sused</th>
      <th>susedov</th></tr></thead><tbody>${rows}</tbody></table></div>`;
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
    : `ešte ~${p.eta_s < 90 ? `${Math.max(1, Math.round(p.eta_s))} s` : fmtMinutes(Math.max(1, Math.round(p.eta_s / 60)))}`;
  // natívny hyperopt (C#) robí desiatky epoch za sekundu - tempo hovorí viac než sekundy na epochu
  const tempo = p.s_per_epoch == null ? ""
    : (p.s_per_epoch < 1 ? ` · ${(1 / Math.max(p.s_per_epoch, 0.01)).toFixed(0)} epoch/s` : ` · ${p.s_per_epoch} s/epocha`);
  const pct = Math.round(100 * p.done / (p.total || spolu));
  return `beží · ${p.done}/${p.total || spolu} epoch (${pct} %)${tempo} · ${odhad}`;
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
    + ` · peňaženka ${esc(String(st.wallet ?? ""))} · profil ${esc(st.profile || "Pine defaulty")}`
    + (r.hyperopt.native ? ` · natívne v C# (emulátor MultiCharts), sampler ${esc(r.hyperopt.sampler || "tpe")}`
      + (r.hyperopt.distinct ? `, ${r.hyperopt.distinct} rôznych backtestov` : "")
      : ` · Freqtrade, sampler ${esc(r.hyperopt.sampler || "predvolený (NSGA-III)")}`)
    + (r.hyperopt.windows && !r.hyperopt.walk_forward ? ` · kritérium cez ${r.hyperopt.windows.length} ${slovom(r.hyperopt.windows.length, "okno", "okná", "okien")} (${esc(r.hyperopt.aggregate || "min")})` : "")
    + (r.hyperopt.merged ? ` · zlúčené s ${r.hyperopt.merged} epochami predošlého hľadania (Freqtrade z nich neučí)` : "")
    + `</p>`);
  if (r.zero_trades) casti_html.push(`<div class="warnbox">${esc(r.zero_trades)}</div>`);

  if ((r.epochs || []).length) {
    // stĺpce po oknách len keď ich epochy nesú (natívne); Freqtrade epocha má len súhrn celého rozpätia
    const okna = (r.hyperopt.windows && !r.hyperopt.walk_forward && (r.epochs[0] || {}).windows) ? r.hyperopt.windows : [];
    const pareto = !!(r.hyperopt.pareto || []).length;
    const head = [...r.params, "obch.", "PnL %", "WR %", "DD %", "skóre",
      ...okna.map(w => `BE ${w.slice(0, 4)}/${w.slice(11, 13)}`), ...(pareto ? ["Pareto"] : [])];
    const rows = r.epochs.slice(0, 20).map((e, i) => {
      const cls = !e.usable ? "out" : (e.is_best ? "best" : (i === 0 && !r.hyperopt.plateau_select ? "best" : ""));
      const cells = [
        ...r.params.map(n => esc(fmtVal(e.params["hp_" + n]))),
        e.trades ?? "—", fmt(e.pnl_pct, 2), fmt(e.winrate, 1),
        fmt(e.max_drawdown_pct, 2), fmt(-e.loss, 4),
        ...okna.map(w => fmt(((e.windows || {})[w] || {}).break_even_pct, 4)),
        ...(pareto ? [e.pareto ? '<span class="ho-pareto" title="na Pareto hranici">◆</span>' : ""] : []),
      ];
      const title = e.usable ? "" : "mimo mantinelov (počet obchodov alebo drawdown)";
      return `<tr class="${cls}" title="${esc(title)}">` + cells.map(c => `<td>${c}</td>`).join("") + "</tr>";
    }).join("");
    casti_html.push(`<table><thead><tr>${head.map(h => `<th>${esc(h)}</th>`).join("")}`
      + `</tr></thead><tbody>${rows}</tbody></table>`);
  }

  if (r.overrides) {
    const zoznam = Object.entries(r.overrides).map(([k, v]) => `${k} = ${esc(fmtVal(v))}`).join(", ");
    const kto = r.hyperopt.walk_forward ? "Parametre posledného foldu"
      : (r.hyperopt.plateau_select ? "Víťaz podľa okolia" : "Najlepšia epocha");
    casti_html.push(`<p class="mode-hint">${kto}: ${zoznam}</p>`);
  }
  if ((r.hyperopt.pareto || []).length) {
    casti_html.push(`<p class="an-note">Pareto hranica: ${r.hyperopt.pareto.length} epoch (◆) — `
      + `ciele ${esc([r.hyperopt.goal, ...(r.hyperopt.objectives || [])].join(", "))}. Víťaz je najlepší v prvom, `
      + "ostatné body hranice sú kompromisy na výber.</p>");
  }
  if (r.hyperopt.plateau_select) casti_html.push(plateauSelectHtml(r.hyperopt.plateau_select));
  if (r.hyperopt.walk_forward) casti_html.push(walkForwardHtml(r.hyperopt.walk_forward));

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
  if (!r.hyperopt.walk_forward) casti_html.push(plateauHtml(r));
  if (r.status === "done" && !r.hyperopt.walk_forward) {
    casti_html.push(`<p class="an-note"><button id="hyper-continue" class="ghost small" type="button"
        title="Tie isté zadanie, ďalšie epochy; nový záznam nesie staré aj nové. Natívne sa staré epochy vložia do hľadania, Freqtrade ich len zlúči (nové hľadanie s iným seedom sa z nich neučí).">
        Pokračovať</button> o <input id="hyper-continue-n" type="number" min="1" max="5000" step="50" value="200"
        style="width:5.5em"> epoch</p>`);
  }
  box.innerHTML = casti_html.join("");
  const dalej = $("#hyper-continue");
  if (dalej) dalej.onclick = () => continueHyperopt(r.id);
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
