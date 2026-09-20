# Základná analytika — Breakout — prerazenie prvej sviečky NY openu (`breakout`)

Zmerané 2026-09-18 na `NAS100/USD` 3m, engine `multicharts`, poplatok 0.0001 % na stranu (1 tick na stranu pri cene 13914.3 = 0.00007 %; odhad: polovica spreadu = 1 tick, nezmerané (Dukascopy export má len bid, spread v ňom nie je)), profil `nas100_dukascopy_3m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy breakout \
   --profile nas100_dukascopy_3m \
   --timeframe 3m
```

## V čom je dobrá

- 1286 obchodov spolu — na štatistiku dosť
- break-even 0.0011 % je nad poplatkom 0.0001 % (rezerva +0.0010 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 42. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20250904-20260904 v strate)
- edge nad poplatkom len v 58 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 62.1 % (namerané 28.7 % medián) — na účet to treba mať
- proti náhode len +0.3 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 259 | -4.98 | -0.0056 | 15.1 | 51.4 | `20260918-084513-feb219` |
| 20221001-20231001 | 256 | -3.69 | -0.0032 | 13.1 | 49.6 | `20260918-084516-1995cf` |
| 20231001-20241001 | 257 | -2.87 | -0.0019 | 16.5 | 49.8 | `20260918-084519-161c94` |
| 20240904-20250904 | 257 | +31.29 | 0.0242 | 9.2 | 57.6 | `20260918-084522-c55e50` |
| 20250904-20260904 | 257 | -13.28 | -0.0088 | 23.4 | 47.1 | `20260918-084525-d63bc6` |

Zisková v **1 z 5** okien, obchodov spolu 1286, break-even celkom 0.0011 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.40 ATR za 5 barov)
- medián držania 8.7 barov grafu
- winrate 51.09 %, payoff 0.969
- 0.72 obchodov za deň
- šikmosť výnosov -0.098

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 48.8 %, `stop_loss` 47.1 %, `session_end` 4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0057 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pondelok | 257 | 20.0 % | 44.4 | -0.0193 | 0.0068 | +0.0057 |
| piatok | 255 | 19.8 % | 53.3 | 0.0050 | 0.0002 | -0.0009 |
| štvrtok | 258 | 20.1 % | 53.5 | 0.0067 | -0.0003 | -0.0014 |
| streda | 258 | 20.1 % | 51.5 | 0.0069 | -0.0003 | -0.0014 |
| utorok | 258 | 20.1 % | 52.7 | 0.0084 | -0.0007 | -0.0018 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| CPI | 58 | 4.5 % | 48.3 | -0.0045 | 0.0014 | +0.0003 |
| žiadna | 1131 | 87.9 % | 50.9 | 0.0005 | 0.0064 | +0.0053 |
| FOMC | 39 | 3.0 % | 51.3 | 0.0015 | 0.0011 | +0.0000 |
| NFP | 57 | 4.4 % | 56.1 | 0.0208 | 0.0004 | -0.0007 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 1131 | 87.9 % | 50.9 | 0.0005 | 0.0064 | +0.0053 |
| pred vyhlásením | 40 | 3.1 % | 52.5 | 0.0048 | 0.0010 | -0.0001 |
| po vyhlásení | 115 | 8.9 % | 52.2 | 0.0070 | 0.0006 | -0.0005 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `entryWindowMinutes`, `limitValidMinutes`, `maxRangePct`, `orderType`, `rrRatio`, `slBufferAtr`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0016 % | 0.0002 % ± 0.0043 | +0.32 | 62.9 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0016 % | -0.0002 % ± 0.0055 | +0.32 | 61.9 |

Neodlisitelne od nahody (+0.3 sigma, percentil 62.9). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 319 | 21.6 | 52.7 | 0.0016 | 49 |
| 2022-12 - 2024-03 | 314 | 21.3 | 47.8 | -0.0074 | 23 |
| 2024-03 - 2025-06 | 335 | 22.7 | 53.7 | 0.0109 | 81 |
| 2025-06 - 2026-09 | 318 | 21.6 | 50.0 | -0.0008 | 42 |

Hranice pre úsek veľkosti posledného obdobia: -0.0175 až +0.0199 % (medián 0.0014).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 42. percentile, teda v medziach -0.0175 až +0.0199 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0011 %**, medián 0.0011 %, 90 % interval -0.0075–0.0099 %
- P(edge > poplatok) = **58.1 %**
- max drawdown: medián 28.7 %, 95. percentil 62.1 %, najhorší 100.0 %
- najdlhšia séria strát: medián 8, 95. percentil 11 obchodov
- pravdepodobnosť ruiny účtu: 0.2 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **34** na obchod pri účte 10 000

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
<!-- POSUDOK cisla=38706122 -->

