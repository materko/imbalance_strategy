# Základná analytika — Silver Bullet 1.0 (BTC) (`silverbulletbtc`)

Zmerané 2026-11-13 na `BTC/USDT:USDT` 5m, engine `multicharts`, poplatok 0.0200 % na stranu (zadané cez --fee), profil `tradebot/strategies/silverbulletbtc/configs/btcusdt_binance_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy silverbulletbtc \
   --profile tradebot/strategies/silverbulletbtc/configs/btcusdt_binance_5m.json \
   --pair BTC/USDT:USDT \
   --timeframe 5m \
   --fee 0.0002 \
   --wallet 60000
```

## V čom je dobrá

- 239 obchodov spolu — na štatistiku dosť
- break-even 0.0354 % je nad poplatkom 0.0200 % (rezerva +0.0154 bodu)
- drawdown drží: 95. percentil 21.5 %
- edge drží aj v poslednom období (2025-06 - 2026-08 na 45. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20221001-20231001, 20231001-20241001 v strate)
- edge nad poplatkom len v 72 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +1.4 sigma: náznak, nie dôkaz
- najhoršia skupina 'deň po sviatku' vlastnosti 'Sviatok na burze v USA': 10 obchodov (4.2 %), bez nej by break-even bol o +0.1215 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 46 | +6.26 | 0.1337 | 2.7 | 43.5 | +4/-7 | `20261113-172134-a58be3` |
| 20221001-20231001 | 44 | -0.35 | 0.0098 | 1.9 | 43.2 | +4/-5 | `20261113-172140-2ca228` |
| 20231001-20241001 | 49 | -4.22 | -0.0251 | 10.1 | 40.8 | +5/-10 | `20261113-172146-f6845e` |
| 20240904-20250904 | 53 | +4.34 | 0.0467 | 7.0 | 39.6 | +4/-5 | `20261113-172155-108735` |
| 20250904-20260904 | 51 | +0.22 | 0.0217 | 4.3 | 39.2 | +2/-7 | `20261113-172201-743a4f` |

Zisková v **3 z 5** okien, obchodov spolu 239, break-even celkom 0.0354 %. Okná sa prekrývajú, 4 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.47 ATR za 5 barov)
- medián držania 12.2 barov grafu
- winrate 41.42 %, payoff 1.527
- 0.14 obchodov za deň
- šikmosť výnosov +0.999

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 58.6 %, `take_profit` 41.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'deň po sviatku' vlastnosti 'Sviatok na burze v USA': 10 obchodov (4.2 %), break-even -0.0718 % oproti 0.0354 % celku. Bez nej by break-even bol 0.0395 % (+0.1215). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň po sviatku | 10 | 4.2 % | 20.0 | -0.0718 | 0.0395 | +0.0041 |
| bežný deň | 220 | 92.1 % | 40.9 | 0.0250 | 0.1569 | +0.1215 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 14 h | 134 | 56.1 % | 38.8 | 0.0045 | 0.0721 | +0.0367 |
| 15 h | 89 | 37.2 % | 43.8 | 0.0494 | 0.0267 | -0.0087 |
| 16 h | 16 | 6.7 % | 50.0 | 0.1904 | 0.0231 | -0.0123 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 9 – 16 | 57 | 23.8 % | 35.1 | -0.0636 | 0.0680 | +0.0326 |
| 16 – 24 | 68 | 28.5 % | 42.6 | 0.0540 | 0.0280 | -0.0074 |
| do 9 | 64 | 26.8 % | 39.1 | 0.0625 | 0.0259 | -0.0095 |
| nad 24 | 50 | 20.9 % | 50.0 | 0.0939 | 0.0199 | -0.0155 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0354 % | -0.0006 % ± 0.0249 | +1.45 | 91.6 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0354 % | 0.0016 % ± 0.0261 | +1.30 | 90.2 |

Naznak, ale nie dokaz (1.4 sigma, percentil 91.6). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-11 - 2023-01 | 64 | 4.5 | 46.9 | 0.1282 | 97 |
| 2023-01 - 2024-03 | 42 | 2.9 | 45.2 | 0.0695 | 71 |
| 2024-03 - 2025-06 | 72 | 5.0 | 36.1 | 0.0004 | 21 |
| 2025-06 - 2026-08 | 61 | 4.3 | 39.3 | 0.0286 | 45 |

