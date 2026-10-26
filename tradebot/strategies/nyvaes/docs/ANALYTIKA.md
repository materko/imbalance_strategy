# Základná analytika — NY VA BREAKOUT ES (`nyvaes`)

Zmerané 2026-10-25 na `ES/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/nyvaes_PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1_2026-10-25.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy nyvaes \
   --profile .nightsearch/checkup/nyvaes_PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1_2026-10-25.json \
   --pair ES/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 775 obchodov spolu — na štatistiku dosť
- break-even 0.0115 % je nad poplatkom 0.0018 % (rezerva +0.0097 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 12.1 %
- odlíšiteľná od náhody (+8.0 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 26. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- proti náhode v tých istých hodinách je rozdiel podstatne menší (+6.3 vs +8.0 sigma) — veľká časť edge je v tom, KEDY obchoduje, nie v tom, čo si vyberá
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 188 | +21.18 | 0.0152 | 4.6 | 76.1 | +21/-4 | `20261025-051057-ce2d4d` |
| 20221001-20231001 | 146 | +12.90 | 0.0121 | 2.8 | 73.3 | +10/-3 | `20261025-051100-e2b3ec` |
| 20231001-20241001 | 102 | +8.58 | 0.0092 | 4.3 | 72.5 | +12/-3 | `20261025-051103-7642c9` |
| 20240904-20250904 | 174 | +20.01 | 0.0118 | 4.1 | 67.8 | +12/-4 | `20261025-051106-a197f2` |
| 20250904-20260904 | 178 | +18.97 | 0.0098 | 7.4 | 75.8 | +9/-3 | `20261025-051109-d904f0` |

Zisková v **5 z 5** okien, obchodov spolu 775, break-even celkom 0.0115 %. Okná sa prekrývajú, 13 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.41 ATR za 5 barov)
- medián držania 2 barov grafu
- winrate 73.29 %, payoff 0.51
- 0.43 obchodov za deň
- šikmosť výnosov +0.515

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 73.3 %, `stop_loss` 26.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0097 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 737 | 95.1 % | 72.7 | 0.0110 | 0.0212 | +0.0097 |
| deň pred sviatkom | 11 | 1.4 % | 81.8 | 0.0137 | 0.0114 | -0.0001 |
| deň po sviatku | 22 | 2.8 % | 86.4 | 0.0294 | 0.0110 | -0.0005 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.1206 % | 195 | 25.2 % | 68.7 | 0.0016 | 0.0176 | +0.0061 |
| 0.1206 % – 0.1853 % | 193 | 24.9 % | 71.5 | 0.0052 | 0.0132 | +0.0017 |
| 0.1853 % – 0.279 % | 194 | 25.0 % | 75.3 | 0.0072 | 0.0125 | +0.0010 |
| nad 0.279 % | 193 | 24.9 % | 77.7 | 0.0420 | 0.0040 | -0.0075 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 17 | 2.2 % | 58.8 | -0.0036 | 0.0118 | +0.0003 |
| žiadna | 665 | 85.8 % | 72.9 | 0.0105 | 0.0172 | +0.0057 |
| CPI | 47 | 6.1 % | 74.5 | 0.0121 | 0.0114 | -0.0001 |
| NFP | 44 | 5.7 % | 81.8 | 0.0322 | 0.0104 | -0.0011 |

Parametre, ktorými sa dá s tým niečo spraviť: `entryEndH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0134 % | -0.0002 % ± 0.0017 | +7.96 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0134 % | -0.0004 % ± 0.0022 | +6.35 | 100.0 |

