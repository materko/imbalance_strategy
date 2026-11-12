# Základná analytika — NOA 1.0 MGC (C# jadro) (`noamgcnet`)

Zmerané 2026-11-12 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/noamgcnet_PRESIEL_SMERNICAMI_NOA_1_0_MGC_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy noamgcnet \
   --profile .nightsearch/checkup/noamgcnet_PRESIEL_SMERNICAMI_NOA_1_0_MGC_1.json \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 420 obchodov spolu — na štatistiku dosť
- break-even 0.0347 % je nad poplatkom 0.0018 % (rezerva +0.0329 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 2.6 %
- odlíšiteľná od náhody (+2.4 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 77. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- 92.1 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 404 obchodov (96.2 %), bez nej by break-even bol o +0.0621 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 95 | +1.09 | 0.0207 | 0.7 | 48.4 | +6/-5 | `20261112-183255-7d861b` |
| 20221001-20231001 | 83 | +0.59 | 0.0130 | 0.6 | 48.2 | +6/-8 | `20261112-183304-93a64e` |
| 20231001-20241001 | 84 | +2.05 | 0.0340 | 0.5 | 52.4 | +4/-4 | `20261112-183316-fa3bce` |
| 20240904-20250904 | 88 | +2.28 | 0.0278 | 0.9 | 46.6 | +5/-8 | `20261112-183328-c72e5e` |
| 20250904-20260904 | 78 | +6.32 | 0.0566 | 1.4 | 44.9 | +5/-5 | `20261112-183343-35de23` |

Zisková v **5 z 5** okien, obchodov spolu 420, break-even celkom 0.0347 %. Okná sa prekrývajú, 8 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.29 ATR za 5 barov)
- medián držania 27.5 barov grafu
- winrate 47.86 %, payoff 1.803
- 0.23 obchodov za deň
- šikmosť výnosov +1.75

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 92.1 %, `stop_loss` 7.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 404 obchodov (96.2 %), break-even 0.0321 % oproti 0.0347 % celku. Bez nej by break-even bol 0.0968 % (+0.0621). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 404 | 96.2 % | 47.5 | 0.0321 | 0.0968 | +0.0621 |
| proti trendu | 16 | 3.8 % | 56.2 | 0.0968 | 0.0321 | -0.0026 |

**Vzdialenosť stopu** (riadi `hardStopPct`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.452 % – 0.5005 % | 105 | 25.0 % | 42.9 | -0.0089 | 0.0475 | +0.0128 |
| 0.4202 % – 0.452 % | 105 | 25.0 % | 50.5 | 0.0338 | 0.0350 | +0.0003 |
| nad 0.5005 % | 104 | 24.8 % | 50.0 | 0.0396 | 0.0331 | -0.0016 |
| do 0.4202 % | 106 | 25.2 % | 48.1 | 0.0665 | 0.0223 | -0.0124 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 8 | 110 | 26.2 % | 41.8 | -0.0011 | 0.0462 | +0.0115 |
| 15 – 23 | 106 | 25.2 % | 48.1 | 0.0341 | 0.0349 | +0.0002 |
| nad 23 | 100 | 23.8 % | 49.0 | 0.0419 | 0.0323 | -0.0024 |
| 8 – 15 | 104 | 24.8 % | 52.9 | 0.0629 | 0.0252 | -0.0095 |

Parametre, ktorými sa dá s tým niečo spraviť: `hardStopPct`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0347 % | 0.0036 % ± 0.0128 | +2.42 | 99.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0347 % | 0.0056 % ± 0.0133 | +2.19 | 98.5 |

Edge je odlisitelny od nahody (2.4 sigma, percentil 99.1).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 115 | 7.8 | 47.0 | 0.0166 | 24 |
| 2022-12 - 2024-03 | 95 | 6.4 | 50.5 | 0.0250 | 38 |
| 2024-03 - 2025-06 | 113 | 7.7 | 50.4 | 0.0331 | 53 |
| 2025-06 - 2026-09 | 97 | 6.6 | 43.3 | 0.0494 | 77 |

Hranice pre úsek veľkosti posledného obdobia: +0.0005 až +0.0761 % (medián 0.0309).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 77. percentile, teda v medziach +0.0005 až +0.0761 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2022-06-17T19:46 až 2022-07-21T19:55, spolu +369.29, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-06-17T19:46 | 2022-06-17T19:55 | +3.35 | +0.02 | `session_end` |
| 2 | 2022-06-30T16:46 | 2022-06-30T19:55 | +30.36 | +0.17 | `session_end` |
| 3 | 2022-07-05T14:36 | 2022-07-05T19:55 | +66.38 | +0.37 | `session_end` |
| 4 | 2022-07-06T14:45 | 2022-07-06T19:55 | +126.39 | +0.72 | `session_end` |
| 5 | 2022-07-20T18:45 | 2022-07-20T19:55 | +65.40 | +0.38 | `session_end` |
| 6 | 2022-07-21T16:37 | 2022-07-21T19:55 | +77.40 | +0.45 | `session_end` |

**Straty za sebou: 8** — 2022-11-18T19:47 až 2022-12-15T17:25, spolu -358.00, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-11-18T19:47 | 2022-11-18T20:25 | -4.61 | -0.03 | `session_end` |
| 2 | 2022-11-21T17:32 | 2022-11-21T20:55 | -28.61 | -0.16 | `session_end` |
| 3 | 2022-11-29T15:43 | 2022-11-29T16:25 | -62.62 | -0.35 | `session_end` |
| 4 | 2022-12-02T15:34 | 2022-12-02T16:29 | -67.63 | -0.38 | `stop_loss` |
| 5 | 2022-12-07T15:34 | 2022-12-07T16:25 | -29.63 | -0.17 | `session_end` |
| 6 | 2022-12-08T15:40 | 2022-12-08T16:25 | -52.63 | -0.29 | `session_end` |
| 7 | 2022-12-14T19:41 | 2022-12-14T20:11 | -87.64 | -0.48 | `stop_loss` |
| 8 | 2022-12-15T16:54 | 2022-12-15T17:25 | -24.63 | -0.14 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0347 %**, medián 0.0340 %, 90 % interval 0.0159–0.0546 %
- P(edge > poplatok) = **99.9 %**
- max drawdown: medián 1.5 %, 95. percentil 2.6 %, najhorší 6.0 %
- najdlhšia séria strát: medián 8, 95. percentil 12 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `c5e15c42`, tu je `a62c1b51`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=c5e15c42 -->

**1. Na čo sa to hodí.** _(C# jadro `noamgcnet`: čísla sú v každom okne zhodné s Python `noamgc`.)_ Intraday momentum (NOA) na zlate MGC 5m v seanse NY 9:30–16:00, jeden kontrakt, bez pozície cez noc. Ide o profil PREŠIEL SMERNICAMI č. 1 (12. 11. 2026). Výstupy sú v 92 % na kontrole (`session_end` = výstup cez VWAP / hranicu pásma alebo 16:00), to je podstata NOA.

**2. Potenciál.** Dobrý a stabilný: zisk v **5 z 5** okien (break-even 0,013–0,057 %, poplatok 0,0018 %). Proti náhode +2,4 sigma, edge nad poplatkom v 100 % bootstrapových vzoriek a v poslednom období drží (77. percentil). Posledný rok je najlepší (+6,3 %, WR 45 %). DD je malý (95. percentil 2,6 %).

**3. Čo dorobiť.** V logike nič, C# `noamgcnet` sedí s Pythonom bar po bare. Skupina „s trendom“ nesie 96 % obchodov, takže filter trendu tu neoddeľuje nič a netreba ho.

**4. Čo otestovať.** Forward test na C# jadre (NinjaTrader / MT5, 1 MGC) a porovnať živé obchody s históriou (Diverzifikácia → Živé behy). Druhý trh (XAU CFD) ukáže krok 8 smernice na stránke.

**5. Použiteľné?** **Áno.** Prešla smernicou aj odloženým rokom a je odlíšiteľná od náhody. Je to kandidát na forward test.

**6. Čo by som pridal.** Vynechať dni veľkých správ USA (CPI, FOMC, NFP): na zlate po správe pásmo šumu z histórie nesedí a NOA vtedy vstupuje do falošných pohybov.

<!-- POSUDOK KONIEC -->
