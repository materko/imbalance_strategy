# Agent B (Inžinier) — 1. kolo: ako sa stratégia buduje správne

*26. 11. 2026 · len čítanie: smernica (iCloud SMERNICA-TESTOVANIA), `.nightsearch/glsearch.py` + `glreport.py` +
`gl_state.json`, iCloud OOS-STARE-ROKY, `docs/ANALYTIKA.md`, literatúra (zdroje v časti 4).*

## 0. Tri čísla z nášho automatu, na ktorých stojí celý zvyšok

| čo | hodnota | odkiaľ |
|---|---|---|
| vyskúšaných kombinácií spolu | **1 551 132** na 85 stratégiách (TKS 82 129, Mag7 45 167, NOA 37 700) | `gl_state.json` → `combos` |
| koľkokrát sa pustil „odložený rok raz“ | **1 965×** (NOA 185 kandidátov, TKS 90, Mag7 86) — vždy ten istý rok 2025-09 – 2026-09 | `gl_state.json` → `candidates[].oos` |
| výsledok na rokoch pred ladením (nikto ich nevidel) | z 3 živých MNQ stratégií IBS EZ 0,79 · TKS 0,94 · VWAP ORB 0,96; obstálo 10 stratégií, väčšinou jednoduché | OOS-STARE-ROKY/VYSLEDKY_TRIEDENIA.md |

Literatúra presne toto predpovedá: veľa pokusov + výber najlepšieho = výsledok z ladenia je hlavne šum
(Bailey a kol. 2014; Harvey a Liu 2015). Technika (parita, krok 1, dáta) je u nás nadštandardná,
**chýba štatistika výberu**.

---

## 1. Proces budovania podľa literatúry (v krokoch)

1. **Hypotéza skôr než dáta.** Ekonomický dôvod, prečo má edge existovať (kto platí, prečo to nezmizne).
   Najprv sa formuluje, potom testuje; hľadanie v dátach bez dôvodu je „data mining“ (Aronson 2006, kap. 6;
   Harvey, Liu a Zhu 2016: t ≥ 3,0 pre nové faktory). López de Prado (2018, §11.4): *backtest nie je výskumný
   nástroj* — nástroj na overenie hotovej hypotézy, nie na jej hľadanie.
2. **Rozpočet pokusov vopred.** Zapísať, koľko variantov sa smie skúsiť; z dĺžky dát plynie strop
   (MinBTL: pri 5 rokoch denných dát najviac ~45 nezávislých konfigurácií, inak Sharpe 1,0 vznikne náhodou —
   Bailey, Borwein, López de Prado, Zhu 2014). **Evidovať všetky pokusy** vrátane zahodených.
3. **Jednoduchý model, málo stupňov voľnosti.** Zložitejšie stratégie strácajú naživo o > 30 % Sharpe viac
   (Suhonen, Lennkh, Perez 2017). Carver (2015): pravidlá „ručne“ / málo parametrov, robustne, nie optimum.
4. **Čisté dáta a realistické náklady** (spread, poplatok, sklz, rolovanie) už v ladení, nie až v stres teste.
   Carver: náklady nesmú zjesť viac než ~⅓ očakávaného hrubého Sharpe („speed limit“).
5. **Validácia, ktorá berie do úvahy výber:**
   - walk-forward ako *hlavný* postup (Pardo 2008, kap. 11; walk-forward efficiency = OOS výkon / IS výkon),
   - kombinatorická krížová validácia s purgingom a embargom (CPCV, López de Prado 2018, kap. 7 a 12),
   - **PBO** cez CSCV (Bailey a kol. 2017) — pravdepodobnosť, že víťaz ladenia je mimo vzorky pod mediánom,
   - **Deflated Sharpe Ratio** (Bailey a López de Prado 2014) — Sharpe opravený o počet pokusov, ich rozptyl,
     šikmosť, špicatosť a dĺžku záznamu; prah DSR ≥ 0,95,
   - **White Reality Check / Hansen SPA** (White 2000; Hansen 2005; aplikácia na technické pravidlá Sullivan,
     Timmermann, White 1999) — test „najlepší z N“ proti nule, nie test jedného pravidla,
   - **haircut Sharpe** (Harvey a Liu 2015) — kúpeľ Sharpe podľa počtu testov; „50 % na všetko“ je zlé
     pravidlo, marginálne stratégie strácajú takmer všetko.
