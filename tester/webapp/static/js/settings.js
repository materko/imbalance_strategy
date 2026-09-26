/* TradeBot Backtester — Nastavenia behu: stratégia, engine, burza, pár, TF, profily, obdobie. */
"use strict";

// --------------------------------------------------------------------------- //
// Nastavenia behu
// --------------------------------------------------------------------------- //

/** Stratégia vo formulári: metadáta, defaulty a profily sú na najvyššej úrovni `state.meta`
 *  vždy tie aktívnej stratégie, takže formulár, profily a diff nič iné nepoznajú. */
function strategyMeta(key) { return (state.meta.strategy_meta || {})[key] || null; }
function strategySpec(key) { return (state.meta.strategies || []).find(s => s.key === key) || null; }

function setStrategy(key) {
  const sm = strategyMeta(key);
  if (!sm) return;
  state.strategy = key;
  Object.assign(state.meta, sm);
  state.activeGroup = null;
  $("#strategy").value = key;
  fillProfiles("");
  const spec = strategySpec(key);
  if (spec && spec.default_timeframe) fillTimeframes($("#pair").value, spec.default_timeframe);
  // Sekcia sweepu ponúkala parametre stratégie, z ktorej sa prepínalo, a históriu všetkých.
  if ($("#sweep-rows")) resetSweepForStrategy();
}

function fillSettings() {
  fillHistoryFilters();
  const ss = $("#strategy"); ss.innerHTML = "";
  for (const s of state.meta.strategies) { const o = document.createElement("option"); o.value = s.key; o.textContent = s.title; ss.append(o); }
  ss.onchange = async () => {
    setStrategy(ss.value);
    const f = $("#filter-strategy");
    if (f && f.value) { f.value = ss.value; historyPage.offset = 0; }
    fillAnalyticsStrategy(ss.value);
    fillAnalyticsProfile(); fillAnalyticsPairs(); refreshAnalyticsPlan();
    if ($("#ai-box")?.open) loadAiMeta();
    $("#profile").value = "";
    await loadProfile("");
  };
  fillProfiles();
  const pair = $("#pair"); pair.innerHTML = "";
  // z jedného riadku má byť vidno, odkiaľ sviečky sú, aký je to trh a ako sa pár volá
  // na burze (BTCUSDT.P je perpetual, BTCUSDT spot) — aj keď je select zavretý
  for (const source of [...new Set(state.meta.pairs.map(p => p.source || "?"))].sort()) {
    const list = state.meta.pairs.filter(p => (p.source || "?") === source);
    if (!list.length) continue;
    const g = document.createElement("optgroup"); g.label = source;
    for (const p of list.sort((a, b) => (a.kind || a.market || "").localeCompare(b.kind || b.market || "")
        || (a.exchange_symbol || a.pair).localeCompare(b.exchange_symbol || b.pair))) {
      const o = document.createElement("option"); o.value = p.pair;
      o.textContent = `${source} · ${p.kind || p.market || "futures"} · ${p.exchange_symbol || p.pair}`
        + (p.has_1m ? "" : " (bez 1m)");
      o.title = p.pair;
      o.dataset.from = p.from; o.dataset.to = p.to;
      g.append(o);
    }
    pair.append(g);
  }
  pair.onchange = () => {
    const o = pair.selectedOptions[0]; if (!o) return;
    checkPairProfile();
    showMarket();
    if (enforceSpotParams()) renderParams(); else lockSpotParams();
    $("#pair-range").textContent = `dáta ${o.dataset.from} → ${o.dataset.to}`;
    fillEngines(o.value);
    fillExchanges(o.value);
    fillTimeframes(o.value);
    $("#from").min = o.dataset.from; $("#from").max = o.dataset.to; $("#to").min = o.dataset.from; $("#to").max = o.dataset.to;
    if (!$("#to").value || $("#to").value > o.dataset.to) $("#to").value = o.dataset.to;
    if (!$("#from").value) { const d = new Date(o.dataset.to); d.setDate(d.getDate() - 365); $("#from").value = d.toISOString().slice(0, 10); }
  };
  pair.onchange();
  $("#profile").onchange = e => loadProfile(e.target.value);
  const who = $("#who");
  let saved = null;
  try { saved = localStorage.getItem("ibs.user"); } catch (_) { /* súkromný režim */ }
  who.value = saved || state.meta.user || "";
  who.onchange = () => { try { localStorage.setItem("ibs.user", who.value.trim()); } catch (_) { /* ignoruj */ } };
  $("#branch").textContent = state.meta.branch;
}

