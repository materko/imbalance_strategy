# Základná analytika — Silver Bullet 1.0 (6E) (`silverbulleteur`)

Zmerané 2026-11-15 na `6E/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/silverbulleteur/configs/6e_databento_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy silverbulleteur \
   --profile tradebot/strategies/silverbulleteur/configs/6e_databento_5m.json \
   --pair 6E/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 273 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 21.3 %
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0073 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 2 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.6 sigma) — výber vstupu nepridáva nič
- najhoršia skupina 'žiadna' vlastnosti 'Makro udalosť v ten deň': 245 obchodov (89.7 %), bez nej by break-even bol o +0.0176 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 51 | -3.95 | -0.0153 | 5.4 | 21.6 | +3/-12 | `20261115-094704-4b3826` |
| 20221001-20231001 | 49 | -2.48 | -0.0096 | 3.7 | 32.6 | +3/-6 | `20261115-094707-200347` |
| 20231001-20241001 | 55 | +0.94 | 0.0055 | 1.3 | 40.0 | +3/-7 | `20261115-094713-0ba607` |
| 20240904-20250904 | 64 | -4.49 | -0.0136 | 5.4 | 28.1 | +2/-16 | `20261115-094719-eaf20f` |
| 20250904-20260904 | 60 | -1.27 | -0.0026 | 2.8 | 28.3 | +3/-14 | `20261115-094722-5d944b` |

Zisková v **1 z 5** okien, obchodov spolu 273, break-even celkom -0.0073 %. Okná sa prekrývajú, 6 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.45 ATR za 5 barov)
- medián držania 9.8 barov grafu
- winrate 29.67 %, payoff 1.775
- 0.15 obchodov za deň
- šikmosť výnosov +1.479

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 70.3 %, `take_profit` 29.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'žiadna' vlastnosti 'Makro udalosť v ten deň': 245 obchodov (89.7 %), break-even -0.0093 % oproti -0.0073 % celku. Bez nej by break-even bol 0.0103 % (+0.0176). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 245 | 89.7 % | 28.6 | -0.0093 | 0.0103 | +0.0176 |
| NFP | 13 | 4.8 % | 38.5 | -0.0026 | -0.0075 | -0.0002 |
| CPI | 10 | 3.7 % | 30.0 | 0.0002 | -0.0076 | -0.0003 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 245 | 89.7 % | 28.6 | -0.0093 | 0.0103 | +0.0176 |
| po vyhlásení | 23 | 8.4 % | 34.8 | -0.0014 | -0.0078 | -0.0005 |

**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 137 | 50.2 % | 26.3 | -0.0159 | 0.0014 | +0.0087 |
| short | 136 | 49.8 % | 33.1 | 0.0014 | -0.0159 | -0.0086 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0073 % | -0.0001 % ± 0.0045 | -1.62 | 5.4 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0073 % | -0.0003 % ± 0.0042 | -1.68 | 5.3 |

HORSIE nez nahoda (-1.6 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 60 | 4.1 | 25.0 | -0.0112 | 37 |
| 2022-12 - 2024-03 | 67 | 4.6 | 34.3 | -0.0050 | 58 |
| 2024-03 - 2025-06 | 73 | 5.0 | 28.8 | -0.0109 | 34 |
| 2025-06 - 2026-08 | 73 | 5.0 | 30.1 | -0.0029 | 70 |

Hranice pre úsek veľkosti posledného obdobia: -0.0205 až +0.0058 % (medián -0.0068).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 70. percentile, teda v medziach -0.0205 až +0.0058 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 3** — 2021-11-29T15:25 až 2021-12-02T07:45, spolu +772.60, rovnako dlhých sérií 6.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-11-29T15:25 | 2021-11-29T16:50 | +132.56 | +0.09 | `take_profit` |
| 2 | 2021-11-30T15:25 | 2021-11-30T15:35 | +201.26 | +0.14 | `take_profit` |
| 3 | 2021-12-01T15:29 | 2021-12-02T07:45 | +438.78 | +0.31 | `take_profit` |

**Straty za sebou: 16** — 2024-11-08T16:03 až 2025-01-20T17:11, spolu -2629.78.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-11-08T16:03 | 2024-11-08T16:06 | -67.22 | -0.05 | `stop_loss` |
| 2 | 2024-11-13T15:40 | 2024-11-14T01:33 | -329.64 | -0.25 | `stop_loss` |
| 3 | 2024-11-14T15:45 | 2024-11-14T15:56 | -148.39 | -0.11 | `stop_loss` |
| 4 | 2024-11-25T15:52 | 2024-11-25T16:23 | -192.11 | -0.15 | `stop_loss` |
| 5 | 2024-11-28T15:48 | 2024-11-28T23:16 | -73.38 | -0.06 | `stop_loss` |
| 6 | 2024-12-04T15:41 | 2024-12-05T13:15 | -217.13 | -0.16 | `stop_loss` |
| 7 | 2024-12-06T16:02 | 2024-12-06T19:11 | -192.13 | -0.15 | `stop_loss` |
| 8 | 2024-12-11T15:23 | 2024-12-11T15:34 | -179.61 | -0.14 | `stop_loss` |
| 9 | 2024-12-20T16:01 | 2024-12-20T16:17 | -104.58 | -0.08 | `stop_loss` |
| 10 | 2024-12-27T15:35 | 2024-12-27T17:22 | -92.09 | -0.07 | `stop_loss` |
| 11 | 2024-12-31T15:20 | 2024-12-31T15:34 | -154.57 | -0.12 | `stop_loss` |
| 12 | 2025-01-02T15:45 | 2025-01-02T15:59 | -135.78 | -0.11 | `stop_loss` |
| 13 | 2025-01-07T15:38 | 2025-01-07T15:45 | -173.31 | -0.13 | `stop_loss` |
| 14 | 2025-01-10T15:43 | 2025-01-10T16:18 | -254.51 | -0.20 | `stop_loss` |
| 15 | 2025-01-14T15:30 | 2025-01-14T15:35 | -123.27 | -0.10 | `stop_loss` |
| 16 | 2025-01-20T16:00 | 2025-01-20T17:11 | -192.07 | -0.15 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0073 %**, medián -0.0073 %, 90 % interval -0.0143–-0.0003 %
- P(edge > poplatok) = **1.7 %**
- max drawdown: medián 13.2 %, 95. percentil 21.3 %, najhorší 31.9 %
- najdlhšia séria strát: medián 15, 95. percentil 23 obchodov
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
<!-- POSUDOK cisla=565eb13f -->

**1. Na čo sa to hodí.** ICT Silver Bullet na 6E 5m — sweep a FVG v okne 10–11 NY, najživšej hodine 6E. Čísla sú z **neladeného východiska** (predloha z MNQ, tickové prahy ×0,12); ladenie pôjde len na 2016–2021/9, tieto okná sú preň čisté overenie a nesmú ho ovplyvniť.

**2. Potenciál.** **Malý.** Zisk v 1 z 5 okien, −1,6 sigma proti náhode, break-even záporný — výber vstupu z MNQ na EUR nič nepridáva.

**3. Čo dorobiť.** Na 75 obchodov za rok je ~55 málo; treba aj londýnske okno (smernica skúša `sbStartH` 3).

**4. Čo otestovať.** Smernica EUR (22.–29. 11. 2026), okná 3–5 a 8–11 NY, cieľ na likvidite vs. RR.

**5. Použiteľné?** **Takto o ničom.**

**6. Čo by som pridal.** Okno 8:30–9:30 NY (správy USA) — vtedy má EUR najväčší rozsah.

<!-- POSUDOK KONIEC -->
