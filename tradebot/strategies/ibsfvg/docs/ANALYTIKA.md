# Základná analytika — IBS FVG + IFVG (`ibsfvg`)

Zmerané 2026-10-26 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/ibsfvg/configs/multicharts_mnq_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibsfvg \
   --profile tradebot/strategies/ibsfvg/configs/multicharts_mnq_3m.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 1538 obchodov spolu — na štatistiku dosť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20221001-20231001, 20231001-20241001, 20240904-20250904 v strate)
- break-even 0.0011 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 24 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 55.0 % (namerané 28.3 % medián) — na účet to treba mať
- proti náhode len +1.8 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 303 | +9.14 | 0.0048 | 6.0 | 54.5 | +10/-8 | `20261026-130818-627a8f` |
| 20221001-20231001 | 299 | -1.85 | 0.0013 | 10.7 | 50.8 | +9/-8 | `20261026-130832-8b0273` |
| 20231001-20241001 | 310 | -12.57 | -0.0008 | 17.3 | 48.4 | +8/-7 | `20261026-130846-4ec089` |
| 20240904-20250904 | 323 | -14.89 | -0.0013 | 21.0 | 48.6 | +10/-13 | `20261026-130858-5eb629` |
| 20250904-20260904 | 327 | +5.73 | 0.0030 | 11.3 | 53.8 | +8/-7 | `20261026-130910-f72ad9` |

