# Základná analytika — VALUE AREA REVERSION 1.0 (Fabio Valentini) (`varev`)

Zmerané 2026-10-26 na `MNQ/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/varev/configs/mnq_databento_15m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy varev \
   --profile tradebot/strategies/varev/configs/mnq_databento_15m.json \
   --pair MNQ/USD \
   --timeframe 15m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 265 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 11.8 %
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001 v strate)
- break-even -0.0044 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 33 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.3 sigma) — výber vstupu nepridáva nič
- najhoršia skupina 'short' vlastnosti 'Smer': 172 obchodov (64.9 %), bez nej by break-even bol o +0.0288 lepší (riadi `tradeDirection`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 45 | -3.31 | -0.0797 | 4.4 | 20.0 | +1/-8 | `20261026-132154-df41d2` |
| 20221001-20231001 | 39 | -1.38 | -0.0392 | 1.8 | 33.3 | +3/-10 | `20261026-132200-794236` |
| 20231001-20241001 | 63 | -1.87 | -0.0234 | 3.1 | 19.1 | +3/-18 | `20261026-132204-acb1ad` |
| 20240904-20250904 | 63 | +2.03 | 0.0246 | 1.3 | 38.1 | +6/-7 | `20261026-132208-f3a426` |
| 20250904-20260904 | 58 | +3.34 | 0.0336 | 1.5 | 37.9 | +3/-6 | `20261026-132212-4d4676` |

Zisková v **2 z 5** okien, obchodov spolu 265, break-even celkom -0.0044 %. Okná sa prekrývajú, 3 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.40 ATR za 5 barov)
- medián držania 6.7 barov grafu
- winrate 29.43 %, payoff 2.248
- 0.15 obchodov za deň
- šikmosť výnosov +0.337

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 70.6 %, `take_profit` 29.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'short' vlastnosti 'Smer': 172 obchodov (64.9 %), break-even -0.0197 % oproti -0.0044 % celku. Bez nej by break-even bol 0.0244 % (+0.0288). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: skus preladit `tradeDirection`.


**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 172 | 64.9 % | 25.0 | -0.0197 | 0.0244 | +0.0288 |
| long | 93 | 35.1 % | 37.6 | 0.0244 | -0.0197 | -0.0153 |

**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| utorok | 64 | 24.2 % | 21.9 | -0.0551 | 0.0110 | +0.0154 |
| streda | 65 | 24.5 % | 33.9 | -0.0010 | -0.0056 | -0.0012 |
| štvrtok | 40 | 15.1 % | 30.0 | 0.0020 | -0.0056 | -0.0012 |
| pondelok | 47 | 17.7 % | 31.9 | 0.0135 | -0.0084 | -0.0040 |
| piatok | 49 | 18.5 % | 30.6 | 0.0323 | -0.0127 | -0.0083 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.3857 – 0.6093 | 66 | 24.9 % | 24.2 | -0.0524 | 0.0108 | +0.0152 |
| nad 0.6093 | 66 | 24.9 % | 42.4 | 0.0068 | -0.0081 | -0.0037 |
| 0.2474 – 0.3857 | 66 | 24.9 % | 27.3 | 0.0068 | -0.0082 | -0.0038 |
| do 0.2474 | 67 | 25.3 % | 23.9 | 0.0186 | -0.0126 | -0.0082 |

Parametre, ktorými sa dá s tým niečo spraviť: `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0044 % | 0.0005 % ± 0.0156 | -0.31 | 37.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0044 % | 0.0007 % ± 0.0169 | -0.30 | 38.9 |

Neodlisitelne od nahody (-0.3 sigma, percentil 37.3). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 55 | 3.8 | 21.8 | -0.0799 | 3 |
| 2023-01 - 2024-03 | 58 | 4.0 | 25.9 | -0.0322 | 21 |
| 2024-03 - 2025-06 | 81 | 5.6 | 32.1 | 0.0148 | 80 |
| 2025-06 - 2026-08 | 71 | 4.9 | 35.2 | 0.0208 | 84 |

Hranice pre úsek veľkosti posledného obdobia: -0.0568 až +0.0383 % (medián -0.0041).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 84. percentile, teda v medziach -0.0568 až +0.0383 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2024-10-18T01:45 až 2024-11-12T01:08, spolu +974.85.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-10-18T01:45 | 2024-10-18T13:12 | +223.57 | +0.55 | `take_profit` |
| 2 | 2024-10-18T15:45 | 2024-10-21T10:51 | +221.57 | +0.54 | `take_profit` |
| 3 | 2024-10-21T16:00 | 2024-10-21T19:54 | +109.06 | +0.27 | `take_profit` |
| 4 | 2024-10-22T13:45 | 2024-10-22T14:08 | +147.06 | +0.36 | `take_profit` |
| 5 | 2024-11-05T05:15 | 2024-11-05T14:31 | +189.59 | +0.47 | `take_profit` |
| 6 | 2024-11-11T20:15 | 2024-11-12T01:08 | +84.01 | +0.20 | `take_profit` |

