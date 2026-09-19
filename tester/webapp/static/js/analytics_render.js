/* TradeBot Backtester — Vykreslenie analytiky: konfigurácia, slabnúci edge, portfólio, náhoda, charakter. */
"use strict";

/** Z akej konfigurácie tie obchody sú. Bez toho sa nedá vedieť, o čom čísla hovoria. */
function configHtml(c) {
  if (!c || !c.note) return "";
  const zoznam = Object.entries(c.differing || {}).map(([k, v]) =>
    `<li><b>${esc(k)}</b>: ${v.map(x => esc(typeof x === "object" && x
      ? `${x.value} ${x.unit || ""}`.trim() : String(x))).join(" · ")}</li>`).join("");
  const detail = zoznam
    ? `<details class="cfg-diff"><summary>v čom sa behy líšia</summary><ul>${zoznam}</ul></details>`
    : "";
  // Rozne profily su chyba (zliate rozne strategie), rozne cisla jedneho profilu su
  // zvycajne zamer (--set, prepocet na ATR) - preto dva stupne, nie jeden.
  if (c.severity === "chyba") return `<div class="warnbox">${esc(c.note)}${detail}</div>`;
  return `<p class="an-note${c.severity === "pozor" ? " warn" : ""}">`
    + `<b>Konfigurácia:</b> ${esc(c.note)}</p>${detail}`;
}

/** Slabne edge? Obdobia proti intervalu, ktorý stratégia vyrobí sama od seba. */
function decayHtml(d) {
  if (!d || !d.periods || !d.periods.length) return "";
  const trieda = { "DRZI": "good", "ZLEPSUJE SA": "good", "SLABNE": "bad" }[d.verdict] || "unsure";
  const posledny = d.periods.length - 1;
  const riadky = d.periods.map((p, i) => {
    // Percentil je test len pre posledne obdobie - ostatne su opis, nech to je vidiet.
    const cls = i === posledny ? "best" : "";
    const pc = p.percentile === null || p.percentile === undefined ? "—"
      : `${fmt(p.percentile, 0)}${i === posledny ? "" : "<span class=\"muted\"> (opis)</span>"}`;
    return `<tr class="${cls}"><td>${esc(p.label)}</td><td>${p.trades}</td>`
      + `<td>${fmt(p.per_month, 1)}</td><td>${fmt(p.winrate, 1)}</td>`
      + `<td>${fmt(p.break_even_pct, 4)}</td><td>${pc}</td></tr>`;
  }).join("");
  const pasmo = d.lo === null || d.lo === undefined ? ""
    : `<p class="an-note">Úsek takej dĺžky, akú má posledné obdobie, vyjde tej istej
        stratégii medzi <b>${fmt(d.lo, 4)}</b> a <b>${fmt(d.hi, 4)} %</b> už len
        preskladaním vlastných obchodov. Preto sa posledné obdobie neporovnáva s celkom:
        je kratšie, teda aj prirodzene rozkolísanejšie.</p>`;
  return `<div class="ch-box">
      <div class="ch-head"><h3>Slabne edge?</h3></div>
      ${pasmo}
      <table class="mx-table"><thead><tr><th>obdobie</th><th>obch.</th><th>/mes.</th>
        <th>WR %</th><th>break-even</th><th>percentil</th></tr></thead>
        <tbody>${riadky}</tbody></table>
      <div class="verdict ${trieda}">${esc(d.note || d.verdict)}</div>
    </div>`;
}