Zisková v **2 z 5** okien, obchodov spolu 1538, break-even celkom 0.0011 %. Okná sa prekrývajú, 24 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.41 ATR za 5 barov)
- medián držania 4 barov grafu
- winrate 51.24 %, payoff 0.919
- 0.86 obchodov za deň
- šikmosť výnosov -2.066

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 49.9 %, `stop_loss` 47.5 %, `session_end` 2.5 %, `trailing_stop` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0017 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Vzdialenosť stopu** (riadi `minSlDistance`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.0627 % | 383 | 25.0 % | 49.4 | -0.0001 | 0.0028 | +0.0017 |
| 0.1222 % – 0.2274 % | 382 | 25.0 % | 50.0 | 0.0001 | 0.0012 | +0.0001 |
| 0.0627 % – 0.1222 % | 382 | 25.0 % | 52.1 | 0.0022 | 0.0007 | -0.0004 |
| nad 0.2274 % | 382 | 25.0 % | 54.7 | 0.0115 | 0.0005 | -0.0006 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 46 | 3.0 % | 41.3 | -0.0061 | 0.0013 | +0.0002 |
| žiadna | 1334 | 86.7 % | 51.0 | 0.0009 | 0.0024 | +0.0013 |
| CPI | 89 | 5.8 % | 50.6 | 0.0012 | 0.0011 | +0.0000 |
| NFP | 68 | 4.4 % | 63.2 | 0.0133 | 0.0007 | -0.0004 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 119 | 7.7 % | 50.4 | 0.0007 | 0.0011 | +0.0000 |
| bez udalosti | 1334 | 86.7 % | 51.0 | 0.0009 | 0.0024 | +0.0013 |
| po vyhlásení | 85 | 5.5 % | 55.3 | 0.0113 | 0.0009 | -0.0002 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `rrRatio`, `sess2TradeStartH`, `state2MaxBars`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0039 % | 0.0003 % ± 0.0020 | +1.80 | 95.9 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0039 % | 0.0001 % ± 0.0021 | +1.85 | 96.9 |

Naznak, ale nie dokaz (1.8 sigma, percentil 95.9). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 363 | 24.7 | 55.1 | 0.0056 | 99 |
| 2022-12 - 2024-03 | 382 | 26.0 | 47.9 | -0.0010 | 14 |
| 2024-03 - 2025-06 | 400 | 27.2 | 50.2 | 0.0001 | 30 |
| 2025-06 - 2026-09 | 393 | 26.7 | 51.9 | 0.0013 | 54 |

Hranice pre úsek veľkosti posledného obdobia: -0.0021 až +0.0042 % (medián 0.0011).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 54. percentile, teda v medziach -0.0021 až +0.0042 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 10** — 2021-10-12T07:24 až 2021-11-02T19:45, spolu +2962.64, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-12T07:24 | 2021-10-12T07:25 | +322.08 | +0.07 | `take_profit` |
| 2 | 2021-10-14T14:51 | 2021-10-14T16:03 | +329.68 | +0.18 | `take_profit` |
| 3 | 2021-10-15T08:09 | 2021-10-15T14:59 | +297.76 | +0.25 | `take_profit` |
| 4 | 2021-10-20T08:55 | 2021-10-20T09:30 | +320.87 | +0.07 | `take_profit` |
| 5 | 2021-10-21T16:04 | 2021-10-21T19:01 | +296.50 | +0.16 | `take_profit` |
| 6 | 2021-10-22T08:45 | 2021-10-22T08:51 | +321.02 | +0.03 | `take_profit` |
| 7 | 2021-10-26T07:09 | 2021-10-26T07:40 | +294.94 | +0.04 | `take_profit` |
| 8 | 2021-10-28T07:51 | 2021-10-28T08:39 | +309.02 | +0.10 | `take_profit` |
| 9 | 2021-11-02T10:03 | 2021-11-02T12:51 | +322.63 | +0.08 | `take_profit` |
| 10 | 2021-11-02T14:35 | 2021-11-02T19:45 | +148.14 | +0.15 | `session_end` |

**Straty za sebou: 13** — 2025-06-27T14:40 až 2025-07-10T15:10, spolu -4533.06.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-06-27T14:40 | 2025-06-27T14:52 | -338.00 | -0.15 | `stop_loss` |
| 2 | 2025-06-27T15:24 | 2025-06-27T17:44 | -334.39 | -0.18 | `stop_loss` |
| 3 | 2025-06-30T07:09 | 2025-06-30T07:17 | -342.09 | -0.04 | `stop_loss` |
| 4 | 2025-07-01T07:21 | 2025-07-01T07:24 | -390.67 | -0.04 | `stop_loss` |
| 5 | 2025-07-01T07:33 | 2025-07-01T07:49 | -324.83 | -0.09 | `stop_loss` |
| 6 | 2025-07-02T09:00 | 2025-07-02T09:04 | -352.69 | -0.04 | `stop_loss` |
| 7 | 2025-07-03T08:03 | 2025-07-03T08:22 | -367.31 | -0.05 | `stop_loss` |
| 8 | 2025-07-04T07:39 | 2025-07-04T07:46 | -408.37 | -0.03 | `stop_loss` |
| 9 | 2025-07-09T08:06 | 2025-07-09T08:22 | -338.46 | -0.08 | `stop_loss` |
| 10 | 2025-07-09T14:39 | 2025-07-09T14:48 | -300.56 | -0.13 | `stop_loss` |
| 11 | 2025-07-09T15:00 | 2025-07-09T15:16 | -336.88 | -0.09 | `stop_loss` |
| 12 | 2025-07-10T08:54 | 2025-07-10T09:21 | -365.52 | -0.06 | `stop_loss` |
| 13 | 2025-07-10T14:48 | 2025-07-10T15:10 | -333.28 | -0.10 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0011 %**, medián 0.0010 %, 90 % interval -0.0006–0.0027 %
- P(edge > poplatok) = **23.8 %**
- max drawdown: medián 28.3 %, 95. percentil 55.0 %, najhorší 98.6 %
- najdlhšia séria strát: medián 10, 95. percentil 14 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

<!-- POSUDOK cisla=f72dcc2b -->

_Posudok (Claude, 26. 10. 2026) — nastavenie `multicharts_mnq_3m`: referenčný profil repozitára (defaulty IBS na MNQ,
zóny len z FVG/IFVG 5m–1h), nie ladený. Čísla hovoria o myšlienke „IBS vstup nad imbalance zónami“, nie o najlepšom
nastavení._

1. **Na čo sa to hodí a na čo nie.** V tejto podobe na nič. MNQ 3m, 1 538 obchodov (0,86 denne), winrate 51 %, payoff
   0,92: break-even 0,0011 % je pod poplatkom 0,0018 %, ziskové sú 2 z 5 rokov a 95. percentil drawdownu je 55,0 %
   pri riziku profilu. Ladené profily testera (`tester/profiles/LEN_FVG_*`, `LEN_IFVG_*`) sú ladené na poslednom roku
   (názov hovorí „posledný rok 132 obch, WR 81 %, PF 2,16“) — to číslo o ostatných rokoch nič nehovorí.
2. **Má to potenciál? Slabý.** Repo profil: +1,8 σ proti náhode — náznak, nie dôkaz. Kontrola ladeného profilu
   `LEN_FVG_WR81_ibsfvg` na tých istých piatich oknách (26. 10., `--no-write`, behy v histórii s poznámkou „posudok
   ibsfvg“): 4 z 5 rokov v zisku, break-even 0,0059 %, +3,0 σ, ale rok 23/24 −24,5 % (break-even −0,0145 %, DD 28,7 %)
   a takmer celý zisk je z ladeného roku 25/26 (+41,5 %, WR 81 %). Bez neho je break-even zvyšných rokov okolo 0,002 %,
   teda na úrovni poplatku. Je to typický obraz ladenia na jednom roku: ladený rok žiari, ostatné sú pri nule.
3. **Čo treba dorobiť.** (a) Ladenie s oknami kritéria cez všetky roky, nie na poslednom — bez toho sú profily
   testera nepoužiteľné na rozhodnutie. (b) Skupiny ukazujú najmenší stop (do 0,063 %) ako jedinú zlú — `minSlDistance`
   by ho odrezal; zvyšok skupín (makro, deň) výsledok nemení.
4. **Čo otestovať ďalej.** `cli hyperopt --strategy ibsfvg --pair MNQ/USD --engine multicharts --timeframe 3m --windows ref
   --aggregate min --select plateau` s priestorom `rrRatio`, `minSlDistance`, `useStructureFilter`, prahy FVG — ak ani
   najhoršie okno nevyjde nad poplatok, myšlienka „len FVG zóny“ nedrží a `ibsentry` (všetky zdroje zón) je lepšia
   voľba. Ako porovnanie stačí `cli checkup` toho istého profilu s `ibsentry`.
5. **Je to použiteľné? Nie** — referenčný profil je pod poplatkom a ladený profil drží len na roku, na ktorom bol
   ladený. Stratégia je užitočná ako test hypotézy (a tá vychádza skôr záporne), nie ako kandidát na účet.
6. **Čo by som pridal.** Rozlíšenie FVG podľa toho, či je zóna z času seansy NY, alebo z noci — FVG vzniknuté na
   otvorení s objemom sú silnejšia úroveň než nočné; jeden prepínač by ukázal, či edge nesie len časť zón.

<!-- POSUDOK KONIEC -->
