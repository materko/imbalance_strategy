/* TradeBot Backtester — Analytika: ktorá skupina obchodov kazí výsledok. */
"use strict";

// --------------------------------------------------------------------------- //
// Analytika: ktora skupina obchodov kazi vysledok
// --------------------------------------------------------------------------- //

/** `20211001-20221001` → `2021-10-01 → 2022-10-01`; okno behu má byť vidieť, nie hádať. */
function fmtWindow(w) {
  const m = /^(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$/.exec(String(w || ""));
  return m ? `${m[1]}-${m[2]}-${m[3]} → ${m[4]}-${m[5]}-${m[6]}` : String(w || "?");
}

/** Stratégia karty Analytika - prvá úroveň výberu. Predvolene tá z hlavičky, ale dá sa
 *  prepnúť nezávisle: analytika inej stratégie nemá meniť formulár Nového behu. */
function anStrategy() {
  return $("#an-strategy")?.value || state.strategy;
}

/** Naplní výber stratégie na Analytike; `key` = ktorú nastaviť (inak tá z hlavičky). */
function fillAnalyticsStrategy(key = "") {
  const sel = $("#an-strategy");
  if (!sel) return;
  if (!sel.options.length) {
    for (const s of state.meta.strategies || []) {
      const o = document.createElement("option"); o.value = s.key; o.textContent = s.title; sel.append(o);
    }
    sel.onchange = () => {
      $("#an-summary").innerHTML = ""; $("#an-result").innerHTML = "";
      state.analytics = null; showPosudok(null);
      $("#an-paper").disabled = true; $("#an-save").disabled = true;
      fillAnalyticsProfile(); fillAnalyticsPairs(); refreshAnalyticsPlan(); loadAnalyticsHistory();
    };
  }
  sel.value = key || state.strategy;
}

/** Ponuka profilov na Analytike - profily stratégie z karty Analytika (nie z hlavičky),
 *  s tým istým názvom „dátum · pár TF · popis" ako v Novom behu. */
function fillAnalyticsProfile() {
  const sel = $("#an-profile");
  if (!sel) return;
  const meta = strategyMeta(anStrategy()) || state.meta;
  const own = new Set(meta.user_profiles || []);
  const info = meta.profile_info || {};
  const keep = sel.value;
  const vlastne = (meta.profiles || []).filter(p => own.has(p))
    .sort((a, b) => String(info[b]?.created || "").localeCompare(String(info[a]?.created || "")) || a.localeCompare(b));
  sel.innerHTML = `<option value="">(Pine defaulty)</option>`;
  for (const [label, names] of [["Profily repozitára", (meta.profiles || []).filter(p => !own.has(p))],
                                ["Vlastné profily", vlastne]]) {
    if (!names.length) continue;
    const g = document.createElement("optgroup"); g.label = label;
    for (const p of names) {
      const o = document.createElement("option"); o.value = p; o.textContent = profileLabel(p, meta); o.title = p;
      g.append(o);
    }
    sel.append(g);
  }
  sel.value = (meta.profiles || []).includes(keep) ? keep : "";
}

/** Pár a TF na Analytike - tá istá ponuka ako v Novom behu; profil si ich predvolí
 *  podľa svojho nástroja a TF (analytika profilu na cudzom trhu nedáva zmysel). */
function fillAnalyticsPairs(pick = "") {
  const sel = $("#an-pair");
  if (!sel) return;
  const keep = pick || sel.value || $("#pair")?.value || "";
  sel.innerHTML = "";
  for (const source of [...new Set(state.meta.pairs.map(p => p.source || "?"))].sort()) {
    const g = document.createElement("optgroup"); g.label = source;
    for (const p of state.meta.pairs.filter(x => (x.source || "?") === source)) {
      const o = document.createElement("option"); o.value = p.pair; o.title = p.pair;
      o.textContent = `${source} · ${p.kind || p.market || "futures"} · ${p.exchange_symbol || p.pair}`;
      g.append(o);
    }
    sel.append(g);
  }
  sel.value = state.meta.pairs.some(p => p.pair === keep) ? keep : (state.meta.pairs[0]?.pair || "");
  fillAnalyticsTf();
}
function fillAnalyticsTf(pick = "") {
  const sel = $("#an-tf");
  if (!sel) return;
  const p = state.meta.pairs.find(x => x.pair === $("#an-pair")?.value);
  const tfs = p ? (p.timeframes || []) : [];
  const keep = pick || sel.value || $("#tf")?.value || "3m";
  sel.innerHTML = tfs.map(tf => `<option value="${esc(tf)}">${esc(tf)}</option>`).join("");
  sel.value = tfs.includes(keep) ? keep : (tfs.includes("3m") ? "3m" : (tfs[0] || ""));
}

/** Po výbere profilu: jeho pár a TF (z `_instrument` a `_timeframe`), potom stav okien. */
function onAnalyticsProfileChange() {
  const meta = strategyMeta(anStrategy()) || state.meta;
  const info = (meta.profile_info || {})[$("#an-profile").value] || {};
  if (info.pair && state.meta.pairs.some(p => p.pair === info.pair)) fillAnalyticsPairs(info.pair);
  if (info.timeframe) fillAnalyticsTf(info.timeframe);
  refreshAnalyticsPlan();
}

function analyticsPlanBody(dry) {
  return {
    strategy: anStrategy(), profile: $("#an-profile")?.value || "", pair: $("#an-pair")?.value || "",
    timeframe: $("#an-tf")?.value || "3m", dry_run: dry, user: currentUser() || null,
  };
}

const PLAN_WORDS = {
  done: "v histórii", queued: "vo fronte", running: "beží", missing: "dopočíta sa",
  no_data: "bez dát", failed: "zlyhalo",
};

/** Riadok s piatimi oknami: čo je hotové, čo sa dopočíta. */
function renderPlan(plan) {
  const box = $("#an-plan");
  if (!box) return;
  if (!plan) { box.textContent = ""; return; }
  const riadok = ws => (ws || []).map(w =>
    `<span class="an-win ${esc(w.status)}" title="${esc(w.run_id || "")}">${esc(fmtWindow(w.window).replace(/-\d\d-\d\d/g, ""))}: ${PLAN_WORDS[w.status] || esc(w.status)}`
    + (w.status === "done" && w.trades !== undefined ? ` (${w.trades} obch.)` : "") + `</span>`).join("");
  const s = plan.synthetic || {};
  // Syntetické dvojča: to isté zadanie na premiešanom trhu ide s analytikou vždy.
  const synt = s.pair
    ? `<div class="an-plan-row"><b title="premiešané bary páru - edge tam nemá z čoho vzniknúť">${esc(pairShort(s.pair))}</b> ${riadok(s.windows)}</div>`
    : (s.note ? `<div class="an-plan-row muted">syntetický trh: ${esc(s.note)}</div>` : "");
  box.innerHTML = `<div class="an-plan-row"><b>${esc(pairShort(plan.pair))}</b> ${riadok(plan.windows)}</div>${synt}`;
}

/** Stav okien pre zvolený profil a trh - len zistí, nič nezaraďuje. Zúži aj históriu
 *  analytík na túto konfiguráciu a trh. */
async function refreshAnalyticsPlan() {
  if (!$("#an-plan") || !$("#an-pair")?.value) return;
  try {
    const plan = await api("/api/analytics/prepare", { method: "POST", body: JSON.stringify(analyticsPlanBody(true)) });
    state.anPlan = plan;
    renderPlan(plan);
  } catch (e) {
    state.anPlan = null;
    $("#an-plan").textContent = e.message;
  }
  loadAnalyticsHistory();
}

/** Počká, kým dobehnú zaradené behy analytiky. Beh je hotový, keď je v sklade a nie je
 *  živý (medzi frontou a skladom je krátke okno, keď nie je nikde - to je „ešte beží"). */
async function waitForRuns(ids, onTick) {
  let pending = [...ids];
  const skoncene = {};
  while (pending.length) {
    await new Promise(r => setTimeout(r, 3000));
    for (const id of [...pending]) {
      try {
        const d = await api(`/api/runs/${encodeURIComponent(id)}`);
        if (!d.live && d.record && ["done", "failed"].includes(d.record.status)) {
          skoncene[id] = d.record.status;
          pending = pending.filter(x => x !== id);
        }
      } catch (e) { /* 404 = medzi frontou a skladom, alebo ešte nezačal */ }
    }
    onTick(pending.length);
  }
  return skoncene;
}

async function loadAnalytics() {
  const btn = $("#an-run");
  btn.disabled = true;
  const status = $("#an-status");
  status.textContent = "hľadám behy…";
  const params = new URLSearchParams({
    q: $("#an-query").value.trim(),
    strategy: anStrategy(),
    quantiles: $("#an-quantiles").value,
    min_bucket: $("#an-minbucket").value || 8,
    limit_runs: $("#an-limit").value || 40,
  });
  try {
    if (!$("#an-query").value.trim()) {
      // Profil na trhu: hotové behy z histórie sa použijú, chýbajúce okná sa dopočítajú
      // a čaká sa na ne - tester klikne raz.
      const plan = await api("/api/analytics/prepare", { method: "POST", body: JSON.stringify(analyticsPlanBody(false)) });
      state.anPlan = plan;
      renderPlan(plan);
      if (plan.pending.length) {
        pollQueue();
        const celkom = plan.windows.filter(w => w.status !== "no_data").length
          + ((plan.synthetic || {}).windows || []).filter(w => w.status !== "no_data").length;
        const tick = n => { status.textContent = `dopočítavam ${n} ${slovom(n, "okno", "okná", "okien")}… (${celkom - n} z ${celkom} hotových)`; };
        tick(plan.pending.length);
        const vysledok = await waitForRuns(plan.pending, tick);
        for (const w of [...plan.windows, ...((plan.synthetic || {}).windows || [])]) if (vysledok[w.run_id]) w.status = vysledok[w.run_id];
        renderPlan(plan);
      }
      const behy = plan.windows.filter(w => w.status === "done" && w.run_id).map(w => w.run_id);
      if (!behy.length) throw new Error("žiadne okno nemá hotový beh (pozri frontu / log behu)");
      params.set("runs", behy.join(","));
      params.set("limit_runs", String(Math.max(behy.length, Number($("#an-limit").value) || 40)));
      status.textContent = "počítam…";
    } else {
      status.textContent = "počítam…";
    }
    const r = await api(`/api/analytics?${params}`);
    state.anReferenceWindows = r.reference_windows || state.anReferenceWindows;
    renderAnalytics(r);
    // Meranie sa pise z tych istych behov, takze tlacidlo ma zmysel az teraz.
    state.analytics = r;
    $("#an-paper").disabled = false;
    status.textContent = "ukladám do histórie…";
    // Ukladá sa automaticky: analytika, ktorá zmizne s obnovením stránky, je na nič.
    // Tá istá vzorka je jeden záznam (server ho nájde podľa odtlačku čísel), takže
    // opakované Spočítať nič neduplikuje - a posudok, ak už je, sa ukáže hneď.
    const ulozene = await api("/api/analytics/history", {
      method: "POST",
      body: JSON.stringify({ report: r, note: "", user: currentUser() || "" }),
    });
    await loadAnalyticsHistory(ulozene.id);
    showPosudok(await api(`/api/analytics/history/${encodeURIComponent(ulozene.id)}`));
    $("#an-save").disabled = false;
    const zlyhane = (state.anPlan?.windows || []).filter(w => w.status === "failed").length;
    status.textContent = (ulozene.reused
      ? `v histórii už je (${ulozene.id})${ulozene.note ? " · " + ulozene.note : ""}`
      : `uložené do histórie ako ${ulozene.id}`)
      + (zlyhane ? ` · ${zlyhane} ${slovom(zlyhane, "okno zlyhalo", "okná zlyhali", "okien zlyhalo")}` : "");
  } catch (e) {
    status.textContent = e.message;
    $("#an-summary").innerHTML = "";
    $("#an-result").innerHTML = "";
    $("#an-paper").disabled = true;
    $("#an-save").disabled = true;
  } finally { btn.disabled = false; }
}

/** Zapíše meranie do docs/merania/ z tých istých behov, aké sú na stránke. */
async function writePaper() {
  const r = state.analytics;
  if (!r) return;
  const btn = $("#an-paper");
  btn.disabled = true;
  $("#an-status").textContent = "píšem meranie…";
  try {
    const out = await api("/api/paper", {
      method: "POST",
      body: JSON.stringify({
        runs: (r.runs || []).map(x => x.id),
        strategy: r.strategy || anStrategy(),
        limit: Number($("#an-limit").value) || 40,
      }),
    });
    const chyby = (out.sections || []).filter(s => s.gap);
    $("#an-status").innerHTML = `zapísané: <code>${esc(out.path)}</code>`
      + (chyby.length ? ` · ${chyby.length} ${slovom(chyby.length, "sekcia nemá dosť dát",
          "sekcie nemajú dosť dát", "sekcií nemá dosť dát")}` : "");
  } catch (e) {
    $("#an-status").textContent = e.message;
  } finally { btn.disabled = false; }
}
