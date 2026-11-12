# Základná analytika — T-MEAN REVERSION 1.0 (MYM) (`tmrmym`)

Zmerané 2026-11-12 na `MYM/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mym_databento_15m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tmrmym \
   --profile mym_databento_15m \
   --pair MYM/USD \
   --timeframe 15m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- break-even 0.0825 % je nad poplatkom 0.0018 % (rezerva +0.0807 bodu)
- drawdown drží: 95. percentil 5.1 %
- edge drží aj v poslednom období (2025-05 - 2026-08 na 34. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- edge nad poplatkom len v 92 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +0.6 sigma: náznak, nie dôkaz
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina '1.574 – 1.918' vlastnosti 'Volatilita voči normálu': 28 obchodov (24.8 %), bez nej by break-even bol o +0.0748 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 25 | +2.35 | 0.1694 | 0.9 | 56.0 | +4/-3 | `20261112-111903-a0a61b` |
| 20221001-20231001 | 20 | +0.24 | 0.0232 | 1.1 | 55.0 | +3/-3 | `20261112-111906-1cc674` |
| 20231001-20241001 | 21 | +0.17 | 0.0148 | 1.0 | 38.1 | +3/-3 | `20261112-111909-885b3f` |
| 20240904-20250904 | 22 | +2.11 | 0.1343 | 1.9 | 40.9 | +4/-7 | `20261112-111912-0813e0` |
| 20250904-20260904 | 27 | +0.92 | 0.0436 | 2.1 | 59.3 | +4/-4 | `20261112-111915-949ca3` |

Zisková v **5 z 5** okien, obchodov spolu 113, break-even celkom 0.0825 %. Okná sa prekrývajú, 2 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (-0.04 ATR za 5 barov)
- medián držania 203 barov grafu
- winrate 51.33 %, payoff 1.309
- 0.06 obchodov za deň
- šikmosť výnosov +1.434

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '1.574 – 1.918' vlastnosti 'Volatilita voči normálu': 28 obchodov (24.8 %), break-even -0.1395 % oproti 0.0825 % celku. Bez nej by break-even bol 0.1573 % (+0.0748). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.574 – 1.918 | 28 | 24.8 % | 35.7 | -0.1395 | 0.1573 | +0.0748 |
| 1.326 – 1.574 | 28 | 24.8 % | 42.9 | -0.0914 | 0.1402 | +0.0577 |
| do 1.326 | 29 | 25.7 % | 69.0 | 0.2696 | 0.0200 | -0.0625 |
| nad 1.918 | 28 | 24.8 % | 57.1 | 0.2933 | 0.0129 | -0.0696 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.6076 – 0.8278 | 28 | 24.8 % | 46.4 | -0.1105 | 0.1475 | +0.0650 |
| do 0.2553 | 29 | 25.7 % | 55.2 | 0.1330 | 0.0660 | -0.0165 |
| nad 0.8278 | 28 | 24.8 % | 60.7 | 0.1528 | 0.0598 | -0.0227 |
| 0.2553 – 0.6076 | 28 | 24.8 % | 42.9 | 0.1565 | 0.0569 | -0.0256 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.0673 | 29 | 25.7 % | 41.4 | -0.0136 | 0.1164 | +0.0339 |
| 0.0673 – 0.1362 | 28 | 24.8 % | 50.0 | 0.0136 | 0.1047 | +0.0222 |
| nad 0.2384 | 28 | 24.8 % | 50.0 | 0.0438 | 0.0950 | +0.0125 |
| 0.1362 – 0.2384 | 28 | 24.8 % | 64.3 | 0.2860 | 0.0140 | -0.0685 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0825 % | 0.0438 % ± 0.0639 | +0.61 | 71.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0825 % | 0.0473 % ± 0.0654 | +0.54 | 70.8 |

Neodlisitelne od nahody (+0.6 sigma, percentil 71.1). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 32 | 2.2 | 59.4 | 0.2052 | 87 |
| 2022-12 - 2024-03 | 23 | 1.6 | 43.5 | -0.1092 | 9 |
| 2024-03 - 2025-05 | 25 | 1.7 | 40.0 | 0.1792 | 80 |
| 2025-05 - 2026-08 | 33 | 2.3 | 57.6 | 0.0332 | 34 |

Hranice pre úsek veľkosti posledného obdobia: -0.0928 až +0.2608 % (medián 0.0743).

**DRZI** — posledné obdobie (2025-05 - 2026-08) je na 34. percentile, teda v medziach -0.0928 až +0.2608 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 4** — 2021-12-20T17:15 až 2022-01-12T20:00, spolu +962.98, rovnako dlhých sérií 4.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-12-20T17:15 | 2021-12-22T20:00 | +483.38 | +2.79 | `session_end` |
| 2 | 2021-12-27T17:15 | 2021-12-29T20:00 | +172.86 | +0.96 | `session_end` |
| 3 | 2022-01-03T17:15 | 2022-01-05T20:00 | +82.36 | +0.45 | `session_end` |
| 4 | 2022-01-10T17:15 | 2022-01-12T20:00 | +224.37 | +1.26 | `session_end` |

**Straty za sebou: 7** — 2024-09-09T17:15 až 2025-01-08T20:00, spolu -1153.77.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-09-09T17:15 | 2024-09-11T20:00 | -66.72 | -0.33 | `session_end` |
| 2 | 2024-09-23T17:15 | 2024-09-25T20:00 | -89.24 | -0.42 | `session_end` |
| 3 | 2024-10-28T17:15 | 2024-10-30T20:00 | -109.75 | -0.52 | `session_end` |
| 4 | 2024-11-18T17:15 | 2024-11-20T20:00 | -111.26 | -0.51 | `session_end` |
| 5 | 2024-12-09T17:15 | 2024-12-11T20:00 | -190.28 | -0.85 | `session_end` |
| 6 | 2024-12-16T17:15 | 2024-12-18T20:00 | -486.77 | -2.20 | `session_end` |
| 7 | 2024-12-30T17:15 | 2025-01-08T20:00 | -99.75 | -0.46 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0825 %**, medián 0.0820 %, 90 % interval -0.0128–0.1826 %
- P(edge > poplatok) = **91.5 %**
- max drawdown: medián 2.7 %, 95. percentil 5.1 %, najhorší 9.0 %
- najdlhšia séria strát: medián 7, 95. percentil 9 obchodov
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
<!-- POSUDOK cisla=eb06a28a -->

**1. Na čo sa to hodí.** Týždenný návrat k priemeru (vstup v pondelok/utorok, výstup v strede týždňa) na MYM 15m, ~22 obchodov za rok.

**2. Potenciál.** Jediná z ôsmich stratégií v zisku vo **všetkých 5 oknách**, break-even 0,08 % je vysoký (náklady jej neublížia) a výsledok je proti náhode +0,6 sigma, teda náznak. Prekážkou je počet obchodov: ~22 za rok je hlboko pod minimom smernice (75), takže takto smernicou neprejde.

**3. Čo dorobiť.** V logike nič. Na viac obchodov by musela obchodovať viac dní v týždni, čo mení podstatu javu.

**4. Čo otestovať.** Smernica od 12. 11. 19:00 skúša dni a hodiny vstupu/výstupu. Ak nájde variant s ≥ 75 obchodmi bez straty stability, je to kandidát. Inak stojí za to zvážiť výnimku z minima obchodov (rozhodne používateľ).

**5. Použiteľné?** Ako doplnok portfólia **áno, s výhradou** malého počtu obchodov. Podľa smernice nie.

**6. Čo by som pridal.** Spojiť s TMR na ES a MNQ do jedného „týždenného“ košíka: spolu by bolo ~70 obchodov za rok a jav by sa dal posúdiť naraz.

<!-- POSUDOK KONIEC -->
