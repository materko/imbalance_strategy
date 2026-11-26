# Základná analytika — MTK EMAS 1.0 (BTC) (`mtkemasbtc`)

Zmerané 2026-11-26 na `BTC/USDT:USDT` 4h, engine `multicharts`, poplatok 0.0500 % na stranu (Binance USDⓈ-M taker, VIP 0), profil `tradebot/strategies/mtkemasbtc/configs/btcusdt_binance_4h.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy mtkemasbtc \
   --profile tradebot/strategies/mtkemasbtc/configs/btcusdt_binance_4h.json \
   --timeframe 4h \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- break-even 0.8120 % je nad poplatkom 0.0500 % (rezerva +0.7620 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 14.7 %
- edge drží aj v poslednom období (2025-05 - 2026-08 na 35. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- proti náhode len +1.4 sigma: náznak, nie dôkaz
- 59.1 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'do 100 R' vlastnosti 'Plánovaný RR': 80 obchodov (86.0 %), bez nej by break-even bol o +1.0441 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 9 | +15.96 | 1.6822 | 1.8 | 44.4 | +3/-3 | `20261126-074438-200a68` |
| 20221001-20231001 | 21 | +39.42 | 0.9665 | 8.6 | 19.1 | +3/-11 | `20261126-074441-afb265` |
| 20231001-20241001 | 24 | +22.37 | 0.6408 | 5.6 | 25.0 | +2/-6 | `20261126-074444-1af499` |
| 20240904-20250904 | 28 | +35.69 | 0.7037 | 3.0 | 17.9 | +1/-8 | `20261126-074447-aa8cbe` |
| 20250904-20260904 | 12 | +17.30 | 0.6341 | 5.2 | 25.0 | +1/-4 | `20261126-074450-124a3f` |

Zisková v **5 z 5** okien, obchodov spolu 93, break-even celkom 0.8120 %. Okná sa prekrývajú, 1 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.29 ATR za 5 barov)
- medián držania 5.3 barov grafu
- winrate 23.66 %, payoff 9.518
- 0.05 obchodov za deň
- šikmosť výnosov +2.973

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 59.1 %, `trailing_stop` 35.5 %, `stop_loss` 4.3 %, `force_exit` 1.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 100 R' vlastnosti 'Plánovaný RR': 80 obchodov (86.0 %), break-even 0.5939 % oproti 0.812 % celku. Bez nej by break-even bol 1.8561 % (+1.0441). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 100 R | 80 | 86.0 % | 18.8 | 0.5939 | 1.8561 | +1.0441 |
| nad 100 R | 13 | 14.0 % | 53.9 | 1.8561 | 0.5939 | -0.2181 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 38 | 40.9 % | 13.2 | -0.0872 | 1.3878 | +0.5758 |
| s trendom | 55 | 59.1 % | 30.9 | 1.3878 | -0.0872 | -0.8992 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 24 | 23 | 24.7 % | 8.7 | -0.2384 | 1.1616 | +0.3496 |
| 6 – 14 | 20 | 21.5 % | 15.0 | -0.0332 | 1.0576 | +0.2456 |
| 14 – 24 | 23 | 24.7 % | 43.5 | 1.6291 | 0.5562 | -0.2558 |
| do 6 | 27 | 29.0 % | 25.9 | 1.7112 | 0.4506 | -0.3614 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.6261 % | 0.1195 % ± 0.3487 | +1.45 | 91.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.6261 % | 0.1073 % ± 0.3574 | +1.45 | 91.7 |

Naznak, ale nie dokaz (1.4 sigma, percentil 91.7). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 12 | 0.8 | 41.7 | 1.0281 | 67 |
| 2022-12 - 2024-03 | 29 | 2.0 | 20.7 | 1.1148 | 73 |
| 2024-03 - 2025-05 | 27 | 1.9 | 25.9 | 0.7716 | 54 |
| 2025-05 - 2026-08 | 25 | 1.7 | 16.0 | 0.4904 | 35 |

Hranice pre úsek veľkosti posledného obdobia: -0.0620 až +1.8929 % (medián 0.7193).

**DRZI** — posledné obdobie (2025-05 - 2026-08) je na 35. percentile, teda v medziach -0.0620 až +1.8929 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 3** — 2021-10-01T12:00 až 2022-02-17T18:14, spolu +10165.87, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-01T12:00 | 2021-10-22T14:37 | +7850.34 | +29.01 | `trailing_stop` |
| 2 | 2021-11-06T20:00 | 2021-11-10T21:22 | +1844.82 | +4.61 | `trailing_stop` |
| 3 | 2022-02-04T20:00 | 2022-02-17T18:14 | +470.72 | +1.55 | `trailing_stop` |

**Straty za sebou: 11** — 2023-02-26T20:00 až 2023-06-18T20:00, spolu -7589.02.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-02-26T20:00 | 2023-02-27T16:00 | -516.60 | -1.07 | `session_end` |
| 2 | 2023-02-28T00:00 | 2023-02-28T04:00 | -553.66 | -1.19 | `session_end` |
| 3 | 2023-02-28T12:00 | 2023-02-28T16:00 | -325.32 | -0.66 | `session_end` |
| 4 | 2023-03-01T04:00 | 2023-03-03T01:31 | -2045.93 | -4.32 | `stop_loss` |
| 5 | 2023-03-13T16:00 | 2023-03-14T21:07 | -25.19 | -0.10 | `trailing_stop` |
| 6 | 2023-04-26T12:00 | 2023-04-26T19:47 | -1591.26 | -3.41 | `trailing_stop` |
| 7 | 2023-04-27T04:00 | 2023-05-01T00:00 | -347.12 | -1.25 | `session_end` |
| 8 | 2023-05-04T00:00 | 2023-05-04T12:00 | -281.79 | -0.68 | `session_end` |
| 9 | 2023-05-05T04:00 | 2023-05-06T12:00 | -1002.75 | -2.25 | `session_end` |
| 10 | 2023-05-28T20:00 | 2023-05-29T17:07 | -68.66 | -0.10 | `trailing_stop` |
| 11 | 2023-06-18T20:00 | 2023-06-18T20:00 | -830.74 | -1.27 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.8120 %**, medián 0.8056 %, 90 % interval 0.4121–1.2679 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 7.5 %, 95. percentil 14.7 %, najhorší 31.9 %
- najdlhšia séria strát: medián 10, 95. percentil 17 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **3 704** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=a5afd1eb -->

1. **Na čo sa to hodí a na čo nie.** BTC 4h (cena × SMA 165 + EMA 200, len longy): pomalé sledovanie trendu na 1h–4h, obchody trvajú dni, zisk robí
   pár veľkých pohybov (WR 20–35 %). Hodí sa ako **časť portfólia** viacerých trhov (MNQ, zlato, ES, MYM, BTC), nie ako
   samostatná stratégia — na jednom trhu je obchodov málo. Na CFD treba prirátať swap za držanie cez noc a víkend.
   Percentá v tabuľkách sú pri riziku 2 000 $ na obchod a účte 60 000 $ — rozhoduje PF a znamienko po rokoch.
2. **Má to potenciál?** Čísla: PF 2,95 (rok 2022 0,80), 19 obchodov za rok, WR 24 %, zisková v 5 z 5 okien. Výhrada: proti náhode +1,4 sigma; v medvedom roku 2022 stratový — bez rastúceho trhu výhoda mizne. Edge je teda skutočný,
   ale zväčša je to **zisk z rastu trhu** zachytený longami — rozhodne porovnanie s „kúp a drž“.
3. **Čo treba dorobiť.** Swap a spread CFD do nákladov; rolovanie futures (dáta nie sú upravené, štúdia áno);
   veľkosť pozície podľa portfólia (spoločné riziko všetkých trhov); výstup pri opačnom krížení sa v emulátore
   označuje ako „session_end“ (nie je to koniec seansy, len zatvorenie pri signáli).
4. **Čo otestovať ďalej.** Podľa iCloud SMERNICA_TREND_CFD: plató (`cli sweep` dĺžka priemeru ±20 %, stop 1–2 ATR,
   trailing ±1 ATR), porovnanie s kúp a drž v tom istom období, roky 2016–2019 (zlato, ES), iný trh s tým istým
   nastavením, 2× poplatok a vstup o sviečku neskôr. Ak plató drží a stratégia má lepší zisk / pokles než kúp a drž,
   ide do portfólia.
5. **Je to použiteľné, alebo je to o ničom?** Použiteľné ako trendový doplnok portfólia — ale až po kroku „kúp a drž“;
   samostatne na jednom trhu nie (málo obchodov, slabý test proti náhode).
6. **Čo by som pridal.** Režim trhu: obchodovať len keď je EMA 200 rastúca (sklon), a portfóliové obmedzenie —
   najviac 2–3 otvorené trhy naraz, aby korelované indexy (MNQ, ES, MYM) nezdvojnásobili riziko.

<!-- POSUDOK KONIEC -->