/** Portfólio: koľko sa dá zarobiť a za aký drawdown. */
function portfolioHtml(p) {
  if (!p || !p.risks) return "";
  const risks = p.risks.map(r => `<tr><td>${fmt(r.risk_pct, 2)} %</td>`
    + `<td>${fmt(r.return_pct, 1)} %</td><td>${fmt(r.cagr_pct, 1)} %</td>`
    + `<td class="${r.max_drawdown_pct > 30 ? "neg" : ""}">${fmt(r.max_drawdown_pct, 1)} %</td>`
    + `<td>${r.ruin ? "RUINA" : r.trades}</td></tr>`).join("");
  const roky = (p.by_year || []).map(r => `<tr><td>${esc(r.year)}</td>`
    + `<td class="${r.return_pct < 0 ? "neg" : "pos"}">${fmt(r.return_pct, 1)} %</td>`
    + `<td>${r.trades}</td></tr>`).join("");
  const dvojice = ((p.correlations || {}).pairs || []).slice(0, 5).map(
    ([a, b, r, m]) => `<tr><td class="${r >= 0.7 ? "neg" : ""}">${fmt(r, 2)}</td>`
      + `<td>${esc(a)}</td><td>${esc(b)}</td><td>${m} mes.</td></tr>`).join("");
  const trieda = p.verdict.startsWith("TO NIE JE PORTFOLIO") ? "bad"
    : (p.verdict.startsWith("CLENOVIA SU MALO") ? "good" : "unsure");
  return `<div class="ch-box">
      <div class="ch-head"><h3>Portfólio</h3>
        <span class="chip">${p.members.length} členov · ${p.trades} obchodov</span></div>
      <p class="an-note">Vybrané behy prehraté cez jeden účet. Veľkosť pozície sa prepočíta
        na zvolené riziko — bez toho by sa sčítavali veľkosti z rôznych behov a výsledok by
        hovoril o peňaženkách, nie o stratégii.</p>
      <table class="mx-table"><thead><tr><th>riziko/obchod</th><th>zhodnotenie</th>
        <th>ročne (CAGR)</th><th>max drawdown</th><th>obchodov</th></tr></thead>
        <tbody>${risks}</tbody></table>
      ${roky ? `<p class="an-note">Rok po roku (pri ${fmt(p.risks.find(r => r.risk_pct === 1)
        ? 1 : p.risks[0].risk_pct, 2)} % na obchod) — nesie to jeden rok, alebo je to rozložené?</p>
        <table class="mx-table"><thead><tr><th>rok</th><th>zhodnotenie</th><th>obchodov</th>
        </tr></thead><tbody>${roky}</tbody></table>` : ""}
      ${dvojice ? `<p class="an-note">Najkorelovanejšie dvojice — nad +0,70 sa členovia
        nediverzifikujú, len zväčšujú pozíciu.</p>
        <table class="mx-table"><thead><tr><th>r</th><th>člen</th><th>člen</th>
        <th>prekryv</th></tr></thead><tbody>${dvojice}</tbody></table>` : ""}
      <div class="verdict ${trieda}">${esc(p.verdict)}</div>
    </div>`;
}

/** Test proti náhode: je ten edge odlíšiteľný od hodu mincou? */
function nullHtml(nt) {
  if (!nt || !nt.nulls) return "";
  const riadky = Object.entries(nt.nulls).map(([kluc, v]) => {
    const trieda = v.sigma >= 2 ? "pos" : (v.sigma <= -1 ? "neg" : "noise");
    return `<tr><td>${esc(v.null_note || kluc)}</td>`
      + `<td>${fmt(v.observed, 4)}</td>`
      + `<td>${fmt(v.mean, 4)} ± ${fmt(v.sd, 4)}</td>`
      + `<td class="${trieda}">${v.sigma > 0 ? "+" : ""}${fmt(v.sigma, 2)} σ</td>`
      + `<td>${fmt(v.percentile, 1)}</td></tr>`;
  }).join("");
  const prvy = Object.values(nt.nulls)[0] || {};
  const trieda = prvy.sigma >= 2 ? "good" : (prvy.sigma <= -1 ? "bad" : "unsure");
  return `<div class="ch-box">
      <div class="ch-head"><h3>Je to odlíšiteľné od náhody?</h3></div>
      <p class="an-note">Tá istá stratégia, ktorá obchoduje rovnako často, rovnakým smerom
        a s rovnakým stopom aj take profitom — len si nevyberá, kedy vstúpiť. Rozdiel je
        presne to, čo výber vstupu prináša.</p>
      <table class="mx-table"><thead><tr><th>náhoda</th><th>stratégia</th>
        <th>náhoda</th><th>rozdiel</th><th>percentil</th></tr></thead>
        <tbody>${riadky}</tbody></table>
      <div class="verdict ${trieda}">${esc(prvy.verdict || "")}</div>
      ${nt.note ? `<p class="an-note">${esc(nt.note)}</p>` : ""}
    </div>`;
}

