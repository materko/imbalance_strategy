# Základná analytika — MTK EMAS 1.0 MYM (C# jadro) (`mtkemasmymnet`)

Zmerané 2026-11-26 na `MYM/USD` 2h, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/mtkemasmymnet/configs/mym_databento_2h.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy mtkemasmymnet \
   --profile tradebot/strategies/mtkemasmymnet/configs/mym_databento_2h.json \
   --timeframe 2h \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- break-even 0.1763 % je nad poplatkom 0.0018 % (rezerva +0.1745 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- odlíšiteľná od náhody (+2.5 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 22. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- 95. percentil max drawdownu 26.0 % (namerané 12.7 % medián) — na účet to treba mať
- najhoršia skupina 'proti trendu' vlastnosti 'S trendom, alebo proti': 35 obchodov (33.3 %), bez nej by break-even bol o +0.0660 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 9 | +36.68 | 0.2868 | 4.6 | 44.4 | +2/-4 | `20261126-074342-7af46f` |
| 20221001-20231001 | 25 | +56.55 | 0.1050 | 15.7 | 24.0 | +3/-10 | `20261126-074345-40d24d` |
| 20231001-20241001 | 21 | +194.99 | 0.3898 | 9.1 | 38.1 | +2/-4 | `20261126-074348-e4183b` |
| 20240904-20250904 | 20 | +82.83 | 0.1782 | 11.6 | 40.0 | +4/-9 | `20261126-074351-26cd74` |
| 20250904-20260904 | 31 | +48.96 | 0.0808 | 11.1 | 25.8 | +2/-8 | `20261126-074354-76ad99` |

Zisková v **5 z 5** okien, obchodov spolu 105, break-even celkom 0.1763 %. Okná sa prekrývajú, 1 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.42 ATR za 5 barov)
- medián držania 5.8 barov grafu
- winrate 31.43 %, payoff 8.445
- 0.06 obchodov za deň
- šikmosť výnosov +5.066

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `trailing_stop` 58.1 %, `stop_loss` 38.1 %, `session_end` 2.9 %, `force_exit` 1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'proti trendu' vlastnosti 'S trendom, alebo proti': 35 obchodov (33.3 %), break-even 0.0627 % oproti 0.1763 % celku. Bez nej by break-even bol 0.2423 % (+0.0660). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 35 | 33.3 % | 17.1 | 0.0627 | 0.2423 | +0.0660 |
| s trendom | 70 | 66.7 % | 38.6 | 0.2423 | 0.0627 | -0.1136 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.937 – 1.019 | 26 | 24.8 % | 23.1 | -0.0089 | 0.2386 | +0.0623 |
| 1.019 – 1.227 | 26 | 24.8 % | 30.8 | 0.0676 | 0.2133 | +0.0370 |
| nad 1.227 | 26 | 24.8 % | 26.9 | 0.1801 | 0.1753 | -0.0010 |
| do 0.937 | 27 | 25.7 % | 44.4 | 0.4332 | 0.0734 | -0.1029 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.3767 % | 26 | 24.8 % | 23.1 | 0.0256 | 0.2055 | +0.0292 |
| do 0.2577 % | 27 | 25.7 % | 29.6 | 0.0656 | 0.2377 | +0.0614 |
| 0.2577 % – 0.3278 % | 26 | 24.8 % | 38.5 | 0.2968 | 0.1333 | -0.0430 |
| 0.3278 % – 0.3767 % | 26 | 24.8 % | 34.6 | 0.3236 | 0.1351 | -0.0412 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.1647 % | 0.0175 % ± 0.0582 | +2.53 | 98.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.1647 % | 0.0224 % ± 0.0622 | +2.29 | 98.7 |

Edge je odlisitelny od nahody (2.5 sigma, percentil 98.7).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 12 | 0.8 | 41.7 | 0.2658 | 77 |
| 2022-12 - 2024-03 | 36 | 2.5 | 25.0 | 0.1903 | 54 |
| 2024-03 - 2025-06 | 17 | 1.2 | 41.2 | 0.2832 | 78 |
| 2025-06 - 2026-09 | 40 | 2.7 | 30.0 | 0.0941 | 22 |

Hranice pre úsek veľkosti posledného obdobia: +0.0212 až +0.3424 % (medián 0.1660).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 22. percentile, teda v medziach +0.0212 až +0.3424 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2024-08-14T16:00 až 2025-02-02T23:00, spolu +56398.60.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-08-14T16:00 | 2024-08-28T18:03 | +13554.91 | +2.05 | `trailing_stop` |
| 2 | 2024-09-13T04:00 | 2024-09-30T18:22 | +16560.38 | +2.77 | `trailing_stop` |
| 3 | 2024-10-09T14:00 | 2024-10-16T07:24 | +8033.93 | +0.97 | `trailing_stop` |
| 4 | 2024-11-06T08:00 | 2024-11-15T06:11 | +5679.57 | +1.19 | `trailing_stop` |
| 5 | 2025-01-15T14:00 | 2025-02-02T23:00 | +12569.81 | +2.32 | `trailing_stop` |

**Straty za sebou: 10** — 2023-01-06T16:00 až 2023-04-28T07:44, spolu -10082.76.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-01-06T16:00 | 2023-01-10T02:34 | -26.15 | -0.01 | `trailing_stop` |
| 2 | 2023-01-23T16:00 | 2023-01-23T19:35 | -20.71 | -0.00 | `trailing_stop` |
| 3 | 2023-01-26T06:00 | 2023-01-26T14:56 | -2019.36 | -0.33 | `stop_loss` |
| 4 | 2023-01-31T18:00 | 2023-02-01T14:30 | -49.46 | -0.01 | `trailing_stop` |
| 5 | 2023-02-06T18:00 | 2023-02-07T14:17 | -1950.10 | -0.35 | `stop_loss` |
| 6 | 2023-02-13T16:00 | 2023-02-14T13:30 | -20.99 | -0.00 | `trailing_stop` |
| 7 | 2023-02-16T18:00 | 2023-02-16T20:16 | -2082.17 | -0.37 | `stop_loss` |
| 8 | 2023-03-06T14:00 | 2023-03-06T18:36 | -3.82 | -0.00 | `trailing_stop` |
| 9 | 2023-03-23T16:00 | 2023-03-23T17:10 | -1925.86 | -0.45 | `stop_loss` |
| 10 | 2023-04-28T06:00 | 2023-04-28T07:44 | -1984.15 | -0.27 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.1763 %**, medián 0.1730 %, 90 % interval 0.0814–0.2733 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 12.7 %, 95. percentil 26.0 %, najhorší 62.1 %
- najdlhšia séria strát: medián 11, 95. percentil 16 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 892** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=e35b5fd5 -->

1. **Na čo sa to hodí a na čo nie.** MYM 2h (VWMA 7 × 200 + EMA 200, len longy): pomalé sledovanie trendu na 1h–4h, obchody trvajú dni, zisk robí
   pár veľkých pohybov (WR 20–35 %). Hodí sa ako **časť portfólia** viacerých trhov (MNQ, zlato, ES, MYM, BTC), nie ako
   samostatná stratégia — na jednom trhu je obchodov málo. Na CFD treba prirátať swap za držanie cez noc a víkend.
   Percentá v tabuľkách sú pri riziku 2 000 $ na obchod a účte 60 000 $ — rozhoduje PF a znamienko po rokoch.
2. **Má to potenciál?** Čísla: PF 3,87 (rok 2022 len 1,07), 21 obchodov za rok, WR 31 %, zisková v 5 z 5 okien. Výhrada: málo obchodov (21 za rok) — jeden dobrý pohyb urobí rok; PF je vďaka výberu výstupu v štúdii optimistický. Edge je teda skutočný,
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
