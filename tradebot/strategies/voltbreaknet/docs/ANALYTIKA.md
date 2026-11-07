# Základná analytika — Volt Break (C# jadro) (`voltbreaknet`)

Zmerané 2026-11-07 na `MNQ/USD` 1h, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `PRESIEL_SMERNICAMI_Volt_Break_1`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy voltbreaknet \
   --profile PRESIEL_SMERNICAMI_Volt_Break_1 \
   --pair MNQ/USD \
   --timeframe 1h \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 802 obchodov spolu — na štatistiku dosť
- break-even 0.0288 % je nad poplatkom 0.0018 % (rezerva +0.0270 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 13.8 %
- odlíšiteľná od náhody (+4.7 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 28. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'do 0.7015' vlastnosti 'Kde v rozsahu, v smere obchodu': 201 obchodov (25.1 %), bez nej by break-even bol o +0.0100 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 160 | +34.04 | 0.0395 | 9.7 | 55.6 | +7/-7 | `20261107-151323-c3d56d` |
| 20221001-20231001 | 151 | +32.45 | 0.0421 | 6.9 | 55.6 | +6/-7 | `20261107-151326-1549f5` |
| 20231001-20241001 | 162 | +32.09 | 0.0294 | 8.9 | 54.3 | +8/-7 | `20261107-151329-e2ba5f` |
| 20240904-20250904 | 150 | +30.27 | 0.0258 | 5.6 | 54.0 | +8/-4 | `20261107-151332-237a24` |
| 20250904-20260904 | 189 | +38.49 | 0.0208 | 7.8 | 54.0 | +6/-5 | `20261107-151335-f5401a` |

Zisková v **5 z 5** okien, obchodov spolu 802, break-even celkom 0.0288 %. Okná sa prekrývajú, 10 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.74 ATR za 5 barov)
- medián držania 1.1 barov grafu
- winrate 54.61 %, payoff 1.2
- 0.45 obchodov za deň
- šikmosť výnosov +0.02

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 54.6 %, `stop_loss` 45.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 0.7015' vlastnosti 'Kde v rozsahu, v smere obchodu': 201 obchodov (25.1 %), break-even -0.0008 % oproti 0.0288 % celku. Bez nej by break-even bol 0.0388 % (+0.0100). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.7015 | 201 | 25.1 % | 45.3 | -0.0008 | 0.0388 | +0.0100 |
| 0.8992 – 0.9702 | 200 | 24.9 % | 57.0 | 0.0350 | 0.0268 | -0.0020 |
| nad 0.9702 | 200 | 24.9 % | 56.0 | 0.0385 | 0.0256 | -0.0032 |
| 0.7015 – 0.8992 | 201 | 25.1 % | 60.2 | 0.0431 | 0.0241 | -0.0047 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 210 | 26.2 % | 46.7 | 0.0033 | 0.0379 | +0.0091 |
| s trendom | 592 | 73.8 % | 57.4 | 0.0379 | 0.0033 | -0.0255 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 682 | 85.0 % | 54.4 | 0.0275 | 0.0365 | +0.0077 |
| NFP | 41 | 5.1 % | 53.7 | 0.0321 | 0.0286 | -0.0002 |
| FOMC | 28 | 3.5 % | 57.1 | 0.0396 | 0.0285 | -0.0003 |
| CPI | 49 | 6.1 % | 57.1 | 0.0398 | 0.0281 | -0.0007 |

Parametre, ktorými sa dá s tým niečo spraviť: `endHHMM`, `slUsd`, `startHHMM`, `tpUsd`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0288 % | 0.0016 % ± 0.0058 | +4.67 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0288 % | 0.0024 % ± 0.0054 | +4.90 | 100.0 |

Edge je odlisitelny od nahody (4.7 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 195 | 13.2 | 53.9 | 0.0336 | 67 |
| 2022-12 - 2024-03 | 196 | 13.3 | 54.6 | 0.0358 | 70 |
| 2024-03 - 2025-06 | 195 | 13.2 | 54.9 | 0.0287 | 49 |
| 2025-06 - 2026-09 | 216 | 14.6 | 55.1 | 0.0231 | 28 |

Hranice pre úsek veľkosti posledného obdobia: +0.0124 až +0.0462 % (medián 0.0290).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 28. percentile, teda v medziach +0.0124 až +0.0462 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2024-06-25T18:00 až 2024-07-10T19:51, spolu +949.57, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-06-25T18:00 | 2024-06-25T22:08 | +118.10 | +0.30 | `take_profit` |
| 2 | 2024-06-27T19:00 | 2024-06-28T00:33 | +118.59 | +0.30 | `take_profit` |
| 3 | 2024-07-02T15:00 | 2024-07-02T17:10 | +118.59 | +0.29 | `take_profit` |
| 4 | 2024-07-02T18:00 | 2024-07-03T08:43 | +118.08 | +0.29 | `take_profit` |
| 5 | 2024-07-03T16:00 | 2024-07-05T06:14 | +119.07 | +0.29 | `take_profit` |
| 6 | 2024-07-05T15:00 | 2024-07-05T15:41 | +119.56 | +0.29 | `take_profit` |
| 7 | 2024-07-05T16:00 | 2024-07-08T15:22 | +119.05 | +0.29 | `take_profit` |
| 8 | 2024-07-10T17:00 | 2024-07-10T19:51 | +118.53 | +0.28 | `take_profit` |

**Straty za sebou: 7** — 2022-01-27T16:00 až 2022-02-08T18:17, spolu -705.14, rovnako dlhých sérií 4.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-01-27T16:00 | 2022-01-27T16:26 | -100.50 | -0.35 | `stop_loss` |
| 2 | 2022-01-27T17:00 | 2022-01-27T17:07 | -100.00 | -0.35 | `stop_loss` |
| 3 | 2022-01-28T17:00 | 2022-01-28T17:22 | -102.00 | -0.36 | `stop_loss` |
| 4 | 2022-01-31T16:00 | 2022-01-31T16:11 | -100.53 | -0.34 | `stop_loss` |
| 5 | 2022-01-31T17:00 | 2022-01-31T17:24 | -100.54 | -0.34 | `stop_loss` |
| 6 | 2022-01-31T18:00 | 2022-01-31T20:17 | -100.04 | -0.34 | `stop_loss` |
| 7 | 2022-02-08T18:00 | 2022-02-08T18:17 | -101.53 | -0.34 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0288 %**, medián 0.0287 %, 90 % interval 0.0201–0.0375 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 8.0 %, 95. percentil 13.8 %, najhorší 29.1 %
- najdlhšia séria strát: medián 8, 95. percentil 10 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **348** na obchod pri účte 10 000

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
<!-- POSUDOK cisla=d7550e32 -->

**Posudok (7. 11. 2026, C# jadro Volt Break, profil PRESIEL_SMERNICAMI_Volt_Break_1, MNQ 1h, riziko z riskDollar.)**

1. **Na čo sa hodí a na čo nie.** Long prierazy Nasdaqu (MNQ / NQ) v okne 10:00–14:30 CT nad hranicou šumu aj nad VWAP. Len long — v dlhom medvedom trhu bude obchodovať menej, nie strácať viac.
2. **Má potenciál?** Áno: zisková v 5 z 5 okien, 802 obchodov, +4,7 sigma proti náhode, break-even 0,029 %, prepad drží (95. percentil 14 %), odložený rok +38 %. Edge v poslednom období na 28. percentile — o niečo slabší, ale v norme. Trieda A, Sortino 3,87.
3. **Čo dorobiť.** Pravidlo vypnutia naživo; veľkosť: profil berie `riskDollar` (150 $) na stop 1 000 $ / NQ bod 20 $ = 50 bodov — na MNQ to je 1 kontrakt (100 $ riziko), riziko nastaviť podľa účtu.
4. **Čo otestovať ďalej.** Forward test na deme 4–8 týždňov (`voltbreaknet`), porovnanie vstupov s testom na karte Live.
5. **Použiteľné?** Áno — C# jadro sedí s Pythonom bar po bare na všetkých 10 profiloch (`test_csharp_parity_voltbreak.py`), pripravené na demo.
6. **Čo by som pridal.** Short zrkadlovo (pod dolnou hranicou šumu a pod VWAP) ako samostatný variant — dnes stratégia v klesajúcom dni nič nerobí.

<!-- POSUDOK KONIEC -->