Edge je odlisitelny od nahody (8.0 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 240 | 16.3 | 75.4 | 0.0149 | 78 |
| 2022-12 - 2024-03 | 129 | 8.8 | 72.9 | 0.0097 | 38 |
| 2024-03 - 2025-06 | 198 | 13.4 | 71.2 | 0.0129 | 63 |
| 2025-06 - 2026-09 | 208 | 14.1 | 73.1 | 0.0084 | 26 |

Hranice pre úsek veľkosti posledného obdobia: +0.0035 až +0.0190 % (medián 0.0115).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 26. percentile, teda v medziach +0.0035 až +0.0190 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 21** — 2022-02-17T18:48 až 2022-03-14T16:52, spolu +6037.22.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-02-17T18:48 | 2022-02-17T19:09 | +242.28 | +0.11 | `take_profit` |
| 2 | 2022-02-21T15:57 | 2022-02-21T16:01 | +229.93 | +0.11 | `take_profit` |
| 3 | 2022-02-22T15:58 | 2022-02-22T15:59 | +417.41 | +0.19 | `take_profit` |
| 4 | 2022-02-24T15:59 | 2022-02-24T16:00 | +342.68 | +0.16 | `take_profit` |
| 5 | 2022-02-25T15:36 | 2022-02-25T15:40 | +204.93 | +0.10 | `take_profit` |
| 6 | 2022-02-28T15:34 | 2022-02-28T15:35 | +179.88 | +0.08 | `take_profit` |
| 7 | 2022-02-28T19:06 | 2022-02-28T19:07 | +179.91 | +0.08 | `take_profit` |
| 8 | 2022-02-28T20:08 | 2022-02-28T20:12 | +179.91 | +0.08 | `take_profit` |
| 9 | 2022-03-01T15:36 | 2022-03-01T15:37 | +164.62 | +0.03 | `take_profit` |
| 10 | 2022-03-02T15:33 | 2022-03-02T15:34 | +329.87 | +0.15 | `take_profit` |
| 11 | 2022-03-04T15:48 | 2022-03-04T15:50 | +117.47 | +0.05 | `take_profit` |
| 12 | 2022-03-04T17:18 | 2022-03-04T18:01 | +542.41 | +0.25 | `take_profit` |
| 13 | 2022-03-07T16:09 | 2022-03-07T16:30 | +442.51 | +0.21 | `take_profit` |
| 14 | 2022-03-08T15:46 | 2022-03-08T15:53 | +380.18 | +0.18 | `take_profit` |
| 15 | 2022-03-09T15:36 | 2022-03-09T15:38 | +117.52 | +0.06 | `take_profit` |
| 16 | 2022-03-10T15:57 | 2022-03-10T15:58 | +210.18 | +0.05 | `take_profit` |
| 17 | 2022-03-10T17:10 | 2022-03-10T17:11 | +210.18 | +0.05 | `take_profit` |
| 18 | 2022-03-10T19:12 | 2022-03-10T19:18 | +392.55 | +0.18 | `take_profit` |
| 19 | 2022-03-11T15:38 | 2022-03-11T16:31 | +517.55 | +0.24 | `take_profit` |
| 20 | 2022-03-14T14:33 | 2022-03-14T14:34 | +230.10 | +0.11 | `take_profit` |
| 21 | 2022-03-14T16:17 | 2022-03-14T16:52 | +405.16 | +0.19 | `take_profit` |

**Straty za sebou: 4** — 2022-09-22T16:00 až 2022-09-29T17:07, spolu -2432.57, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-09-22T16:00 | 2022-09-22T16:03 | -306.63 | -0.16 | `stop_loss` |
| 2 | 2022-09-23T15:05 | 2022-09-23T15:07 | -463.01 | -0.12 | `stop_loss` |
| 3 | 2022-09-26T14:33 | 2022-09-26T14:48 | -569.02 | -0.31 | `stop_loss` |
| 4 | 2022-09-29T16:00 | 2022-09-29T17:07 | -1093.91 | -0.60 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0115 %**, medián 0.0115 %, 90 % interval 0.0074–0.0156 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 6.7 %, 95. percentil 12.1 %, najhorší 31.2 %
- najdlhšia séria strát: medián 4, 95. percentil 5 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 431** na obchod pri účte 60 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

<!-- POSUDOK cisla=e8c1827d -->

**1. Na čo sa to hodí a na čo nie.** Na ES (aj MES) 3m počas newyorskej seansy: profil 9:30–10:30, potom **retest** — limitka na VAH / VAL po prieraze, ktorá platí 20 barov, vstup len s **pin barom** v smere a v smere **EMA 50** grafu, cieľ ~0,47 R, stop 3 ticky za POC (najviac 5 ATR), value area aspoň 10,9 bodu široká, jeden obchod denne, vstupy do 16:00. Medián držania 2 bary, WR ~73 %, 0,43 obchodu denne. Hodí sa na prop a ako druhý trh k NQ stratégiám — DD v 95 % ciest do 12 %, séria strát najviac 5. Nehodí sa na CFD so širokým spreadom: cieľ je pár bodov a rozhoduje 1 tick.

**2. Má to potenciál?** Áno. Zisk v **5 z 5** okien (PnL +8,6 až +21 % ročne), odložený rok +19 % pri WR 75,8 %, break-even 0,0115 % je 6× poplatok, edge nad poplatkom v 100 % bootstrapových vzoriek a +8,0 sigma proti náhodnému vstupu. Šikmosť výnosov je kladná (+0,5) — straty sú malé voči ziskom, nie opačne. Opatrne: proti náhode **v tých istých hodinách** je to +6,3 sigma, časť edge je teda v načasovaní (prvé hodiny NY). Rok 23/24 má len 102 obchodov a posledné obdobie je na 26. percentile — v norme, ale treba sledovať. Na US500 (krok 8) je PF 1,09 s dvoma stratovými rokmi (0,84, 0,96) — jav drží len na futures.

**3. Čo treba dorobiť.** (a) C# kópia `nyvaesnet` je hotová a bar po bare zhodná; ostáva overiť fill retestovej limitky na NT / MT5 a sklz. Pozor na veľkosť: pri riziku 500 $ na ES strop straty vynechá široké obchody (478 namiesto 775, rok 24/25 v strate) — s týmto rizikom patrí na MES. (b) Frekvencia kolíše (102 až 188 obchodov za rok) kvôli prahu šírky VA 10,9 bodu — prah v ATR by bol stabilnejší. (c) Dni so správami: FOMC 17 obchodov, WR 59 %, break-even −0,0036 %; NFP 44 obchodov a 0,0322 %, CPI 0,0121 %. Bez FOMC by sa celok zlepšil len o 0,0003 % — filter na to nestojí za zložitosť.

**4. Čo otestovať ďalej.** Na C# jadre (`nyvaesnet`): natívny hyperopt `cli hyperopt --engine multicharts --windows ref --aggregate min --select plateau` na `rrRatio`, `vaMinPoints` (v ATR) a `retestBars`, potom `cli plateau`; `--walk-forward` rozhodne, či by pravidelné preladenie držalo. Potom krok 9: forward test na MES 4–6 týždňov, porovnať WR a sklz s backtestom.

**5. Je to použiteľné, alebo je to o ničom?** **Použiteľné len na futures (ES / MES).** Prešlo smernicou cez krok 7 s 5 profilmi, edge je jasný a stabilný po rokoch; krok 8 na US500 neprešiel, preto nie na CFD. Do forward testu ide ako doplnok k IBS EZ ES — obe ES, ale iná logika a iné hodiny.

**6. Čo by som pridal.** Potvrdenie z NQ: prieraz ES len keď NQ v prvej hodine prerazil tým istým smerom — falošné prierazy ES často prídu, keď Nasdaq ide opačne. Druhý nápad: prah šírky value area v ATR namiesto bodov, aby počet obchodov nezávisel od úrovne volatility v danom roku.

<!-- POSUDOK KONIEC -->
