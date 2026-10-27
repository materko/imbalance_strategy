# S&P 500 (ES / MES) — ako trh funguje, čo dodržiava, čo nie (MacBook, 21. 10. 2026)

Podklad na skladanie stratégií na ES. Dve časti: **(A) rešerš z internetu** (fakty + výskum, so zdrojmi) a **(B) naše merania**
na 1m dátach **Dukascopy US500** (CFD na S&P 500, len ako náhrada, kým nie sú v archíve dáta ES z Databenta). Každé číslo z B je
porovnané s **NAS100** z toho istého zdroja, aby bolo vidno, v čom je S&P iný ako Nasdaq (na ktorom stoja naše stratégie).
**(C)** čo z toho plynie pre stratégie a **(D)** čo zmerať znova na skutočnom ES, keď ho IT nahrá (skripty v `skripty/`).

---

## A. Rešerš (internet)

**Kontrakt (CME):** ES = 50 $ × index, tick 0,25 b. = **12,50 $**; MES = 5 $ × index, tick **1,25 $**. Globex ne 18:00 – pi 17:00 ET,
denná prestávka **17:00–18:00 ET**. Seansa akcií 9:30–16:00 ET. Expirácia štvrťročne (3., 6., 9., 12.), tretí piatok, končí 9:30 ET
(vyrovnanie na otváraciu cenu indexu). **Rolovanie** tradične druhý štvrtok pred tretím piatkom (8 dní pred expiráciou); niektoré zdroje
uvádzajú pondelok týždňa expirácie — overiť v kalendári CME a podľa objemu (dni rolovania v backteste vyhodiť alebo spojiť bez skoku).
Limity poklesu 7 / 13 / 20 % (CME pravidlá).

**Časy, ktoré hýbu ES (ET):** 8:30 makro dáta (CPI, NFP, PPI, maloobchod), 9:30 otvorenie akcií, 10:00 dáta (ISM, JOLTS, sentiment),
14:00 FOMC (+ 14:30 tlačovka), **15:50 MOC imbalance NYSE** (uzávierka MOC/LOC príkazov, zverejnenie nerovnováhy; od 15:00 môžu prísť
skoršie zverejnenia) → pohyb do zavretia 16:00. Mesačná expirácia opcií (3. piatok), štvrťročná „quad witching“, koniec štvrťroka
(rebalansovanie fondov).

**0DTE opcie a gamma dealerov:** opcie na SPX s expiráciou v ten istý deň tvoria podľa dodávateľov dát **~40–60 % objemu opcií SPX**
(2025–2026). Keď sú dealeri **long gamma**, hedžujú proti pohybu (kupujú poklesy, predávajú rasty) → **tlmí to pohyb, deň býva v range**;
pri short gamma naopak zosilňuje. Je to dobre popísaný mechanizmus, ale nezávisle dokázaný efekt na ES chýba (hlavne komentáre
predajcov dát). Pre nás: ES má prirodzene viac „rangeových“ dní ako NQ.

**Výskum, ktorý stojí na S&P:**
- *Market Intraday Momentum* (Gao, Han, Li, Zhou, JFE 2018; SPY 1993–2013): výnos 1. polhodiny (od včerajšieho zavretia) predpovedá
  poslednú polhodinu, R² ~2 %, silnejšie v dni s vysokou volatilitou, objemom a makro správami.
- *Beat the Market* (Zarattini, Aziz, Barbon 2024; **SPY**): pásmo šumu (Noise Area, 14 dní), vstup pri úniku, posúvaný stop / VWAP;
  2007 – začiatok 2024: Sharpe 1,33, 19,6 % ročne po nákladoch (čísla autorov, nezávislá replikácia nenájdená). = naša **NOA**.
- *Can Day Trading Really Be Profitable* (Zarattini, Aziz 2023): 5-min ORB, hlavne **QQQ**; nezávislá replikácia na indexových CFD:
  pred nákladmi sedí, **po nákladoch ~0** (spread a sklz zjedia náskok).
- Nočná anomália (NY Fed 2020): väčšina výnosu indexov v noci, silnejšie po červenom dni (pre NQ sme overili; pre S&P viď B4).

