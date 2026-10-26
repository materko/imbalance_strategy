# Základná analytika — Overnight Bias ORB (`onbiasorb`)

Zmerané 2026-10-26 na `MNQ/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/onbiasorb/configs/mnq_databento_15m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy onbiasorb \
   --profile tradebot/strategies/onbiasorb/configs/mnq_databento_15m.json \
   --pair MNQ/USD \
   --timeframe 15m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 455 obchodov spolu — na štatistiku dosť
- break-even 0.0459 % je nad poplatkom 0.0018 % (rezerva +0.0441 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 5.5 %
- odlíšiteľná od náhody (+3.8 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-04 - 2026-06 na 9. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 59.3 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'long' vlastnosti 'Smer': 248 obchodov (54.5 %), bez nej by break-even bol o +0.0181 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 106 | +5.11 | 0.0468 | 2.4 | 55.7 | +7/-4 | `20261026-131509-21153c` |
| 20221001-20231001 | 98 | +6.82 | 0.0564 | 1.6 | 54.1 | +8/-7 | `20261026-131515-dc130d` |
| 20231001-20241001 | 109 | +10.63 | 0.0560 | 3.3 | 51.4 | +7/-5 | `20261026-131521-306ab6` |
| 20240904-20250904 | 81 | +3.72 | 0.0341 | 2.0 | 50.6 | +4/-4 | `20261026-131527-a3c211` |
| 20250904-20260904 | 67 | +2.70 | 0.0253 | 1.8 | 52.2 | +7/-4 | `20261026-131533-2905d2` |

Zisková v **5 z 5** okien, obchodov spolu 455, break-even celkom 0.0459 %. Okná sa prekrývajú, 6 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.61 ATR za 5 barov)
- medián držania 15.1 barov grafu
- winrate 53.19 %, payoff 1.253
- 0.27 obchodov za deň
- šikmosť výnosov +0.761

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 59.3 %, `stop_loss` 36.5 %, `take_profit` 4.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'long' vlastnosti 'Smer': 248 obchodov (54.5 %), break-even 0.0312 % oproti 0.0459 % celku. Bez nej by break-even bol 0.064 % (+0.0181). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 248 | 54.5 % | 54.8 | 0.0312 | 0.0640 | +0.0181 |
| short | 207 | 45.5 % | 51.2 | 0.0640 | 0.0312 | -0.0147 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 15 – 23 | 112 | 24.6 % | 42.9 | -0.0071 | 0.0630 | +0.0171 |
| 8 – 15 | 111 | 24.4 % | 56.8 | 0.0467 | 0.0457 | -0.0002 |
| nad 23 | 109 | 24.0 % | 56.0 | 0.0590 | 0.0417 | -0.0042 |
| do 8 | 123 | 27.0 % | 56.9 | 0.0814 | 0.0329 | -0.0130 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.9109 | 114 | 25.1 % | 46.5 | 0.0103 | 0.0573 | +0.0114 |
| nad 0.9786 | 113 | 24.8 % | 53.1 | 0.0553 | 0.0427 | -0.0032 |
| 0.9515 – 0.9786 | 114 | 25.1 % | 56.1 | 0.0558 | 0.0427 | -0.0032 |
| 0.9109 – 0.9515 | 114 | 25.1 % | 57.0 | 0.0608 | 0.0409 | -0.0050 |

Parametre, ktorými sa dá s tým niečo spraviť: `adxMin`, `exitHHMM`, `minEntryHHMM`, `rr`, `slPct`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0447 % | 0.0013 % ± 0.0115 | +3.78 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0447 % | 0.0020 % ± 0.0133 | +3.21 | 99.7 |

Edge je odlisitelny od nahody (3.8 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 124 | 8.8 | 55.6 | 0.0522 | 60 |
| 2022-12 - 2024-02 | 114 | 8.1 | 53.5 | 0.0444 | 50 |
| 2024-02 - 2025-04 | 127 | 9.1 | 52.8 | 0.0711 | 84 |
| 2025-04 - 2026-06 | 90 | 6.4 | 50.0 | 0.0075 | 9 |

Hranice pre úsek veľkosti posledného obdobia: -0.0005 až +0.0971 % (medián 0.0467).

**DRZI** — posledné obdobie (2025-04 - 2026-06) je na 9. percentile, teda v medziach -0.0005 až +0.0971 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2022-11-09T15:45 až 2022-12-08T20:15, spolu +1421.01.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-11-09T15:45 | 2022-11-09T20:15 | +186.73 | +0.85 | `session_end` |
| 2 | 2022-11-10T15:00 | 2022-11-10T20:15 | +251.69 | +1.10 | `session_end` |
| 3 | 2022-11-16T15:00 | 2022-11-16T20:15 | +111.67 | +0.47 | `session_end` |
| 4 | 2022-11-22T19:00 | 2022-11-22T20:15 | +57.68 | +0.25 | `session_end` |
| 5 | 2022-11-29T15:15 | 2022-11-29T20:15 | +109.69 | +0.47 | `session_end` |
| 6 | 2022-12-05T15:15 | 2022-12-05T20:15 | +284.67 | +1.20 | `session_end` |
| 7 | 2022-12-06T15:00 | 2022-12-06T20:15 | +307.19 | +1.32 | `session_end` |
| 8 | 2022-12-08T15:00 | 2022-12-08T20:15 | +111.68 | +0.48 | `session_end` |

**Straty za sebou: 7** — 2023-03-06T15:15 až 2023-03-28T19:15, spolu -999.16.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-03-06T15:15 | 2023-03-06T20:17 | -159.87 | -0.64 | `stop_loss` |
| 2 | 2023-03-07T15:30 | 2023-03-07T15:36 | -156.86 | -0.64 | `stop_loss` |
| 3 | 2023-03-09T15:00 | 2023-03-09T17:02 | -154.36 | -0.63 | `stop_loss` |
| 4 | 2023-03-14T15:45 | 2023-03-14T17:14 | -152.36 | -0.62 | `stop_loss` |
| 5 | 2023-03-22T14:30 | 2023-03-22T19:08 | -155.91 | -0.60 | `stop_loss` |
| 6 | 2023-03-23T14:15 | 2023-03-23T18:25 | -157.90 | -0.61 | `stop_loss` |
| 7 | 2023-03-28T14:45 | 2023-03-28T19:15 | -61.89 | -0.24 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0459 %**, medián 0.0458 %, 90 % interval 0.0253–0.0673 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 3.2 %, 95. percentil 5.5 %, najhorší 10.5 %
- najdlhšia séria strát: medián 6, 95. percentil 9 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **2 015** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=14dc14c9 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie: repo profil `mnq_databento_15m` (MNQ 15m), Pine defaulty
stratégie; ladený profil testera neexistuje._

1. **Na čo sa to hodí a na čo nie.** Na index futures Nasdaq (MNQ) v NY seanse, graf 15m: prerazenie otváracieho
   rozsahu v smere overnight biasu, 455 obchodov (0,27 za deň), winrate 53 %, payoff 1,25, 59 % pozícií zatvorí koniec
   seansy (`session_end`), 37 % SL, len 4 % TP — teda je to „chyť smer dňa a drž do konca“, nie cieľ na TP.
   Nehodí sa na trhy bez overnight seansy (akcie, CFD bez noci) — bias by nebolo z čoho počítať.
2. **Má to potenciál?** Áno. Za: 5 z 5 okien v zisku (+5,1 / +6,8 / +10,6 / +3,7 / +2,7 %), break-even 0,0459 % je
   25× nad poplatkom, 100 % vzoriek nad poplatkom, +3,8 σ proti náhode (+3,2 σ aj proti vstupom v tých istých
   hodinách), drawdown malý (95. percentil 5,5 %). Proti: posledné obdobie (2025-04 – 2026-06) je na 9. percentile
   (break-even 0,0075 %) a break-even po rokoch klesá 0,056 → 0,034 → 0,025 % — stále v medziach, ale smer je zlý.
   Ide o Pine defaulty bez ladenia, takže výber na vzorke tu nie je.
3. **Čo treba dorobiť.** C# port (pre NT8/MT5) neexistuje. Výstup je z 59 % `session_end` — čas zatvorenia
   (`exitHHMM`) je tu fakticky hlavný parameter výstupu a v analytike by mal mať vlastné meno, nie „koniec seansy“.
4. **Čo otestovať ďalej.** `cli sweep` cez `exitHHMM` a `rr` na piatich oknách — či zníženie edge v poslednom roku
   je trh (iné správanie popoludní), alebo len rozptyl. A dni 15. – 23. v mesiaci (break-even −0,007 %, 112 obchodov)
   proti makro kalendáru — ak ide o CPI/FOMC týždeň, je to filter, nie náhoda.
5. **Je to použiteľné?** Áno ako kandidát — najčistejší výsledok v tejto dávke (bez ladenia, 5/5, 3,8 σ). Na ostrý
   účet až po sweepe výstupu a forward teste; slabnúci posledný rok sleduj.
6. **Čo by som pridal.** Shorty majú dvojnásobný break-even (0,064 %) oproti longom (0,031 %) — filter, ktorý longy
   pustí len pri silnom overnight biase (napr. gap nad 0,3 %), by sa oplatilo zmerať; vypnúť longy úplne by bolo
   ladenie na jednu vlastnosť.

<!-- POSUDOK KONIEC -->