const ENGINE_TITLES = { freqtrade: "Freqtrade", multicharts: "MultiCharts (emulátor)" };
const ENGINE_NOTES = {
  freqtrade: "backtest Freqtradu — jeho fill model, hyperopt a FreqAI",
  multicharts: "emulátor MultiCharts — ten istý runner, čo beží v štúdii; referencia pre MultiCharts",
};

/** Engine pre beh: ponuka podľa toho, pre ktorý sú na disku dáta. */
function fillEngines(pairName, wanted) {
  const sel = $("#engine");
  const p = state.meta.pairs.find(x => x.pair === pairName);
  const list = (p && p.engines && p.engines.length) ? p.engines : ["freqtrade"];
  const keep = wanted || sel.value;
  sel.innerHTML = "";
  for (const e of list) {
    const o = document.createElement("option"); o.value = e; o.textContent = ENGINE_TITLES[e] || e; sel.append(o);
  }
  sel.value = list.includes(keep) ? keep : ((p && p.default_engine) || list[0]);
  sel.onchange = () => { showEngineNote(); fillExchanges($("#pair").value); };
  showEngineNote();
}

function showEngineNote() {
  const e = $("#engine").value;
  $("#engine-note").textContent = ENGINE_NOTES[e] || "";
}

/** Burza pre Freqtrade beh: naša fiktívna Tester a tá, odkiaľ sviečky naozaj sú.
 *  Emulátor MultiCharts burzu nepotrebuje — vtedy je pole zamknuté. */
function fillExchanges(pairName, wanted) {
  const sel = $("#exchange");
  const p = state.meta.pairs.find(x => x.pair === pairName);
  const list = (p && p.exchanges && p.exchanges.length) ? p.exchanges : [state.meta.default_exchange];
  const titles = Object.fromEntries((state.meta.exchanges || []).map(e => [e.key, e.title]));
  const keep = wanted || sel.value;
  sel.innerHTML = "";
  for (const e of list) {
    const o = document.createElement("option");
    o.value = e; o.textContent = titles[e] || e;
    sel.append(o);
  }
  sel.value = list.includes(keep) ? keep : (list.includes(state.meta.default_exchange)
    ? state.meta.default_exchange : list[0]);
  const emulator = $("#engine").value === "multicharts";
  sel.disabled = emulator;
  $("#exchange-note").textContent = emulator
    ? "emulátor MultiCharts burzu nepotrebuje — číta priamo 1m sviečky"
    : (sel.value === state.meta.default_exchange
      ? "fiktívna burza: pozná všetky naše timeframy, poplatok zadáva beh"
      : "skutočná burza: platia jej timeframy a pravidlá trhu");
  sel.onchange = () => fillExchanges(pairName, sel.value);
}

/** TF grafu pre beh: ponuka podľa stiahnutých dát páru, zachová voľbu, inak 3m. */
function fillTimeframes(pairName, wanted) {
  const sel = $("#tf");
  const keep = wanted || sel.value || "3m";
  const p = state.meta.pairs.find(x => x.pair === pairName);
  const tfs = ((p && p.timeframes) || ["3m"]).filter(t => t in TF_MINUTES);
  sel.innerHTML = "";
  for (const t of tfs) { const o = document.createElement("option"); o.value = t; o.textContent = t; sel.append(o); }
  sel.value = tfs.includes(keep) ? keep : (tfs.includes("3m") ? "3m" : tfs[0]);
}

/** Pár tak, ako sa volá na burze (BTCUSDT.P, NAS100) - keď ho stránka pozná; inak ako je. */
function pairShort(pair) {
  const p = (state.meta?.pairs || []).find(x => x.pair === pair);
  return (p && p.exchange_symbol) || pair || "";
}