**Gapy (internet, rôzne definície, len orientačne):** malé gapy (< 0,25–0,3 %) sa v ten deň vyplnia **80–90 %**, 0,25–0,5 % ~60–84 %,
0,5–1 % ~40–70 %, > 1 % ~20–55 %; väčšina vyplnení do poludnia. Naše čísla v B4 (jednotná definícia).

**Initial Balance (prvá hodina 9:30–10:30):** publikované štatistiky hlavne pre NQ (prieraz IB do poludnia ~83 %, do 16:00 ~96 %);
cieľ predĺženia 1–2× IB. Pre ES zmerať (D).

**ES vs NQ (prax, nie výskum):** NQ sa hýbe 1,5–2× viac v %, trenduje ostrejšie a otáča rovnako rýchlo; ES je „pokojnejší“, viac
rangeový, menšie pohyby v $ na kontrakt; 1 NQ ≈ 1,5–2 ES v dolárovej volatilite. Denne veľmi korelované, cez deň sa rozchádzajú
(tech správy). Priemerné denné rozpätie ES (MRCI, celý deň): 2022 **93 b.**, 2023 **54 b.**, 2024 **50 b.** Očakávaný denný pohyb z VIX:
VIX 15 ≈ 0,95 %, VIX 20 ≈ 1,26 %, VIX 25 ≈ 1,57 % (1 smerodajná odchýlka).

---

## B. Naše merania (US500 Dukascopy 1m, seansa 9:30–16:00 ET; 2021 – 8/2026, kontrola 2015–2020; vedľa NAS100 2021–2026)

### B1. Veľkosť pohybov
| | p10 | p25 | **medián** | p75 | p90 |
|---|---|---|---|---|---|
| S&P rozpätie seansy (body) | 25 | 35 | **49** | 71 | 98 |
| S&P rozpätie seansy (%) | 0,49 | 0,67 | **0,97** | 1,41 | 2,05 |
| NAS100 rozpätie seansy (%) | 0,75 | 0,99 | **1,37** | 1,93 | 2,70 |
- **S&P ≈ 0,7× Nasdaq v %**; v bodoch ES ≈ 1/4,8 NQ (49 vs 235 b.).
- Noc 18:00–9:30: medián **34 b. (0,67 %)** (NQ 0,92 %).
- Po rokoch (medián b. / %): 2021 35 / 0,81 · **2022 70 / 1,70** · 2023 40 / 0,93 · 2024 43 / 0,80 · 2025 58 / 0,90 · 2026 67 / 0,91.
  2015–2020: medián 0,79 % (2017 len 0,47 %).

### B2. Kedy sa trh hýbe (aktivita 5m sviečok, 100 = priemer seansy)
9:30 **145** · 10:00 **132** · 10:30 113 · 11:00 101 · 11:30 92 · 12:00 85 · 12:30 **82** · 13:00 86 · 13:30 **82** · 14:00 90 · 14:30 89 ·
15:00 91 · 15:30 **112** (NQ 15:30 len 98 → **S&P má silnejšie zavretie — MOC**).
- High / low seansy: 27 % v 9:30–10:00, **19 % v 15:30–16:00**; 37 % v prvej hodine, 25 % v poslednej (NQ 41 % / 22 %).
- Obed 12:00–13:30 je najmrtvejší (~82–86).

### B3. Trend alebo návrat k priemeru
| | variance ratio 5 / 15 / 30 / 60 min (1 = náhoda, < 1 návrat) | korelácia 9:30–10:00 → zvyšok dňa | ORB 30 min: +1R skôr ako opačná strana |
|---|---|---|---|
| S&P 2021–26 | 1,01 / 1,01 / 0,97 / 0,97 | +0,036 | 55 % |
| NAS100 2021–26 | 1,02 / 1,03 / 1,01 / 1,00 | +0,078 | 57 % |
| S&P 2015–20 | 0,97 / 0,91 / 0,86 / **0,83** | **−0,104** | 53 % |
- S&P je **menej trendový ako Nasdaq**; v rokoch 2015–2020 bol **výrazne návratový** (prvá polhodina predpovedala opačný smer).
  2021–26 skoro náhodná prechádzka. → Trendové stratégie (ORB, NOA, TKS) budú na ES slabšie ako na NQ; režim sa mení.