/** Syntetický trh: nevyrába tú výhodu náš backtest? */
function syntheticHtml(v) {
  if (!v || !v.rows || !v.rows.length) {
    if (!v || !v.verdict) return "";
    // Chýbajúce behy sa nezamlčia — je pri nich rovno príkaz, ktorým vzniknú.
    return `<div class="ch-box"><div class="ch-head"><h3>Nevyrába to náš backtest?</h3></div>
        <p class="an-note">${esc(v.verdict)}</p>
        ${v.command ? `<pre class="cmd">${esc(v.command)}</pre>` : ""}</div>`;
  }
  const cely = x => (x === null || x === undefined) ? "—" : fmt(x, 0) + " %";
  const riadky = v.rows.map(r => {
    const s2 = r.synth;
    return `<tr class="${s2 ? "" : "muted"}"><td>${esc(r.timerange)}</td>
        <td>${fmt(r.real.break_even_pct, 4)}</td><td>${r.real.trades}</td>
        <td>${cely(r.real.fill_pct)}</td>
        <td>${s2 ? fmt(s2.break_even_pct, 4) : "—"}</td>
        <td>${s2 ? s2.trades : "—"}</td><td>${s2 ? cely(s2.fill_pct) : "—"}</td></tr>`;
  }).join("");
  const trieda = { ok: "good", chyba: "bad" }[v.severity] || "unsure";
  return `<div class="ch-box">
      <div class="ch-head"><h3>Nevyrába to náš backtest?</h3>
        <span class="chip ${v.severity === "chyba" ? "warn" : ""}">${esc(v.severity || "")}</span></div>
      <p class="an-note">Tá istá konfigurácia na <b>premiešanom</b> trhu: rozdelenie výnosov
        aj celkový drift sú tie isté, zmizlo len poradie. Edge tam nemá z čoho vzniknúť —
        a keď predsa vznikne, vyrobil ho backtest.</p>
      <table class="mx-table"><thead><tr><th>okno</th><th>break-even</th><th>obch.</th>
        <th>vyplnené</th><th>synt. break-even</th><th>obch.</th><th>vyplnené</th></tr></thead>
        <tbody>${riadky}</tbody></table>
      <div class="verdict ${trieda}">${esc(v.verdict || "")}</div>
      ${v.command && (v.missing || []).length
        ? `<p class="an-note">Bez syntetického behu: ${v.missing.map(esc).join(", ")}</p>
           <pre class="cmd">${esc(v.command)}</pre>` : ""}
    </div>`;
}

/** Charakter stratégie: čísla, dôkazy a čo z toho vyplýva pre ladenie. */
function characterHtml(ch) {
  if (!ch || !ch.title) return "";
  const cisla = [
    ["winrate", ch.winrate, "%"],
    ["payoff (zisk / strata)", ch.payoff, ""],
    ["očakávanie na obchod", ch.expectancy_pct, "%"],
    ["medián držania", ch.median_bars, "barov"],
    ["obchodov za deň", ch.trades_per_day, ""],
    ["šikmosť výnosov", ch.skew, ""],
    ["pohyb pred vstupom", ch.pre_entry_atr, "ATR"],
    ["vstupov po pohybe", ch.momentum_share, "%"],
    ["teplo pred ziskom", ch.heat_ratio, "MAE/MFE"],
  ].filter(([, v]) => v !== null && v !== undefined);

  const vystupy = Object.entries(ch.exits || {})
    .map(([k, v]) => `${esc(k)} ${fmt(v, 1)} %`).join(" · ");

  return `<div class="ch-box">
      <div class="ch-head"><h3>${esc(ch.title)}</h3>
        <span class="chip ${ch.confidence === "dobrá" ? "" : "warn"}">istota ${esc(ch.confidence)}</span></div>
      <ul class="ch-evidence">${(ch.evidence || []).map(e => `<li>${esc(e)}</li>`).join("")}</ul>
      <div class="ch-grid">${cisla.map(([meno, v, u]) =>
        `<div><span>${esc(meno)}</span><b>${fmt(v, 2)}${u ? " " + esc(u) : ""}</b></div>`).join("")}</div>
      ${vystupy ? `<p class="an-note">výstupy: ${vystupy}</p>` : ""}
      <dl class="ch-advice">
        <dt>Čo je pri tomto type normálne</dt><dd>${esc(ch.normal || "")}</dd>
        <dt>Na čo pozor</dt><dd>${esc(ch.watch || "")}</dd>
        <dt>Čo ladiť</dt><dd>${esc(ch.tune || "")}</dd>
      </dl>
    </div>`;
}

/** Ostatné typy — aby bolo vidieť, do čoho sa stratégia zaradila a čo je vedľa. */
function archetypesHtml(list, aktivny) {
  if (!list || !list.length) return "";
  const rows = list.map(a => `<tr class="${a.key === aktivny ? "tuned" : ""}">
      <td>${esc(a.title)}</td><td class="wide">${esc(a.signature)}</td></tr>`).join("");
  return `<details class="ch-types"><summary>Aké typy stratégií rozoznávame</summary>
      <table class="verify-table"><tbody>${rows}</tbody></table>
      <p class="an-note">Zaradenie je pravidlá nad zmeranými číslami, nie model — vidno,
        prečo to vyšlo. Podrobne: docs/TYPY_STRATEGII.md</p></details>`;
}