Hranice pre úsek veľkosti posledného obdobia: -0.0607 až +0.1209 % (medián 0.0339).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 45. percentile, teda v medziach -0.0607 až +0.1209 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2022-09-23T14:51 až 2022-10-11T15:36, spolu +1031.30, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-09-23T14:51 | 2022-09-23T22:27 | +372.05 | +1.99 | `take_profit` |
| 2 | 2022-10-04T14:43 | 2022-10-04T17:15 | +219.99 | +1.09 | `take_profit` |
| 3 | 2022-10-05T14:52 | 2022-10-05T16:08 | +200.72 | +1.01 | `take_profit` |
| 4 | 2022-10-07T14:40 | 2022-10-07T15:42 | +85.17 | +0.43 | `take_profit` |
| 5 | 2022-10-11T14:21 | 2022-10-11T15:36 | +153.37 | +0.81 | `take_profit` |

**Straty za sebou: 10** — 2024-05-13T14:50 až 2024-06-14T15:48, spolu -3954.68.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-05-13T14:50 | 2024-05-13T15:51 | -307.79 | -0.49 | `stop_loss` |
| 2 | 2024-05-14T14:58 | 2024-05-15T09:44 | -556.62 | -0.90 | `stop_loss` |
| 3 | 2024-05-16T14:49 | 2024-05-16T14:56 | -323.44 | -0.49 | `stop_loss` |
| 4 | 2024-05-23T14:20 | 2024-05-23T14:50 | -489.16 | -0.72 | `stop_loss` |
| 5 | 2024-05-24T14:51 | 2024-05-24T15:01 | -241.98 | -0.36 | `stop_loss` |
| 6 | 2024-05-28T14:36 | 2024-05-28T18:36 | -394.49 | -0.58 | `stop_loss` |
| 7 | 2024-05-30T14:45 | 2024-05-30T17:14 | -314.80 | -0.46 | `stop_loss` |
| 8 | 2024-06-04T14:54 | 2024-06-04T15:20 | -527.99 | -0.76 | `stop_loss` |
| 9 | 2024-06-13T14:48 | 2024-06-13T15:17 | -436.13 | -0.65 | `stop_loss` |
| 10 | 2024-06-14T15:03 | 2024-06-14T15:48 | -362.28 | -0.54 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0354 %**, medián 0.0359 %, 90 % interval -0.0085–0.0793 %
- P(edge > poplatok) = **72.2 %**
- max drawdown: medián 10.5 %, 95. percentil 21.5 %, najhorší 43.1 %
- najdlhšia séria strát: medián 9, 95. percentil 13 obchodov
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
<!-- POSUDOK cisla=65303f17 -->

**1. Na čo sa to hodí.** ICT Silver Bullet (sweep likvidity + FVG v okne 10–11 NY) na BTCUSDT.P 5m. Len ~50 obchodov za rok — pod minimom smernice (75).

**2. Potenciál.** **Málo.** Zisk v 3 z 5 okien, +1,5 sigma; FVG na BTC sa dorovnávajú rovnako ako na MNQ (~72 %), takže logika sedí, ale výsledok je zatiaľ na hranici náhody.

**3. Čo dorobiť.** Na 75 obchodov za rok treba širšie okno (`sbStartH`/`sbEndH`) alebo viac obchodov za deň.

**4. Čo otestovať.** Smernica na BTC (od ne 15. 11. 2026 po testoch MYM, do ne 22. 11. 18:00) s poplatkom maker 0,02 %; rozhodne odložený rok 9/2025–9/2026 a stabilita po rokoch. Smernica skúša aj okná 3–11 a 14–16 NY.

**5. Použiteľné?** **Zatiaľ o ničom**, kým ladenie nenájde viac obchodov s rovnakým edgeom.

**6. Čo by som pridal.** Okno pri otvorení NY 9:30–10:00, kde má BTC najväčší rozsah.

<!-- POSUDOK KONIEC -->
