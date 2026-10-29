# Základná analytika — SPRÁVY 3.0 (`spravy`)

Zmerané 2026-10-29 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mgc_databento_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy spravy \
   --profile mgc_databento_5m \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 100000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 271 obchodov spolu — na štatistiku dosť
- break-even 0.0784 % je nad poplatkom 0.0018 % (rezerva +0.0766 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 1.2 %
- odlíšiteľná od náhody (+4.8 sigma proti náhodnému vstupu)
- posledné obdobie (2025-06 - 2026-09) je nad horným intervalom vlastnej minulosti — dôvod zvyšovať riziko to ale nie je, rovnako dobre to môže byť priaznivý režim

## Kde má chyby

- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 72 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'short' vlastnosti 'Smer': 153 obchodov (56.5 %), bez nej by break-even bol o +0.0341 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 57 | +0.47 | 0.0244 | 0.4 | 45.6 | +3/-4 | `20261029-084601-99a5c1` |
| 20221001-20231001 | 55 | +0.14 | 0.0083 | 0.3 | 45.5 | +3/-5 | `20261029-084604-8353bf` |
| 20231001-20241001 | 55 | +0.76 | 0.0329 | 0.3 | 43.6 | +4/-4 | `20261029-084607-39f449` |
| 20240904-20250904 | 57 | +1.82 | 0.0552 | 1.0 | 57.9 | +6/-6 | `20261029-084610-a690f3` |
| 20250904-20260904 | 52 | +7.92 | 0.1722 | 0.4 | 63.5 | +4/-2 | `20261029-084613-327a08` |

Zisková v **5 z 5** okien, obchodov spolu 271, break-even celkom 0.0784 %. Okná sa prekrývajú, 5 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (-0.18 ATR za 5 barov)
- medián držania 11 barov grafu
- winrate 51.29 %, payoff 2.106
- 0.15 obchodov za deň
- šikmosť výnosov +1.642

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `session_end` 72 %, `stop_loss` 23.6 %, `take_profit` 4.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'short' vlastnosti 'Smer': 153 obchodov (56.5 %), break-even 0.052 % oproti 0.0784 % celku. Bez nej by break-even bol 0.1125 % (+0.0341). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 153 | 56.5 % | 50.3 | 0.0520 | 0.1125 | +0.0341 |
| long | 118 | 43.5 % | 52.5 | 0.1125 | 0.0520 | -0.0264 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 166 | 61.3 % | 48.8 | 0.0616 | 0.1043 | +0.0259 |
| s trendom | 105 | 38.7 % | 55.2 | 0.1043 | 0.0616 | -0.0168 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 10 | 73 | 26.9 % | 41.1 | 0.0112 | 0.1020 | +0.0236 |
| 10 – 13 | 65 | 24.0 % | 53.9 | 0.0661 | 0.0823 | +0.0039 |
| nad 26 | 60 | 22.1 % | 55.0 | 0.1140 | 0.0677 | -0.0107 |
| 13 – 26 | 73 | 26.9 % | 56.2 | 0.1230 | 0.0618 | -0.0166 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0784 % | 0.0001 % ± 0.0161 | +4.85 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0784 % | 0.0007 % ± 0.0179 | +4.33 | 100.0 |

Edge je odlisitelny od nahody (4.8 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 70 | 4.8 | 44.3 | 0.0111 | 5 |
| 2022-12 - 2024-03 | 68 | 4.6 | 44.1 | 0.0258 | 10 |
| 2024-03 - 2025-06 | 67 | 4.5 | 56.7 | 0.0499 | 29 |
| 2025-06 - 2026-09 | 66 | 4.5 | 60.6 | 0.1525 | 97 |

Hranice pre úsek veľkosti posledného obdobia: +0.0073 až +0.1426 % (medián 0.0705).

**ZLEPSUJE SA** — posledné obdobie (2025-06 - 2026-09) je nad hornou hranicou +0.1426 %. Pozor na opačnú chybu — dôvod zvyšovať riziko to nie je, rovnako dobre to môže byť priaznivý režim.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2025-07-29T15:00 až 2025-08-29T17:25, spolu +1134.85.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-07-29T15:00 | 2025-07-29T15:55 | +79.81 | +0.24 | `session_end` |
| 2 | 2025-07-30T18:00 | 2025-07-30T20:50 | +270.83 | +0.81 | `session_end` |
| 3 | 2025-07-31T13:30 | 2025-07-31T17:25 | +126.82 | +0.38 | `session_end` |
| 4 | 2025-08-12T13:30 | 2025-08-12T14:25 | +122.81 | +0.36 | `session_end` |
| 5 | 2025-08-14T12:45 | 2025-08-14T14:05 | +132.81 | +0.39 | `take_profit` |
| 6 | 2025-08-29T13:30 | 2025-08-29T17:25 | +401.77 | +1.16 | `session_end` |

**Straty za sebou: 6** — 2023-09-20T18:00 až 2023-10-27T17:25, spolu -222.02, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-09-20T18:00 | 2023-09-20T18:00 | -36.69 | -0.19 | `stop_loss` |
| 2 | 2023-09-29T13:30 | 2023-09-29T13:50 | -48.66 | -0.26 | `stop_loss` |
| 3 | 2023-10-03T15:00 | 2023-10-03T15:55 | -17.65 | -0.10 | `session_end` |
| 4 | 2023-10-11T12:45 | 2023-10-11T13:05 | -19.66 | -0.10 | `stop_loss` |
| 5 | 2023-10-12T13:30 | 2023-10-12T14:25 | -30.66 | -0.16 | `session_end` |
| 6 | 2023-10-27T13:30 | 2023-10-27T17:25 | -68.70 | -0.34 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0784 %**, medián 0.0774 %, 90 % interval 0.0447–0.1120 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 0.7 %, 95. percentil 1.2 %, najhorší 3.0 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

<!-- POSUDOK cisla=f83f2c4d -->

**Posudok východiskového profilu SPRÁVY 3.0 (29. 10. 2026, MGC 5m, 1 kontrakt; pravidlá: FOMC PRED do 16:55 NY, CPI a JOLTS proti prvej hodine, PPI proti prvým 15 min so stopom za extrémom a cieľom 1 : 3, PCE v smere nohy 15 → 60; cieľ RRR len pri PPI).**

1. **Na čo sa hodí a na čo nie.** Zlato (MGC / GC, na MT5 XAUUSD) na 5m grafe, len v dni červených správ USA, ~55 obchodov za rok, 0,15 obchodu za deň. Doplnkový modul k iným stratégiám, nie celodenný systém. 72 % obchodov končí na čase — výstup v čase je zámer (pri FOMC a PCE cieľ odrezal veľké pohyby), nie chyba seansy. Na indexy sa pravidlá neprenášajú (MNQ a ES reagujú na CPI / NFP opačne).
2. **Má to potenciál?** Áno. Zisková v 5 z 5 okien, +4,8 sigma proti náhodnému vstupu (1.0 malo +3,6), break-even 0,08 % = 44× poplatok, edge nad poplatkom v 100 % vzoriek, 95. percentil prepadu 1,2 %. Pravidlá majú vysvetlenie (otočenie driftu pred FOMC, návrat výstrelu PPI). Varovanie: výsledok drží hlavne posledné okno (break-even 0,17 % proti 0,008–0,055 % v predošlých) — býčí trh zlata 2025–26; prvé dve obdobia sú na 5. a 10. percentile vlastnej krivky. Pravidlá aj RRR pri PPI sú vybrané z mnohých variantov na tých istých dátach (~45 hypotéz + 25 variantov cieľa), čísla sú preto optimistické.
3. **Čo treba dorobiť.** Kalendár: 2027 doplnený pre FOMC, CPI, NFP, PPI, ISM, CLAIMS; JOLTS, PCE, GDP, RETAIL čakajú na zverejnenie (test `test_kalendar_pokryva_buducnost` pripomenie). Porovnanie s exportom ForexFactory na hube (presunuté správy) a upozornenie na karte Live. Sklz pri vstupe PRED presne v čase FOMC (volatilita 10× bežnej) — v teste je fill na open baru 14:00, naživo môže byť horší.
4. **Čo otestovať ďalej.** `python -m tester.robust` (krok 9: 2× poplatok, vstup o sviečku neskôr — pre PRED rozhodujúce), `cli matrix` na XAU/USD (Dukascopy). Každé pravidlo samostatne po rokoch: CPI slabne (PF 6,4 → 1,0), PCE a JOLTS boli v prvých dvoch oknách pod 1 — ak to tak ostane aj na XAU, vypnúť prepínačom. RRR pri PPI (1 : 3) overiť na XAU, kým sa zapne aj inde.
5. **Použiteľné?** **Áno, ako modul na zlato po správach**, s 1 kontraktom alebo malým rizikom. Pod hranicou smernice (150 obchodov za rok) — výnimka používateľa 29. 10. 2026.
6. **Čo by som pridal.** Pravidlo 2 (tlačovka FOMC) je pripravené: zisk +2 831 $ samostatne, ale s ním padne prvé okno na PF 0,95 — zapnúť až po overení na XAU. Filter „prekvapenie“ (veľkosť nohy voči bežnej reakcii na ten typ správy), aby FADE bral len prehnané reakcie.

<!-- POSUDOK KONIEC -->