6. **Holdout je jednorazový.** Keď sa na ňom robí výber (alebo sa naň opakovane pozerá), stáva sa
   in-sample (Bailey a kol. 2014, „holdout je nespoľahlivý“; López de Prado 2018 §11.6). Nové, nevidené dáta
   sa šetria na úplný koniec.
7. **Robustnosť:** plató v parametroch, iné trhy (aj iné *podkladové aktíva*, nielen iný zdroj dát), iné
   obdobia a režimy. Trend-following napr. je potvrdený na 67 trhoch a 137 rokoch (Hurst, Ooi, Pedersen 2017;
   Moskowitz, Ooi, Pedersen 2012) — to je úroveň dôkazu, ktorá robí edge vierohodným.
8. **Očakávaj zrážku naživo.** Medián Sharpe 215 bankových stratégií klesol z backtestu 1,20 na 0,31 naživo
   (−73 %; Suhonen a kol. 2017). Prediktory z publikácií: −26 % mimo vzorky, −58 % po publikácii
   (McLean a Pontiff 2016).
9. **Veľkosť pozície z rizika a portfólia**, nie z backtestu: cieľ volatility, zlomok Kelly, korelácie medzi
   stratégiami (Carver 2015, kap. 9–11). Pri prop účte drawdown limit = absorpčná hranica → riešiť
   pravdepodobnosť ruiny, nie priemerný DD.
10. **Paper / malá veľkosť s vopred zapísaným vypínacím pravidlom**, potom postupné zvyšovanie
    (Chan 2009, 2013; Carver 2015). Minimálna dĺžka záznamu (MinTRL) určuje, kedy je živý výsledok vôbec
    štatisticky čitateľný (Bailey a López de Prado 2012).

---

## 2. Literatúra vs. naša smernica