**Straty za sebou: 18** — 2023-10-30T08:45 až 2024-01-10T14:32, spolu -1186.91.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-30T08:45 | 2023-10-30T09:10 | -62.01 | -0.22 | `stop_loss` |
| 2 | 2023-10-30T14:30 | 2023-10-31T17:53 | -270.01 | -0.94 | `stop_loss` |
| 3 | 2023-11-09T14:45 | 2023-11-09T14:59 | -80.08 | -0.26 | `stop_loss` |
| 4 | 2023-11-14T12:45 | 2023-11-14T13:01 | -30.09 | -0.10 | `stop_loss` |
| 5 | 2023-11-15T00:00 | 2023-11-15T01:15 | -17.12 | -0.05 | `stop_loss` |
| 6 | 2023-11-17T06:45 | 2023-11-17T06:48 | -14.12 | -0.04 | `stop_loss` |
| 7 | 2023-11-17T21:45 | 2023-11-19T23:00 | -52.62 | -0.17 | `stop_loss` |
| 8 | 2023-12-05T16:30 | 2023-12-06T00:16 | -170.12 | -0.54 | `stop_loss` |
| 9 | 2023-12-08T15:45 | 2023-12-08T19:47 | -144.13 | -0.45 | `stop_loss` |
| 10 | 2023-12-19T03:00 | 2023-12-19T03:15 | -20.19 | -0.06 | `stop_loss` |
| 11 | 2023-12-19T04:15 | 2023-12-19T08:23 | -30.69 | -0.09 | `stop_loss` |
| 12 | 2023-12-22T03:30 | 2023-12-22T09:33 | -13.19 | -0.04 | `stop_loss` |
| 13 | 2023-12-29T02:45 | 2023-12-29T03:00 | -12.70 | -0.04 | `stop_loss` |
| 14 | 2023-12-29T04:15 | 2023-12-29T04:18 | -5.20 | -0.02 | `stop_loss` |
| 15 | 2024-01-03T13:30 | 2024-01-03T14:13 | -83.17 | -0.25 | `stop_loss` |
| 16 | 2024-01-05T04:15 | 2024-01-05T04:54 | -13.65 | -0.04 | `stop_loss` |
| 17 | 2024-01-05T21:00 | 2024-01-08T09:29 | -121.65 | -0.37 | `stop_loss` |
| 18 | 2024-01-10T12:45 | 2024-01-10T14:32 | -46.18 | -0.14 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0044 %**, medián -0.0046 %, 90 % interval -0.0288–0.0183 %
- P(edge > poplatok) = **32.6 %**
- max drawdown: medián 6.1 %, 95. percentil 11.8 %, najhorší 21.4 %
- najdlhšia séria strát: medián 15, 95. percentil 23 obchodov
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
<!-- POSUDOK cisla=75c92000 -->

_Posudok (Claude, 26. 10. 2026) — repo profil „mnq_databento_15m“ (celý deň), MNQ 15m. Na porovnanie som pustil ladený
profil testera `VARev_POC_15m_NY` (len NY 9:30–16:00, cieľ POC) na tých istých piatich oknách (behy
`20261026-132719-5afefe` až `-132744-a86b00`)._

1. **Na čo sa to hodí a na čo nie.** Reverzia do value area (F. Valentini) dáva zmysel v likvidnej seanse, kde sa VA
   tvorí; repo profil obchoduje aj mimo NY. MNQ 15m, 0,15 obchodu denne.
2. **Má to potenciál?** Repo profil nie: 2 z 5 okien, break-even −0,0044 %, −0,3 σ proti náhode, 33 % bootstrapu;
   shorty (172, 65 %) majú −0,020 %. NY variant áno, ale nedokázaný: 4 z 5 okien v pluse (PF 4,87 / 1,17 / 1,50 /
   1,63 / 0,97), len 14–28 obchodov ročne (102 spolu) a posledný rok na nule. Náznak, nie dôkaz.
3. **Čo treba dorobiť.** Obmedzenie na NY a cieľ POC prevziať do repo profilu v `configs/` — dnešný repo profil meria
   inú stratégiu. Charakter vychádza ako prerazenie (vstup +0,40 ATR v smere pohybu), teda port vstupuje skôr s pohybom
   než proti nemu; overiť, či podmienka návratu do VA nie je príliš voľná. Shorty v rastovom trhu 2021–2026 brzdia.
4. **Čo otestovať ďalej.** `cli checkup --strategy varev --profile tester/profiles/VARev_POC_15m_NY.json --pair MNQ/USD --timeframe 15m --fee 1.755e-05 --wallet 60000`
   — test proti náhode na ~100 obchodoch rozhodne, či je NY variant odlíšiteľný (treba nad 2 σ).
   `cli matrix --pairs ES/USD,NAS100/USD --timeframes 15m,30m` — viac obchodov a iný trh.
5. **Je to použiteľné?** Repo profil je o ničom. NY variant: rozhodne checkup vyššie, dovtedy nie.
6. **Čo by som pridal.** Pravidlo 80 %: vstup až po tom, čo cena po výjazde z VA dve 15m sviečky uzavrie späť vnútri,
   cieľ protiľahlý okraj VA. Vstup by bol naozaj proti neúspešnému výjazdu, nie s pohybom.

<!-- POSUDOK KONIEC -->