**1. Na čo sa to hodí a na čo nie.** Toto je meranie holého zadania na NAS100 CFD, 3m graf,
market vstup, cieľ 1:1, bez jediného filtra. V tej podobe sa to hodí ako **referenčný bod**
— číslo, proti ktorému sa dá porovnať každý nápad, ktorý sa k tomu dopíše. Ako obchodný
model sa to nehodí nikam: zisková je v jednom z piatich rokov a ten jeden rok (2024-09 až
2025-09, +31,3 %) nesie celý súčet. Účet pod ~25 000 USD netreba ani zvažovať — 95.
percentil drawdownu je 62 % a medián 28,7 %, čo je pri prop účte s denným limitom
mimo hry. Poplatok je tu odhadnutý ako jeden tick na stranu (Dukascopy export nemá spread);
na trhu so širším spreadom než NAS100 by rezerva 0,0010 bodu zmizla úplne.

**2. Má to potenciál?** Za skutočný jav hovoria tri veci: obchodov je dosť (1 286), počet
obchodov je naprieč oknami takmer konštantný (256–259, teda signál nezávisí od režimu trhu,
len jeho výsledok), a posledné obdobie je na 42. percentile vlastného rozdelenia — edge
neslabne, lebo nie je čo by slablo. Proti hovorí to hlavné: **+0,3 sigma a percentil 62,9
proti náhodnému výberu vstupu**. Výber vstupu neprináša nič, čo by nedal hod mincou.
Winrate 51,1 % pri payoffe 0,969 je presne to, čo vyjde z mince s poplatkom. Rok 2024-09 až
2025-09 je vlastnosť vzorky, nie stratégie — v jeho prospech nehovorí nič okrem toho, že
nastal.

**3. Čo treba dorobiť.** Chýba všetko, čo z prerazenia robí výber, a nie štatistiku:
(a) **filter smeru** — long aj short sa berú rovnako, hoci na indexe to nie sú dve zrkadlové
stratégie; (b) **kontext predošlého dňa** — kde je otvorenie voči včerajšiemu high/low
a voči zatvoreniu; (c) **sviatky a poldni** — 24. a 31. decembra a pri poldenných seansách
sa otváracia sviečka správa inak a dnes sa obchodujú ako každý iný deň; (d) **výstup** —
pevné 1:1 nechá bežať presne 48,8 % obchodov do cieľa a nič viac, pričom medián držania je
8,7 barov, takže priestor na čiastočný výber alebo posun na break-even tam je.

**4. Čo otestovať ďalej** (v tomto poradí, každý krok rozhodne jednu vec):

```bash
PY -m tester.webapp.cli sweep --strategy breakout --profile nas100_dukascopy_3m \
   --set rrRatio=0.5:4:0.25 --timerange 20211001-20260904 --note "RR: kde je optimum"
PY -m tester.webapp.cli sweep --strategy breakout --profile nas100_dukascopy_3m \
   --set orderType=market,limit --set tradeDirection=Both,"Long only","Short only" \
   --timerange 20211001-20260904 --note "typ prikazu x smer"
PY -m tester.webapp.cli matrix --strategy breakout --pairs all --timeframes 1m,2m,3m
```

Prvý povie, či je 1:1 náhodou to najhoršie možné RR (pri payoffe 0,969 a winrate 51 % je to
pravdepodobné). Druhý rozhodne dve veci naraz: či limitka zaplatí za lepšiu cenu menším
počtom obchodov alebo nie, a či je edge iba v jednom smere. Tretí povie to
podstatné — či je čokoľvek z toho vlastnosť NAS100 a 3m grafu, alebo myšlienky. **Keby
matica ukázala rovnaký výsledok na viacerých trhoch a TF, +0,3 sigma z jedného trhu by
zrazu znamenalo oveľa viac.** Druhý engine je overený: ten istý profil dal na Freqtrade
254 obchodov (WR 46,5 %) proti 257 emulátora (WR 47,1 %) — rozdiel 1,2 % je fill model
(market order na zavretí baru proti otvoreniu ďalšieho), nie odchýlka signálu.

**5. Je to použiteľné, alebo je to o ničom?** V tejto podobe je to **o ničom** — a je to
jednoznačná odpoveď, nie opatrnosť: jedno ziskové okno z piatich a +0,3 sigma proti
náhode znamenajú, že sa tu nemeria stratégia, ale trh. Zároveň to **nie je zbytočná práca**:
signál je stabilný (256–259 obchodov v každom roku), takže je to čistá základňa, na ktorej
sa dá merať prínos každého pridaného pravidla. Použiteľné to bude až vtedy, keď niektorý
z testov v bode 4 posunie sigma nad 2 a znamienko aspoň v štyroch oknách z piatich.

**6. Čo by som pridal.** Jedno pravidlo, ktoré tu chýba najviac a z týchto čísel vyplýva:
**vstupovať len na tú stranu, ktorá je v smere otvorenia proti včerajšiemu zatvoreniu**.
Otváracia sviečka je dnes jediný kontext, ktorý stratégia má, a je to päť minút histórie;
gap oproti včerajšku je zadarmo (netreba naň nový indikátor ani vyšší TF) a je to presne
tá informácia, ktorá na indexoch delí dni, keď prerazenie openu pokračuje, od dní, keď sa
vracia. Ako druhé v poradí by som skúsil **plávajúci cieľ podľa šírky otváracej sviečky**
namiesto pevného RR — úzka otváracia sviečka a široká otváracia sviečka dnes dostávajú
rovnaký cieľ v R, hoci znamenajú iný deň.

<!-- POSUDOK KONIEC -->