### B4. Gapy a noc
| gap pri otvorení 9:30 (vs zavretie 16:00) | dní | **vyplnený v ten deň** (S&P) | NAS100 |
|---|---|---|---|
| 0–0,25 % | 583 | **84 %** | 88 % |
| 0,25–0,5 % | 386 | 59 % | 67 % |
| 0,5–1 % | 294 | 35 % | 48 % |
| > 1 % | 143 | 24 % | 24 % |
(2015–2020: 78 / 51 / 31 / 16 %.) Veľké gapy S&P vypĺňa **menej** ako Nasdaq — pokračujú.
- Súčet výnosov 2021–26: seansa +46 %, noc +34 %. **Noc po červenom dni na S&P nepomáha** (2,2 bps vs 2,6 bps po zelenom),
  na NQ áno (4,5 vs 1,7) → nočná stratégia s filtrom červeného dňa sa na ES pravdepodobne neprenesie.

### B5. FVG (3-sviečková medzera, seansa)
| TF | počet / deň | veľkosť medián (body / % / × ATR) | p75 | dotyk | **odraz 1× veľkosť pred prerazením** | náhodná úroveň |
|---|---|---|---|---|---|---|
| 1m | 89 | 0,69 b. / 0,013 % / 0,32 | 1,30 | 90 % | 65 % | 62 % |
| 3m | 27,5 | 1,09 b. / 0,021 % / 0,28 | 2,28 | 90 % | 65 % | 62 % |
| 5m | 16,2 | 1,41 b. / 0,027 % / 0,26 | 2,90 | 90 % | 65 % | 62 % |
| 15m | 5,2 | 2,34 b. / 0,046 % / 0,24 | 4,87 | 86 % | 64 % | 60 % |
- **Bežné FVG sú len o ~3 p. b. lepšie ako náhodná úroveň** (rovnako na NQ) → samotné FVG ako signál takmer nič. Sú drobné:
  medián 1m FVG = 0,69 b. ≈ 3 ticky ES → náklady rozhodujú. Zmysel má len veľké FVG / FVG ako súčasť zóny (viď D).
- NQ pre porovnanie: 1m 2,92 b., 5m 6,41 b., 15m 10,79 b. (v % podobné, ES o ~25 % menšie).

### B6. SD zóny (báza 1–3 malé sviečky ≤ 0,6 ATR + impulz ≥ 1,5 ATR zavretý za bázou; prvý návrat do 3 dní)
| TF | zón / deň | výška × ATR | návrat | **odraz 2× výška pred prerazením** | **náhodná báza** | prerazená |
|---|---|---|---|---|---|---|
| 5m | 0,59 | 0,56 | 93 % | **50 %** | 30 % | 50 % (náhodná 70 %) |
| 15m | 0,19 | 0,57 | 89 % | **50 %** | 30 % | 50 % (náhodná 70 %) |
- **SD zóny sú najsilnejší štruktúrny jav: o ~20 p. b. lepšie ako náhoda** (NQ 47–52 % vs 29–32 %). Zóna z impulzu sa pri prvom
  návrate rešpektuje výrazne častejšie. → Stratégie postavené na zónach (IBS EZ, JSS, SD Zones) majú na ES dobrý základ.

---

## C. Čo z toho plynie pre stratégie na ES
1. **Veľkosti v ATR alebo %, nie v bodoch** (ES ≈ 1/4,8 bodov NQ, 0,7× v %). Medián seansy ~50 b., 1m ATR rádovo 2 b.
2. **Kedy obchodovať:** 9:30–11:00 a **15:00–16:00** (MOC, high/low dňa v 19 % dní v poslednej polhodine). Obed 12:00–13:30 vynechať.
3. **SD zóny áno, holé FVG nie.** Zónové stratégie sú najsľubnejšie; FVG len veľké alebo ako potvrdenie zóny.
4. **Trendové stratégie slabšie** ako na NQ (ORB 1:1 55 %, momentum dňa +0,04); fungovať môžu, ale s menším náskokom a závislé
   od režimu (2015–20 bol S&P návratový). NOA má výhodu, že pôvodný výskum je na SPY.
