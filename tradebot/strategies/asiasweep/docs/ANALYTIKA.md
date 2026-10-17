# Základná analytika — ASIA SWEEP 1.0 (`asiasweep`)

Zmerané 2026-10-17 na `EURUSD/USD` 5m, engine `multicharts`, poplatok 0.0040 % na stranu (zadané cez --fee), profil `tradebot/strategies/asiasweep/configs/eurusd_dukascopy_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy asiasweep \
   --profile tradebot/strategies/asiasweep/configs/eurusd_dukascopy_5m.json \
   --pair EURUSD/USD \
   --timeframe 5m \
   --fee 4e-05
```

## V čom je dobrá

- 874 obchodov spolu — na štatistiku dosť
- odlíšiteľná od náhody (+2.4 sigma proti náhodnému vstupu)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20240904-20250904, 20250904-20260904 v strate)
- break-even 0.0020 % je pod poplatkom 0.0040 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 8 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 97.7 % pri riziku, s akým beh bežal

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 174 | -349.23 | -0.0025 | 423.2 | 31.0 | +4/-12 | `20261017-125324-a00d86` |
| 20221001-20231001 | 191 | -121.78 | 0.0017 | 139.6 | 35.6 | +4/-12 | `20261017-125330-bec7a7` |
| 20231001-20241001 | 186 | +7.52 | 0.0041 | 72.5 | 40.3 | +8/-8 | `20261017-125336-b005b2` |
| 20240904-20250904 | 164 | -121.71 | 0.0014 | 169.0 | 35.4 | +5/-10 | `20261017-125342-903ddd` |
| 20250904-20260904 | 174 | -97.73 | 0.0027 | 143.1 | 39.1 | +4/-10 | `20261017-125348-65e592` |

Zisková v **1 z 5** okien, obchodov spolu 874, break-even celkom 0.0020 %. Okná sa prekrývajú, 15 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.79 ATR za 5 barov)
- medián držania 8.8 barov grafu
- winrate 36.61 %, payoff 1.559
- 0.49 obchodov za deň
- šikmosť výnosov +1.204

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 62.7 %, `take_profit` 34.2 %, `session_end` 3.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0059 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 695 | 79.5 % | 35.4 | 0.0011 | 0.0079 | +0.0059 |
| s trendom | 179 | 20.5 % | 41.3 | 0.0079 | 0.0011 | -0.0009 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.1433 | 218 | 24.9 % | 32.1 | -0.0011 | 0.0034 | +0.0014 |
| 0.0816 – 0.1433 | 217 | 24.8 % | 35.0 | 0.0011 | 0.0023 | +0.0003 |
| 0.0373 – 0.0816 | 220 | 25.2 % | 37.3 | 0.0028 | 0.0018 | -0.0002 |
| do 0.0373 | 219 | 25.1 % | 42.0 | 0.0071 | 0.0007 | -0.0013 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.2771 | 219 | 25.1 % | 33.3 | -0.0000 | 0.0034 | +0.0014 |
| 0.4286 – 0.6048 | 217 | 24.8 % | 35.0 | 0.0011 | 0.0022 | +0.0002 |
| 0.2771 – 0.4286 | 220 | 25.2 % | 37.7 | 0.0031 | 0.0016 | -0.0004 |
| nad 0.6048 | 218 | 24.9 % | 40.4 | 0.0069 | 0.0012 | -0.0008 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `sweepStartH`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0043 % | 0.0001 % ± 0.0018 | +2.38 | 99.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0043 % | 0.0003 % ± 0.0020 | +2.03 | 97.4 |

Edge je odlisitelny od nahody (2.4 sigma, percentil 99.1).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 214 | 14.5 | 33.2 | -0.0008 | 15 |
| 2022-12 - 2024-03 | 232 | 15.7 | 36.2 | 0.0019 | 50 |
| 2024-03 - 2025-06 | 216 | 14.6 | 38.4 | 0.0035 | 66 |
| 2025-06 - 2026-09 | 212 | 14.4 | 38.7 | 0.0027 | 59 |

Hranice pre úsek veľkosti posledného obdobia: -0.0026 až +0.0067 % (medián 0.0020).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 59. percentile, teda v medziach -0.0026 až +0.0067 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2023-10-18T07:05 až 2023-10-27T11:01, spolu +14345.27.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-18T07:05 | 2023-10-18T14:29 | +1712.76 | +0.32 | `take_profit` |
| 2 | 2023-10-19T06:25 | 2023-10-19T11:14 | +1925.62 | +0.18 | `take_profit` |
| 3 | 2023-10-20T06:50 | 2023-10-20T08:23 | +1838.07 | +0.12 | `take_profit` |
| 4 | 2023-10-23T06:35 | 2023-10-23T07:48 | +1855.45 | +0.13 | `take_profit` |
| 5 | 2023-10-24T07:35 | 2023-10-24T12:54 | +1612.46 | +0.50 | `take_profit` |
| 6 | 2023-10-25T07:30 | 2023-10-25T08:00 | +1705.68 | +0.07 | `take_profit` |
| 7 | 2023-10-26T06:55 | 2023-10-26T08:19 | +1853.46 | +0.12 | `take_profit` |
| 8 | 2023-10-27T06:10 | 2023-10-27T11:01 | +1841.77 | +0.12 | `take_profit` |

