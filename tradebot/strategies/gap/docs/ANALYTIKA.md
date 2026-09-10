# Základná analytika — Gap Fill — výplň otváracej medzery (`gap`)

Zmerané 2026-09-10 na `NAS100/USD` 15m, engine `multicharts`, poplatok 0.0000 % na stranu (zadané cez --fee), profil `tradebot/strategies/gap/configs/nas100_dukascopy_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy gap \
   --profile tradebot/strategies/gap/configs/nas100_dukascopy_5m.json \
   --pair NAS100/USD \
   --timeframe 15m \
   --fee 0.0
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 352 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 13.1 %
- odlíšiteľná od náhody (+2.1 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 64. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- náklad na tomto trhu nepoznáme, takže break-even sa proti ničomu neposudzuje — doplň ho do inštrumentu (`half_spread_ticks`)
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 66 | +9.47 | 0.0232 | 6.3 | 59.1 | `20260910-172732-8524c4` |
| 20221001-20231001 | 80 | +5.65 | 0.0088 | 6.0 | 56.2 | `20260910-172735-0d25b7` |
| 20231001-20241001 | 68 | +8.09 | 0.0120 | 4.8 | 54.4 | `20260910-172738-272fa4` |
| 20240904-20250904 | 77 | +8.98 | 0.0125 | 6.5 | 58.4 | `20260910-172741-029d44` |
| 20250904-20260904 | 61 | +12.33 | 0.0222 | 4.7 | 60.7 | `20260910-172744-542f4e` |

Zisková v **5 z 5** okien, obchodov spolu 352, break-even celkom 0.0149 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.30 ATR za 5 barov)
- medián držania 0.7 barov grafu
- winrate 57.67 %, payoff 1.007
- 0.2 obchodov za deň
- šikmosť výnosov -0.539

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 55.4 %, `stop_loss` 40.9 %, `session_end` 3.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0053 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 14 h | 232 | 65.9 % | 57.3 | 0.0120 | 0.0202 | +0.0053 |
| 15 h | 120 | 34.1 % | 58.3 | 0.0202 | 0.0120 | -0.0029 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 8 – 16 | 94 | 26.7 % | 56.4 | 0.0045 | 0.0184 | +0.0035 |
| do 8 | 93 | 26.4 % | 59.1 | 0.0168 | 0.0142 | -0.0007 |
| nad 23 | 86 | 24.4 % | 59.3 | 0.0172 | 0.0140 | -0.0009 |
| 16 – 23 | 79 | 22.4 % | 55.7 | 0.0220 | 0.0129 | -0.0020 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 167 | 47.4 % | 56.9 | 0.0110 | 0.0182 | +0.0033 |
| long | 185 | 52.6 % | 58.4 | 0.0182 | 0.0110 | -0.0039 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0097 % | 0.0000 % ± 0.0045 | +2.15 | 99.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0097 % | -0.0003 % ± 0.0063 | +1.60 | 94.0 |

Edge je odlisitelny od nahody (2.1 sigma, percentil 99.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 87 | 5.9 | 59.8 | 0.0264 | 82 |
| 2022-12 - 2024-03 | 91 | 6.2 | 55.0 | 0.0072 | 21 |
| 2024-03 - 2025-06 | 95 | 6.5 | 56.8 | 0.0116 | 40 |
| 2025-06 - 2026-09 | 79 | 5.4 | 59.5 | 0.0194 | 64 |

Hranice pre úsek veľkosti posledného obdobia: -0.0045 až +0.0340 % (medián 0.0149).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 64. percentile, teda v medziach -0.0045 až +0.0340 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0149 %**, medián 0.0148 %, 90 % interval 0.0059–0.0238 %
- P(edge > poplatok) = **99.7 %**
- max drawdown: medián 7.1 %, 95. percentil 13.1 %, najhorší 40.5 %
- najdlhšia séria strát: medián 4, 95. percentil 6 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **238** na obchod pri účte 10 000

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
<!-- POSUDOK cisla=ef62d396 -->

**1. Na čo sa to hodí a na čo nie.**
Na trh s **jasným otvorením burzy** a s prestávkou, počas ktorej medzera vôbec vznikne —
indexové CFD a futures. Timeframe 15m; na 5m tá istá myšlienka nefunguje (PF 0.76 oproti
1.65), lebo cieľ je menší než šum. Krypto vypadáva z princípu: beží 24/7, medzera medzi
„včerajším close" a „dnešným open" tam nie je. Forex majors majú medzery len cez víkend,
takže by z toho ostalo pár obchodov ročne. Veľkosť účtu je bez problému, pokiaľ má nástroj
malú hodnotu bodu — na `NAS100` (point value 1.0) sa riziko 0.5 % nastaviť dá, na `WTI`
(1000) ani na `XAU` (100) nie.

**2. Má to potenciál?**
Za skutočným javom hovorí viac vecí naraz, a to je tu podstatné: **zisková v 5 z 5 okien**
(+5.65 až +12.33 %), winrate stabilný 54.4–60.7 %, drawdown po oknách 4.7–6.5 %,
**+2.1 sigma proti náhode** na 352 obchodoch a edge neupadá (posledné obdobie na 64.
percentile). Žiadna vopred známa vlastnosť obchodov výsledok nekazí. To je najvyrovnanejší
profil zo všetkého, čo je v tomto repozitári — `ibs` bola zisková v 3 z 5 okien, `orb`
v 4 z 5 a proti náhode dal len +1.1 sigma.

Proti hovorí veľkosť vzorky: 352 obchodov naprieč piatimi rokmi je ~70 ročne, takže jeden
zlý rok sa v priemeroch stratí. A `+2.1 sigma` je nad hranicou, nie ďaleko za ňou —
pri 61 obchodoch jedného okna to spadne na +0.8 sigma, čo je náhoda. Záver drží na
spoločnej vzorke, nie na jednotlivom roku.

**3. Čo treba dorobiť.**
Predovšetkým **náklad na trh** (`half_spread_ticks` do inštrumentu). Break-even 0.0149 %
je proti spreadu na `NAS100` CFD (~0.004 %) zhruba 3.7-násobok, čo je slušná rezerva — ale
kým náklad nie je v inštrumente, je to odhad, nie meranie. Ďalej chýba kalendár sviatkov:
po dlhom víkende a po poldni je medzera systematicky iná a teraz sa nerozlišuje. A stojí
za zváženie čiastočný výber zisku na 50 % výplne, keďže medián času do výplne je 18 minút,
ale 90. percentil 207.

**4. Čo otestovať ďalej.**
- `cli matrix --strategy gap --pairs all --timeframes 15m` — či myšlienka drží na `US500`,
  `DJ30`, `DAX`, `JP225`. Ak áno na indexoch a nie na komoditách, potvrdí to, že za tým je
  otvorenie burzy a nie ladenie.
- `cli run --engine freqtrade` — čísla sú z emulátora MultiCharts; vstup je na otvorení
  seansy, kde sa fill model líši najviac.
- `cli hyperopt --param slAtrMult=0.10:0.35:0.05 --param maxGapAtr=0.2:0.6:0.1`
  s povinným overením na ďalších oknách. Rozhodne, či je `0.15` skutočné optimum, alebo
  len najlepšia bunka z mriežky.
- Zopakovať checkup s reálnym spreadom. To je test, po ktorom je jasno.

**5. Je to použiteľné, alebo je to o ničom?**
**Použiteľné — a z toho, čo je v repozitári, je to najlepší kandidát na prop účet.** Dôvod
nie je najvyšší výnos (ten má `ibs`), ale to, čo prop pravidlá skutočne merajú: zisk
rozložený do piatich rokov bez straty, drawdown pod 7 % v každom okne, a zisky rozdelené
do ~70 obchodov ročne namiesto pár veľkých dní — čo je presne to, čo consistency rule
vyžaduje. Podmienka je riziko 0.5 % na obchod: 95. percentil drawdownu 13.1 % pri 1 %
riziku je nad limitom väčšiny firiem.

**6. Čo by som pridal.**
Veľkosť medzery ako **spojitú váhu**, nie ako prah. Teraz je to `min`/`max` a všetko medzi
nimi sa obchoduje rovnako, hoci meranie hovorí, že pravdepodobnosť výplne klesá plynulo
(77.8 % pod 0.3 dňa, 42 % pri 0.3–0.7, 25.6 % pri 0.7–1.2). Menšia medzera by teda mala
dostať väčšiu pozíciu — nie preto, že je „lepšia", ale preto, že jej výplň je istejšia.
Druhý nápad je použiť ju ako **filter smeru pre `orb`**: prerazenie opening rangu proti
nevyplnenej medzere je štatisticky slabšie než prerazenie smerom k nej, a `orb` túto
informáciu dnes zahadzuje.

<!-- POSUDOK KONIEC -->
