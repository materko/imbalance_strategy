/* TradeBot Backtester — Matica trhov: výber trhov a TF, zadanie, priebeh a tabuľka. */
"use strict";

/** Naplní výber trhov a timeframov; zvýrazní trhy, kde sa nezmestí jeden kontrakt. */
async function initMatrixPick() {
  const sel = $("#matrix-pairs");
  if (!sel.options.length) {
    for (const p of state.meta.pairs || []) {
      const o = document.createElement("option");
      o.value = p.pair;
      o.textContent = `${p.source || "?"} · ${p.kind || ""} · ${p.pair}`;
      if (p.pair === $("#pair").value) o.selected = true;
      sel.append(o);
    }
  }
  const box = $("#matrix-tfs");
  if (!box.children.length) {
    // Timeframy sú vlastnosť páru (nie všetky trhy majú všetky), takže tu je zjednotenie
    // toho, čo je aspoň na jednom trhu — čo na konkrétnom páre nie je, sa preskočí.
    const vsetky = [...new Set((state.meta.pairs || []).flatMap(p => p.timeframes || []))]
      .sort((a, b) => (tfMinutes(a) || 0) - (tfMinutes(b) || 0));
    for (const tf of (vsetky.length ? vsetky : ["3m"])) {
      const label = document.createElement("label");
      label.innerHTML = `<input type="checkbox" value="${tf}"${tf === $("#tf").value ? " checked" : ""}> ${tf}`;
      label.querySelector("input").onchange = refreshSweep;
      box.append(label);
    }
  }
  await matrixWalletCheck();
}

/** Jeden lot EURUSD je ~112 000 — s peňaženkou 10 000 sa nezmestí a bunka dá nula obchodov. */
async function matrixWalletCheck() {
  const box = $("#matrix-warn");
  try {
    const tf = matrixTimeframes()[0] || "3m";
    const r = await api(`/api/matrix/meta?wallet=${encodeURIComponent($("#wallet").value || 10000)}`
      + `&timeframe=${encodeURIComponent(tf)}&strategy=${encodeURIComponent(state.strategy)}`);
    const male = Object.entries(r.small_wallet || {})
      .filter(([pair]) => matrixPairs().includes(pair))
      .sort((a, b) => b[1] - a[1]);
    if (!male.length) { box.hidden = true; return; }
    box.hidden = false;
    box.textContent = `Peňaženka ${$("#wallet").value} nestačí na jeden kontrakt na `
      + `${male.length} vybraných trhoch (${male.slice(0, 3).map(([p, n]) =>
        `${p} ${Math.round(n).toLocaleString("sk")}`).join(", ")}…). `
      + `Tie bunky skončia s nula obchodmi. Break-even od peňaženky nezávisí, tak ju zvýš `
      + `na ${Math.round(male[0][1] * 2).toLocaleString("sk")}.`;
  } catch (e) { box.hidden = true; }
}

/** `3m` -> 3, `1h` -> 60. Na zoradenie timeframov podľa dĺžky, nie abecedy. */
function tfMinutes(tf) {
  const m = /^(\d+)([mhdw])$/.exec(String(tf || ""));
  if (!m) return 0;
  const n = Number(m[1]);
  return n * { m: 1, h: 60, d: 1440, w: 10080 }[m[2]];
}

const matrixPairs = () => [...$("#matrix-pairs").selectedOptions].map(o => o.value);
const matrixTimeframes = () => [...$$("#matrix-tfs input:checked")].map(i => i.value);

