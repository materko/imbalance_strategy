# Základná analytika — T-MEAN REVERSION 1.0 (BTC) (`tmrbtc`)

Zmerané 2026-11-13 na `BTC/USDT:USDT` 15m, engine `multicharts`, poplatok 0.0200 % na stranu (zadané cez --fee), profil `tradebot/strategies/tmrbtc/configs/btcusdt_binance_15m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tmrbtc \
   --profile tradebot/strategies/tmrbtc/configs/btcusdt_binance_15m.json \
   --pair BTC/USDT:USDT \
   --timeframe 15m \
   --fee 0.0002 \
   --wallet 60000
```

## V čom je dobrá

- break-even 0.2154 % je nad poplatkom 0.0200 % (rezerva +0.1954 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 50. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20231001-20241001, 20250904-20260904 v strate)
- edge nad poplatkom len v 84 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 62.0 % (namerané 28.2 % medián) — na účet to treba mať
- proti náhode len +1.2 sigma: náznak, nie dôkaz
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 97.7 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'do 1.101' vlastnosti 'Volatilita voči normálu': 33 obchodov (25.4 %), bez nej by break-even bol o +0.1798 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 31 | -7.03 | -0.1622 | 16.9 | 51.6 | +3/-5 | `20261113-172303-f16a57` |
| 20221001-20231001 | 27 | +13.49 | 0.6591 | 0.9 | 63.0 | +5/-3 | `20261113-172306-19903c` |
| 20231001-20241001 | 24 | -10.32 | -0.2084 | 25.9 | 41.7 | +3/-6 | `20261113-172309-7d639a` |
| 20240904-20250904 | 24 | +55.64 | 0.7317 | 13.6 | 66.7 | +4/-2 | `20261113-172312-f2b926` |
| 20250904-20260904 | 25 | -1.22 | 0.0024 | 23.4 | 48.0 | +3/-5 | `20261113-172315-76d638` |

Zisková v **2 z 5** okien, obchodov spolu 130, break-even celkom 0.2154 %. Okná sa prekrývajú, 1 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (-0.14 ATR za 5 barov)
- medián držania 203 barov grafu
- winrate 53.85 %, payoff 1.087
- 0.07 obchodov za deň
- šikmosť výnosov +0.082

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `session_end` 97.7 %, `stop_loss` 2.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 1.101' vlastnosti 'Volatilita voči normálu': 33 obchodov (25.4 %), break-even -0.4612 % oproti 0.2154 % celku. Bez nej by break-even bol 0.3952 % (+0.1798). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 1.101 | 33 | 25.4 % | 42.4 | -0.4612 | 0.3952 | +0.1798 |
| 1.101 – 1.301 | 33 | 25.4 % | 48.5 | -0.1246 | 0.3444 | +0.1290 |
| nad 1.612 | 32 | 24.6 % | 65.6 | 0.6622 | 0.0608 | -0.1546 |
| 1.301 – 1.612 | 32 | 24.6 % | 59.4 | 0.6841 | 0.0526 | -0.1628 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.255 – 0.5348 | 33 | 25.4 % | 60.6 | -0.3353 | 0.3836 | +0.1682 |
| nad 0.7682 | 32 | 24.6 % | 53.1 | 0.2126 | 0.2163 | +0.0009 |
| 0.5348 – 0.7682 | 32 | 24.6 % | 46.9 | 0.2461 | 0.2076 | -0.0078 |
| do 0.255 | 33 | 25.4 % | 54.5 | 0.6250 | 0.0387 | -0.1767 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 24 | 27 | 20.8 % | 44.4 | -0.1641 | 0.3078 | +0.0924 |
| 14 – 24 | 34 | 26.2 % | 47.1 | -0.0640 | 0.3330 | +0.1176 |
| do 7 | 35 | 26.9 % | 54.3 | 0.4143 | 0.1469 | -0.0685 |
| 7 – 14 | 34 | 26.2 % | 67.7 | 0.6372 | 0.0734 | -0.1420 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.2154 % | -0.0023 % ± 0.1772 | +1.23 | 88.6 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.2154 % | -0.0214 % ± 0.1750 | +1.35 | 90.8 |

