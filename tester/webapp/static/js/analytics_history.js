/* TradeBot Backtester — História analytiky. */
"use strict";

// --------------------------------------------------------------------------- //
// Historia analytiky — per strategia, rovnako ako mriezky a matice
// --------------------------------------------------------------------------- //

/** Naplni ponuku ulozenych analytik. Per strategia: vlastnosti aj parametre su pri
 *  kazdej ine, takze zliate v jednom zozname by sa neporovnavali. */
async function loadAnalyticsHistory(vybrat = "") {
  const sel = $("#an-history");
  if (!sel) return;
  try {
    // Vybraná konfigurácia zúži aj históriu: analytika patrí ku konfigurácii, nie len
    // k stratégii - záver o inom nastavení by tu len miatol.
    const nast = (!$("#an-query")?.value.trim() && state.anPlan?.config_key) || "";
    const trh = (nast && state.anPlan?.market) || "";
    const r = await api(`/api/analytics/history?strategy=${encodeURIComponent(anStrategy())}`
      + (nast ? `&config_key=${encodeURIComponent(nast)}` : "")
      + (nast && trh ? `&market=${encodeURIComponent(trh)}` : ""));
    sel.innerHTML = `<option value="">— nová analytika${nast ? " (história tohto profilu a trhu)" : ""} —</option>`
      + (r.items || []).map(x => {
        const be = x.break_even_pct === null || x.break_even_pct === undefined
          ? "" : ` · break-even ${fmt(x.break_even_pct, 4)} %`;
        const profil = x.profile ? ` · ${String(x.profile).split("/").pop().replace(/\.json$/, "")}` : "";
        const trhX = x.market && x.market !== "mixed" ? ` · ${String(x.market).replace("|", " ")}`
          : (x.market === "mixed" ? " · všetky trhy" : "");
        const okna = (x.timeranges || []).length;
        const popis = `${anStamp(x.created)}${profil}${trhX} · ${x.trades} obch. z ${x.runs} behov`
          + (okna ? ` / ${okna} ${slovom(okna, "okno", "okná", "okien")}` : "")
          + (x.config_key === "mixed" ? " · zmiešané konfigurácie" : "")
          + `${be}` + (x.note ? ` · ${x.note}` : "");
        return `<option value="${esc(x.id)}">${esc(popis)}</option>`;
      }).join("");
    sel.value = vybrat;
  } catch (e) {
    sel.innerHTML = `<option value="">história sa nenačítala: ${esc(e.message)}</option>`;
  }
}

function anStamp(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? String(iso).slice(0, 16)
    : d.toLocaleString("sk-SK", { dateStyle: "short", timeStyle: "short" });
}

/** Posudok patrí k uloženej analytike — čerstvá ho ešte nemá kam pripísať. */
function showPosudok(zaznam) {
  const box = $("#posudok-box");
  if (!zaznam) { box.hidden = true; state.posudokId = null; return; }
  state.posudokId = zaznam.id;
  box.hidden = false;
  $("#posudok-text").value = zaznam.posudok || "";
  // Posudok napísaný k iným číslam nie je nepravdivý, len starý — a to musí byť vidieť.
  const stary = zaznam.posudok && zaznam.posudok_stamp !== zaznam.numbers;
  const chip = $("#posudok-stav");
  chip.className = "chip" + (stary ? " stale" : "");
  chip.textContent = !zaznam.posudok ? "zatiaľ nenapísaný"
    : (stary ? "starý — čísla sa medzitým zmenili" : `napísaný ${anStamp(zaznam.posudok_at)}`);
  box.open = !zaznam.posudok;
  $("#posudok-status").textContent = "";
}

async function copyZadanie() {
  if (!state.posudokId) return;
  try {
    const r = await api(`/api/analytics/history/${encodeURIComponent(state.posudokId)}/zadanie`);
    await navigator.clipboard.writeText(r.text);
    $("#posudok-status").textContent = "zadanie je v schránke — vlož ho AI";
  } catch (e) {
    $("#posudok-status").textContent = e.message;
  }
}

async function savePosudok() {
  if (!state.posudokId) return;
  const btn = $("#posudok-save");
  btn.disabled = true;
  $("#posudok-status").textContent = "ukladám…";
  try {
    const out = await api(`/api/analytics/history/${encodeURIComponent(state.posudokId)}/posudok`, {
      method: "POST",
      body: JSON.stringify({ text: $("#posudok-text").value, user: currentUser() || "" }),
    });
    $("#posudok-status").textContent = "uložené";
    $("#posudok-stav").className = "chip";
    $("#posudok-stav").textContent = `napísaný ${anStamp(out.posudok_at)}`;
    await loadAnalyticsHistory(state.posudokId);
  } catch (e) {
    $("#posudok-status").textContent = e.message;
  } finally { btn.disabled = false; }
}

/** Otvori ulozenu analytiku — vykresli sa tym istym kodom ako cerstva. */
async function openAnalyticsHistory(id) {
  if (!id) return;
  $("#an-status").textContent = "načítavam…";
  try {
    const z = await api(`/api/analytics/history/${encodeURIComponent(id)}`);
    state.analytics = z.report;
    renderAnalytics(z.report);
    $("#an-paper").disabled = false;
    $("#an-save").disabled = false;     // poznamka sa da dopisat aj k starsiemu zaznamu
    showPosudok(z);
    $("#an-status").innerHTML = `uložená ${esc(anStamp(z.created))}`
      + (z.note ? ` · ${esc(z.note)}` : "");
  } catch (e) {
    $("#an-status").textContent = e.message;
  }
}

/** Poznamka k ulozenej analytike - ukladanie je automaticke, poznamka sa dopise. */
async function saveAnalytics() {
  if (!state.posudokId) return;
  const note = prompt("Čo si tým zisťoval? (poznámka k uloženej analytike)", "");
  if (note === null) return;
  const btn = $("#an-save");
  btn.disabled = true;
  $("#an-status").textContent = "ukladám poznámku…";
  try {
    const out = await api(`/api/analytics/history/${encodeURIComponent(state.posudokId)}/note`, {
      method: "POST",
      body: JSON.stringify({ note }),
    });
    await loadAnalyticsHistory(out.id);
    $("#an-status").textContent = `poznámka uložená k ${out.id}`;
  } catch (e) {
    $("#an-status").textContent = e.message;
  } finally { btn.disabled = false; }
}
