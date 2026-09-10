# Základná analytika — Demo Donchian Breakout (`demo_breakout`)

Zmerané 2026-09-10 na `BTC/USDT:USDT` 5m, engine `freqtrade`, poplatok 0.0500 % na stranu, profil `binance_btcusdt_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy demo_breakout \
   --profile binance_btcusdt_5m \
   --timeframe 5m
```

## V čom je dobrá

- 6962 obchodov spolu — na štatistiku dosť

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0068 % je pod poplatkom 0.0500 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 100.0 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-2.0 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'short' vlastnosti 'Smer': 3491 obchodov (50.1 %), bez nej by break-even bol o +0.0129 lepší (riadi `allowShort`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 1336 | -99.96 | -0.0249 | 100.0 | 30.9 | `20260910-075625-6397f2` |
| 20221001-20231001 | 1331 | -99.96 | -0.0195 | 100.0 | 26.5 | `20260910-075729-f1151c` |
| 20231001-20241001 | 1608 | -99.92 | 0.0035 | 99.9 | 34.3 | `20260910-075831-4feb4b` |
| 20240904-20250904 | 1278 | -99.84 | -0.0010 | 99.8 | 31.7 | `20260910-075945-bae02b` |
| 20250904-20260904 | 1409 | -99.88 | -0.0022 | 99.9 | 31.4 | `20260910-080047-f9baa6` |

Zisková v **0 z 5** okien, obchodov spolu 6962, break-even celkom -0.0068 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.77 ATR za 5 barov)
- medián držania 5 barov grafu
- winrate 31.08 %, payoff 1.134
- 4.07 obchodov za deň
- šikmosť výnosov +0.977

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 51.5 %, `roi` 31.3 %, `trailing_stop_loss` 12.7 %, `signal_close` 4.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'short' vlastnosti 'Smer': 3491 obchodov (50.1 %), break-even -0.0217 % oproti -0.0068 % celku. Bez nej by break-even bol 0.0061 % (+0.0129). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: skus preladit `allowShort`.


