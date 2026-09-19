/* TradeBot Backtester — Prop výzva. */
"use strict";

// --------------------------------------------------------------------------- //
// Prop vyzva: dostanes sa k vyplate skor, nez ucet zhori?
// --------------------------------------------------------------------------- //
//
// Formular je jeden a montuje sa na dve miesta: do Analytiky (nad vybranymi behmi) a
// k Novemu behu (nad tym jednym, ked dobehne). Preto vsetky id nesu prefix - dve kopie
// s rovnakymi id by boli chyba, ktoru prehliadac nenahlasi, len prestane fungovat.

/** Markup formulára pravidiel. `p` je prefix id (`prop` alebo `nprop`). */
function propFormHtml(p) {
  return `<div class="form-grid an-form">
      <div class="field span2">Ktoré predlohy porovnať
        <span class="hint">zaškrtni firmy; tie isté obchody sa prehrajú cez každú</span>
        <div id="${p}-presets" class="prop-presets"></div>
      </div>
      <label class="field inline small span2"><input type="checkbox" id="${p}-custom">
        aj vlastné pravidlá z polí nižšie
        <span class="hint">(predlohy firiem sa nemenia; polia platia len pre vlastné pravidlá)</span></label>
      <label class="field span2">Predvyplniť polia z predlohy
        <select id="${p}-preset"></select>
      </label>
      <label class="field">Účet
        <input type="number" id="${p}-account" min="1000" step="1000">
      </label>
      <label class="field">Ciele fáz (% oddelené čiarkou)
        <input type="text" id="${p}-targets" placeholder="10,5">
      </label>
      <label class="field">Denný limit % <span class="hint">0 = firma ho nemá</span>
        <input type="number" id="${p}-daily" min="0" step="0.1">
      </label>
      <label class="field">Celkový limit %
        <input type="number" id="${p}-maxloss" min="0.1" step="0.1">
      </label>
      <label class="field">Od čoho sa počíta celkový limit
        <select id="${p}-trailing"></select>
      </label>
      <label class="field inline small"><input type="checkbox" id="${p}-freeze">
        hranica sa zastaví na počiatočnom zostatku</label>
      <label class="field">Minimum dní
        <input type="number" id="${p}-mindays" min="0" step="1">
      </label>
      <label class="field">Najlepší deň max % zisku <span class="hint">0 = bez pravidla</span>
        <input type="number" id="${p}-dayshare" min="0" max="100" step="5">
      </label>
      <label class="field">Cena výzvy
        <input type="number" id="${p}-cost" min="0" step="10">
      </label>
      <label class="field">Podiel zo zisku %
        <input type="number" id="${p}-payout" min="1" max="100" step="5">
      </label>
      <label class="field inline small"><input type="checkbox" id="${p}-refund">
        cena sa vracia pri prvej výplate</label>
      <label class="field">Horizont v dňoch <span class="hint">0 = bez limitu</span>
        <input type="number" id="${p}-horizon" min="0" step="10">
      </label>
      <div class="an-actions span2">
        <button id="${p}-run" class="primary" type="button">Spočítať výzvu</button>
        <span id="${p}-status" class="hint"></span>
      </div>
    </div>
    <p id="${p}-source" class="an-note"></p>
    <div id="${p}-result"></div>`;
}

/** Predlohy pravidiel firiem; nacitaju sa raz a drzia sa v state. */
async function loadPropMeta(p) {
  const box = $(`#${p}-form`);
  if (!box) return null;
  if (!box.dataset.ready) { box.innerHTML = propFormHtml(p); box.dataset.ready = "1"; }
  state.propMeta = state.propMeta || await api("/api/prop/meta");
  const sel = $(`#${p}-preset`);
  if (!sel.options.length) {
    const predlohy = Object.entries(state.propMeta.presets);
    sel.innerHTML = predlohy
      .map(([k, v]) => `<option value="${esc(k)}">${esc(v.name)}</option>`).join("");
    // Zaskrtavacie predlohy: prva je zaskrtnuta, ostatne si tester prida. Kazda
    // predloha navyse je dalsia simulacia nad tymi istymi obchodmi.
    $(`#${p}-presets`).innerHTML = predlohy.map(([k, v], i) =>
      `<label class="inline small" title="${esc(v.source || "")}">`
      + `<input type="checkbox" data-preset="${esc(k)}"${i === 0 ? " checked" : ""}> ${esc(v.name)}</label>`)
      .join("");
    $(`#${p}-trailing`).innerHTML = Object.entries(state.propMeta.trailing)
      .map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join("");
    sel.onchange = () => fillPropForm(p, sel.value);
    $(`#${p}-run`).onclick = () => runProp(p);
    fillPropForm(p, sel.value);
  }
  return state.propMeta;
}

