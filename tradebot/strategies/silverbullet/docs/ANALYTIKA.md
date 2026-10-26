# Základná analytika — Silver Bullet 1.0 (ICT) — 10–11 NY, sweep, FVG (`silverbullet`)

Zmerané 2026-10-26 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/silverbullet/configs/mnq_databento_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy silverbullet \
   --profile tradebot/strategies/silverbullet/configs/mnq_databento_5m.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 234 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 11.7 %
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0061 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 31 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.5 sigma) — výber vstupu nepridáva nič
- najhoršia skupina 'short' vlastnosti 'Smer': 118 obchodov (50.4 %), bez nej by break-even bol o +0.0251 lepší (riadi `tradeDirection`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 49 | +0.74 | 0.0182 | 2.1 | 38.8 | +4/-6 | `20261026-131744-91d4f8` |
| 20221001-20231001 | 55 | +1.67 | 0.0365 | 1.1 | 41.8 | +4/-5 | `20261026-131750-1550c1` |
| 20231001-20241001 | 39 | -1.23 | -0.0246 | 2.3 | 30.8 | +3/-13 | `20261026-131756-bd612e` |
| 20240904-20250904 | 48 | -0.98 | -0.0129 | 4.0 | 35.4 | +4/-11 | `20261026-131802-f37b6c` |
| 20250904-20260904 | 43 | -2.42 | -0.0301 | 4.2 | 25.6 | +2/-10 | `20261026-131808-e177f9` |

Zisková v **2 z 5** okien, obchodov spolu 234, break-even celkom -0.0061 %.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.46 ATR za 5 barov)
- medián držania 10 barov grafu
- winrate 35.04 %, payoff 1.726
- 0.13 obchodov za deň
- šikmosť výnosov -0.473

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 65 %, `take_profit` 35 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'short' vlastnosti 'Smer': 118 obchodov (50.4 %), break-even -0.0302 % oproti -0.0061 % celku. Bez nej by break-even bol 0.019 % (+0.0251). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: skus preladit `tradeDirection`.


**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 118 | 50.4 % | 31.4 | -0.0302 | 0.0190 | +0.0251 |
| long | 116 | 49.6 % | 38.8 | 0.0190 | -0.0302 | -0.0241 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 9 | 64 | 27.4 % | 31.2 | -0.0590 | 0.0140 | +0.0201 |
| 9 – 15 | 57 | 24.4 % | 33.3 | -0.0166 | -0.0026 | +0.0035 |
| 15 – 23 | 57 | 24.4 % | 36.8 | 0.0240 | -0.0153 | -0.0092 |
| nad 23 | 56 | 23.9 % | 39.3 | 0.0366 | -0.0194 | -0.0133 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 182 | 77.8 % | 33.0 | -0.0109 | 0.0106 | +0.0167 |
| s trendom | 52 | 22.2 % | 42.3 | 0.0106 | -0.0109 | -0.0048 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0061 % | 0.0006 % ± 0.0150 | -0.45 | 32.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0061 % | 0.0011 % ± 0.0152 | -0.47 | 32.1 |

Neodlisitelne od nahody (-0.5 sigma, percentil 32.7). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 67 | 4.6 | 38.8 | 0.0323 | 90 |
| 2022-12 - 2024-03 | 58 | 4.0 | 31.0 | -0.0266 | 25 |
| 2024-03 - 2025-06 | 58 | 4.0 | 41.4 | -0.0085 | 44 |
| 2025-06 - 2026-08 | 51 | 3.5 | 27.4 | -0.0161 | 38 |

Hranice pre úsek veľkosti posledného obdobia: -0.0574 až +0.0504 % (medián -0.0058).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 38. percentile, teda v medziach -0.0574 až +0.0504 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 4** — 2022-08-08T15:00 až 2022-08-23T22:00, spolu +822.76, rovnako dlhých sérií 4.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-08-08T15:00 | 2022-08-08T15:42 | +210.07 | +0.79 | `take_profit` |
| 2 | 2022-08-11T14:33 | 2022-08-11T15:05 | +170.05 | +0.63 | `take_profit` |
| 3 | 2022-08-16T14:58 | 2022-08-16T15:47 | +207.54 | +0.77 | `take_profit` |
| 4 | 2022-08-23T14:34 | 2022-08-23T22:00 | +235.09 | +0.91 | `take_profit` |

