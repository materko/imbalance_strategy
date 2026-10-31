# Základná analytika — LONDON LIQUIDITY IFVG 1.0 (`lliq`)

Zmerané 2026-10-31 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_lliq.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy lliq \
   --profile /Users/martin/IBS/.nightsearch/base_lliq.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 322 obchodov spolu — na štatistiku dosť
- break-even 0.0053 % je nad poplatkom 0.0018 % (rezerva +0.0035 bodu)
- drawdown drží: 95. percentil 15.3 %
- edge drží aj v poslednom období (2025-06 - 2026-08 na 56. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20221001-20231001, 20240904-20250904 v strate)
- edge nad poplatkom len v 81 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +1.7 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'proti trendu' vlastnosti 'S trendom, alebo proti': 249 obchodov (77.3 %), bez nej by break-even bol o +0.0153 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 66 | +7.88 | 0.0238 | 1.1 | 66.7 | +14/-3 | `20261031-085034-772eb6` |
| 20221001-20231001 | 59 | -2.82 | -0.0074 | 3.7 | 42.4 | +4/-4 | `20261031-085037-f96abc` |
| 20231001-20241001 | 43 | +0.02 | 0.0018 | 2.1 | 48.8 | +3/-5 | `20261031-085040-64cc1d` |
| 20240904-20250904 | 65 | -2.77 | -0.0032 | 6.4 | 50.8 | +5/-7 | `20261031-085046-883a40` |
| 20250904-20260904 | 92 | +6.65 | 0.0084 | 5.2 | 55.4 | +8/-5 | `20261031-085049-763381` |

Zisková v **3 z 5** okien, obchodov spolu 322, break-even celkom 0.0053 %. Okná sa prekrývajú, 3 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.28 ATR za 5 barov)
- medián držania 5 barov grafu
- winrate 53.42 %, payoff 0.991
- 0.18 obchodov za deň
- šikmosť výnosov -0.276

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 53.4 %, `stop_loss` 46.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'proti trendu' vlastnosti 'S trendom, alebo proti': 249 obchodov (77.3 %), break-even 0.0006 % oproti 0.0053 % celku. Bez nej by break-even bol 0.0206 % (+0.0153). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 249 | 77.3 % | 51.8 | 0.0006 | 0.0206 | +0.0153 |
| s trendom | 73 | 22.7 % | 58.9 | 0.0206 | 0.0006 | -0.0047 |

**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| streda | 56 | 17.4 % | 46.4 | -0.0126 | 0.0090 | +0.0037 |
| utorok | 66 | 20.5 % | 48.5 | -0.0024 | 0.0075 | +0.0022 |
| piatok | 53 | 16.5 % | 52.8 | 0.0039 | 0.0056 | +0.0003 |
| pondelok | 91 | 28.3 % | 58.2 | 0.0129 | 0.0025 | -0.0028 |
| štvrtok | 52 | 16.1 % | 59.6 | 0.0237 | 0.0018 | -0.0035 |

**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.97 R | 86 | 26.7 % | 46.5 | -0.0052 | 0.0087 | +0.0034 |
| 0.97 R – 1 R | 111 | 34.5 % | 51.4 | 0.0049 | 0.0056 | +0.0003 |
| nad 1.03 R | 75 | 23.3 % | 62.7 | 0.0081 | 0.0046 | -0.0007 |
| 1 R – 1.03 R | 50 | 15.5 % | 56.0 | 0.0171 | 0.0028 | -0.0025 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0053 % | -0.0001 % ± 0.0032 | +1.71 | 95.4 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0053 % | -0.0001 % ± 0.0028 | +1.93 | 97.4 |

Naznak, ale nie dokaz (1.7 sigma, percentil 95.4). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 82 | 5.6 | 59.8 | 0.0162 | 86 |
| 2022-12 - 2024-03 | 60 | 4.1 | 45.0 | -0.0054 | 12 |
| 2024-03 - 2025-06 | 68 | 4.6 | 52.9 | 0.0018 | 38 |
| 2025-06 - 2026-08 | 112 | 7.6 | 53.6 | 0.0061 | 56 |