**Straty za sebou: 12** — 2021-10-21T06:40 až 2021-11-16T09:06, spolu -13604.31, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-21T06:40 | 2021-10-21T06:51 | -1342.20 | -0.03 | `stop_loss` |
| 2 | 2021-10-26T07:20 | 2021-10-26T07:28 | -1160.73 | -0.06 | `stop_loss` |
| 3 | 2021-10-27T06:20 | 2021-10-27T08:30 | -1082.63 | -0.07 | `stop_loss` |
| 4 | 2021-10-28T07:55 | 2021-10-28T08:09 | -1225.66 | -0.05 | `stop_loss` |
| 5 | 2021-11-01T06:20 | 2021-11-01T07:57 | -1080.72 | -0.08 | `stop_loss` |
| 6 | 2021-11-02T06:40 | 2021-11-02T07:02 | -1393.12 | -0.03 | `stop_loss` |
| 7 | 2021-11-08T07:35 | 2021-11-08T08:41 | -1073.24 | -0.10 | `stop_loss` |
| 8 | 2021-11-09T07:05 | 2021-11-09T07:09 | -1320.92 | -0.04 | `stop_loss` |
| 9 | 2021-11-11T08:35 | 2021-11-11T16:55 | -295.20 | -0.04 | `session_end` |
| 10 | 2021-11-12T07:10 | 2021-11-12T07:23 | -1620.91 | -0.02 | `stop_loss` |
| 11 | 2021-11-15T09:00 | 2021-11-15T14:11 | -946.08 | -0.12 | `stop_loss` |
| 12 | 2021-11-16T08:05 | 2021-11-16T09:06 | -1062.88 | -0.10 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0020 %**, medián 0.0020 %, 90 % interval -0.0002–0.0043 %
- P(edge > poplatok) = **7.8 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 13, 95. percentil 18 obchodov
- pravdepodobnosť ruiny účtu: 97.7 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **15** na obchod pri účte 10 000

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
<!-- POSUDOK cisla=5261c7ff -->

**1. Na čo sa to hodí a na čo nie**

Stratégia je postavená na **EURUSD 5m v londýnskej seanse** a nič iné zmerané nie je. Rozhodujúce
číslo je break-even **0,0020 %** na stranu. Pri cene okolo 1,10 je to **~0,22 pipu hrubého zisku
na stranu, teda ~0,45 pipu na obchod**. Realistický náklad na EURUSD (polovica spreadu ECN plus
provízia ~35 $ za milión na stranu) je okolo 0,45 pipu **na stranu**, teda ~0,9 pipu na obchod.
Tento beh rátal s poplatkom 0,0040 % na stranu, čo zodpovedá práve tomu. Pri ňom je to strata
a edge nad poplatkom vyšiel len v 7,8 % bootstrapových vzoriek. Pri predvolenom poplatku 1 tick
(0,1 pipu) by vyzerala zisková, ale taký náklad u žiadneho brokera nie je.

**PnL a drawdown v tabuľke sú pre posudok bezcenné.** Predvolené `riskDollar = 1000` pri účte
10 000 je 10 % riziko na obchod, preto drawdown 100 % a ruina 97,7 %. To je chyba veľkosti, nie
stratégie. O stratégii vypovedá break-even, ktorý od veľkosti nezávisí.

Nehodí sa na nič, kde náklad na obchod presahuje ~0,4 pipu, čiže na bežný retail spread aj na
prop účty. Zmysel by mala len pri náklade, aký dnes nemáme.

**2. Má to potenciál?**

Za skutočným javom hovorí málo, ale niečo áno:
- **Proti náhode +2,38 sigma** (percentil 99,1) a **+2,03 sigma proti náhode v tých istých
  hodinách**, čiže edge nie je len v tom, kedy obchoduje.
- **874 obchodov** (po oprave duplicít z prekrývajúcich sa okien).
- **Neslabne:** posledné obdobie je na 59. percentile vlastnej minulosti a break-even po úsekoch
  rastie (−0,0008 → 0,0019 → 0,0035 → 0,0027).

Proti hovorí:
- **Okná:** zisková len v 1 z 5. Break-even po rokoch je síce v 4 z 5 kladný, ale menší než
  náklad.
- **Interval** break-evenu −0,0002 až 0,0043 % siaha pod nulu.
- **Rok 2021-10 až 2022-10 je záporný aj pred poplatkom** (−0,0025). Bol to rok silného trendu
  EURUSD k parite, a práve v trende sweep do protismeru nefunguje (bod 3).

Jav teda pravdepodobne existuje, len je **o rád menší, než aby sa dal zaplatiť**.

**3. Čo treba dorobiť**

