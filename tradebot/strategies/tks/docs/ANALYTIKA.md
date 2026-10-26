# Základná analytika — TKS 1.0 (NQ Kompas) (`tks`)

Zmerané 2026-10-26 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tester/profiles/PRESIEL_SMERNICAMI_TKS_1_0_NQ_Kompas_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tks \
   --profile tester/profiles/PRESIEL_SMERNICAMI_TKS_1_0_NQ_Kompas_1.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 844 obchodov spolu — na štatistiku dosť
- break-even 0.0511 % je nad poplatkom 0.0018 % (rezerva +0.0493 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 5.3 %
- odlíšiteľná od náhody (+5.5 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 66. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'long' vlastnosti 'Smer': 525 obchodov (62.2 %), bez nej by break-even bol o +0.0325 lepší (riadi `tradeDirection`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 158 | +5.06 | 0.0366 | 4.2 | 71.5 | +9/-7 | `20261026-125919-53a20d` |
| 20221001-20231001 | 167 | +8.39 | 0.0592 | 1.5 | 74.2 | +15/-3 | `20261026-125925-f6e1dc` |
| 20231001-20241001 | 186 | +6.68 | 0.0317 | 1.5 | 69.3 | +9/-4 | `20261026-125931-eaf07e` |
| 20240904-20250904 | 176 | +12.54 | 0.0523 | 2.3 | 76.1 | +15/-3 | `20261026-125938-4cfaf8` |
| 20250904-20260904 | 171 | +18.69 | 0.0634 | 2.2 | 76.0 | +10/-3 | `20261026-125944-d4e94c` |

Zisková v **5 z 5** okien, obchodov spolu 844, break-even celkom 0.0511 %. Okná sa prekrývajú, 14 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.37 ATR za 5 barov)
- medián držania 16.7 barov grafu
- winrate 73.7 %, payoff 0.557
- 0.47 obchodov za deň
- šikmosť výnosov -1.035

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 73.7 %, `stop_loss` 26.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'long' vlastnosti 'Smer': 525 obchodov (62.2 %), break-even 0.0321 % oproti 0.0511 % celku. Bez nej by break-even bol 0.0836 % (+0.0325). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: skus preladit `tradeDirection`.


**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 525 | 62.2 % | 71.4 | 0.0321 | 0.0836 | +0.0325 |
| short | 319 | 37.8 % | 77.4 | 0.0836 | 0.0321 | -0.0190 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.4172 % – 0.6455 % | 211 | 25.0 % | 67.8 | 0.0053 | 0.0668 | +0.0157 |
| do 0.4172 % | 212 | 25.1 % | 75.0 | 0.0230 | 0.0615 | +0.0104 |
| 0.6455 % – 0.9792 % | 211 | 25.0 % | 74.9 | 0.0593 | 0.0484 | -0.0027 |
| nad 0.9792 % | 210 | 24.9 % | 77.1 | 0.1276 | 0.0288 | -0.0223 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 24 | 2.8 % | 79.2 | 0.0103 | 0.0523 | +0.0012 |
| žiadna | 741 | 87.8 % | 73.8 | 0.0494 | 0.0638 | +0.0127 |
| CPI | 31 | 3.7 % | 71.0 | 0.0703 | 0.0504 | -0.0007 |
| NFP | 48 | 5.7 % | 70.8 | 0.0851 | 0.0490 | -0.0021 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0511 % | -0.0004 % ± 0.0093 | +5.52 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0511 % | -0.0000 % ± 0.0093 | +5.48 | 100.0 |

Edge je odlisitelny od nahody (5.5 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 197 | 13.4 | 72.1 | 0.0446 | 40 |
| 2022-12 - 2024-03 | 207 | 14.0 | 72.0 | 0.0420 | 33 |
| 2024-03 - 2025-06 | 227 | 15.4 | 74.0 | 0.0514 | 52 |
| 2025-06 - 2026-09 | 213 | 14.4 | 76.5 | 0.0590 | 66 |

Hranice pre úsek veľkosti posledného obdobia: +0.0220 až +0.0805 % (medián 0.0513).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 66. percentile, teda v medziach +0.0220 až +0.0805 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 15** — 2023-06-01T14:09 až 2023-06-30T14:20, spolu +1904.33, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-06-01T14:09 | 2023-06-01T14:45 | +78.49 | +0.27 | `take_profit` |
| 2 | 2023-06-02T15:00 | 2023-06-05T13:43 | +115.97 | +0.40 | `take_profit` |
| 3 | 2023-06-05T14:09 | 2023-06-05T14:55 | +69.47 | +0.24 | `take_profit` |
| 4 | 2023-06-06T14:51 | 2023-06-07T13:32 | +93.97 | +0.32 | `take_profit` |
| 5 | 2023-06-07T14:57 | 2023-06-07T17:38 | +219.49 | +0.76 | `take_profit` |
| 6 | 2023-06-09T17:45 | 2023-06-12T00:00 | +346.47 | +1.19 | `take_profit` |
| 7 | 2023-06-12T15:39 | 2023-06-12T17:43 | +55.46 | +0.19 | `take_profit` |
| 8 | 2023-06-14T14:15 | 2023-06-14T15:17 | +88.94 | +0.29 | `take_profit` |
| 9 | 2023-06-15T13:48 | 2023-06-15T14:08 | +115.93 | +0.38 | `take_profit` |
| 10 | 2023-06-20T14:39 | 2023-06-21T14:49 | +169.44 | +0.56 | `take_profit` |
| 11 | 2023-06-21T15:48 | 2023-06-22T05:09 | +153.45 | +0.51 | `take_profit` |
| 12 | 2023-06-27T15:42 | 2023-06-27T16:43 | +104.95 | +0.35 | `take_profit` |
| 13 | 2023-06-28T14:00 | 2023-06-28T14:20 | +64.94 | +0.22 | `take_profit` |
| 14 | 2023-06-28T14:21 | 2023-06-28T14:34 | +96.44 | +0.32 | `take_profit` |
| 15 | 2023-06-30T13:45 | 2023-06-30T14:20 | +130.92 | +0.43 | `take_profit` |

**Straty za sebou: 7** — 2022-05-24T17:06 až 2022-06-09T17:44, spolu -1919.66.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-05-24T17:06 | 2022-05-24T19:37 | -306.32 | -1.31 | `stop_loss` |
| 2 | 2022-05-30T15:30 | 2022-05-31T00:33 | -141.90 | -0.55 | `stop_loss` |
| 3 | 2022-06-01T13:45 | 2022-06-01T14:13 | -191.39 | -0.75 | `stop_loss` |
| 4 | 2022-06-01T15:45 | 2022-06-02T15:10 | -318.88 | -1.27 | `stop_loss` |
| 5 | 2022-06-03T15:15 | 2022-06-06T08:11 | -431.39 | -1.72 | `stop_loss` |
| 6 | 2022-06-08T13:51 | 2022-06-08T16:39 | -233.39 | -0.92 | `stop_loss` |
| 7 | 2022-06-09T14:39 | 2022-06-09T17:44 | -296.38 | -1.17 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0511 %**, medián 0.0513 %, 90 % interval 0.0361–0.0660 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 3.1 %, 95. percentil 5.3 %, najhorší 10.7 %
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
<!-- POSUDOK cisla=4726b33a -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „TKS 1“ (PREŠIEL SMERNICAMI TKS 1.0 NQ Kompas č. 1): long nad 70 / short
pod 15 po 2 zavretiach, RR 0,5, trend EMA 200 na 15m, vstupy 15–270 min po otvorení s pauzou 150–210 min,
**bez** zatvárania na konci seansy._

1. **Na čo sa to hodí a na čo nie.** MNQ / NQ 3m, newyorská seansa. Je to stratégia s vysokou úspešnosťou
   (winrate 73,7 %) a malým ziskom k strate (payoff 0,56, RR 0,5): séria strát má medián 6, 95. percentil 8,
   najhoršia bola 7 strát −1 920 $ (máj–jún 2022); 95. percentil drawdownu 5,3 % (~3 200 $ zo 60 000 $), najhorší
   10,7 %. Pozor: `closeAtSessionEnd = false` — výstupy sú len TP a SL (0 % `session_end`), takže pozícia môže
   ostať cez noc. Na prop účty s povinným flat je to nepoužiteľné — tam patrí `tksneteod`. Charakter „prerazenie“
   má len priemernú istotu (bližšie je to pokračovanie trendu s krátkym TP).
2. **Má to potenciál?** Áno. Za javom: zisk v 5 z 5 okien (+5,1 až +18,7 %), +5,5 sigma proti náhode, break-even
   0,0511 % je 28× nad poplatkom (interval 0,0361–0,0660 %), posledné obdobie na 66. percentile a posledné dva roky
   sú najlepšie. Za vzorkou: nastavenie je z prehľadávania podľa smernice a payoff pod 1 je citlivý na sklz — tick
   sklzu na TP pri RR 0,5 zoberie väčší podiel zisku než pri RR 2. Rok 2021/22 je slabý (0,0366 %, DD 4,2 %).
3. **Čo treba dorobiť.** (a) Rozhodnúť držanie cez noc: dnes ho výsledok obsahuje, živé prop nasadenie nie
   (porovnanie s `tksneteod`: zatvorenie o 15:59 zníži break-even na 0,0328 %). (b) Smer: longy sú 62 % obchodov
   s break-even 0,0321 %, bez nich by celok mal 0,0836 % — edge nesú shorty, prah pre long je slabý.
   (c) Sviatky a skrátené seansy.
4. **Čo otestovať ďalej.** `cli sweep --strategy tks --profile tester/profiles/PRESIEL_SMERNICAMI_TKS_1_0_NQ_Kompas_1.json
   --space "hiLevel=60:85:5"` — rozhodne, či slabý long opraví prísnejší prah, alebo je to vlastnosť trhu.
   `cli run … --fee 3.51e-05` (2× poplatok) — pri payoffe 0,56 je to dôležitejšie než pri NOA.
   `cli matrix --pairs all --timeframes 3m` — drží to na ES?
5. **Je to použiteľné?** Áno — najsilnejšie čísla z rodiny TKS / NOA. Ako je (s držaním cez noc) len na účet, ktorý
   overnight dovoľuje; na prop účty `tksneteod`. Ostro až po forward teste.
6. **Čo by som pridal.** Asymetrické prahy pre long a short (dnes 70 / 15) a časový stop: medián držania je 16,7 barov
   (~50 min), obchod, ktorý do 2–3 hodín nedosiahol TP, by sa mal zavrieť skôr, než prenesie riziko do noci.

<!-- POSUDOK KONIEC -->