**Straty za sebou: 13** — 2023-10-19T14:47 až 2024-01-11T16:13, spolu -1002.66.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-19T14:47 | 2023-10-19T15:14 | -65.55 | -0.22 | `stop_loss` |
| 2 | 2023-10-26T15:04 | 2023-10-26T15:23 | -106.50 | -0.37 | `stop_loss` |
| 3 | 2023-11-17T15:33 | 2023-11-17T16:05 | -63.11 | -0.20 | `stop_loss` |
| 4 | 2023-11-20T15:52 | 2023-11-20T16:00 | -51.62 | -0.16 | `stop_loss` |
| 5 | 2023-11-22T15:53 | 2023-11-24T14:31 | -74.62 | -0.23 | `stop_loss` |
| 6 | 2023-11-28T16:02 | 2023-11-28T16:31 | -67.13 | -0.21 | `stop_loss` |
| 7 | 2023-11-29T16:00 | 2023-11-29T16:10 | -67.63 | -0.21 | `stop_loss` |
| 8 | 2023-11-30T15:21 | 2023-11-30T15:38 | -102.62 | -0.32 | `stop_loss` |
| 9 | 2023-12-08T15:49 | 2023-12-08T19:49 | -109.63 | -0.34 | `stop_loss` |
| 10 | 2023-12-21T15:26 | 2023-12-21T17:08 | -113.68 | -0.34 | `stop_loss` |
| 11 | 2023-12-28T16:03 | 2023-12-28T18:03 | -37.70 | -0.11 | `stop_loss` |
| 12 | 2024-01-09T15:35 | 2024-01-09T15:43 | -33.68 | -0.10 | `stop_loss` |
| 13 | 2024-01-11T15:28 | 2024-01-11T16:13 | -109.18 | -0.32 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0061 %**, medián -0.0063 %, 90 % interval -0.0319–0.0196 %
- P(edge > poplatok) = **30.7 %**
- max drawdown: medián 6.0 %, 95. percentil 11.7 %, najhorší 20.7 %
- najdlhšia séria strát: medián 12, 95. percentil 20 obchodov
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
<!-- POSUDOK cisla=169573e7 -->

_Posudok (Claude, 26. 10. 2026) — repo profil „mnq_databento_5m“, MNQ 5m, okno 10–11 NY. Ladený profil testera
pre túto stratégiu nie je, toto je jediný obraz._

1. **Na čo sa to hodí a na čo nie.** ICT Silver Bullet na MNQ 5m: jedna hodina denne, 0,13 obchodu za deň (234 za päť
   rokov). V tejto podobe sa nehodí na nič — ani ako doplnok portfólia, lebo nemá edge, ktorý by sa dal pridať.
2. **Má to potenciál?** Nie. Zisková v 2 z 5 okien a to v najstarších (2021/22 0,018 %, 2022/23 0,037 %); posledné tri
   roky sú v strate (−0,025 / −0,013 / −0,030 %). Break-even −0,0061 % je pod poplatkom, −0,5 σ proti náhode,
   P(edge > poplatok) 31 %. Séria 13 strát (10/2023–1/2024) je pri tejto frekvencii štvrť roka bez zisku.
3. **Čo treba dorobiť.** Smer. Shorty (118 obchodov) majú break-even −0,030 %, longy +0,019 %; 78 % obchodov ide proti
   trendu (−0,011 %), s trendom +0,011 %. Model ICT predpokladá denný bias (kam ide likvidita) — v porte chýba.
   Výstupy sú len SL/TP (65/35 %) pri payoffe 1,7; cieľ na najbližšiu likviditu by bol bližší originálu.
4. **Čo otestovať ďalej.** `cli sweep --strategy silverbullet --profile mnq_databento_5m --pair MNQ/USD --timeframe 5m --space tradeDirection="Long only,Both" --space rrRatio=1:3:0.5`
   na piatich oknách — ak ani long-only nedá 4 z 5, stratégiu odložiť. `cli matrix --pairs all --timeframes 3m,5m`
   ukáže, či je to vlastnosť MNQ.
5. **Je to použiteľné?** Nie — v dnešnej podobe je to o ničom.
6. **Čo by som pridal.** Denný bias: obchodovať len v smere polohy ceny voči otvoreniu o 0:00 NY (alebo voči
   predchádzajúcemu dňu). Obe silnejšie skupiny z tabuliek (long, s trendom) ukazujú tým istým smerom.

<!-- POSUDOK KONIEC -->
