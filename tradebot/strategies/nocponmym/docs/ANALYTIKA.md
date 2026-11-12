# Základná analytika — NOC + PONDELOK 1.0 (MYM) (`nocponmym`)

Zmerané 2026-11-12 na `MYM/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mym_databento_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy nocponmym \
   --profile mym_databento_5m \
   --pair MYM/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 813 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 11.5 %
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0064 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 10 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-2.2 sigma) — výber vstupu nepridáva nič
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 99.6 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 84 | -1.47 | -0.0281 | 1.9 | 41.7 | +4/-6 | `20261112-112029-55bb15` |
| 20221001-20231001 | 174 | +0.23 | 0.0041 | 1.3 | 52.3 | +8/-7 | `20261112-112036-cfc2cf` |
| 20231001-20241001 | 185 | +0.33 | 0.0045 | 1.6 | 52.4 | +6/-5 | `20261112-112042-b9b324` |
| 20240904-20250904 | 170 | -0.42 | -0.0017 | 2.0 | 47.1 | +6/-9 | `20261112-112045-4dd7f3` |
| 20250904-20260904 | 214 | -2.75 | -0.0138 | 4.7 | 54.2 | +6/-10 | `20261112-112051-d8c667` |

Zisková v **2 z 5** okien, obchodov spolu 813, break-even celkom -0.0064 %. Okná sa prekrývajú, 14 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.06 ATR za 5 barov)
- medián držania 132 barov grafu
- winrate 50.55 %, payoff 0.853
- 0.45 obchodov za deň
- šikmosť výnosov -0.278

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `session_end` 99.6 %, `force_exit` 0.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0089 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| NFP | 33 | 4.1 % | 48.5 | -0.0435 | -0.0049 | +0.0015 |
| žiadna | 729 | 89.7 % | 50.1 | -0.0075 | 0.0025 | +0.0089 |
| CPI | 30 | 3.7 % | 56.7 | 0.0241 | -0.0076 | -0.0012 |
| FOMC | 21 | 2.6 % | 61.9 | 0.0425 | -0.0078 | -0.0014 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 729 | 89.7 % | 50.1 | -0.0075 | 0.0025 | +0.0089 |
| po vyhlásení | 84 | 10.3 % | 54.8 | 0.0025 | -0.0075 | -0.0011 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.5912 – 0.8214 | 203 | 25.0 % | 47.3 | -0.0207 | -0.0017 | +0.0047 |
| do 0.2761 | 204 | 25.1 % | 52.5 | -0.0188 | -0.0023 | +0.0041 |
| nad 0.8214 | 203 | 25.0 % | 48.3 | -0.0065 | -0.0064 | +0.0000 |
| 0.2761 – 0.5912 | 203 | 25.0 % | 54.2 | 0.0201 | -0.0153 | -0.0089 |

Parametre, ktorými sa dá s tým niečo spraviť: `nightExitH`, `useMonday`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0064 % | 0.0492 % ± 0.0254 | -2.19 | 1.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0064 % | 0.0493 % ± 0.0259 | -2.15 | 1.7 |

HORSIE nez nahoda (-2.2 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 123 | 8.4 | 47.1 | -0.0085 | 39 |
| 2022-12 - 2024-03 | 212 | 14.4 | 52.8 | 0.0034 | 78 |
| 2024-03 - 2025-06 | 208 | 14.1 | 47.1 | -0.0137 | 26 |
| 2025-06 - 2026-09 | 270 | 18.4 | 53.0 | -0.0066 | 47 |

Hranice pre úsek veľkosti posledného obdobia: -0.0263 až +0.0117 % (medián -0.0059).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 47. percentile, teda v medziach -0.0263 až +0.0117 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2023-08-22T19:55 až 2023-09-04T06:55, spolu +224.63.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-08-22T19:55 | 2023-08-23T06:55 | +41.90 | +0.24 | `session_end` |
| 2 | 2023-08-23T19:55 | 2023-08-24T06:55 | +20.39 | +0.12 | `session_end` |
| 3 | 2023-08-25T19:55 | 2023-08-28T06:55 | +51.40 | +0.30 | `session_end` |
| 4 | 2023-08-28T13:30 | 2023-08-29T06:55 | +37.39 | +0.22 | `session_end` |
| 5 | 2023-08-29T19:55 | 2023-08-30T06:55 | +8.89 | +0.05 | `session_end` |
| 6 | 2023-08-30T19:55 | 2023-08-31T06:55 | +41.39 | +0.24 | `session_end` |
| 7 | 2023-08-31T19:55 | 2023-09-01T06:55 | +15.39 | +0.09 | `session_end` |
| 8 | 2023-09-01T19:55 | 2023-09-04T06:55 | +7.89 | +0.05 | `session_end` |

**Straty za sebou: 10** — 2026-02-20T20:55 až 2026-04-10T06:55, spolu -1155.09.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-02-20T20:55 | 2026-02-23T07:55 | -89.87 | -0.36 | `session_end` |
| 2 | 2026-02-23T14:30 | 2026-02-24T07:55 | -295.86 | -1.20 | `session_end` |
| 3 | 2026-02-24T20:55 | 2026-02-25T07:55 | -16.86 | -0.07 | `session_end` |
| 4 | 2026-02-25T20:55 | 2026-02-26T07:55 | -69.37 | -0.28 | `session_end` |
| 5 | 2026-02-26T20:55 | 2026-02-27T07:55 | -106.37 | -0.43 | `session_end` |
| 6 | 2026-02-27T20:55 | 2026-03-02T07:55 | -342.35 | -1.40 | `session_end` |
| 7 | 2026-03-02T14:30 | 2026-03-03T07:55 | -7.85 | -0.03 | `session_end` |
| 8 | 2026-03-03T20:55 | 2026-03-04T07:55 | -56.85 | -0.23 | `session_end` |
| 9 | 2026-03-04T20:55 | 2026-03-05T07:55 | -105.36 | -0.43 | `session_end` |
| 10 | 2026-04-09T19:55 | 2026-04-10T06:55 | -64.35 | -0.27 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0064 %**, medián -0.0065 %, 90 % interval -0.0170–0.0041 %
- P(edge > poplatok) = **9.9 %**
- max drawdown: medián 6.4 %, 95. percentil 11.5 %, najhorší 18.8 %
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
<!-- POSUDOK cisla=880031a9 -->

**1. Na čo sa to hodí.** Long cez noc (15:55 → 3:00 NY) a pondelok v seanse nad SMA 100 na MYM 5m, ~170–210 obchodov za rok.

**2. Potenciál.** Na MYM žiadny: proti náhode −2,2 sigma (výber dní škodí), zisk v 2 z 5 okien, posledný rok −2,75 %. Nočný drift, ktorý nesie stratégiu na MNQ, je na Dow slabší a noc má malý objem, takže aj sklz.

**3. Čo dorobiť.** V logike nič. Rozbor MacBooku odporúča na MYM „nič nočné“ a výsledok to potvrdzuje.

**4. Čo otestovať.** Smernica od 12. 11. 19:00 (časy, pondelok zvlášť, SMA). Prípadne len pondelková časť bez noci. Ak zostane pod náhodou, vyradiť.

**5. Použiteľné?** **Nie.**

**6. Čo by som pridal.** Na Dow ponechať len pondelkový jav (bez noci) a overiť ho samostatne: ak má výhodu, nesie ju práve tá časť.

<!-- POSUDOK KONIEC -->