/** Matica: každá bunka je obyčajný beh s tou istou značkou. */
async function startMatrix() {
  const pairs = matrixPairs(), timeframes = matrixTimeframes();
  if (!pairs.length || !timeframes.length) return;
  const btn = $("#sweep-run");
  btn.disabled = true;
  $("#sweep-status").textContent = "zaraďujem do fronty…";
  try {
    const r = await api("/api/matrices", {
      method: "POST",
      body: JSON.stringify({
        ...runBody(), pairs, timeframes,
        goal: $("#sweep-goal").value,
        min_trades: $("#sweep-mintrades").value === "" ? 10 : Number($("#sweep-mintrades").value),
        relative: $("#matrix-relative").checked,
      }),
    });
    matrixState.id = r.id;
    try { localStorage.setItem(matrixKey(), r.id); } catch (e) { /* súkromné okno */ }
    const preskocene = Object.keys(r.skipped || {}).length;
    $("#sweep-status").textContent = `${r.cells} buniek vo fronte`
      + (preskocene ? ` · ${preskocene} preskočených` : "");
    if ((r.converted || []).length) {
      $("#sweep-warn").hidden = false;
      $("#sweep-warn").textContent = "Prahy prepočítané: " + r.converted.join("; ");
    }
    pollQueue();
    pollMatrix();
    loadSweepHistory();
  } catch (e) {
    $("#sweep-status").textContent = e.message;
  } finally { refreshSweep(); }
}

const matrixKey = () => `matrix:${state.strategy}`;
const matrixState = { id: null, timer: null };

async function pollMatrix() {
  if (!matrixState.id) return;
  try {
    const r = await api(`/api/matrices/${matrixState.id}`);
    renderMatrix(r);
    if (r.pending) {
      clearTimeout(matrixState.timer);
      matrixState.timer = setTimeout(pollMatrix, 4000);
    }
  } catch (e) {
    clearTimeout(matrixState.timer);
    matrixState.timer = setTimeout(pollMatrix, 4000);
  }
}

function renderMatrix(r) {
  $("#sweep-status").textContent = `hotových ${r.done} z ${r.total ?? (r.done + r.pending)}`
    + ` · ${r.goal_note}` + (r.relative ? " · prahy v ATR" : " · prahy nezmenené (!)");
  const t = r.table || {};
  const casti = [];
  if ((t.pairs || []).length) {
    const head = ["trh", ...t.timeframes].map(h => `<th>${esc(h)}</th>`).join("");
    const rows = t.pairs.map(pair => {
      const cells = t.timeframes.map(tf => {
        const b = (t.cells[pair] || {})[tf];
        if (!b) return `<td class="wait">.</td>`;
        if (b.status !== "done") return `<td class="wait">${esc(b.status || "…")}</td>`;
        if (b.value === null || b.value === undefined) {
          // Rozdiel je zásadný: „0 setupov" je vlastnosť stratégie na tom trhu,
          // „odmietnuté" je náš problém s peňaženkou alebo sizingom.
          const text = b.empty === "bez setupu" ? "0 setupov"
            : b.empty === "odmietnute" ? "odmietnuté" : "—";
          return `<td class="wait" title="${esc(b.warning || "")}">${text}</td>`;
        }
        const cls = !b.ok ? "noise" : (b.value > 0 ? "pos" : "neg");
        const title = b.ok ? `${b.trades} obchodov` : esc(b.why || "mimo mantinelov");
        return `<td class="${cls}" data-run="${b.id}" title="${title}">${fmt(b.value, 4)}</td>`;
      }).join("");
      return `<tr><td>${esc(pair)}</td>${cells}</tr>`;
    }).join("");
    casti.push(`<table class="mx-table"><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`);
    casti.push('<p class="an-note">Čísla sú break-even poplatok v % na stranu. Kurzívou sú bunky'
      + " s málo obchodmi — číslo tam je, ale záver z neho nie. PnL % nie je medzi trhmi"
      + " porovnateľné (závisí od peňaženky), break-even áno.</p>");
  }
  if (r.verdict) {
    const trieda = r.verdict.startsWith("MYSLIENKA DRZI") ? "good"
      : (r.verdict.includes("LEN NA JEDNOM") || r.verdict.startsWith("SLABE") ? "bad" : "unsure");
    casti.push(`<div class="verdict ${trieda}">${esc(r.verdict)}</div>`);
  }
  $("#sweep-result").innerHTML = casti.join("");
  for (const td of $$("#sweep-result td[data-run]")) {
    td.onclick = () => openPoint(td.dataset.run);
  }
}
