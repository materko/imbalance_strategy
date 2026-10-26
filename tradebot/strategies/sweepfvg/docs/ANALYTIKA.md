# Základná analytika — SWEEP FVG 1.0 — výber LQ, CHoCH / BOS, FVG (`sweepfvg`)

Zmerané 2026-10-26 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/sweepfvg/configs/mnq_databento_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sweepfvg \
   --profile tradebot/strategies/sweepfvg/configs/mnq_databento_5m.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 930 obchodov spolu — na štatistiku dosť
- break-even 0.0055 % je nad poplatkom 0.0018 % (rezerva +0.0037 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 37. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20231001-20241001, 20240904-20250904 v strate)
- edge nad poplatkom len v 60 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 30.0 % (namerané 14.6 % medián) — na účet to treba mať
- proti náhode len +0.3 sigma: náznak, nie dôkaz
- najhoršia skupina '1.426 – 2.166' vlastnosti 'Volatilita voči normálu': 232 obchodov (24.9 %), bez nej by break-even bol o +0.0169 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 203 | +9.23 | 0.0512 | 8.6 | 36.0 | +4/-10 | `20261026-131926-4b7176` |
| 20221001-20231001 | 168 | +1.70 | 0.0131 | 3.8 | 33.3 | +7/-11 | `20261026-131936-c2288f` |
| 20231001-20241001 | 195 | -3.37 | -0.0127 | 10.5 | 33.3 | +4/-12 | `20261026-131945-fbcd87` |
| 20240904-20250904 | 184 | -5.75 | -0.0203 | 6.8 | 27.7 | +3/-14 | `20261026-131953-da8af0` |
| 20250904-20260904 | 192 | +0.12 | 0.0021 | 9.7 | 35.4 | +7/-9 | `20261026-132001-1264c3` |

Zisková v **3 z 5** okien, obchodov spolu 930, break-even celkom 0.0055 %. Okná sa prekrývajú, 12 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.86 ATR za 5 barov)
- medián držania 33.2 barov grafu
- winrate 33.44 %, payoff 2.038
- 0.52 obchodov za deň
- šikmosť výnosov +1.277

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 66.6 %, `take_profit` 33.2 %, `force_exit` 0.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '1.426 – 2.166' vlastnosti 'Volatilita voči normálu': 232 obchodov (24.9 %), break-even -0.0476 % oproti 0.0055 % celku. Bez nej by break-even bol 0.0224 % (+0.0169). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.426 – 2.166 | 232 | 24.9 % | 27.2 | -0.0476 | 0.0224 | +0.0169 |
| do 0.934 | 233 | 25.1 % | 31.3 | -0.0001 | 0.0075 | +0.0020 |
| 0.934 – 1.426 | 233 | 25.1 % | 38.6 | 0.0260 | -0.0013 | -0.0068 |
| nad 2.166 | 232 | 24.9 % | 36.6 | 0.0432 | -0.0067 | -0.0122 |

**Kalendárny mesiac**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 06 | 92 | 9.9 % | 20.6 | -0.1108 | 0.0193 | +0.0138 |
| 05 | 80 | 8.6 % | 31.2 | -0.0673 | 0.0121 | +0.0066 |
| 07 | 79 | 8.5 % | 24.1 | -0.0629 | 0.0123 | +0.0068 |
| 11 | 66 | 7.1 % | 24.2 | -0.0301 | 0.0081 | +0.0026 |
| … | | | | | | |
| 09 | 65 | 7.0 % | 38.5 | 0.0323 | 0.0036 | -0.0019 |
| 04 | 78 | 8.4 % | 41.0 | 0.0633 | 0.0005 | -0.0050 |
| 10 | 86 | 9.2 % | 44.2 | 0.0771 | -0.0013 | -0.0068 |
| 03 | 70 | 7.5 % | 47.1 | 0.1162 | -0.0029 | -0.0084 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.5085 | 234 | 25.2 % | 27.8 | -0.0282 | 0.0170 | +0.0115 |
| 0.5085 – 0.6866 | 232 | 24.9 % | 30.2 | -0.0202 | 0.0139 | +0.0084 |
| nad 0.8299 | 232 | 24.9 % | 39.2 | 0.0288 | -0.0024 | -0.0079 |
| 0.6866 – 0.8299 | 232 | 24.9 % | 36.6 | 0.0420 | -0.0065 | -0.0120 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0055 % | 0.0018 % ± 0.0117 | +0.31 | 62.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0055 % | 0.0018 % ± 0.0117 | +0.31 | 62.5 |

Neodlisitelne od nahody (+0.3 sigma, percentil 62.5). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 234 | 15.9 | 35.0 | 0.0451 | 92 |
| 2022-12 - 2024-03 | 226 | 15.3 | 35.0 | 0.0218 | 70 |
| 2024-03 - 2025-06 | 235 | 15.9 | 30.6 | -0.0200 | 16 |
| 2025-06 - 2026-09 | 235 | 15.9 | 33.2 | -0.0043 | 37 |