5. **Malé gapy (< 0,25 %) sa vyplnia v 84 %** → kandidát na stratégiu vyplnenia gapu; veľké gapy (> 0,5 %) skôr pokračujú.
6. **Posledná polhodina** (MOC 15:50, momentum Gao) — kandidát na samostatnú stratégiu.
7. Nočná stratégia s filtrom červeného dňa (ktorá na NQ funguje) na S&P **nefunguje**.
8. Náklady: tick ES 12,50 $ (MES 1,25 $); pri cieľoch pod 2–3 b. rozhoduje sklz.

## D. Na skutočnom ES (Databento), keď ho IT nahrá — postup
Skripty v `skripty/` (na Mac mini nastav `REPO=~/IBS`, na MacBooku sa nájde sám). Zdroj sa volí premennými:
```
cd skripty
SETS=ES:2019:2026 python p1.py      # veľkosti pohybov, profil dňa, kedy vzniká high/low
SETS=ES:2019:2026 python p2.py      # trend vs návrat, ORB, gapy, noc
SYMS=ES python p3.py                # FVG a SD zóny proti náhodným úrovniam
```
(Ak sa súbory volajú inak, napr. `MES_USD-1m`, použi `SETS=MES:...`; `load.py` hľadá `data/archive/tester/databento/futures/<SYM>_USD-1m.<rok>.feather`.)
Na ES navyše doplniť (skutočný objem burzy to umožní): Initial Balance (prieraz, predĺženie 1–2× IB, po časoch), Value Area / POC
predošlého dňa a pravidlo 80 %, VWAP (dotyky, návrat od ±1/2 σ), typy dní (trend / range / dvojité rozdelenie), FVG po veľkosti
(> 1 ATR) a v zónach, dni FOMC / CPI / NFP, expirácie a rolovanie, režimy volatility (realizovaná vol. 5/20 dní), London 3:00 a Ázia.
Ladenie stratégií podľa smernice: 2021-10 – 2025-09, odložený rok 2025/26 raz na konci.

## Zdroje
CME — E-mini S&P 500 špecifikácia: https://cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html ·
Micro E-mini: https://cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.contractSpecs.options.html ·
NYSE Closing Auction (15:50): https://www.nyse.com/publicdocs/nyse/NYSE_Auctions_Closing_Process_Fact_Sheet.pdf ·
SpotGamma 0DTE: https://spotgamma.com/0dte-options-explained/ · FlashAlpha 0DTE gamma: https://flashalpha.com/articles/0dte-gamma-exposure-pin-risk-intraday-options-analytics ·
Gao a kol. Market Intraday Momentum: https://profiles.wustl.edu/en/publications/market-intraday-momentum/ , https://alphaarchitect.com/2014/08/attention-prop-traders-the-first-half-hour-of-trading-predicts-the-last-half-hour/ ·
Zarattini, Aziz, Barbon Beat the Market (SPY): https://concretumgroup.com/beat-the-market-an-effective-intraday-momentum-strategy-for-sp500-etf-spy/ ·
ORB 5 min (CXO): https://www.cxoadvisory.com/technical-trading/day-trading-with-an-opening-range-breakout-strategy · replikácia: https://www.mql5.com/en/blogs/post/776235 ·
Gapy: https://nexusfi.com/a/strategies/gap-trading-futures , https://www.vtmarkets.com/discover/gap-trading-overnight-price-gaps-in-shares-indices/ ·
Rolovanie: https://investinglive.com/Education/what-the-september-futures-rollover-means-for-traders-es-and-nq-as-examples/ , https://crosstrade.io/learn/futures-trading/contract-rollover ·
Initial Balance: https://docs.edgeful.com/trade-using-edgeful/price-action-reports/initial-balance-breakout ·
ES vs NQ: https://www.edgeful.com/blog/posts/es-vs-nq-futures-comparison , https://bookmap.com/blog/nq-vs-es-why-they-move-together-until-they-dont ·
MRCI denné rozpätie ES: https://www.mrci.com/futstats/stat-esr.php
