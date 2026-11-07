# Základná analytika — MTK RANGE 1.0 (C# jadro) (`va80net`)

Zmerané 2026-11-07 na `MNQ/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `profil_1_oba_smery`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy va80net \
   --profile profil_1_oba_smery \
   --pair MNQ/USD \
   --timeframe 1m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- break-even 0.0577 % je nad poplatkom 0.0018 % (rezerva +0.0559 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 18.6 %
- odlíšiteľná od náhody (+3.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-05 - 2026-08 na 30. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 29.7 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'long' vlastnosti 'Smer': 85 obchodov (46.7 %), bez nej by break-even bol o +0.0317 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 43 | +11.98 | 0.0509 | 7.2 | 55.8 | +4/-4 | `20261107-163851-274e28` |
| 20221001-20231001 | 48 | +25.38 | 0.1014 | 4.7 | 64.6 | +13/-6 | `20261107-163906-73fdb6` |
| 20231001-20241001 | 29 | +5.60 | 0.0279 | 6.0 | 58.6 | +6/-3 | `20261107-163921-427e47` |
| 20240904-20250904 | 31 | +21.91 | 0.0864 | 7.8 | 58.1 | +5/-2 | `20261107-163937-b62495` |
| 20250904-20260904 | 36 | +10.57 | 0.0288 | 12.1 | 63.9 | +12/-3 | `20261107-163952-1579de` |

Zisková v **5 z 5** okien, obchodov spolu 182, break-even celkom 0.0577 %. Okná sa prekrývajú, 5 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.34 ATR za 5 barov)
- medián držania 133.5 barov grafu
- winrate 60.44 %, payoff 1.05
- 0.1 obchodov za deň
- šikmosť výnosov +1.182

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 45.6 %, `session_end` 29.7 %, `stop_loss` 24.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'long' vlastnosti 'Smer': 85 obchodov (46.7 %), break-even 0.0187 % oproti 0.0577 % celku. Bez nej by break-even bol 0.0894 % (+0.0317). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 85 | 46.7 % | 56.5 | 0.0187 | 0.0894 | +0.0317 |
| short | 97 | 53.3 % | 63.9 | 0.0894 | 0.0187 | -0.0390 |

**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| štvrtok | 36 | 19.8 % | 44.4 | -0.0396 | 0.0809 | +0.0232 |
| pondelok | 38 | 20.9 % | 44.7 | -0.0097 | 0.0753 | +0.0176 |
| utorok | 34 | 18.7 % | 76.5 | 0.0827 | 0.0521 | -0.0056 |
| piatok | 33 | 18.1 % | 66.7 | 0.0878 | 0.0510 | -0.0067 |
| streda | 41 | 22.5 % | 70.7 | 0.1538 | 0.0281 | -0.0296 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.8191 – 0.8963 | 45 | 24.7 % | 55.6 | -0.0033 | 0.0776 | +0.0199 |
| nad 0.8963 | 45 | 24.7 % | 57.8 | 0.0259 | 0.0680 | +0.0103 |
| do 0.7113 | 46 | 25.3 % | 60.9 | 0.0538 | 0.0592 | +0.0015 |
| 0.7113 – 0.8191 | 46 | 25.3 % | 67.4 | 0.1606 | 0.0266 | -0.0311 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0577 % | 0.0001 % ± 0.0174 | +3.30 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0577 % | -0.0005 % ± 0.0199 | +2.92 | 99.9 |

Edge je odlisitelny od nahody (3.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 53 | 3.6 | 54.7 | 0.0588 | 52 |
| 2022-12 - 2024-03 | 44 | 3.0 | 65.9 | 0.0845 | 71 |
| 2024-03 - 2025-05 | 44 | 3.0 | 59.1 | 0.0686 | 64 |
| 2025-05 - 2026-08 | 41 | 2.8 | 63.4 | 0.0329 | 30 |

Hranice pre úsek veľkosti posledného obdobia: -0.0167 až +0.1340 % (medián 0.0569).

**DRZI** — posledné obdobie (2025-05 - 2026-08) je na 30. percentile, teda v medziach -0.0167 až +0.1340 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 13** — 2023-02-03T15:00 až 2023-04-12T14:35, spolu +1641.96.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-02-03T15:00 | 2023-02-03T15:47 | +264.10 | +1.04 | `take_profit` |
| 2 | 2023-02-07T16:00 | 2023-02-07T16:32 | +108.62 | +0.43 | `take_profit` |
| 3 | 2023-02-08T16:00 | 2023-02-08T20:54 | +130.12 | +0.52 | `session_end` |
| 4 | 2023-02-09T15:30 | 2023-02-09T17:37 | +189.12 | +0.75 | `take_profit` |
| 5 | 2023-02-16T15:00 | 2023-02-16T15:38 | +161.12 | +0.64 | `take_profit` |
| 6 | 2023-02-20T15:00 | 2023-02-21T08:15 | +150.63 | +0.61 | `take_profit` |
| 7 | 2023-02-28T15:00 | 2023-02-28T17:21 | +67.65 | +0.28 | `take_profit` |
| 8 | 2023-03-08T16:30 | 2023-03-08T20:54 | +46.64 | +0.19 | `session_end` |
| 9 | 2023-03-15T15:00 | 2023-03-15T18:21 | +165.64 | +0.68 | `take_profit` |
| 10 | 2023-03-23T14:00 | 2023-03-23T14:45 | +153.09 | +0.59 | `take_profit` |
| 11 | 2023-04-04T16:00 | 2023-04-04T19:54 | +48.57 | +0.18 | `session_end` |
| 12 | 2023-04-11T14:00 | 2023-04-11T19:54 | +64.58 | +0.25 | `session_end` |
| 13 | 2023-04-12T14:30 | 2023-04-12T14:35 | +92.08 | +0.35 | `take_profit` |

**Straty za sebou: 6** — 2023-04-20T14:30 až 2023-06-06T19:54, spolu -575.76.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-04-20T14:30 | 2023-04-20T19:16 | -175.92 | -0.67 | `stop_loss` |
| 2 | 2023-04-21T16:00 | 2023-04-21T19:54 | -3.42 | -0.01 | `session_end` |
| 3 | 2023-05-01T14:30 | 2023-05-01T15:00 | -81.93 | -0.31 | `stop_loss` |
| 4 | 2023-05-11T14:00 | 2023-05-11T15:28 | -96.44 | -0.36 | `stop_loss` |
| 5 | 2023-06-02T14:00 | 2023-06-02T19:54 | -206.52 | -0.71 | `session_end` |
| 6 | 2023-06-06T15:00 | 2023-06-06T19:54 | -11.52 | -0.04 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0577 %**, medián 0.0574 %, 90 % interval 0.0255–0.0923 %
- P(edge > poplatok) = **99.7 %**
- max drawdown: medián 10.2 %, 95. percentil 18.6 %, najhorší 47.4 %
- najdlhšia séria strát: medián 5, 95. percentil 7 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `567efff3`, tu je `fb450bd7`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=567efff3 -->

**Posudok (7. 11. 2026, MTK RANGE 1.0 — pravidlo 80 %, C# jadro, profil 1 oba smery, MNQ 1m, 1 kontrakt.)**

1. **Na čo sa hodí a na čo nie.** Rangeové dni Nasdaqu (MNQ / NQ): RTH otvorí mimo včerajšej value area a prvá 30m sviečka zavrie späť v nej → obchod na opačný okraj VA, výstup najneskôr 15:55. Na ES a zlate prieskum edge nenašiel. Beží na 1m grafe (value area z 1m sviečok — z 5m je hrubá).
2. **Má potenciál?** Áno: zisková v 5 z 5 okien (PF 1,33 · 2,33 · 1,30 · 2,09 · 1,32), +3,3 sigma proti náhodnému vstupu, break-even 0,058 % (32× poplatok), edge nad poplatkom v 100 % bootstrapových vzoriek, prepad drží. Mriežka 225 variantov výpočtu VA: odložený rok PF > 1 v 86 %. Všetky obchody majú plánované RR ≥ 0,5.
3. **Čo dorobiť.** Long strana je slabšia (odložený rok PF 0,34) — profil 2 (len short) a profil 3 (stop najviac 0,4 denného ATR) sú kvalitnejšie. Málo obchodov (~37 / rok, s filtrami 20–25).
4. **Čo otestovať ďalej.** Smernica (plató, typ vstupu, iný trh NAS100, krok 9 robustnosť) a forward test na deme.
5. **Použiteľné?** Áno ako malá rangeová stratégia do portfólia (nekorelovaná s trendovými Nasdaq stratégiami); C# jadro (`va80net`) sedí s Pythonom bar po bare.
6. **Čo by som pridal.** Zloženú value area z dvoch dní alebo nočnú VA ako druhý zdroj signálov — viac obchodov z toho istého javu.

<!-- POSUDOK KONIEC -->