/** Zaskrtnute predlohy (+ `custom`, ked su polia zapnute). */
function propRulesSelected(p) {
  const kluce = [...document.querySelectorAll(`#${p}-presets input[data-preset]:checked`)]
    .map(el => el.dataset.preset);
  if ($(`#${p}-custom`)?.checked) kluce.push("custom");
  return kluce;
}

/** Predloha do formulara. Kazde pole sa da prepisat - firmy pravidla menia. */
function fillPropForm(p, key) {
  const r = (state.propMeta.presets || {})[key];
  if (!r) return;
  $(`#${p}-account`).value = r.account;
  $(`#${p}-targets`).value = (r.targets || []).join(",");
  $(`#${p}-daily`).value = r.max_daily_loss_pct;
  $(`#${p}-maxloss`).value = r.max_loss_pct;
  $(`#${p}-trailing`).value = r.trailing;
  $(`#${p}-freeze`).checked = !!r.trailing_freeze_at_start;
  $(`#${p}-mindays`).value = r.min_days;
  $(`#${p}-dayshare`).value = r.max_day_share_pct;
  $(`#${p}-cost`).value = r.cost;
  $(`#${p}-payout`).value = r.payout_pct;
  $(`#${p}-refund`).checked = !!r.refund;
  $(`#${p}-horizon`).value = r.horizon_days;
  $(`#${p}-source`).innerHTML = r.source
    ? `Zdroj čísel: ${esc(r.source)}<br><b>Firmy pravidlá menia často — over si ich`
      + " podľa svojej zmluvy.</b>"
    : "";
}

/** Pravidla z formulara ako telo requestu. */
function propBody(p) {
  // Polia pravidiel sa posielaju LEN pre vlastne pravidla: predlohy firiem sa nemenia,
  // inak by jedina zaskrtnuta firma dostala cisla predvyplnene z inej predlohy.
  if (!$(`#${p}-custom`)?.checked) return { rules: propRulesSelected(p) };
  const ciele = $(`#${p}-targets`).value.split(",").map(x => Number(x.trim()))
    .filter(x => Number.isFinite(x) && x > 0);
  return {
    rules: propRulesSelected(p),
    account: Number($(`#${p}-account`).value),
    targets: ciele.length ? ciele : null,
    max_daily_loss_pct: Number($(`#${p}-daily`).value),
    max_loss_pct: Number($(`#${p}-maxloss`).value),
    trailing: $(`#${p}-trailing`).value,
    trailing_freeze_at_start: $(`#${p}-freeze`).checked,
    min_days: Number($(`#${p}-mindays`).value),
    max_day_share_pct: Number($(`#${p}-dayshare`).value),
    cost: Number($(`#${p}-cost`).value),
    payout_pct: Number($(`#${p}-payout`).value),
    refund: $(`#${p}-refund`).checked,
    horizon_days: Number($(`#${p}-horizon`).value),
  };
}

/** Spusti simulaciu. V Analytike nad vybranymi behmi, pri Novom behu nad `runIds`. */
async function runProp(p, runIds = null) {
  const behy = runIds || ((state.analytics || {}).runs || []).map(x => x.id);
  if (!behy.length) { $(`#${p}-status`).textContent = "najprv spočítaj analytiku"; return; }
  if (!propRulesSelected(p).length) {
    $(`#${p}-status`).textContent = "zaškrtni aspoň jednu predlohu (alebo vlastné pravidlá)";
    return;
  }
  const btn = $(`#${p}-run`);
  btn.disabled = true;
  $(`#${p}-status`).textContent = "počítam…";
  try {
    const out = await api("/api/prop", {
      method: "POST",
      body: JSON.stringify({
        ...propBody(p),
        runs: behy,
        strategy: (state.analytics || {}).strategy || anStrategy(),
        limit: Math.max(behy.length, Number($("#an-limit")?.value) || 40),
      }),
    });
    renderProp(p, out);
    $(`#${p}-status`).textContent = "";
  } catch (e) {
    $(`#${p}-status`).textContent = e.message;
    $(`#${p}-result`).innerHTML = "";
  } finally { btn.disabled = false; }
}