Naznak, ale nie dokaz (1.2 sigma, percentil 88.6). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 40 | 2.8 | 55.0 | -0.0644 | 21 |
| 2023-01 - 2024-03 | 27 | 1.9 | 55.6 | 0.7797 | 86 |
| 2024-03 - 2025-06 | 30 | 2.1 | 53.3 | 0.1419 | 45 |
| 2025-06 - 2026-08 | 33 | 2.3 | 51.5 | 0.2268 | 50 |

Hranice pre úsek veľkosti posledného obdobia: -0.4661 až +0.8805 % (medián 0.2263).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 50. percentile, teda v medziach -0.4661 až +0.8805 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2023-03-13T17:15 až 2023-05-03T20:00, spolu +2787.03.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-03-13T17:15 | 2023-03-15T20:00 | +314.66 | +1.31 | `session_end` |
| 2 | 2023-03-27T17:15 | 2023-03-29T20:00 | +1250.40 | +4.61 | `session_end` |
| 3 | 2023-04-10T17:15 | 2023-04-12T20:00 | +688.51 | +2.36 | `session_end` |
| 4 | 2023-04-24T17:15 | 2023-04-26T20:00 | +451.91 | +1.66 | `session_end` |
| 5 | 2023-05-01T17:15 | 2023-05-03T20:00 | +81.55 | +0.29 | `session_end` |

**Straty za sebou: 6** — 2024-03-18T17:15 až 2024-05-01T08:21, spolu -16909.09.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-03-18T17:15 | 2024-03-20T20:00 | -834.18 | -1.24 | `session_end` |
| 2 | 2024-03-25T17:15 | 2024-03-27T20:00 | -1613.02 | -2.28 | `session_end` |
| 3 | 2024-04-01T17:15 | 2024-04-03T20:00 | -2841.27 | -4.14 | `session_end` |
| 4 | 2024-04-08T17:15 | 2024-04-10T20:00 | -1813.22 | -2.53 | `session_end` |
| 5 | 2024-04-15T17:15 | 2024-04-17T20:00 | -3496.90 | -5.42 | `session_end` |
| 6 | 2024-04-29T17:15 | 2024-05-01T08:21 | -6310.49 | -10.04 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.2154 %**, medián 0.2193 %, 90 % interval -0.1123–0.5271 %
- P(edge > poplatok) = **84.1 %**
- max drawdown: medián 28.2 %, 95. percentil 62.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
- pravdepodobnosť ruiny účtu: 0.4 %

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
<!-- POSUDOK cisla=b5c09c4b -->

**1. Na čo sa to hodí.** Týždenný návrat (pondelok → streda) na BTCUSDT.P 15m. ~25 obchodov za rok, veľký pohyb na obchod (~3 %), poplatok mu neublíži.

**2. Potenciál.** **Nestabilné.** Dva silné roky (22/23 +13 %, 24/25 +56 %) a tri slabé; +1,2 sigma — výsledok drží niekoľko veľkých obchodov.

**3. Čo dorobiť.** BTC nemá víkendovú pauzu — „červený piatok“ a vstup v pondelok znamenajú na BTC niečo iné než na CME; stop poistka z MNQ.

**4. Čo otestovať.** Smernica na BTC (od ne 15. 11. 2026 po testoch MYM, do ne 22. 11. 18:00) s poplatkom maker 0,02 %; rozhodne odložený rok 9/2025–9/2026 a stabilita po rokoch. Pozor: pod 75 obchodov za rok smernicou neprejde bez výnimky.

**5. Použiteľné?** **Zatiaľ o ničom** — veľké výkyvy medzi rokmi.

**6. Čo by som pridal.** Definovať týždeň podľa nedele 0:00 UTC (začiatok týždňa BTC), nie podľa CME.

<!-- POSUDOK KONIEC -->