| # | čo hovorí literatúra | čo robí naša smernica / automat | rozdiel | závažnosť |
|---|---|---|---|---|
| 1 | Hypotéza pred dátami (Aronson; HLZ; LdP §11.4) | `glsearch` hľadá mriežkou + Optuna donekonečna, kým niečo neprejde; dôvod edge sa nezapisuje | výskum = data mining | **kritická** |
| 2 | Rozpočet pokusov vopred, MinBTL (~45 konf. na 5 r.) | pokusy sa len *počítajú*; jediný dôsledok: nad 1000 kombinácií OOS PF 1,3 namiesto 1,2 | 82 129 pokusov na 4 roky ladenia ≈ 3 rády nad MinBTL; prah sa nemení s N spojito | **kritická** |
| 3 | Holdout raz, nevidený | „odložený rok raz na kandidáta“ = 1 965 behov na *ten istý* rok; výber na stránku/webapp ho používa (glreport `ok`, „posl. rok PF“) | holdout je de facto in-sample (výber najlepšieho z desiatok OOS) | **kritická** |
| 4 | DSR ≥ 0,95 / PBO < ~0,2 ako brána | DSR počítaný (ROBUSTNOST 29. 10.), ale „na prejdenie nemá vplyv“; najvyšší 0,93, živé TKS 0,79, VWAP ORB 0,75, NOA 0,33 | metrika existuje a hovorí NIE, ignoruje sa | **kritická** |
| 5 | Reality Check / SPA: test najlepšieho z N | „test proti náhode“ v checkupe = 1 pravidlo proti náhodným vstupom | neopravuje výber z N; 95–99 % je ľahké pri tisícoch pokusov | vysoká |
| 6 | Walk-forward / CPCV ako hlavná validácia (Pardo; LdP) | walk-forward len „doplnkový“; jedno pevné rozdelenie IS/OOS | jedna cesta = jeden náhodný výsledok | vysoká |
| 7 | Haircut Sharpe podľa N (Harvey–Liu); zrážka 50–73 % | smernica: „naživo o 20–30 % nižšie“, PF 1,5 → 1,2–1,3 | očakávaná zrážka podhodnotená 2–3× | vysoká |
| 8 | Optimalizačný cieľ = robustný, nie max | skóre = PF (strop 4) + 0,3·najhorší rok; vrchol z ladenia → plató je **min ±1 krok len v skupine 4 parametrov**, prah 80 % | plató je lokálne, ignoruje ostatné parametre a TF; vrchol sa neposúva do stredu (glsearch berie `cur`) | stredná |
| 9 | Nezávislé potvrdenie na inom aktíve / období | krok 8: MNQ→NAS100, ES→US500, MGC→XAU, 6E→EURUSD (OTHER_MARKET) | to isté podkladové aktívum, iný zdroj dát — nie nezávislý dôkaz | stredná |
| 10 | Dĺžka záznamu / štat. sila (MinTRL) | OOS 1 rok, ~75–300 obchodov; prah PF ≥ 1,2 | pri PF 1,2 a 150 obch. je t ≈ 1 (pozri 3e) — OOS nemá silu nič potvrdiť | vysoká |
| 11 | Náklady realisticky už v ladení (Carver ⅓ SR) | poplatok áno (1,755e-05 MNQ); sklz len ako doplnkový stres; break-even poplatok ≥ 2× | sklz v ladení chýba; na ES staré roky poplatky zjedli PF 1,1–1,5 → 0,75 | stredná |
| 12 | Analytika mimo vzorky | checkup „5 okien“ = 4 roky ladenia + odložený rok | „4 z 5 rokov v pluse“ je takmer celé in-sample | stredná |
| 13 | Sizing z rizika + portfólio + ruina pri pevnom limite | testy na 1 kontrakt, MC DD 95 % ako vypínač; portfólio len doplnok | chýba P(ruina) pri FTMO 5 % denne / 10 % celkovo, korelácia stratégií v tých istých dňoch | vysoká |
| 14 | Vypínanie podľa vopred zapísaného štat. pravidla | „PF < 1 po 50 obchodoch“, DD > MC 95 % | 50 obchodov má SE PF ≈ ±0,3 — pravidlo je zároveň pomalé aj šumové; nevychádza z MinTRL/SPRT | stredná |
| 15 | Technická správnosť (no lookahead, parita) | krok 1 (1a–1d), C# parita, kontrola dát Databento | **nad literatúrou** — toto robíme dobre | — (silná stránka) |

---

## 3. Merateľné kritériá, ktoré nám chýbajú

**a) Register pokusov (povinný vstup všetkého ostatného).** Na stratégiu: N všetkých konfigurácií
(mriežka + hyperopt + ručné + výbery profilov + zmeny kódu po pozretí výsledkov), *efektívne* N po
zhlukovaní korelovaných pokusov (LdP 2018 §8; Bailey–LdP 2014 navrhujú odhad cez zhlukovanie). Dnes máme
len hrubé `combos`.

**b) DSR ako brána, nie informácia.** DSR ≥ 0,95 pri efektívnom N. Dnes by neprešla žiadna z 14
(ROBUSTNOST_2026-10-29). Ak považujeme N za nadhodnotené, odhadnúť efektívne N, nie prah zmäkčiť.

**c) PBO cez CSCV.** Matica výsledkov všetkých konfigurácií (máme ju v `gl_<key>.jsonl` — PnL po
mesiacoch treba doplniť), rozdeliť na S = 16 blokov, PBO ≤ 0,2 (Bailey a kol. 2017 ukazujú, že nad ~0,5 je
výber horší než náhodný). Lacné: nevyžaduje nové behy, ak sa ukladá mesačný PnL.

**d) Reality Check / SPA** nad všetkými konfiguráciami jednej stratégie (stationary bootstrap denných PnL),
p < 0,05. Nahradí dnešný test proti náhode tam, kde sa vyberalo.

**e) Minimálna štatistická sila OOS.** Hrubý odhad: PF 1,2 pri WR 50 % → priemer ~0,1 R, σ ~1,1 R →
t ≈ 0,09·√n. Pri 150 obchodoch t ≈ 1,1; pri 600 t ≈ 2,2; t = 3 potrebuje ~1 100 obchodov. → **OOS
kritérium = t-stat (alebo PSR) ≥ 2 na nevidených dátach**, nie PF ≥ 1,2 na 1 roku. Pre HLZ prah t ≥ 3
pri veľkom N.