- **Sizing v profile.** `riskDollar` v `eurusd_dukascopy_5m.json` treba nastaviť na 1 % účtu
  (100 pri 10 000), inak každý budúci beh ukazuje ruinu, ktorá s logikou nesúvisí.
- **Filter režimu: obchodovať len v rozsahu.** Najsilnejší signál v dokumente je „trend alebo
  rozsah". Najpokojnejšia štvrtina (sila trendu do 0,037) má winrate 42 % a break-even
  **0,0071 %**, najtrendovejšia štvrtina (nad 0,143) **−0,0011 %**. Rozdiel je monotónny cez
  všetky štyri štvrtiny, takže to nie je náhoda jednej skupiny. Stratégia filter režimu nemá,
  zdieľaný `volFilter = low` je najbližšia náhrada.
- **Smer voči vyššiemu trendu.** 79,5 % obchodov ide proti trendu (break-even 0,0011) a 20,5 %
  s trendom (0,0079). Sweep, ktorý vyberie stopky proti vyššiemu trendu a vráti sa doň, je lepší
  obchod než pokus otočiť trend. Na to je `trendFilter = with` (EMA na `trendTF`).
- **Shorty sú takmer nulové** (break-even 0,0001 proti 0,0032 pri longoch). Pri EURUSD, ktorý
  bol 2021–2022 v páde, to je zvláštne a stojí to za samostatný beh `tradeDirection`.
- **Neskorý vstup.** Charakter vyšiel „prerazenie", hoci myšlienka je obrat. Vstup prichádza po
  pohybe +0,79 ATR v smere obchodu za 5 barov, teda keď sa návrat do rangu už stal: stratégia
  čaká na imbalance alebo pin bar a dobrú časť pohybu nechá ležať. Vplyv má aj na RR: TP je
  2× stop, no payoff vyšiel 1,56.

**4. Čo otestovať ďalej**

```
cli sweep --strategy asiasweep --profile tradebot/strategies/asiasweep/configs/eurusd_dukascopy_5m.json \
   --pair EURUSD/USD --timeframe 5m --set riskDollar=100 --param trendFilter=off,with --param volFilter=off,low
cli sweep --strategy asiasweep … --set riskDollar=100 --param entryOrderType=market,limit --param limitOffsetPct=25:75:25
cli sweep --strategy asiasweep … --set riskDollar=100 --param entryModel=imbalance,pinbar,any,close
cli matrix --strategy asiasweep --pairs all --timeframes 5m
cli hyperopt --strategy asiasweep --suggested --timerange 20211001-20241001
```

- **Prvý sweep** rozhodne bod 3: ak `with` alebo `low` zdvihne break-even celku nad ~0,004 %
  a drží v 4 z 5 okien, je to stratégia. Ak nie, filter len zúžil vzorku.
- **Limitka späť do signálnej sviečky** rozhodne, či sa dá získať späť to, čo neskorý vstup
  nechal ležať.
- **Matica** povie, či je jav vlastnosťou EURUSD, alebo likvidity Ázie všeobecne (GBPUSD, zlato,
  DAX).
- **Hyperopt** na 2021–2024 a overenie na 2024–2026 rozhodne, či ladením nevzniká len vlastnosť
  vzorky.

**5. Je to použiteľné, alebo je to o ničom?**

**V tejto podobe nepoužiteľné.** Edge je odlíšiteľný od náhody (2,4 sigma), ale je asi o polovicu
menší, než stojí obchod na EURUSD (0,0020 % proti 0,0040 % na stranu). Bez zmeny logiky sa to
nezmení.

Nie je to však o ničom. Stratégia má **jednu konkrétnu stopu**: v pokojnom trhu a v smere vyššieho
trendu je break-even 0,007–0,008 %, čiže 2× nad nákladom. Presvedčil by ma test, v ktorom profil
s `volFilter = low` (alebo `trendFilter = with`) dá break-even nad 0,004 % **v aspoň 4 z 5 okien
pri 1 % riziku**. Ak ho nedá, stratégiu ďalej neladiť.

**6. Čo by som pridal**

**Filter šírky rangu Ázie voči jeho vlastnej histórii.** Dnes sa veľkosť rangu filtruje len
v percentách ceny (`rangeMinPct`, `rangeMaxPct`, oba vypnuté). Sweep má zmysel, keď Ázia
naozaj „stála": jej range je užší než medián posledných N ázijských rangov. Vtedy nad ním a pod
ním leží nahustená likvidita a Londýn ju vyberie a otočí. Keď je Ázia široká, trh už smer má
a „sweep" je len pokračovanie, čo sedí s tým, že najtrendovejšia štvrtina obchodov je stratová.
Pridal by som parameter `rangeVsMedian` (šírka ≤ X-násobok mediánu posledných N rangov) a zmeral
ho hneď po filtri režimu z bodu 3. Meria to isté (pokojný trh), ale na úrovni, ktorú stratégia
pozná, a nie cez ATR 14 barov.

<!-- POSUDOK KONIEC -->
