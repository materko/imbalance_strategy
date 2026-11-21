# Základná analytika — SPRÁVY (EUR/USD) (`spravyeur`, čísla z C# jadra `spravyeurnet`)

Zmerané 2026-11-21 na `6E/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/spravyeurnet/configs/profil_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy spravyeurnet \
   --profile tradebot/strategies/spravyeurnet/configs/profil_1.json \
   --pair 6E/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 350 obchodov spolu — na štatistiku dosť
- break-even 0.0312 % je nad poplatkom 0.0018 % (rezerva +0.0294 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 5.1 %
- odlíšiteľná od náhody (+7.1 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 30. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 65.4 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'long' vlastnosti 'Smer': 165 obchodov (47.1 %), bez nej by break-even bol o +0.0148 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 67 | +17.11 | 0.0302 | 3.2 | 53.7 | +6/-6 | `20261121-102042-ee80a0` |
| 20221001-20231001 | 69 | +19.18 | 0.0378 | 2.9 | 58.0 | +5/-3 | `20261121-102045-f3c0c1` |
| 20231001-20241001 | 76 | +19.45 | 0.0266 | 3.2 | 51.3 | +5/-7 | `20261121-102048-f81d2f` |
| 20240904-20250904 | 78 | +26.46 | 0.0415 | 2.3 | 59.0 | +7/-3 | `20261121-102051-72e7c9` |
| 20250904-20260904 | 68 | +18.84 | 0.0217 | 1.7 | 51.5 | +3/-4 | `20261121-102054-efc37b` |

Zisková v **5 z 5** okien, obchodov spolu 350, break-even celkom 0.0312 %. Okná sa prekrývajú, 8 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (-0.23 ATR za 5 barov)
- medián držania 8.9 barov grafu
- winrate 54.86 %, payoff 2.007
- 0.2 obchodov za deň
- šikmosť výnosov +1.128

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `session_end` 65.4 %, `stop_loss` 32 %, `take_profit` 2.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'long' vlastnosti 'Smer': 165 obchodov (47.1 %), break-even 0.0151 % oproti 0.0312 % celku. Bez nej by break-even bol 0.046 % (+0.0148). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 165 | 47.1 % | 49.7 | 0.0151 | 0.0460 | +0.0148 |
| short | 185 | 52.9 % | 59.5 | 0.0460 | 0.0151 | -0.0161 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 20 | 5.7 % | 45.0 | 0.0056 | 0.0324 | +0.0012 |
| žiadna | 169 | 48.3 % | 55.6 | 0.0187 | 0.0430 | +0.0118 |
| CPI | 53 | 15.1 % | 62.3 | 0.0383 | 0.0304 | -0.0008 |
| NFP | 107 | 30.6 % | 52.3 | 0.0496 | 0.0207 | -0.0105 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 10 | 2.9 % | 50.0 | 0.0075 | 0.0320 | +0.0008 |
| bez udalosti | 169 | 48.3 % | 55.6 | 0.0187 | 0.0430 | +0.0118 |
| po vyhlásení | 171 | 48.9 % | 54.4 | 0.0454 | 0.0180 | -0.0132 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0279 % | 0.0001 % ± 0.0039 | +7.09 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0279 % | 0.0005 % ± 0.0041 | +6.63 | 100.0 |

Edge je odlisitelny od nahody (7.1 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 85 | 5.8 | 51.8 | 0.0286 | 38 |
| 2022-12 - 2024-03 | 89 | 6.0 | 56.2 | 0.0423 | 83 |
| 2024-03 - 2025-06 | 95 | 6.5 | 59.0 | 0.0306 | 47 |
| 2025-06 - 2026-09 | 81 | 5.5 | 51.9 | 0.0252 | 30 |

Hranice pre úsek veľkosti posledného obdobia: +0.0141 až +0.0504 % (medián 0.0313).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 30. percentile, teda v medziach +0.0141 až +0.0504 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 7** — 2025-04-03T15:00 až 2025-05-04T22:00, spolu +5150.42.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-04-03T15:00 | 2025-04-03T15:55 | +845.12 | +0.61 | `session_end` |
| 2 | 2025-04-04T15:15 | 2025-04-06T22:00 | +895.17 | +0.65 | `session_end` |
| 3 | 2025-04-10T13:00 | 2025-04-10T14:55 | +1088.84 | +0.78 | `session_end` |
| 4 | 2025-04-17T13:45 | 2025-04-17T14:40 | +176.25 | +0.12 | `session_end` |
| 5 | 2025-04-29T15:00 | 2025-04-29T15:25 | +402.48 | +0.14 | `session_end` |
| 6 | 2025-05-02T12:30 | 2025-05-02T12:55 | +377.53 | +0.13 | `session_end` |
| 7 | 2025-05-02T15:15 | 2025-05-04T22:00 | +1365.03 | +0.48 | `session_end` |

**Straty za sebou: 7** — 2024-04-03T15:00 až 2024-05-01T15:25, spolu -2066.54.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-04-03T15:00 | 2024-04-03T15:23 | -239.29 | -0.06 | `stop_loss` |
| 2 | 2024-04-05T12:30 | 2024-04-05T12:30 | -397.04 | -0.15 | `stop_loss` |
| 3 | 2024-04-05T15:15 | 2024-04-05T15:43 | -295.55 | -0.07 | `stop_loss` |
| 4 | 2024-04-10T13:00 | 2024-04-10T13:10 | -296.98 | -0.11 | `stop_loss` |
| 5 | 2024-04-11T13:15 | 2024-04-11T13:29 | -271.96 | -0.10 | `stop_loss` |
| 6 | 2024-04-11T13:45 | 2024-04-11T14:19 | -446.94 | -0.17 | `stop_loss` |
| 7 | 2024-05-01T15:00 | 2024-05-01T15:25 | -118.78 | -0.02 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0312 %**, medián 0.0312 %, 90 % interval 0.0228–0.0403 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 3.1 %, 95. percentil 5.1 %, najhorší 9.6 %
- najdlhšia séria strát: medián 7, 95. percentil 9 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **3 428** na obchod pri účte 60 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

Chýba. Napíše ho AI: prečíta čísla vyššie a odpovie na týchto šesť otázok. Text patrí **medzi značky** nižšie, aby ho ďalší `cli checkup` preniesol ďalej.

1. **Na čo sa to hodí a na čo nie** — trh, timeframe, režim, veľkosť účtu; kde by to isté číslo znamenalo niečo iné.
2. **Má to potenciál?** Čo z čísel hovorí, že za tým je skutočný jav, a čo hovorí, že je to vlastnosť vzorky.
3. **Čo treba dorobiť** v samotnej stratégii — filtre, výstupy, sizing, sviatky a seansy, chýbajúce parametre.
4. **Čo otestovať ďalej** — konkrétne príkazy (`cli sweep`, `cli matrix`, `cli hyperopt`, druhý engine) a čo by ich výsledok rozhodol.
5. **Je to použiteľné, alebo je to o ničom?** Odpoveď má byť jednoznačná; „ešte uvidíme" je odpoveď len vtedy, keď je za ňou konkrétny test.
6. **Čo by som pridal** — nápad, ktorý v stratégii nie je a z týchto čísel dáva zmysel.
<!-- POSUDOK cisla=bb6d8eef -->

_21. 11. 2026, profil 1 (výskum + ladenie na Mac mini)._

1. **Na čo sa to hodí a na čo nie.** EUR/USD (6E futures, EURUSD CFD) okolo naplánovaných správ USA a ECB, 5m graf,
   ~70 obchodov za rok, riziko 500 $ na obchod → účet od ~25–60 tis. $ (95. percentil DD 5,1 % pri 60 tis.). Nie je to
   denná stratégia na plynulý príjem: 0,2 obchodu za deň a väčšina mesiacov má 5–7 obchodov. Na inom trhu (zlato, indexy)
   tie isté pravidlá neplatia — každá správa má inú reakciu (zlato: vlastný profil SPRÁV).
2. **Potenciál — áno.** Za javom je výskum, nie len optimalizátor: návrat 6E po správach USA (JOLTS, PPI, CPI, ISM) drží
   5–6 rokov zo 6 a v tých istých časoch dní bez správ nie je; trend po FOMC a tlačovke ECB tiež. Tu: 5 z 5 okien v zisku,
   +7,1 sigma nad náhodným vstupom v tých istých hodinách, posledný rok (odložený) PF 2,14, EUR/USD CFD PF 2,33, 2× poplatok
   a vstup o sviečku neskôr drží. Proti: pravidlá NFP (drift pred správou a trend o 165 min) prišli z hľadania, nie z výskumu
   (výskum pri NFP ukázal návrat a ten je aj v kontrolných dňoch) — sú najslabším miestom; DSR 0,81 pri 27 600 skúškach.
3. **Čo dorobiť.** 65 % obchodov končí na čase — v poriadku (zámer: držanie po správe), ale treba overiť, že presun času
   výstupu o ±30 min výsledok nemení. Long je výrazne slabší (break-even 0,015 vs. short 0,046) — overiť na zlate, či je to
   vlastnosť EUR (silný dolár po správach) alebo náhoda, potom prípadne `allowLong` po pravidlách. Kalendár: ECB 2016–2028,
   USA do 11–12/2027 (Retail 2027 Census ešte nezverejnil — EUR ho neobchoduje); presuny správ zachytí hub (ff_calendar).
4. **Čo otestovať ďalej.** (a) Bez pravidiel NFP (r7, r8) — ak drží PF ≥ 1,5 v každom roku, je robustnejší než profil 1;
   (b) `python -m tester.robust` s počtom skúšok 27 600 (DSR), (c) forward test na demo účte MT5 (EURUSD) aspoň 2 mesiace —
   ~12 obchodov, rozhodne len o technike (časy, sklz pri správach), nie o edge, (d) sklz: 6E pri správach o 1–2 ticky horší
   fill — `--fee` ×2 už drží, overiť aj ×3.
5. **Použiteľné?** Áno — ako samostatný „správový“ modul s malým počtom obchodov. Najsilnejšia časť (fade po správach USA,
   trend po FOMC / ECB) má oporu vo výskume; NFP pravidlá berte ako podmienené, kým neprejde test (a).
6. **Čo by som pridal.** Filter veľkosti prvého pohybu pri fade pravidlách (výskum: pri pohybe ≥ 0,15 ATR je návrat
   čistejší) a eurozónne správy (flash HICP, PMI) — v kalendári chýbajú, historické termíny treba z Eurostatu / datasetu
   ForexFactory; s nimi by obchodov pribudlo bez nových typov logiky.

<!-- POSUDOK KONIEC -->
