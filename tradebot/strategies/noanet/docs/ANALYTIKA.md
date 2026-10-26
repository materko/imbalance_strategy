# Základná analytika — NOA 1.0 (C# jadro) (`noanet`)

Zmerané 2026-10-26 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tester/profiles/SMERNICE_CS_NOA_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy noanet \
   --profile tester/profiles/SMERNICE_CS_NOA_1.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 778 obchodov spolu — na štatistiku dosť
- break-even 0.0396 % je nad poplatkom 0.0018 % (rezerva +0.0378 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 3.5 %
- odlíšiteľná od náhody (+5.0 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 15. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- 81.9 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 767 obchodov (98.6 %), bez nej by break-even bol o +0.1252 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 174 | +7.43 | 0.0484 | 1.0 | 41.4 | +5/-6 | `20261026-125615-57673c` |
| 20221001-20231001 | 175 | +4.51 | 0.0313 | 0.8 | 42.9 | +5/-6 | `20261026-125621-8d462d` |
| 20231001-20241001 | 131 | +6.12 | 0.0411 | 1.3 | 37.4 | +3/-11 | `20261026-125628-920083` |
| 20240904-20250904 | 144 | +12.26 | 0.0620 | 1.6 | 42.4 | +5/-6 | `20261026-125634-30dcbe` |
| 20250904-20260904 | 158 | +6.70 | 0.0257 | 1.7 | 38.6 | +4/-8 | `20261026-125640-2c1b68` |

Zisková v **5 z 5** okien, obchodov spolu 778, break-even celkom 0.0396 %. Okná sa prekrývajú, 4 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.00 ATR za 5 barov)
- medián držania 4.5 barov grafu
- winrate 40.62 %, payoff 2.609
- 0.43 obchodov za deň
- šikmosť výnosov +8.782

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 81.9 %, `stop_loss` 18.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 767 obchodov (98.6 %), break-even 0.0376 % oproti 0.0396 % celku. Bez nej by break-even bol 0.1648 % (+0.1252). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 767 | 98.6 % | 40.5 | 0.0376 | 0.1648 | +0.1252 |
| proti trendu | 11 | 1.4 % | 45.5 | 0.1648 | 0.0376 | -0.0020 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 678 | 87.1 % | 39.8 | 0.0320 | 0.0932 | +0.0536 |
| CPI | 34 | 4.4 % | 47.1 | 0.0519 | 0.0391 | -0.0005 |
| FOMC | 18 | 2.3 % | 44.4 | 0.0806 | 0.0387 | -0.0009 |
| NFP | 47 | 6.0 % | 46.8 | 0.1285 | 0.0338 | -0.0058 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 16 | 2.1 % | 37.5 | 0.0008 | 0.0404 | +0.0008 |
| bez udalosti | 678 | 87.1 % | 39.8 | 0.0320 | 0.0932 | +0.0536 |
| po vyhlásení | 84 | 10.8 % | 47.6 | 0.1099 | 0.0313 | -0.0083 |

Parametre, ktorými sa dá s tým niečo spraviť: `hardStopPct`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0396 % | 0.0018 % ± 0.0076 | +4.99 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0396 % | 0.0034 % ± 0.0085 | +4.26 | 100.0 |

Edge je odlisitelny od nahody (5.0 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 218 | 14.8 | 41.3 | 0.0505 | 72 |
| 2022-12 - 2024-03 | 201 | 13.6 | 38.8 | 0.0167 | 15 |
| 2024-03 - 2025-06 | 165 | 11.2 | 45.5 | 0.0830 | 95 |
| 2025-06 - 2026-09 | 194 | 13.2 | 37.6 | 0.0182 | 15 |

Hranice pre úsek veľkosti posledného obdobia: +0.0086 až +0.0811 % (medián 0.0357).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 15. percentile, teda v medziach +0.0086 až +0.0811 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2022-09-02T17:31 až 2022-09-07T19:55, spolu +146.24, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-09-02T17:31 | 2022-09-02T18:25 | +4.15 | +0.02 | `session_end` |
| 2 | 2022-09-02T19:00 | 2022-09-02T19:55 | +17.65 | +0.07 | `session_end` |
| 3 | 2022-09-06T17:19 | 2022-09-06T17:20 | +8.66 | +0.04 | `session_end` |
| 4 | 2022-09-07T16:57 | 2022-09-07T16:55 | +27.65 | +0.11 | `session_end` |
| 5 | 2022-09-07T18:17 | 2022-09-07T19:55 | +88.14 | +0.36 | `session_end` |

**Straty za sebou: 11** — 2023-10-10T15:25 až 2023-11-07T19:40, spolu -650.06.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-10T15:25 | 2023-10-10T17:12 | -163.07 | -0.53 | `stop_loss` |
| 2 | 2023-10-13T15:32 | 2023-10-13T16:30 | -52.07 | -0.17 | `session_end` |
| 3 | 2023-10-13T17:55 | 2023-10-13T18:05 | -16.56 | -0.05 | `stop_loss` |
| 4 | 2023-10-16T15:36 | 2023-10-16T15:35 | -36.07 | -0.12 | `session_end` |
| 5 | 2023-10-20T15:47 | 2023-10-20T16:30 | -71.53 | -0.24 | `session_end` |
| 6 | 2023-10-23T13:45 | 2023-10-23T13:48 | -84.52 | -0.29 | `stop_loss` |
| 7 | 2023-10-23T17:04 | 2023-10-23T17:19 | -64.04 | -0.22 | `stop_loss` |
| 8 | 2023-10-31T13:45 | 2023-10-31T14:05 | -51.51 | -0.18 | `session_end` |
| 9 | 2023-11-01T15:10 | 2023-11-01T15:10 | -46.53 | -0.16 | `session_end` |
| 10 | 2023-11-07T15:57 | 2023-11-07T17:05 | -41.58 | -0.14 | `session_end` |
| 11 | 2023-11-07T19:40 | 2023-11-07T19:40 | -22.58 | -0.07 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0396 %**, medián 0.0387 %, 90 % interval 0.0228–0.0601 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 2.1 %, 95. percentil 3.5 %, najhorší 7.4 %
- najdlhšia séria strát: medián 10, 95. percentil 14 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

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
<!-- POSUDOK cisla=889ebe26 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „NOA 1 C#“ (`SMERNICE_CS_NOA_1`, parametre zhodné s PREŠIEL SMERNICAMI
NOA 1.0 č. 1), C# jadro pre NinjaTrader 8 a MetaTrader 5._

1. **Na čo sa to hodí a na čo nie.** Index futures Nasdaq (MNQ / NQ) počas newyorskej seansy, graf 5m, jeden obchod
   naraz. Nehodí sa na trhy bez výrazného otvorenia (krypto 24/7, FX) — pásmo šumu sa počíta od 9:30 NY. Na účte
   60 000 $ je 95. percentil drawdownu 3,5 % (~2 100 $), séria 10 strát je medián, 14 ešte normálna (winrate 40,6 %,
   payoff 2,6). **Parita:** Python `noa` s tými istými parametrami dáva na okne 2021/22 presne 174 obchodov a +7,43 %
   ako tu — C# jadro obchoduje to isté, čo predloha. Rozdiel oproti analytike `noa` z 18. 10. (752 obchodov, break-even
   0,0429 %) robí oprava emulátora (N-CORE-1/2/3: plán vyplneného príkazu, SL v tej istej minúte, predhistória), nie
   jadro; analytiku `noa` treba prepočítať.