**f) Walk-forward ako hlavná brána:** okná IS 2 r. / OOS 6 mes., reoptimalizácia **tým istým automatom
s tým istým rozpočtom**, spojená OOS krivka: PF ≥ 1,15, WFE ≥ 0,5, ≥ 70 % OOS okien v pluse. (WFE 0,5 je
bežná prax odvodená od Pardo 2008; presný prah v knihe overiť.)

**g) Haircut Sharpe (Harvey–Liu 2015)** z efektívneho N; do webapp a na stránku dávať **ohaircutované
očakávanie**, nie PF z ladenia. Pre marginálne stratégie (PF ~1,2–1,3) vychádza haircut 70–100 %.

**h) Skutočne nevidené dáta (krok 12 z MacBooku) s vopred zapísanou hranicou** — to je fakticky
CSCV/holdout v duchu literatúry a už ukázal svoju hodnotu. Doplniť: hranica rastie s N; po použití je
obdobie „spálené“ (zapísať dátum).

**i) Nezávislý trh** = iné podkladové aktívum tej istej triedy (MNQ → ES/MYM/DAX/Nikkei, MGC → SI/HG,
6E → 6B/6J) bez zmeny parametrov, PF > 1,05 a rovnaký znak vo väčšine rokov. Dukascopy CFD nechať ako test
zdroja dát.

**j) Riziko ruiny pre prop účet:** Monte Carlo blokovým bootstrapom *denných* PnL portfólia (zachová zhluky
ako november 2026), P(denná strata > 5 %) a P(celkový DD > 10 %) za 12 mesiacov; brána napr. ≤ 5 %.
Veľkosť pozície voliť tak, aby sa ňou splnila (cieľ volatility, Carver kap. 9–10).

**k) Sklz v ladení:** min. 1 tick/strana pri market/stop vstupoch už v hľadaní; break-even poplatok
počítať aj so sklzom. Carver: náklady ≤ ⅓ hrubého výnosu.

**l) Zložitosť:** strop počtu voľných parametrov (napr. ≤ 4–5 vrátane TF) a pravidlo „ak jednoduchšia verzia
dá ≥ 90 % výsledku, berie sa jednoduchšia“. Dáta OOS-STARE-ROKY to potvrdzujú: obstáli jednoduché stratégie.

**m) Živé vypínanie podľa sekvenčného testu** (SPRT / PSR proti backtestovanému SR) namiesto „PF < 1 po 50“;
MinTRL povie, po koľkých obchodoch je živý výsledok vôbec rozlíšiteľný od nuly.

### Navrhovaná minimálna brána (zhrnutie pre debatu)
`krok 1 ✓` → `register N` → `walk-forward OOS PF ≥ 1,15, WFE ≥ 0,5` → `DSR ≥ 0,95 alebo PBO ≤ 0,2` →
`nevidené roky raz, t ≥ 2` → `iné aktívum ✓` → `P(ruina prop) ≤ 5 %` → paper. Prah „PF z ladenia ≥ 1,3“ sa
stáva len filtrom kandidátov, nie dôkazom.

---

## 4. Zdroje

