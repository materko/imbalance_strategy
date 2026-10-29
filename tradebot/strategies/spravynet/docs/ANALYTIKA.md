# Základná analytika — SPRÁVY (C# jadro) (`spravynet`)

Zmerané 2026-10-29 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mgc_databento_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy spravynet \
   --profile mgc_databento_5m \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 100000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 271 obchodov spolu — na štatistiku dosť
- break-even 0.0621 % je nad poplatkom 0.0018 % (rezerva +0.0603 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 1.1 %
- odlíšiteľná od náhody (+3.6 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 84. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 87.5 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'short' vlastnosti 'Smer': 141 obchodov (52.0 %), bez nej by break-even bol o +0.0286 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 57 | +0.23 | 0.0126 | 0.3 | 50.9 | +4/-5 | `20261029-063258-cf3418` |
| 20221001-20231001 | 55 | +0.08 | 0.0054 | 0.5 | 45.5 | +5/-6 | `20261029-063301-879fbb` |
| 20231001-20241001 | 55 | +1.31 | 0.0555 | 0.3 | 52.7 | +5/-3 | `20261029-063304-52affb` |
| 20240904-20250904 | 57 | +1.82 | 0.0550 | 0.5 | 64.9 | +6/-3 | `20261029-063307-74b578` |
| 20250904-20260904 | 52 | +5.61 | 0.1225 | 0.5 | 59.6 | +6/-3 | `20261029-063310-9d8a73` |

Zisková v **5 z 5** okien, obchodov spolu 271, break-even celkom 0.0621 %. Okná sa prekrývajú, 5 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.19 ATR za 5 barov)
- medián držania 11 barov grafu
- winrate 54.61 %, payoff 1.781
- 0.15 obchodov za deň
- šikmosť výnosov +2.142

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `session_end` 87.5 %, `stop_loss` 12.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'short' vlastnosti 'Smer': 141 obchodov (52.0 %), break-even 0.0359 % oproti 0.0621 % celku. Bez nej by break-even bol 0.0907 % (+0.0286). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 141 | 52.0 % | 56.7 | 0.0359 | 0.0907 | +0.0286 |
| long | 130 | 48.0 % | 52.3 | 0.0907 | 0.0359 | -0.0262 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 149 | 55.0 % | 52.4 | 0.0419 | 0.0851 | +0.0230 |
| s trendom | 122 | 45.0 % | 57.4 | 0.0851 | 0.0419 | -0.0202 |

**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 996.32 R – 1 000 R | 42 | 31.6 % | 54.8 | 0.0329 | 0.1118 | +0.0230 |
| 1 000 R – 1 003 R | 24 | 18.0 % | 54.2 | 0.0912 | 0.0882 | -0.0006 |
| nad 1 003 R | 33 | 24.8 % | 39.4 | 0.1159 | 0.0797 | -0.0091 |
| do 996.32 R | 34 | 25.6 % | 55.9 | 0.1243 | 0.0768 | -0.0120 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0621 % | 0.0003 % ± 0.0171 | +3.62 | 99.9 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0621 % | 0.0017 % ± 0.0177 | +3.40 | 100.0 |

Edge je odlisitelny od nahody (3.6 sigma, percentil 99.9).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 71 | 4.8 | 47.9 | 0.0044 | 4 |
| 2022-12 - 2024-03 | 67 | 4.5 | 46.3 | 0.0109 | 9 |
| 2024-03 - 2025-06 | 67 | 4.5 | 65.7 | 0.0646 | 71 |
| 2025-06 - 2026-09 | 66 | 4.5 | 59.1 | 0.1113 | 84 |

Hranice pre úsek veľkosti posledného obdobia: +0.0030 až +0.1494 % (medián 0.0468).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 84. percentile, teda v medziach +0.0030 až +0.1494 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2024-12-12T14:30 až 2025-01-15T15:25, spolu +545.38, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-12-12T14:30 | 2024-12-12T15:25 | +3.05 | +0.01 | `session_end` |
| 2 | 2024-12-18T20:00 | 2024-12-18T23:55 | +180.08 | +0.69 | `session_end` |
| 3 | 2024-12-20T14:30 | 2024-12-20T18:25 | +123.07 | +0.47 | `session_end` |
| 4 | 2025-01-07T16:00 | 2025-01-07T16:55 | +45.07 | +0.17 | `session_end` |
| 5 | 2025-01-14T14:30 | 2025-01-14T15:25 | +101.06 | +0.38 | `session_end` |
| 6 | 2025-01-15T14:30 | 2025-01-15T15:25 | +93.05 | +0.34 | `session_end` |

**Straty za sebou: 6** — 2023-05-02T15:00 až 2023-05-31T15:09, spolu -328.23.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-05-02T15:00 | 2023-05-02T15:55 | -61.71 | -0.31 | `session_end` |
| 2 | 2023-05-03T19:00 | 2023-05-03T19:51 | -69.71 | -0.34 | `stop_loss` |
| 3 | 2023-05-10T13:30 | 2023-05-10T14:25 | -4.72 | -0.02 | `session_end` |
| 4 | 2023-05-11T13:30 | 2023-05-11T14:25 | -120.71 | -0.59 | `session_end` |
| 5 | 2023-05-26T13:30 | 2023-05-26T14:35 | -62.68 | -0.32 | `stop_loss` |
| 6 | 2023-05-31T15:00 | 2023-05-31T15:09 | -8.70 | -0.04 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0621 %**, medián 0.0596 %, 90 % interval 0.0280–0.1036 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 0.7 %, 95. percentil 1.1 %, najhorší 2.2 %
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
<!-- POSUDOK cisla=070131a5 -->

**Posudok východiskového profilu (29. 10. 2026, MGC 5m, 1 kontrakt, TREND FOMC + PCE, FADE CPI + PPI + JOLTS).**

1. **Na čo sa hodí a na čo nie.** Zlato (MGC / GC futures, na MT5 XAUUSD) na 5m grafe, len v dni červených správ USA, ~55 obchodov za rok. Je to doplnkový modul k iným stratégiám, nie celodenný systém. Pevný počet kontraktov je zámer: veľkosť z rizika pri tesnom stope nafúkne pozíciu (PF 1,11 vs 2,18). Pri riziku v $ treba minimum stopu na výpočet veľkosti (`sizeMinRisk` ~8 ATR). Na indexy sa to neprenáša: MNQ a ES reagujú na CPI / NFP inak (prvý pohyb sa vráti, FOMC nič).
2. **Má to potenciál?** Áno. Zisková v 5 z 5 okien, +3,6 sigma proti náhodnému vstupu, edge nad poplatkom v 100 % vzoriek, posledné obdobie na 84. percentile a prepad v 95. percentile len 1,1 %. Ťahá to hlavne TREND po FOMC a PCE (PF ~3, na odloženom 2025–26 PF 3,5). FADE je slabší (PF ~1,5) a v rokoch 22/23 a 24/25 okolo nuly. Typy správ som vybral až z prieskumu všetkých 12, takže čísla sú optimistické.
3. **Čo treba dorobiť.** Kalendár na ďalší rok (raz ročne, BLS / BEA / Fed), porovnanie s exportom ForexFactory na hube (presunuté správy, shutdown) a sviatky so skoršou seansou. Výstup v čase prechádza prestávkou CME 17:00–18:00 NY (FOMC + 5 h), zavrie sa na prvom bare po nej.
4. **Čo otestovať ďalej.** `cli matrix` na GC / XAU (Dukascopy) pre krok 8. `tester.robust` (krok 9: 2× poplatok, oneskorenie o sviečku, DSR pri počte skúšaných variantov ~300). FADE zvlášť na odloženom roku: ak tam PF nebude nad 1,2, nechať len TREND.
5. **Použiteľné?** **Áno, ako modul na zlato po správach**, s 1 kontraktom alebo malým rizikom. Počet obchodov je pod hranicou smernice (150 za rok), preto ide mimo štandardného hodnotenia (výnimka používateľa 29. 10. 2026).
6. **Čo by som pridal.** Pri TREND po FOMC trailing až do rána (Ázia často pokračuje), keď noha prekročí 1 ATR dňa. Filter „prekvapenie“ (veľkosť nohy voči bežnej reakcii na ten typ správy), aby sa FADE bral len pri prehnanej reakcii.

**C# jadro:** čísla sú bar po bare zhodné s Python predlohou `spravy` (`tester/tests/test_csharp_parity_spravy.py`, aj cez posun času USA / SK).

<!-- POSUDOK KONIEC -->