function renderAnalytics(r) {
  // Okná behov: bez nich nie je vidieť, že "40 behov" je päť rokov, alebo štyridsaťkrát
  // ten istý rok s inými parametrami.
  const okna = (r.runs || []).map(x => x.timerange).filter(Boolean);
  const unikat = [...new Set(okna)].sort();
  const oknaText = unikat.length
    ? `okná: ${unikat.map(w => esc(fmtWindow(w))).join(" · ")}`
      + (okna.length > unikat.length ? ` · <b>${okna.length - unikat.length}×</b> to isté okno viackrát` : "")
    : "behy nemajú uložené okno";
  const ref = (state.anReferenceWindows || []);
  const chybaRef = ref.filter(w => !unikat.includes(w));
  const zhrnutie = [
    `<div class="headline">${esc(r.headline)}</div>`,
    `<p class="an-note"><b>${r.trades}</b> obchodov z <b>${r.runs.length}</b> behov`
      + ` · break-even <b>${fmt(r.break_even_pct, 4)} %</b> · winrate ${fmt(r.winrate, 1)} %`
      + ` · ${esc(r.pairs.join(", "))}</p>`,
    `<p class="an-note">${oknaText}</p>`,
  ];
  if (ref.length && chybaRef.length) {
    zhrnutie.push(`<div class="warnbox">Pokrýva len ${ref.length - chybaRef.length} z ${ref.length}`
      + " referenčných okien — jeden rok o stratégii nepovie nič. Chýbajú: "
      + chybaRef.map(w => esc(fmtWindow(w))).join(", ")
      + ". Pri vybranej konfigurácii ich doplní tlačidlo „Doplniť chýbajúce okná“.</div>");
  }
  zhrnutie.push(configHtml(r.config));
  if (r.mixed_pairs) {
    zhrnutie.push('<div class="warnbox">Zliate sú obchody z viacerých párov. Vzdialenosť'
      + " stopu ani prahy v cenových bodoch medzi nimi porovnateľné nie sú — pozeraj hlavne"
      + " hodinu, deň a smer, alebo si vyber jeden pár.</div>");
  }
  if (r.mixed_timeframes) {
    zhrnutie.push('<div class="warnbox">Zliate sú behy z viacerých timeframov ('
      + esc((r.timeframes || []).join(", ")) + "). Dĺžka v baroch a limity v baroch znamenajú"
      + " na každom inú vec — charakter je bez dĺžky držania a test proti náhode sa nepočíta.</div>");
  }
  // Po trhoch: to isté nastavenie na viacerých trhoch - drží myšlienka aj inde?
  const trhy = r.by_market || [];
  if (trhy.length > 1) {
    const refW = r.reference_windows || state.anReferenceWindows || [];
    const hlav = refW.map(w => `<th title="${esc(fmtWindow(w))}">${w.slice(2, 4)}/${w.slice(11, 13)}</th>`).join("");
    const rows = trhy.map(t => `<tr><td style="text-align:left">${esc(t.pair)} ${esc(t.timeframe)}</td>`
      + `<td>${t.trades}</td><td class="${t.positive === t.done_ref && t.done_ref ? "pos" : ""}">${t.positive} z ${t.done_ref}</td>`
      + refW.map(w => edgeCell(t.windows[w])).join("") + "</tr>").join("");
    const drzi = trhy.filter(t => t.done_ref && t.positive === t.done_ref).length;
    zhrnutie.push(`<div class="ch-box"><b>Po trhoch</b> — to isté nastavenie, break-even mínus poplatok trhu`
      + ` (% na stranu) v referenčných oknách. Nad poplatkom vo všetkých svojich oknách: <b>${drzi} z ${trhy.length}</b> trhov.`
      + `<table class="mx-table"><thead><tr><th style="text-align:left">trh</th><th>obchodov</th><th>nad popl.</th>${hlav}</tr></thead>`
      + `<tbody>${rows}</tbody></table>`
      + '<p class="an-note">Skupiny obchodov, náhoda a charakter sú pri zliatych trhoch vynechané alebo bez páru — na plnú analytiku vyber jeden trh.</p></div>');
  }
  if (r.duplicates) {
    zhrnutie.push(`<p class="an-note">${r.duplicates} obchodov bolo v dvoch behoch naraz`
      + " (prekrývajúce sa okná) — počítajú sa raz.</p>");
  }
  zhrnutie.push(portfolioHtml(r.portfolio));
  zhrnutie.push(decayHtml(r.decay));
  zhrnutie.push(nullHtml(r.nulltest));
  zhrnutie.push(syntheticHtml(r.synthetic));
  zhrnutie.push(characterHtml(r.character));
  zhrnutie.push(archetypesHtml(r.archetypes, (r.character || {}).archetype));
  zhrnutie.push(`<div class="an-runs">${r.runs.map(x =>
    `<span title="${esc(x.note)}">${esc(x.id)} · ${esc(fmtWindow(x.timerange))} (${x.trades})</span>`).join(" · ")}</div>`);
  $("#an-summary").innerHTML = zhrnutie.join("");

  const sekcia = (s, neskor) => {
    const posledny = s.buckets.length - 1;
    const rows = s.buckets.map((b, i) => {
      const cls = i === 0 ? "worst" : (i === posledny ? "best" : "");
      return `<tr class="${cls}"><td>${esc(b.label)}</td>`
        + `<td>${b.trades}</td><td>${fmt(b.share_pct, 1)} %</td>`
        + `<td>${fmt(b.winrate, 1)}</td><td>${fmt(b.break_even_pct, 4)}</td>`
        + `<td>${fmt(b.without_pct, 4)}</td>`
        + `<td>${b.impact === null ? "—" : (b.impact > 0 ? "+" : "") + fmt(b.impact, 4)}</td></tr>`;
    }).join("");
    // Parameter, ktory vlastnost riadi, je vedomost strategie - klik z neho spravi zadanie.
    const gate = s.param
      ? `<button class="ghost small param" data-param="${esc(s.param)}"
           title="Nachystá hľadanie tohto parametra na karte Nový beh">preladiť ${esc(s.param)}</button>`
      : "";
    return `<div class="an-split ${neskor ? "an-later" : ""}">
        <div class="an-head"><h3>${esc(s.title)}</h3>${gate}</div>
        <p class="an-note">${esc(s.note)}</p>
        <table><thead><tr><th>skupina</th><th>obch.</th><th>podiel</th><th>WR %</th>
          <th>break-even</th><th>bez nej</th><th>zmena</th></tr></thead>
        <tbody>${rows}</tbody></table>
      </div>`;
  };

  const casti = ["<h3>Vopred známe — podľa toho sa dá filtrovať</h3>"];
  casti.push(...r.splits.map(s => sekcia(s, false)));
  if ((r.descriptive || []).length) {
    casti.push("<h3>Známe až po obchode — len opis</h3>");
    casti.push('<p class="an-note">Tieto vlastnosti sa pri vstupe nedajú poznať, takže'
      + " „bez nej by break-even bol" + '" tu nie je príležitosť, ale pohľad dozadu.'
      + " Užitočné sú na to, aby bolo vidieť, kde obchody končia.</p>");
    casti.push(...r.descriptive.map(s => sekcia(s, true)));
  }
  $("#an-result").innerHTML = casti.join("");

  for (const b of $$("#an-result [data-param]")) {
    b.onclick = () => prepareTuning(b.dataset.param);
  }
}

