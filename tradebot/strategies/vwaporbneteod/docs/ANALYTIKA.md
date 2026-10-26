# Základná analytika — VWAP ORB 1.5 (C# jadro EOD) (`vwaporbneteod`)

Zmerané 2026-10-26 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tester/profiles/SMERNICE_CS_EOD_VWAP_ORB_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy vwaporbneteod \
   --profile tester/profiles/SMERNICE_CS_EOD_VWAP_ORB_1.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 832 obchodov spolu — na štatistiku dosť
- break-even 0.0312 % je nad poplatkom 0.0018 % (rezerva +0.0294 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 9.1 %
- odlíšiteľná od náhody (+4.2 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 15. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 30.9 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'bežný deň' vlastnosti 'Sviatok na burze v USA': 780 obchodov (93.8 %), bez nej by break-even bol o +0.0517 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 177 | +6.98 | 0.0442 | 3.3 | 68.9 | +11/-4 | `20261026-130216-f2d9d6` |
| 20221001-20231001 | 173 | +4.27 | 0.0298 | 2.4 | 63.6 | +10/-4 | `20261026-130226-300a7e` |
| 20231001-20241001 | 181 | +8.53 | 0.0410 | 1.5 | 69.1 | +9/-4 | `20261026-130234-5e44b8` |
| 20240904-20250904 | 172 | +5.04 | 0.0226 | 5.1 | 62.2 | +9/-5 | `20261026-130242-457fb1` |
| 20250904-20260904 | 141 | +6.13 | 0.0263 | 3.1 | 61.0 | +9/-4 | `20261026-130250-2a3bb9` |

Zisková v **5 z 5** okien, obchodov spolu 832, break-even celkom 0.0312 %. Okná sa prekrývajú, 12 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.44 ATR za 5 barov)
- medián držania 32 barov grafu
- winrate 65.02 %, payoff 0.695
- 0.46 obchodov za deň
- šikmosť výnosov -0.677

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 52.2 %, `session_end` 30.9 %, `stop_loss` 16.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'bežný deň' vlastnosti 'Sviatok na burze v USA': 780 obchodov (93.8 %), break-even 0.0275 % oproti 0.0312 % celku. Bez nej by break-even bol 0.0829 % (+0.0517). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 780 | 93.8 % | 64.2 | 0.0275 | 0.0829 | +0.0517 |
| deň pred sviatkom | 19 | 2.3 % | 73.7 | 0.0543 | 0.0306 | -0.0006 |
| deň po sviatku | 18 | 2.2 % | 72.2 | 0.0958 | 0.0297 | -0.0015 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 737 | 88.6 % | 63.6 | 0.0295 | 0.0449 | +0.0137 |
| proti trendu | 95 | 11.4 % | 75.8 | 0.0449 | 0.0295 | -0.0017 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.6078 % | 209 | 25.1 % | 66.5 | 0.0030 | 0.0417 | +0.0105 |
| 0.8917 % – 1.3186 % | 208 | 25.0 % | 62.5 | 0.0310 | 0.0313 | +0.0001 |
| 0.6078 % – 0.8917 % | 208 | 25.0 % | 69.7 | 0.0409 | 0.0279 | -0.0033 |
| nad 1.3186 % | 207 | 24.9 % | 61.4 | 0.0536 | 0.0244 | -0.0068 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0312 % | -0.0014 % ± 0.0078 | +4.20 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0312 % | -0.0013 % ± 0.0087 | +3.73 | 100.0 |

Edge je odlisitelny od nahody (4.2 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 210 | 14.3 | 67.1 | 0.0385 | 61 |
| 2022-12 - 2024-03 | 212 | 14.4 | 64.6 | 0.0304 | 45 |
| 2024-03 - 2025-06 | 223 | 15.2 | 69.5 | 0.0504 | 84 |
| 2025-06 - 2026-08 | 187 | 12.7 | 57.8 | 0.0098 | 15 |

Hranice pre úsek veľkosti posledného obdobia: -0.0035 až +0.0669 % (medián 0.0316).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 15. percentile, teda v medziach -0.0035 až +0.0669 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 11** — 2022-04-06T19:21 až 2022-04-26T19:56, spolu +1984.31.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-04-06T19:21 | 2022-04-06T19:33 | +115.98 | +0.40 | `take_profit` |
| 2 | 2022-04-12T14:51 | 2022-04-12T17:46 | +114.01 | +0.40 | `take_profit` |
| 3 | 2022-04-14T14:12 | 2022-04-14T18:54 | +200.02 | +0.71 | `take_profit` |
| 4 | 2022-04-19T14:09 | 2022-04-19T14:43 | +198.01 | +0.70 | `take_profit` |
| 5 | 2022-04-21T15:06 | 2022-04-21T15:57 | +202.01 | +0.72 | `take_profit` |
| 6 | 2022-04-21T16:00 | 2022-04-21T18:11 | +321.03 | +1.15 | `take_profit` |
| 7 | 2022-04-21T18:12 | 2022-04-21T19:54 | +155.03 | +0.56 | `session_end` |
| 8 | 2022-04-22T13:51 | 2022-04-22T13:59 | +87.54 | +0.32 | `take_profit` |
| 9 | 2022-04-22T14:00 | 2022-04-22T14:21 | +119.04 | +0.44 | `take_profit` |
| 10 | 2022-04-22T14:24 | 2022-04-22T16:02 | +186.05 | +0.68 | `take_profit` |
| 11 | 2022-04-26T14:48 | 2022-04-26T19:56 | +285.58 | +1.08 | `take_profit` |

**Straty za sebou: 5** — 2025-01-29T19:06 až 2025-02-03T15:24, spolu -1220.06, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-01-29T19:06 | 2025-01-29T20:54 | -229.51 | -0.54 | `session_end` |
| 2 | 2025-01-30T17:18 | 2025-01-30T20:02 | -261.52 | -0.61 | `stop_loss` |
| 3 | 2025-01-30T20:45 | 2025-01-30T20:54 | -212.52 | -0.49 | `session_end` |
| 4 | 2025-01-31T17:12 | 2025-01-31T18:34 | -277.03 | -0.63 | `stop_loss` |
| 5 | 2025-02-03T15:12 | 2025-02-03T15:24 | -239.49 | -0.57 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0312 %**, medián 0.0312 %, 90 % interval 0.0138–0.0486 %
- P(edge > poplatok) = **99.7 %**
- max drawdown: medián 5.2 %, 95. percentil 9.1 %, najhorší 18.2 %
- najdlhšia séria strát: medián 5, 95. percentil 7 obchodov
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
<!-- POSUDOK cisla=ded1282f -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „VWAP ORB 1 C# EOD“ (`SMERNICE_CS_EOD_VWAP_ORB_1`): tie isté
parametre ako `vwaporbnet` (range 5 min, RR 0,5, 1 kontrakt), navyše `EodCloseEngine` — všetko zatvorené najneskôr
o 15:59 NY, čakajúce vstupy zrušené (prop účty)._

1. **Na čo sa to hodí a na čo nie.** MNQ 3m na prop účte, ktorý nedovolí držať cez noc. Zatvorenie o 15:59 NY mení
   stratégiu podstatne: 30,9 % obchodov končí na čase (`session_end`) namiesto TP/SL, WR klesne 73 → 65 %, break-even
   0,072 → **0,031 %** (−57 %). Veľká časť edge `vwaporbnet` teda pochádza z obchodov, ktoré dobehnú do TP až na druhý
   deň. Drawdown sa nezlepší (95. percentil 9,1 % vs. 8,0 %), séria 5 strát (jan./feb. 2025, −1 220 $) je tá istá.
   Na denný limit straty prop výzvy (typicky 1 000–2 000 $ pri 50k) je séria 5 × ~250 $ na hrane jedného zlého týždňa.
2. **Má to potenciál?** Áno, ale menší. 5 z 5 okien v zisku (+6,98/+4,27/+8,53/+5,04/+6,13 %), +4,2 σ proti náhode,
   100 % bootstrapu nad poplatkom, rezerva ~17× poplatok. Proti: posledné obdobie 2025-06 – 2026-08 má break-even len
   0,010 % (15. percentil, WR 58 %) — dolná hranica úseku je −0,004 %, takže ďalší slabý rok môže byť na nule.
3. **Čo treba dorobiť.** Obchody otvorené popoludní nemajú čas dobehnúť — chýba „posledný čas vstupu“ (napr. nevstupovať
   po 14:30 NY), aby EOD neuzatváral polovičaté pozície. Analytika ukazuje „bežný deň“ ako najhoršiu skupinu (93,8 %
   obchodov) — to je artefakt (sviatky sú len 52 obchodov s výrazne lepším výsledkom), nie filter.
4. **Čo otestovať ďalej.** `cli sweep --strategy vwaporbneteod --space "rrRatio=0.3:0.8:0.1"` — pri kratšom čase na
   dobehnutie môže nižšie RR vrátiť časť edge; ak nie, EOD verzia stojí len na rannom prieraze. Prop simulácia
   (`/api/prop`, karta Prop) s pravidlami konkrétnej výzvy — rozhodne, či séria strát a pomalý rast pod 0,03 % prejdú
   denný limit a cieľ v čase.
5. **Je to použiteľné?** Podmienečne áno — na prop výzvu, kde držanie cez noc nie je dovolené, s vedomím, že edge je
   o polovicu menší ako bez EOD a posledný rok je najslabší. Na vlastný účet radšej `vwaporbnet`.
6. **Čo by som pridal.** Časový limit vstupu podľa zostávajúceho času do 15:59 (vstúpiť len, keď medián času do TP
   — ~32 barov × 3 min ≈ 1,5 h — ešte vyjde) a pri vstupe po 14:00 menší cieľ.

<!-- POSUDOK KONIEC -->
