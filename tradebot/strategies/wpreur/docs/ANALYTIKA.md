# Základná analytika — WILLIAMS %R LONG 1.0 (6E) (`wpreur`)

Zmerané 2026-11-15 na `6E/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/wpreur/configs/6e_databento_15m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy wpreur \
   --profile tradebot/strategies/wpreur/configs/6e_databento_15m.json \
   --pair 6E/USD \
   --timeframe 15m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 4308 obchodov spolu — na štatistiku dosť
- break-even 0.0022 % je nad poplatkom 0.0018 % (rezerva +0.0004 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 24. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: protitrendová (mean reversion) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20211001-20221001, 20250904-20260904 v strate)
- edge nad poplatkom len v 70 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 29.8 % (namerané 14.4 % medián) — na účet to treba mať
- proti náhode len +1.7 sigma: náznak, nie dôkaz
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 899 | -5.49 | 0.0004 | 10.8 | 63.1 | +15/-4 | `20261115-094600-9bcc62` |
| 20221001-20231001 | 881 | +8.61 | 0.0039 | 7.3 | 66.3 | +11/-6 | `20261115-094603-4ea2c2` |
| 20231001-20241001 | 858 | +4.20 | 0.0028 | 6.7 | 67.8 | +13/-5 | `20261115-094606-ec5994` |
| 20240904-20250904 | 865 | +3.18 | 0.0026 | 6.7 | 65.4 | +19/-5 | `20261115-094613-339c46` |
| 20250904-20260904 | 865 | -0.64 | 0.0016 | 7.4 | 62.3 | +10/-6 | `20261115-094616-9e9701` |

Zisková v **3 z 5** okien, obchodov spolu 4308, break-even celkom 0.0022 %. Okná sa prekrývajú, 60 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota dobrá)

- vstup proti poslednému pohybu (-1.44 ATR za 5 barov)
- medián držania 3 barov grafu
- winrate 64.9 %, payoff 0.554
- 2.39 obchodov za deň
- šikmosť výnosov -2.52

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0020 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 120 | 2.8 % | 64.2 | 0.0017 | 0.0022 | +0.0000 |
| žiadna | 3881 | 90.1 % | 64.8 | 0.0020 | 0.0042 | +0.0020 |
| NFP | 138 | 3.2 % | 65.9 | 0.0029 | 0.0022 | +0.0000 |
| CPI | 166 | 3.9 % | 65.1 | 0.0069 | 0.0020 | -0.0002 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| po vyhlásení | 213 | 4.9 % | 56.3 | -0.0014 | 0.0024 | +0.0002 |
| bez udalosti | 3881 | 90.1 % | 64.8 | 0.0020 | 0.0042 | +0.0020 |
| pred vyhlásením | 214 | 5.0 % | 74.3 | 0.0098 | 0.0018 | -0.0004 |

**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 99.96 R – 100 R | 2227 | 51.7 % | 64.8 | 0.0009 | 0.0035 | +0.0013 |
| nad 100 R | 922 | 21.4 % | 64.0 | 0.0024 | 0.0021 | -0.0001 |
| do 99.96 R | 1159 | 26.9 % | 65.8 | 0.0044 | 0.0014 | -0.0008 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0022 % | 0.0001 % ± 0.0013 | +1.71 | 96.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0022 % | 0.0001 % ± 0.0013 | +1.71 | 96.3 |

Naznak, ale nie dokaz (1.7 sigma, percentil 96.3). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 1101 | 74.6 | 63.8 | 0.0027 | 57 |
| 2022-12 - 2024-03 | 1067 | 72.3 | 67.7 | 0.0023 | 50 |
| 2024-03 - 2025-06 | 1077 | 73.0 | 65.8 | 0.0028 | 63 |
| 2025-06 - 2026-09 | 1063 | 72.1 | 62.4 | 0.0010 | 24 |

Hranice pre úsek veľkosti posledného obdobia: -0.0007 až +0.0050 % (medián 0.0022).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 24. percentile, teda v medziach -0.0007 až +0.0050 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 19** — 2025-05-30T03:45 až 2025-06-05T20:00, spolu +1317.50.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-05-30T03:45 | 2025-05-30T04:00 | +20.02 | +0.01 | `session_end` |
| 2 | 2025-05-30T05:00 | 2025-05-30T05:45 | +57.52 | +0.04 | `session_end` |
| 3 | 2025-05-30T09:00 | 2025-05-30T10:00 | +126.27 | +0.09 | `session_end` |
| 4 | 2025-05-30T13:45 | 2025-05-30T14:00 | +88.78 | +0.06 | `session_end` |
| 5 | 2025-05-30T20:30 | 2025-06-01T22:00 | +113.76 | +0.08 | `session_end` |
| 6 | 2025-06-02T03:45 | 2025-06-02T03:45 | +45.01 | +0.03 | `session_end` |
| 7 | 2025-06-02T11:00 | 2025-06-02T12:30 | +88.74 | +0.06 | `session_end` |
| 8 | 2025-06-03T01:15 | 2025-06-03T01:30 | +13.73 | +0.01 | `session_end` |
| 9 | 2025-06-03T03:30 | 2025-06-03T04:45 | +69.98 | +0.05 | `session_end` |
| 10 | 2025-06-03T05:30 | 2025-06-03T05:45 | +76.24 | +0.05 | `session_end` |
| 11 | 2025-06-03T10:30 | 2025-06-03T10:30 | +76.24 | +0.05 | `session_end` |
| 12 | 2025-06-03T12:15 | 2025-06-03T13:00 | +82.50 | +0.06 | `session_end` |
| 13 | 2025-06-04T03:45 | 2025-06-04T04:00 | +101.26 | +0.07 | `session_end` |
| 14 | 2025-06-04T05:00 | 2025-06-04T05:00 | +45.01 | +0.03 | `session_end` |
| 15 | 2025-06-04T10:30 | 2025-06-04T10:45 | +45.00 | +0.03 | `session_end` |
| 16 | 2025-06-04T19:30 | 2025-06-04T20:15 | +38.74 | +0.03 | `session_end` |
| 17 | 2025-06-05T02:15 | 2025-06-05T02:30 | +57.49 | +0.04 | `session_end` |
| 18 | 2025-06-05T04:00 | 2025-06-05T06:00 | +82.49 | +0.06 | `session_end` |
| 19 | 2025-06-05T17:45 | 2025-06-05T20:00 | +88.73 | +0.06 | `session_end` |

**Straty za sebou: 6** — 2022-10-27T17:45 až 2022-10-31T14:15, spolu -463.78, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-10-27T17:45 | 2022-10-27T18:30 | -104.39 | -0.08 | `session_end` |
| 2 | 2022-10-28T05:15 | 2022-10-28T06:30 | -123.14 | -0.10 | `session_end` |
| 3 | 2022-10-28T07:15 | 2022-10-28T08:30 | -116.88 | -0.09 | `session_end` |
| 4 | 2022-10-28T15:15 | 2022-10-28T16:45 | -29.38 | -0.02 | `session_end` |
| 5 | 2022-10-31T08:00 | 2022-10-31T09:00 | -35.62 | -0.03 | `session_end` |
| 6 | 2022-10-31T13:00 | 2022-10-31T14:15 | -54.36 | -0.04 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0022 %**, medián 0.0022 %, 90 % interval 0.0008–0.0036 %
- P(edge > poplatok) = **69.8 %**
- max drawdown: medián 14.4 %, 95. percentil 29.8 %, najhorší 59.2 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
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
<!-- POSUDOK cisla=b97963b1 -->

**1. Na čo sa to hodí.** Williams %R long na 6E 15m — kúpa pri prepredanosti a výstup pri návrate; sedí na EUR, ktorý sa vracia späť (charakter mean reversion, istota dobrá). Čísla sú z **neladeného východiska** (predloha z MNQ, tickové prahy ×0,12); ladenie pôjde len na 2016–2021/9, tieto okná sú preň čisté overenie a nesmú ho ovplyvniť.

**2. Potenciál.** **Stredný.** ~860 obchodov za rok, zisk v 3 z 5 okien, +1,7 sigma, ale break-even 0,0022 % je len tesne nad poplatkom 0,0018 % — na 6E sa malý edge ľahko stratí v sklze.

**3. Čo dorobiť.** Menej a kvalitnejších vstupov (prísnejší `entryLevel`, vyšší TF), aby priemer na obchod vyrástol nad 2× poplatok.

**4. Čo otestovať.** Smernica EUR (ne 22. 11. – 29. 11. 2026): ladenie 2016–2021/9, potom raz päť okien; krok 8 na EURUSD CFD. Rozhodne break-even ≥ 2× poplatok a 4 z 5 okien.

**5. Použiteľné?** **Zatiaľ nie** — edge je, ale tenký; uvidí sa po ladení.

**6. Čo by som pridal.** Obchodovať len v živých oknách (London 2–5, NY 8–11 NY), kde je pohyb dosť veľký na poplatok.

<!-- POSUDOK KONIEC -->