/** Z analytiky rovno do hľadania: nachystá riadok parametra a prepne na formulár. */
async function prepareTuning(name) {
  showView("new");
  $("#sweep-box").open = true;
  const meta = metaByName()[name];
  $("#sweep-rows").innerHTML = "";
  addSweepRow(name);
  const row = $$("#sweep-rows .sweep-row").at(-1);
  if (isMatrix()) {
    const pocet = matrixPairs().length * matrixTimeframes().length;
    const min = pocet ? sweepMinutes(pocet) : 0;
    $("#sweep-run").textContent = pocet
      ? `▶ Prejsť trhy (${pocet} ${slovom(pocet, "beh", "behy", "behov")}${min ? ` ≈ ${fmtMinutes(min)}` : ""})`
      : "▶ Prejsť trhy";
    $("#sweep-run").disabled = !pocet;
    matrixWalletCheck();
  } else if (isHyper()) {
    const odporucane = (state.hyperMeta.suggested || {})[name];
    if (odporucane) row.querySelector("input.spec").value = odporucane;
  } else if (meta) {
    row.querySelector("input.spec").value = defaultSpec(meta);
  }
  refreshSweep();
  $("#sweep-status").textContent = `nachystané z analytiky: ${name}`;
  row.querySelector("input.spec").focus();
}