2. **Má to potenciál?** Áno. Za javom: zisk v 5 z 5 okien (+4,5 až +12,3 %), +5,0 sigma proti náhode (+4,3 aj proti
   vstupom v tých istých hodinách), break-even 0,0396 % je 22× nad poplatkom a 100 % bootstrapových vzoriek je nad
   ním; je to publikovaná anomália (Concretum / Zarattini). Za vzorkou: nastavenie vzišlo z rozsiahleho prehľadávania,
   posledné obdobie je na 15. percentile a posledný rok má najnižší break-even z piatich (0,0257 %) — slabšie, ale
   v medziach, ktoré stratégia vyrobí sama od seba.
3. **Čo treba dorobiť.** (a) 81,9 % výstupov je `session_end` — sú to zatvorenia na kontrolách cez VWAP / hranicu
   pásma aj o 16:00; v telemetrii a analytike by mali mať vlastné meno, aby sa dali oddeliť od konca dňa.
   (b) Skrátené seansy pred sviatkami (zatvára 13:00): overiť, že hodinové zatvorenie (`IClockFlatten`) pozíciu
   zavrie aj vtedy. (c) Skupina „s trendom“ (98,6 % obchodov) nie je filter, ale nastavenie filtra trendu.
4. **Čo otestovať ďalej.** Týždeň na Sim101 / MT5 deme po `install` (fasáda verzie 5) a
   `python -m tester.ninjatrader compare --strategy noanet --profile tester/profiles/SMERNICE_CS_NOA_1.json --timeframe 5m` — rozhodne, či sedia vstupy
   aj sklz naživo. `cli run --strategy noanet --profile tester/profiles/SMERNICE_CS_NOA_1.json --fee 3.51e-05`
   (2× poplatok; PF musí ostať nad 1). `cli matrix --pairs all --timeframes 5m` ukáže, či to drží aj na ES.
5. **Je to použiteľné?** Áno — robustné čísla, parita s predlohou je potvrdená. Na ostrý účet po forward teste
   4–8 týždňov na deme; dovtedy nie s reálnymi peniazmi.
6. **Čo by som pridal.** Riadenie veľkosti podľa makro dňa: obchody po vyhlásení (84, break-even 0,1099 %) a v deň
   NFP (47, 0,1285 %) sú 3–4× lepšie než bežné dni (0,0320 %), naopak 16 obchodov tesne pred vyhlásením je na nule
   (0,0008 %) — neotvárať pozíciu pár minút pred správou a v deň po nej zvýšiť riziko.

<!-- POSUDOK KONIEC -->