/** Dátum z id behu (`20260910-082607-…`) v tom istom tvare ako dátumy histórie. */
function runIdStamp(id) {
  const m = /^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})/.exec(String(id || ""));
  return m ? anStamp(`${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}`) : "";
}

/** Názov profilu v ponuke: „dátum · pár TF · popis". Vlastné profily majú dátum vzniku;
 *  profily repozitára ho nemajú (sú z gitu), tie ostávajú „meno — popis". */
function profileLabel(name, meta = state.meta) {
  const info = (meta.profile_info || {})[name] || {};
  const titles = meta.profile_titles || {};
  const popis = info.title || (titles[name] && titles[name] !== name ? titles[name] : "") || name;
  if (!info.created) return popis === name ? name : `${name} — ${popis}`;
  const trh = `${pairShort(info.pair)} ${info.timeframe || ""}`.trim();
  return [anStamp(info.created), trh, popis].filter(Boolean).join(" · ");
}

/** Ponuka profilov: z repozitára (nemenné) a vlastné (premenovať/zmazať sa dajú len tie);
 *  vlastné zoradené od najnovšieho, lebo sa volajú dátumom vzniku. */
function fillProfiles(selected) {
  const ps = $("#profile");
  const keep = selected !== undefined ? selected : ps.value;
  const own = new Set(state.meta.user_profiles || []);
  const info = state.meta.profile_info || {};
  const vlastne = state.meta.profiles.filter(p => own.has(p))
    .sort((a, b) => String(info[b]?.created || "").localeCompare(String(info[a]?.created || "")) || a.localeCompare(b));
  ps.innerHTML = `<option value="">(Pine defaulty)</option>`;
  for (const [label, names] of [["Profily repozitára", state.meta.profiles.filter(p => !own.has(p))],
                                ["Vlastné profily", vlastne]]) {
    if (!names.length) continue;
    const g = document.createElement("optgroup"); g.label = label;
    for (const p of names) {
      const o = document.createElement("option"); o.value = p;
      o.textContent = profileLabel(p);
      o.title = p;                       // meno súboru v tester/profiles/ - to sa premenúva a maže
      g.append(o);
    }
    ps.append(g);
  }
  ps.value = state.meta.profiles.includes(keep) ? keep : "";
  updateProfileActions();
}

function updateProfileActions() {
  const name = $("#profile").value;
  const own = (state.meta.user_profiles || []).includes(name);
  const why = !name ? "Vyber vlastný profil." : "Profily repozitára sa z webapp nemenia — ulož si vlastný cez „Uložiť ako profil“ v detaile behu.";
  for (const id of ["#profile-rename", "#profile-delete"]) {
    const b = $(id); b.disabled = !own; b.title = own ? "" : why;
  }
}

/** Odpoveď API o profiloch nesie aktuálny zoznam — prekresli ponuku a načítaj `pick`.
 *
 * Načítanie musí ísť cez `loadProfile`, nie len prestaviť `value`: inak by v ponuke
 * svietil jeden profil, vo formulári by boli iné hodnoty a beh by sa uložil s iným
 * (alebo žiadnym) profilom, než tester vidí. */
async function applyProfileList(r, pick) {
  // zoznam patrí stratégii — zapíš ho aj do strategy_meta, aby po prepnutí a návrate nezmizol
  for (const target of [state.meta, strategyMeta(r.strategy || state.strategy) || {}]) {
    target.profiles = r.profiles; target.user_profiles = r.user_profiles;
    if (r.profile_titles) target.profile_titles = r.profile_titles;
    if (r.profile_instruments) target.profile_instruments = r.profile_instruments;
    if (r.profile_info) target.profile_info = r.profile_info;
  }
  fillProfiles(pick);
  fillAnalyticsProfile();
  if (pick !== undefined) await loadProfile($("#profile").value);
}

function profileMsg(text, isError) {
  const el = $("#profile-msg");
  el.textContent = text; el.classList.toggle("err", !!isError);
}

/** Meno súboru: medzera je podtržník, diakritika a zvyšné znaky pryč — inak by ho
 *  server odmietol a tester by si všimol až to, že sa nič neuložilo. */