Hranice pre úsek veľkosti posledného obdobia: -0.0056 až +0.0167 % (medián 0.0049).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 56. percentile, teda v medziach -0.0056 až +0.0167 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 14** — 2022-02-22T01:50 až 2022-05-27T03:26, spolu +668.13.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-02-22T01:50 | 2022-02-22T03:08 | +89.54 | +0.33 | `take_profit` |
| 2 | 2022-03-07T02:05 | 2022-03-07T03:27 | +68.55 | +0.25 | `take_profit` |
| 3 | 2022-03-14T01:35 | 2022-03-14T02:02 | +56.06 | +0.21 | `take_profit` |
| 4 | 2022-03-25T02:15 | 2022-03-25T03:48 | +30.46 | +0.10 | `take_profit` |
| 5 | 2022-04-19T00:50 | 2022-04-19T01:02 | +33.52 | +0.12 | `take_profit` |
| 6 | 2022-04-20T03:00 | 2022-04-20T03:51 | +34.51 | +0.12 | `take_profit` |
| 7 | 2022-04-21T02:25 | 2022-04-21T02:36 | +27.51 | +0.10 | `take_profit` |
| 8 | 2022-04-25T03:20 | 2022-04-25T03:54 | +44.07 | +0.17 | `take_profit` |
| 9 | 2022-05-10T01:55 | 2022-05-10T02:10 | +63.64 | +0.26 | `take_profit` |
| 10 | 2022-05-12T00:40 | 2022-05-12T00:42 | +65.16 | +0.27 | `take_profit` |
| 11 | 2022-05-16T01:20 | 2022-05-16T01:36 | +49.63 | +0.20 | `take_profit` |
| 12 | 2022-05-19T02:35 | 2022-05-19T02:42 | +40.67 | +0.17 | `take_profit` |
| 13 | 2022-05-25T00:15 | 2022-05-25T00:27 | +36.17 | +0.15 | `take_profit` |
| 14 | 2022-05-27T03:05 | 2022-05-27T03:26 | +28.64 | +0.12 | `take_profit` |

**Straty za sebou: 7** — 2025-03-28T02:10 až 2025-05-09T02:56, spolu -550.34.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-03-28T02:10 | 2025-03-28T04:16 | -33.90 | -0.08 | `stop_loss` |
| 2 | 2025-04-08T01:00 | 2025-04-08T01:36 | -138.75 | -0.39 | `stop_loss` |
| 3 | 2025-04-09T01:50 | 2025-04-09T01:56 | -185.20 | -0.54 | `stop_loss` |
| 4 | 2025-04-16T02:05 | 2025-04-16T02:15 | -53.81 | -0.14 | `stop_loss` |
| 5 | 2025-04-25T01:35 | 2025-04-25T01:38 | -53.36 | -0.14 | `stop_loss` |
| 6 | 2025-05-01T02:50 | 2025-05-01T03:24 | -41.90 | -0.11 | `stop_loss` |
| 7 | 2025-05-09T02:20 | 2025-05-09T02:56 | -43.42 | -0.11 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0053 %**, medián 0.0053 %, 90 % interval -0.0013–0.0121 %
- P(edge > poplatok) = **80.8 %**
- max drawdown: medián 7.4 %, 95. percentil 15.3 %, najhorší 33.5 %
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
<!-- POSUDOK cisla=f89d35bc -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MNQ, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Večerný sweep high / low popoludnia NY (19:15–23:45) a inverzný FVG — málo obchodov (~60 / rok na MNQ), likvidita v Ázii je tenká.
2. **Má potenciál?** Zisková v 3 z 5 okien, 322 obchodov (~64 za rok), break-even 0.0053 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 53.42 % pri payoffe 0.991. Odložený rok 25/26: +6.65 % PnL, break-even 0.0084 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Okno seansy aj sweepu sú pre NQ nevhodné (popoludnie NY → večer); skúsiť Ázia / Londýn ako zdroj likvidity a sweep v NY ráno.
4. **Čo otestovať ďalej.** Smernica (`lliq*`: okná seansy a sweepu, stop / cieľ, vek FVG); pri ~60 obchodoch za rok hranicu 150 z princípu nesplní, kým sa okno nezmení.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Likviditu brať z Ázie (20:00–2:00 NY) a sweep v Londýne / NY ráno — klasické ICT poradie, ktoré dá viac obchodov.

<!-- POSUDOK KONIEC -->