/** Jedna predloha: tabulka rizik, preco pokusy koncia, verdikt. */
function propVariantHtml(v) {
  const najlepsi = v.best_risk;
  const rows = (v.results || []).map(x => {
    const dni = x.median_days === null || x.median_days === undefined ? "—" : fmt(x.median_days, 0);
    const ev = x.ev === null || x.ev === undefined ? "—"
      : `<span class="${x.ev > 0 ? "good" : "bad"}">${x.ev > 0 ? "+" : ""}${fmt(x.ev, 0)}</span>`;
    return `<tr class="${x.risk_pct === najlepsi ? "best" : ""}">
        <td>${fmt(x.risk_pct, 2)} %</td><td>${x.attempts}</td><td>${x.passed}</td>
        <td>${x.burned}</td><td>${x.unfinished}</td>
        <td>${fmt(x.p_pass * 100, 1)} %</td><td>${dni}</td><td>${ev}</td></tr>`;
  }).join("");
  // Preco pokusy koncia je casto dolezitejsie nez samotna pravdepodobnost: iny dovod
  // znamena iny zasah (ine riziko vs. viac trhov vs. ina firma).
  const naj = (v.results || []).find(x => x.risk_pct === najlepsi) || {};
  const dovody = Object.entries(naj.reasons || {}).sort((a, b) => b[1] - a[1])
    .map(([k, r]) => `${esc(k)} ${r}×`).join(" · ");
  const trieda = (naj.ev || 0) > 0 ? "good" : "bad";
  const r = v.rules || {};
  return `<p class="an-note"><b>${esc(r.name || v.key)}</b> ·
        ${r.phases} ${r.phases === 1 ? "fáza" : "fázy"} ·
        ciele ${(r.targets || []).map(x => fmt(x, 2) + " %").join(" + ")}
        · denný limit ${r.max_daily_loss_pct ? fmt(r.max_daily_loss_pct, 1) + " %" : "žiadny"}
        · celkový ${fmt(r.max_loss_pct, 1)} % (${esc(r.trailing)})</p>
      <table class="mx-table"><thead><tr><th>riziko</th><th>pokusov</th><th>prešiel</th>
        <th>spálený</th><th title="došla história alebo horizont">nedobehol</th>
        <th title="prešiel / rozhodnuté pokusy; pokusy, ktorým len došla história, sa nepočítajú">P(výplata)</th>
        <th>dní</th><th>EV</th></tr></thead>
        <tbody>${rows}</tbody></table>
      ${dovody ? `<p class="an-note">prečo pokusy končia (pri ${fmt(najlepsi, 2)} %): ${dovody}</p>` : ""}
      <div class="verdict ${trieda}">${esc(v.verdict || "")}</div>`;
}

function renderProp(p, out) {
  const varianty = out.variants || [{ key: "", rules: out.rules, results: out.results,
                                       best_risk: out.best_risk, verdict: out.verdict }];
  // Porovnanie firiem vedla seba: pri kazdej najlepsie riziko podla EV. To je odpoved
  // na otazku "ktoru propku" - jednotlive tabulky su az pod tym.
  let porovnanie = "";
  if (varianty.length > 1) {
    const rows = varianty.map(v => {
      const naj = (v.results || []).find(x => x.risk_pct === v.best_risk) || {};
      const ev = naj.ev === null || naj.ev === undefined ? "—"
        : `<span class="${naj.ev > 0 ? "good" : "bad"}">${naj.ev > 0 ? "+" : ""}${fmt(naj.ev, 0)}</span>`;
      const dni = naj.median_days === null || naj.median_days === undefined ? "—" : fmt(naj.median_days, 0);
      const znacka = (v.verdict || "").split(":")[0];
      return `<tr><td>${esc((v.rules || {}).name || v.key)}</td><td>${fmt(v.best_risk, 2)} %</td>
          <td>${fmt((naj.p_pass || 0) * 100, 1)} %</td><td>${dni}</td><td>${ev}</td>
          <td class="${(naj.ev || 0) > 0 ? "good" : "bad"}">${esc(znacka)}</td></tr>`;
    }).join("");
    porovnanie = `<table class="mx-table"><thead><tr><th>predloha</th><th>najlepšie riziko</th>
        <th>P(výplata)</th><th>dní</th><th>EV</th><th>verdikt</th></tr></thead>
        <tbody>${rows}</tbody></table>`;
  }
  const detaily = varianty.map(v => varianty.length > 1
    ? `<details class="prop-variant"><summary>${esc((v.rules || {}).name || v.key)}</summary>${propVariantHtml(v)}</details>`
    : propVariantHtml(v)).join("");
  $(`#${p}-result`).innerHTML = `<div class="ch-box">
      ${configHtml(out.config)}
      <p class="an-note">${out.trades} obchodov z ${out.runs} behov ·
        ${esc((out.pairs || []).join(", "))}${out.duplicates ? ` · ${out.duplicates} duplicít z prekrývajúcich sa okien vynechaných` : ""}</p>
      ${porovnanie}
      ${detaily}
    </div>`;
}

/** Po dobehnutí behu z karty Nový beh: spočítať výzvu z jeho obchodov. */
async function runPropForRun(runId) {
  if (!runId) return;
  await loadPropMeta("nprop");
  await runProp("nprop", [runId]);
}