**Smer** (riadi `allowShort`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 3491 | 50.1 % | 30.1 | -0.0217 | 0.0061 | +0.0129 |
| long | 3471 | 49.9 % | 32.1 | 0.0061 | -0.0217 | -0.0149 |

**Vzdialenosť stopu** (riadi `slAtrMult`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.255 % – 0.3786 % | 1737 | 24.9 % | 31.3 | -0.0319 | 0.0005 | +0.0073 |
| 0.1625 % – 0.255 % | 1743 | 25.0 % | 32.6 | -0.0007 | -0.0093 | -0.0025 |
| do 0.1625 % | 1743 | 25.0 % | 29.4 | 0.0004 | -0.0103 | -0.0035 |
| nad 0.3786 % | 1739 | 25.0 % | 31.1 | 0.0030 | -0.0086 | -0.0018 |

**Mesiac**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 2026-02 | 17 | 0.2 % | 17.6 | -0.1452 | -0.0068 | +0.0000 |
| 2022-01 | 46 | 0.7 % | 26.1 | -0.0465 | -0.0068 | +0.0000 |
| 2021-10 | 388 | 5.6 % | 28.6 | -0.0254 | -0.0037 | +0.0031 |
| 2022-10 | 410 | 5.9 % | 25.9 | -0.0210 | -0.0043 | +0.0025 |
| … | | | | | | |
| 2024-11 | 406 | 5.8 % | 32.5 | 0.0099 | -0.0068 | +0.0000 |
| 2022-06 | 141 | 2.0 % | 34.0 | 0.0213 | -0.0068 | +0.0000 |
| 2025-12 | 45 | 0.6 % | 40.0 | 0.0323 | -0.0068 | +0.0000 |
| 2026-01 | 15 | 0.2 % | 40.0 | 0.0474 | -0.0068 | +0.0000 |

Parametre, ktorými sa dá s tým niečo spraviť: `allowShort`, `exitMode`, `slAtrMult`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0045 % | 0.0004 % ± 0.0025 | -1.96 | 2.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0045 % | 0.0004 % ± 0.0025 | -1.96 | 2.3 |

HORSIE nez nahoda (-2.0 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 2162 | 154.1 | 29.8 | -0.0221 | 3 |
| 2022-12 - 2024-02 | 2113 | 150.6 | 31.9 | 0.0035 | 90 |
| 2024-02 - 2025-04 | 1277 | 91.0 | 31.7 | -0.0010 | 73 |
| 2025-04 - 2026-06 | 1410 | 100.5 | 31.4 | -0.0022 | 67 |

Hranice pre úsek veľkosti posledného obdobia: -0.0225 až +0.0093 % (medián -0.0064).

**DRZI** — posledné obdobie (2025-04 - 2026-06) je na 67. percentile, teda v medziach -0.0225 až +0.0093 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0068 %**, medián -0.0067 %, 90 % interval -0.0141–0.0004 %
- P(edge > poplatok) = **0.0 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 22, 95. percentil 30 obchodov
- pravdepodobnosť ruiny účtu: 100.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **3** na obchod pri účte 10 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

<!-- POSUDOK cisla=b401fb0b -->

**Zhrnutie:** ako obchodná stratégia je to **o ničom** a nie je to prekvapenie — je to
ukážka rámca, nie nápad na trh. Číslo, ktoré rozhoduje: break-even −0,0068 % pri poplatku
0,05 %, teda edge nie je nula, ale záporný, a to na 6 962 obchodoch. Za tým už nie je
neistota vzorky: proti náhodnému vstupu za tých istých pravidiel je **horšia** o 2,0
sigma. Výber vstupu tu výsledku škodí, čo je najhoršia možná odpoveď.

**1. Na čo sa to hodí a na čo nie.** Na obchodovanie na nič. Hodí sa presne na dve veci:
overiť, že celá cesta rámca funguje end-to-end (Pine → config → engine → oba adaptéry →
história → analytika), a ako **negatívna kontrola** — keď batéria niečo nájde na ostrej
stratégii, tu je vidieť, ako vyzerá to isté meranie na niečom, čo edge nemá. Tá druhá
úloha je cennejšia, než sa zdá: bez nej sa ťažko posudzuje, či je „+4,3 sigma" veľa.

**2. Má to potenciál?** Ako je napísaná, nie. Donchian prerazenie s trhovým vstupom robí
4,07 obchodu za deň a drží ich mediánovo 5 barov — pri payoff 1,13 a winrate 31 % je
očakávaná hodnota na obchod rádovo taká veľká ako poplatok, takže o výsledku rozhoduje
poplatok, nie stratégia (klasický scalpingový problém, [TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md)).
Ani jedno okno z piatich nie je ziskové a rozdiely medzi rokmi (−0,0249 až +0,0035
break-even) sú menšie než poplatok — to nie je „raz vyšla, raz nie", to je konzistentne
nulový až záporný edge. Test úpadku to potvrdzuje z druhej strany: verdikt `DRZI`
neznamená, že to drží, ale že sa nič nemení — posledné obdobie je presne tam, kde všetky
ostatné, teda pod poplatkom. Jediný náznak: longy majú break-even +0,0061 % a shorty
−0,0217 %; aj tak sú longy hlboko pod poplatkom.

**3. Čo treba dorobiť.** Nie „doladiť", ale zmeniť podstatu: (a) **žiadny filter režimu** —
Donchian prerazenie v rozsahovom trhu generuje falošné prerazenia a práve tie tvoria
väčšinu z tých 7 000 obchodov; (b) **trhový vstup** platí spread aj poplatok na oboch
stranách, pri edge veľkosti poplatku je to rozhodujúce; (c) **žiadne pravidlo, ktoré bráni
okamžitému znovuvstupu** po strate — kanál je po prerazení stále prerazený; (d) sizing
profilu (100 USD rizika na obchod, páka 5, účet 10 000) je pri tejto frekvencii zárukou
ruiny: Monte Carlo dáva pravdepodobnosť ruiny 100 %.

**4. Čo otestovať ďalej.** Len ak niekto chce vidieť, ako sa taká vec ladí — nie preto, že
by z toho niečo malo byť:

```bash
# a) je záporný edge vlastnosťou dĺžky kanála, alebo celej myšlienky?
PY -m tester.webapp.cli sweep --strategy demo_breakout --param channelLen=10,20,40,80 \
   --profile binance_btcusdt_5m --timeframe 5m --timerange 20240904-20250904 --goal break_even
# b) nesú stratu shorty? (rozdelenie hovorí, že áno — ale aj longy sú pod poplatkom)
PY -m tester.webapp.cli sweep --strategy demo_breakout --param allowShort=true,false \
   --profile binance_btcusdt_5m --timeframe 5m --timerange 20240904-20250904 --goal break_even
# c) rovnaká vec druhým enginom — kontrola, že rámec dáva rovnaké signály
PY -m tester.webapp.cli run --strategy demo_breakout --engine multicharts --pair NAS100/USD \
   --timeframe 5m --timerange 20240904-20250904 --note "demo cez emulator"
```

Čo by rozhodli: (a) a (b) či je záporný edge všade v priestore parametrov (očakávanie: áno,
lebo poplatok je konštanta a frekvencia klesá pomalšie než rastie priemerný zisk);
(c) nič o trhu, ale všetko o rámci — a to je jediné, na čo je táto stratégia.

**5. Je to použiteľné?** **Nie.** Ani s inými parametrami, ani na inom trhu — nie preto, že
by prerazenie kanála nemohlo fungovať, ale preto, že táto implementácia obchoduje príliš
často na to, aby prežila poplatok, a nemá jediný filter, ktorý by frekvenciu znížil na
setupy, kde má prerazenie zmysel. V repozitári má zostať presne v tejto podobe: je to
ukážka a negatívna kontrola, a preprodať ju na „skoro fungujúcu" by jej obe úlohy pokazilo.

**6. Čo by som pridal** — keby to mala byť stratégia, a nie ukážka: filter režimu (napr.
šírka kanála voči ATR — obchodovať len prerazenie **úzkeho** kanála), vstup limitkou na
úrovni kanála namiesto trhu (poplatok je tu rozhodujúci), zákaz znovuvstupu do konca
periódy kanála po strate, a trend vyšším TF ako povolenie smeru. To sú štyri zmeny a každá
znižuje počet obchodov — čo je pri tomto probléme celý zmysel. Ako ukážka rámca ale
netreba nič: `demo_breakout` má dnes všetko, čo [docs/STRATEGIE.md](../../../../docs/STRATEGIE.md)
vyžaduje, vrátane SL/TP kresieb a vedomostí o ladení, takže sa dá kopírovať.

<!-- POSUDOK KONIEC -->