Hranice pre úsek veľkosti posledného obdobia: -0.0398 až +0.0504 % (medián 0.0044).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 37. percentile, teda v medziach -0.0398 až +0.0504 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 7** — 2023-04-18T05:25 až 2023-04-28T11:31, spolu +1028.60, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-04-18T05:25 | 2023-04-18T06:18 | +52.57 | +0.20 | `take_profit` |
| 2 | 2023-04-20T19:02 | 2023-04-25T16:33 | +410.59 | +1.57 | `take_profit` |
| 3 | 2023-04-26T07:10 | 2023-04-26T11:04 | +102.59 | +0.40 | `take_profit` |
| 4 | 2023-04-26T12:30 | 2023-04-26T15:15 | +127.59 | +0.49 | `take_profit` |
| 5 | 2023-04-26T16:41 | 2023-04-26T18:37 | +172.09 | +0.66 | `take_profit` |
| 6 | 2023-04-27T11:35 | 2023-04-27T13:53 | +119.59 | +0.46 | `take_profit` |
| 7 | 2023-04-28T09:52 | 2023-04-28T11:31 | +43.57 | +0.17 | `take_profit` |

**Straty za sebou: 14** — 2025-05-22T14:12 až 2025-06-12T08:03, spolu -2410.79.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-05-22T14:12 | 2025-05-23T11:43 | -490.99 | -1.15 | `stop_loss` |
| 2 | 2025-05-27T01:01 | 2025-05-27T01:07 | -61.99 | -0.15 | `stop_loss` |
| 3 | 2025-06-03T12:52 | 2025-06-03T13:04 | -49.01 | -0.11 | `stop_loss` |
| 4 | 2025-06-04T02:35 | 2025-06-04T08:04 | -87.02 | -0.20 | `stop_loss` |
| 5 | 2025-06-04T10:46 | 2025-06-04T12:07 | -60.53 | -0.14 | `stop_loss` |
| 6 | 2025-06-04T12:30 | 2025-06-04T13:36 | -159.53 | -0.37 | `stop_loss` |
| 7 | 2025-06-04T13:51 | 2025-06-04T14:08 | -193.52 | -0.44 | `stop_loss` |
| 8 | 2025-06-05T10:10 | 2025-06-05T12:49 | -92.53 | -0.21 | `stop_loss` |
| 9 | 2025-06-05T12:55 | 2025-06-05T13:47 | -205.03 | -0.47 | `stop_loss` |
| 10 | 2025-06-05T15:05 | 2025-06-05T16:52 | -335.03 | -0.77 | `stop_loss` |
| 11 | 2025-06-06T11:20 | 2025-06-06T12:30 | -42.02 | -0.10 | `stop_loss` |
| 12 | 2025-06-06T18:26 | 2025-06-09T02:31 | -243.53 | -0.56 | `stop_loss` |
| 13 | 2025-06-09T13:42 | 2025-06-09T14:09 | -82.53 | -0.19 | `stop_loss` |
| 14 | 2025-06-10T16:10 | 2025-06-12T08:03 | -307.53 | -0.70 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0055 %**, medián 0.0053 %, 90 % interval -0.0170–0.0283 %
- P(edge > poplatok) = **60.1 %**
- max drawdown: medián 14.6 %, 95. percentil 30.0 %, najhorší 59.1 %
- najdlhšia séria strát: medián 15, 95. percentil 22 obchodov
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
<!-- POSUDOK cisla=268031df -->

_Posudok (Claude, 26. 10. 2026) — repo profil „mnq_databento_5m“, MNQ 5m; ladený profil testera pre túto stratégiu
nie je._

1. **Na čo sa to hodí a na čo nie.** MNQ 5m, 0,52 obchodu denne, medián držania 33 barov (~2,75 h), winrate 33 % pri
   payoffe 2,0. Na prop ani malý účet sa nehodí: 95. percentil drawdownu 30 % (medián 14,6 %), séria strát medián 15,
   95. percentil 22 obchodov.
2. **Má to potenciál?** Zatiaľ nie. 930 obchodov na štatistiku stačí a tá hovorí: break-even 0,0055 % je nad poplatkom
   len o 0,004 bodu, +0,3 σ proti náhode, 60 % bootstrapu nad poplatkom. Ziskové 3 z 5 okien (2021/22 0,051 %,
   2022/23 0,013 %, 2025/26 0,002 %) a rad období klesá 0,045 → 0,022 → −0,020 → −0,004 %.
3. **Čo treba dorobiť.** Filter volatility: obchody pri volatilite 1,4–2,2× normálu (232, 25 %) majú break-even
   −0,048 %, bez nich by celok mal 0,0224 % — a žiadny parameter to neriadi. Riziko na obchod pri drawdowne 30 %
   znížiť.
4. **Čo otestovať ďalej.** Po pridaní filtra (ATR voči 20-dňovému priemeru pod 1,4) `cli checkup` na piatich oknách —
   ak dá 4–5 z 5 a sigmu nad 2, oplatí sa ladiť. `cli sweep --space rrRatio=1:3:0.5` — payoff 2 pri winrate 33 % je
   hraničný a RR môže byť zle.
5. **Je to použiteľné?** Dnes nie, odlíšenie od náhody nie je preukázané. Rozhodne jeden konkrétny test: filter
   volatility vyššie.
6. **Čo by som pridal.** Vynechať dni s výbuchom volatility (makro, otvorenie po gape) — práve tam FVG po sweepe
   neznamená zmenu smeru, len pokračovanie chaosu.

<!-- POSUDOK KONIEC -->