function slugProfileName(raw) {
  return (raw || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .trim().replace(/\s+/g, "_").replace(/[^A-Za-z0-9._-]/g, "_")
    .replace(/_{2,}/g, "_").replace(/^[^A-Za-z0-9]+/, "");
}

/** Meno z promptu: očistí, a keď z neho po očistení nič nezostane, povie to nahlas. */
function askProfileName(question, preset) {
  const raw = prompt(question, preset || "");
  if (raw === null) return null;
  const name = slugProfileName(raw);
  if (!name) { alert(`„${raw}" sa ako meno profilu použiť nedá — treba aspoň jedno písmeno bez diakritiky alebo číslicu.`); return null; }
  return name;
}

/** Chyba od servera musí byť vidno: popup aj červený text vedľa ponuky. */
function profileFailed(e, el) {
  alert(`Profil: ${e.message}`);
  if (el) { el.textContent = e.message; el.classList.add("err"); }
}

async function renameProfile() {
  const cur = $("#profile").value;
  const name = askProfileName("Nové meno profilu:", cur);
  if (!name || name === cur) return;
  try {
    const r = await api(`/api/profiles/${encodeURIComponent(cur)}?strategy=${encodeURIComponent(state.strategy)}`, { method: "PATCH", body: JSON.stringify({ name }) });
    await applyProfileList(r, r.name);
    profileMsg(`premenované na ${r.name} — nezabudni na Push`);
  } catch (e) { profileFailed(e, $("#profile-msg")); }
}

async function deleteProfile() {
  const cur = $("#profile").value;
  if (!cur || !confirm(`Zmazať vlastný profil ${cur}? (zmaže súbor v tester/profiles/)`)) return;
  try {
    const r = await api(`/api/profiles/${encodeURIComponent(cur)}?strategy=${encodeURIComponent(state.strategy)}`, { method: "DELETE" });
    await applyProfileList(r, "");
    profileMsg(`${cur} zmazaný — nezabudni na Push`);
  } catch (e) { profileFailed(e, $("#profile-msg")); }
}

/** Uloženie profilu — `what` je buď {from_run}, alebo {params, instrument, timeframe}. */
async function saveProfile(what, msg) {
  const name = askProfileName("Meno profilu (medzera sa zmení na podtržník):", "");
  if (!name) return;
  const note = (prompt("Krátky popis, čo profil je (nepovinné):", "") || "").trim();
  const body = { name, note, strategy: state.strategy, ...what };
  msg.classList.remove("err"); msg.textContent = "ukladám…";
  try {
    let r;
    try {
      r = await api("/api/profiles", { method: "POST", body: JSON.stringify(body) });
    } catch (e) {
      if (!/už existuje/.test(e.message) || !confirm(`${e.message}. Prepísať ho?`)) throw e;
      r = await api("/api/profiles", { method: "POST", body: JSON.stringify({ ...body, overwrite: true }) });
    }
    if (r.strategy && r.strategy !== state.strategy) { setStrategy(r.strategy); }
    await applyProfileList(r, r.name);
    msg.textContent = `uložené ako ${r.name} — formulár teraz vychádza z neho, do gitu ide cez Push`;
  } catch (e) { msg.textContent = ""; profileFailed(e, msg); }
}

/** Beh z histórie ako východiskový profil pod vlastným menom. */
async function saveRunAsProfile() {
  if (!state.detailId) return;
  const rec = state.detailRecord;
  await saveProfile({ from_run: state.detailId, strategy: (rec && rec.settings && rec.settings.strategy) || state.strategy }, $("#save-profile-msg"));
}

/** Aktuálny formulár (vrátane zmeneného TF) ako vlastný profil. */
async function saveFormAsProfile() {
  const pair = state.meta.pairs.find(p => p.pair === $("#pair").value);
  if (!pair) { alert("Najprv vyber pár."); return; }
  await saveProfile({
    params: state.params, instrument: pair.instrument, timeframe: $("#tf").value,
    base: state.profile || null,
    timerange: timerange(), fee: $("#fee").value === "" ? null : Number($("#fee").value) / 100,
    wallet: Number($("#wallet").value), timeframe_detail: $("#detail").checked ? "1m" : null,
  }, $("#profile-msg"));
}

let profileLoadSeq = 0;

async function loadProfile(name) {
  const seq = ++profileLoadSeq;
  $("#profile-base").textContent = "";
  if (!name) {
    $("#run").disabled = false;
    state.profile = null; state.profileInstrument = null; updateProfileActions();
    setParams({}, true); checkPairProfile(); return;
  }
  // Kým hodnoty profilu nie sú vo formulári, beh sa spustiť nedá — inak by odišiel s menom
  // nového profilu a parametrami predošlého. `state.profile` sa prepne až s hodnotami.
  $("#run").disabled = true;
  let r;
  try {
    r = await api(`/api/profiles/${encodeURIComponent(name)}?strategy=${encodeURIComponent(state.strategy)}`);
  } catch (e) {
    if (seq !== profileLoadSeq) return;
    // Profil medzičasom zmizol (zmazaný inde, stránka má starý zoznam): obnov zoznam
    // a vráť formulár na Pine defaulty, aby meno profilu nesľubovalo iné hodnoty.
    try {
      await applyProfileList(await api(`/api/profiles?strategy=${encodeURIComponent(state.strategy)}`), "");
    } catch { $("#profile").value = ""; }
    state.profile = null; state.profileInstrument = null; updateProfileActions();
    setParams({}, true); checkPairProfile();
    profileMsg(`Profil ${name} sa nepodarilo načítať (${e.message}) — zoznam je obnovený, formulár je na Pine defaultoch.`, true);
    return;
  } finally {
    if (seq === profileLoadSeq) $("#run").disabled = false;
  }
  if (seq !== profileLoadSeq) return;   // medzitým si tester vybral iný profil
  state.profile = name;
  state.profileInstrument = r.instrument;
  updateProfileActions();
  setParams(r.params, true);
  // profil určuje aj nástroj -> prepni pár, ak zodpovedá
  const inst = r.instrument;
  const pair = state.meta.pairs.find(p => p.instrument === inst);
  if (pair) { $("#pair").value = pair.pair; $("#pair").onchange(); }
  // limity *MaxBars sú v baroch, takže k profilu patrí aj TF, na ktorom bol ladený;
  // profil bez `_timeframe` (tie z repozitára) znamená 3m, nie „nechaj, čo tam bolo"
  fillEngines($("#pair").value, r.engine);
  fillExchanges($("#pair").value, r.exchange);
  fillTimeframes($("#pair").value, r.timeframe || "3m");
  applyProfileSettings(r.settings || {});
  const chyba = (r.missing || []).length
    ? `profil nemá ${r.missing.length} ${r.missing.length === 1 ? "pole" : "polí"} (uložený pred ich pridaním) — beh použije default: ${r.missing.slice(0, 8).join(", ")}${r.missing.length > 8 ? "…" : ""}`
    : "";
  $("#profile-base").textContent = [r.base ? `vychádza z profilu ${r.base}` : "", chyba].filter(Boolean).join(" · ");
}

function currentPair() {
  return state.meta.pairs.find(p => p.pair === $("#pair").value) || null;
}

function isSpotPair() {
  const p = currentPair();
  return !!p && (p.market || "futures") === "spot";
}

function showMarket() {
  const p = currentPair();
  const el = $("#pair-market");
  if (!p) { el.textContent = ""; return; }
  const src = p.source || "?";
  const kind = p.kind || p.market || "futures";
  const popis = {spot: "spot — len longy, bez páky", futures: "futures perpetual",
                 cfd: "CFD (mimo burzy)"}[kind] || kind;
  el.textContent = `${src} ${p.exchange_symbol} · ${popis} (${p.pair})`;
}

/** Na spote nie sú shorty ani páka — hodnoty sa nastavia natvrdo, nech beh zodpovedá
 *  tomu, čo sa dá naozaj obchodovať. Vracia `true`, keď niečo zmenil. */
function enforceSpotParams() {
  if (!isSpotPair()) return false;
  let changed = false;
  if ("tradeDirection" in (state.meta.defaults || {}) && state.params.tradeDirection !== "Long only") { state.params.tradeDirection = "Long only"; changed = true; }
  if ("leverage" in (state.meta.defaults || {}) && Number(state.params.leverage) > 1) { state.params.leverage = 1; changed = true; }
  return changed;
}

/** Zamkne polia, ktoré na spote nemajú význam (a povie prečo). */
function lockSpotParams() {
  const spot = isSpotPair();
  for (const name of ["tradeDirection", "leverage"]) {
    const ctl = $(`.ctl[data-name="${name}"]`);
    if (!ctl) continue;
    ctl.classList.toggle("locked", spot);
    for (const el of ctl.querySelectorAll("input, select")) {
      el.disabled = spot;
      el.title = spot ? "Spotový pár: na spote sa nedá shortovať ani páčiť." : "";
    }
  }
}

/** Obdobie, poplatok, peňaženka a 1m detail uložené v profile — čo profil nemá,
 *  ostane tak, ako to má tester nastavené. Obdobie sa oreže na stiahnuté dáta páru. */
function applyProfileSettings(setup) {
  if (setup.timerange) {
    const o = $("#pair").selectedOptions[0];
    const [a, b] = setup.timerange.split("-").map(d => `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6)}`);
    const lo = (o && o.dataset.from) || a, hi = (o && o.dataset.to) || b;
    $("#from").value = a < lo ? lo : (a > hi ? hi : a);
    $("#to").value = b > hi ? hi : (b < lo ? lo : b);
  }
  if (setup.fee !== undefined) $("#fee").value = setup.fee * 100;
  if (setup.wallet !== undefined) $("#wallet").value = setup.wallet;
  if (setup.detail !== undefined) $("#detail").checked = !!setup.detail;
}

/** Profil je ladený na konkrétny nástroj — BTC prahy v bodoch na ETH dajú stovky nezmyselných obchodov. */
function checkPairProfile() {
  const box = $("#pair-warn");
  const pair = state.meta.pairs.find(p => p.pair === $("#pair").value);
  if (!pair || !state.profileInstrument || pair.instrument === state.profileInstrument) { box.hidden = true; return; }
  const fit = state.meta.profiles.filter(p => (state.meta.profile_instruments || {})[p] === pair.instrument);
  box.textContent = `Profil ${state.profile} je pre iný nástroj (${state.profileInstrument}). Prahy v bodoch/tickoch na ${pair.pair} nesedia a výsledok nebude porovnateľný. Pre tento pár: ${fit.join(", ") || "(Pine defaulty) alebo profil z docs/profily_archiv/"}.`;
  box.hidden = false;
}

/** Profil, s ktorým sa beh uloží do histórie — vždy ten, čo tester vidí v ponuke.
 *
 * Archívny profil („Načítať do formulára" z behu, ktorého profil už v `ibs/configs`
 * nie je) je cesta a v ponuke nie je — vtedy platí `state.profile`. */
function profileForRun() {
  const shown = $("#profile").value;
  if (shown) return shown;
  return state.profile && !state.meta.profiles.includes(state.profile) ? state.profile : null;
}

/** Rýchly rozsah obdobia: posledný rok, dva roky alebo celé dáta páru.
 *  Koniec je vždy koniec dát — na nedávnom okne testuje človek najčastejšie. */
function setQuickRange(years) {
  const o = $("#pair").selectedOptions[0];
  if (!o) return;
  const first = o.dataset.from, last = o.dataset.to;
  $("#to").value = last;
  if (years === "max") { $("#from").value = first; markQuickRange(years); return; }
  const d = new Date(last + "T00:00:00Z");
  if (years.endsWith("m")) {
    const day = d.getUTCDate();
    d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() - parseInt(years, 10));
    const lastDay = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
    d.setUTCDate(Math.min(day, lastDay));
  } else d.setUTCFullYear(d.getUTCFullYear() - Number(years));
  const want = d.toISOString().slice(0, 10);
  $("#from").value = want < first ? first : want;
  markQuickRange(years);
}

function markQuickRange(value) {
  for (const button of $$(".chip-btn[data-range]")) {
    button.classList.toggle("active", button.dataset.range === value);
    button.setAttribute("aria-pressed", String(button.dataset.range === value));
  }
}

function timerange() {
  const a = $("#from").value.replaceAll("-", ""), b = $("#to").value.replaceAll("-", "");
  return `${a}-${b}`;
}