- Bailey D. H., Borwein J., López de Prado M., Zhu Q. J. (2014): *Pseudo-Mathematics and Financial
  Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance*, Notices of the AMS 61(5),
  458–471, doi:10.1090/noti1105 — MinBTL, „45 konfigurácií na 5 rokov“. https://www.ams.org/notices/201405/rnoti-p458.pdf
  (súhrn: https://phys.org/news/2014-04-pseudo-mathematics-financial-charlatanism.html)
- Bailey, Borwein, López de Prado, Zhu (2017): *The Probability of Backtest Overfitting*, Journal of
  Computational Finance 20(4), doi:10.21314/jcf.2016.322 — PBO, CSCV. https://papers.ssrn.com/abstract=2326253
- Bailey D. H., López de Prado M. (2014): *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest
  Overfitting and Non-Normality*, Journal of Portfolio Management 40(5). https://papers.ssrn.com/abstract=2460551
- Bailey D. H., López de Prado M. (2012): *The Sharpe Ratio Efficient Frontier* (PSR, MinTRL), Journal of Risk 15(2).
- López de Prado M. (2018): *Advances in Financial Machine Learning*, Wiley — kap. 7 (purged/embargoed CV),
  11 (§11.4 „Backtesting is not a research tool“), 12 (CPCV). https://www.oreilly.com/library/view/advances-in-financial/9781119482086/
- Harvey C. R., Liu Y. (2015): *Backtesting*, Journal of Portfolio Management 42(1) — haircut Sharpe.
  https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF
- Harvey C. R., Liu Y., Zhu H. (2016): *…and the Cross-Section of Expected Returns*, Review of Financial
  Studies 29(1) — prah t ≥ 3,0.
- White H. (2000): *A Reality Check for Data Snooping*, Econometrica 68(5), 1097–1126.
  https://users.ssc.wisc.edu/~bhansen/718/White2000.pdf
- Hansen P. R. (2005): *A Test for Superior Predictive Ability*, Journal of Business & Economic Statistics 23(4).
- Sullivan R., Timmermann A., White H. (1999): *Data-Snooping, Technical Trading Rule Performance, and the
  Bootstrap*, Journal of Finance 54(5), 1647–1691.
  https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf
- Aronson D. (2006): *Evidence-Based Technical Analysis*, Wiley — data-mining bias, Reality Check v praxi.
- Pardo R. (2008): *The Evaluation and Optimization of Trading Strategies*, 2. vyd., Wiley — kap. 11
  walk-forward, walk-forward efficiency. https://www.oreilly.com/library/view/the-evaluation-and/9781118045053/
- Carver R. (2015): *Systematic Trading*, Harriman House — cieľ volatility, „speed limit“ nákladov ⅓ SR,
  očakávaný Sharpe max ~1. https://harriman-house.com/systematic-trading (súhrn: https://www.cxoadvisory.com/big-ideas/a-few-notes-on-systematic-trading)
- Chan E. (2009, 2013): *Quantitative Trading*; *Algorithmic Trading*, Wiley — paper trading, Kelly, postupné zvyšovanie.
- Suhonen A., Lennkh M., Perez F. (2017): *Quantifying Backtest Overfitting in Alternative Beta Strategies*,
  Journal of Portfolio Management 43(2) — Sharpe −73 % naživo, zložitosť +30 % zrážky. https://alphaarchitect.com/?p=36892
- McLean R. D., Pontiff J. (2016): *Does Academic Research Destroy Stock Return Predictability?*, Journal of
  Finance 71(1), 5–32. https://econpapers.repec.org/RePEc:bla:jfinan:v:71:y:2016:i:1:p:5-32
- Moskowitz T., Ooi Y. H., Pedersen L. H. (2012): *Time Series Momentum*, Journal of Financial Economics 104(2).
- Hurst B., Ooi Y. H., Pedersen L. H. (2017): *A Century of Evidence on Trend-Following Investing*, Journal of
  Portfolio Management 44(1) — 67 trhov, 1880–2016. https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing
- Chague F., De-Losso R., Giovannetti B. (2019): *Day Trading for a Living?*, SSRN 3423101 — 97 % vytrvalých
  day traderov na futures (Brazília) prerobilo. https://ideas.repec.org/p/fgv/eesptd/525.html
- FTMO pravidlá (5 % denná, 10 % celková strata; výpočet dennej sa v zdrojoch líši — overiť na oficiálnej
  stránke): https://ftmo.oanda.com/how-to-pass-ftmo-challenge/

*Poznámka k istote: prah WFE ≥ 0,5 pochádza zo sekundárnych zdrojov (Pardo ho v dostupných ukážkach výslovne
neuvádza); čísla McLean–Pontiff (26 % / 58 %) sú z abstraktu podľa mojej znalosti, vyhľadávač potvrdil len
„dolnú hranicu ~32 %“ efektu publikácie. Ostatné citácie overené cez SSRN / vydavateľa.*
