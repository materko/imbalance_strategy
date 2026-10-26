# Základná analytika — IBS Entry Zone (C# jadro) (`ibsentrynet`)

Zmerané 2026-10-26 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tester/profiles/SMERNICE_CS_IBS_Entry_Zone_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibsentrynet \
   --profile tester/profiles/SMERNICE_CS_IBS_Entry_Zone_1.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 817 obchodov spolu — na štatistiku dosť
- break-even 0.0179 % je nad poplatkom 0.0018 % (rezerva +0.0161 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 13.7 %
- odlíšiteľná od náhody (+8.0 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 83. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'bežný deň' vlastnosti 'Sviatok na burze v USA': 786 obchodov (96.2 %), bez nej by break-even bol o +0.0103 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 222 | +50.98 | 0.0230 | 8.3 | 76.1 | +13/-3 | `20261026-130436-3c6ec4` |
| 20221001-20231001 | 124 | +12.62 | 0.0098 | 9.1 | 71.8 | +8/-3 | `20261026-130448-b32ae8` |
| 20231001-20241001 | 98 | +9.88 | 0.0089 | 6.1 | 72.5 | +8/-3 | `20261026-130500-118ad8` |
| 20240904-20250904 | 161 | +33.27 | 0.0183 | 6.7 | 75.2 | +13/-3 | `20261026-130512-9ef26f` |
| 20250904-20260904 | 212 | +58.13 | 0.0222 | 6.7 | 78.3 | +18/-4 | `20261026-130524-ed88ea` |

Zisková v **5 z 5** okien, obchodov spolu 817, break-even celkom 0.0179 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.71 ATR za 5 barov)
- medián držania 2.3 barov grafu
- winrate 75.4 %, payoff 0.498
- 0.45 obchodov za deň
- šikmosť výnosov -1.46

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 75.6 %, `stop_loss` 24.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'bežný deň' vlastnosti 'Sviatok na burze v USA': 786 obchodov (96.2 %), break-even 0.0175 % oproti 0.0179 % celku. Bez nej by break-even bol 0.0282 % (+0.0103). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 786 | 96.2 % | 75.2 | 0.0175 | 0.0282 | +0.0103 |
| deň po sviatku | 17 | 2.1 % | 82.3 | 0.0258 | 0.0177 | -0.0002 |
| deň pred sviatkom | 11 | 1.3 % | 81.8 | 0.0418 | 0.0176 | -0.0003 |

**S trendom, alebo proti** (riadi `useStructureFilter`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 575 | 70.4 % | 73.6 | 0.0142 | 0.0263 | +0.0084 |
| proti trendu | 242 | 29.6 % | 79.8 | 0.0263 | 0.0142 | -0.0037 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 7 – 14 | 205 | 25.1 % | 70.2 | 0.0084 | 0.0210 | +0.0031 |
| do 7 | 211 | 25.8 % | 74.9 | 0.0169 | 0.0183 | +0.0004 |
| 14 – 23 | 203 | 24.8 % | 76.8 | 0.0196 | 0.0173 | -0.0006 |
| nad 23 | 198 | 24.2 % | 79.8 | 0.0268 | 0.0151 | -0.0028 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `rrRatio`, `sess2TradeStartH`, `state2MaxBars`, `tradeDirection`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0205 % | -0.0000 % ± 0.0026 | +8.04 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0205 % | -0.0001 % ± 0.0026 | +7.81 | 100.0 |

Edge je odlisitelny od nahody (8.0 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 267 | 18.1 | 74.2 | 0.0179 | 49 |
| 2022-12 - 2024-03 | 112 | 7.6 | 75.9 | 0.0159 | 41 |
| 2024-03 - 2025-06 | 209 | 14.2 | 72.7 | 0.0129 | 21 |
| 2025-06 - 2026-09 | 229 | 15.5 | 79.0 | 0.0232 | 83 |

Hranice pre úsek veľkosti posledného obdobia: +0.0088 až +0.0266 % (medián 0.0181).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 83. percentile, teda v medziach +0.0088 až +0.0266 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 18** — 2026-01-29T18:09 až 2026-02-12T15:54, spolu +9058.81.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-01-29T18:09 | 2026-01-29T18:10 | +439.50 | +0.11 | `take_profit` |
| 2 | 2026-01-30T07:27 | 2026-01-30T07:37 | +449.30 | +0.07 | `take_profit` |
| 3 | 2026-01-30T17:54 | 2026-01-30T18:00 | +467.68 | +0.15 | `take_profit` |
| 4 | 2026-01-30T20:01 | 2026-01-30T20:05 | +455.59 | +0.11 | `take_profit` |
| 5 | 2026-01-30T21:11 | 2026-02-01T23:00 | +1417.22 | +0.46 | `take_profit` |
| 6 | 2026-02-04T15:33 | 2026-02-04T15:34 | +458.66 | +0.18 | `take_profit` |
| 7 | 2026-02-04T15:54 | 2026-02-04T16:01 | +442.35 | +0.09 | `take_profit` |
| 8 | 2026-02-04T18:32 | 2026-02-04T18:42 | +442.76 | +0.13 | `take_profit` |
| 9 | 2026-02-04T18:45 | 2026-02-04T18:50 | +443.28 | +0.10 | `take_profit` |
| 10 | 2026-02-05T00:24 | 2026-02-05T00:38 | +471.90 | +0.12 | `take_profit` |
| 11 | 2026-02-05T15:51 | 2026-02-05T15:52 | +444.65 | +0.13 | `take_profit` |
| 12 | 2026-02-05T18:00 | 2026-02-05T18:10 | +452.55 | +0.18 | `take_profit` |
| 13 | 2026-02-05T19:33 | 2026-02-05T20:25 | +390.05 | +0.26 | `take_profit` |
| 14 | 2026-02-05T21:09 | 2026-02-05T21:19 | +423.10 | +0.21 | `take_profit` |
| 15 | 2026-02-09T14:39 | 2026-02-09T14:40 | +457.95 | +0.23 | `take_profit` |
| 16 | 2026-02-10T15:18 | 2026-02-10T15:24 | +472.64 | +0.08 | `take_profit` |
| 17 | 2026-02-11T18:19 | 2026-02-11T18:27 | +461.73 | +0.08 | `take_profit` |
| 18 | 2026-02-12T15:54 | 2026-02-12T15:54 | +467.88 | +0.08 | `take_profit` |

**Straty za sebou: 5** — 2024-09-18T19:18 až 2024-10-03T15:40, spolu -4713.40.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-09-18T19:18 | 2024-09-18T19:20 | -953.97 | -0.19 | `stop_loss` |
| 2 | 2024-09-18T19:18 | 2024-09-18T19:20 | -953.97 | -0.19 | `stop_loss` |
| 3 | 2024-09-27T17:30 | 2024-09-27T18:00 | -979.22 | -0.24 | `stop_loss` |
| 4 | 2024-09-27T17:30 | 2024-09-27T18:00 | -979.22 | -0.24 | `stop_loss` |
| 5 | 2024-10-03T15:00 | 2024-10-03T15:40 | -847.02 | -0.42 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0179 %**, medián 0.0180 %, 90 % interval 0.0131–0.0227 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 7.7 %, 95. percentil 13.7 %, najhorší 37.1 %
- najdlhšia séria strát: medián 4, 95. percentil 5 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **2 434** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=01ae8325 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „IBS EZ 1 C#“ (`SMERNICE_CS_IBS_Entry_Zone_1`, kópia PREŠIEL SMERNICAMI č. 1 z `ibsentry`):
TP 0,5 R, IBS imbalance + pin bar, tri seansy (Ázia 0–3 NY, NY, popoludnie), veľkosť z rizika (~950 $ na obchod, `legacyPineSizing` vypnutý — nie 1 kontrakt)._

1. **Na čo sa to hodí a na čo nie.** Na MNQ / NQ futures, graf 3m s 1m detailom, intraday scalp: medián držania 2,3 baru
   (~7 min), winrate 75 %, payoff 0,5, 0,45 obchodu denne. Na účet 60 000 $ s rizikom ~950 $ na obchod je 95. percentil
   drawdownu 13,7 % a séria 4–5 strát po sebe (≈ 4 700 $) je normálna; Monte Carlo pustí najviac ~2 400 $ na obchod.
   Nehodí sa tam, kde je plnenie horšie než na CME (CFD so spreadom, pomalá platforma) — pri cieli 0,5 R rozhoduje
   každý tick. Pozor: profil nezatvára o konci seansy (`closeAtSessionEnd=false`), pár obchodov prežije noc aj víkend
   (napr. 30. 1. → 1. 2. 2026) — na prop účty je preto `ibsentryneteod`.
2. **Má to potenciál? Áno.** C# jadro dáva okno po okne to isté čo Python predloha: dnešný `ibsentry` s tým istým
   profilom má na 2024/25 presne 161 obchodov, +33,27 %, break-even 0,0183 % (beh `20261026-131117-979862`); rozdiel
   proti analytike `ibsentry` z 11. 10. (+34,78 %, 0,0190) spravili opravy emulátora N-CORE-1/2/3, nie port. Za javom:
   5 z 5 okien v zisku, +8,0 σ proti náhodnému vstupu, break-even 0,0179 % je ~10× nad poplatkom a 100 % bootstrapu je
   nad ním, posledné obdobie na 83. percentile. Proti: roky 22/23 a 23/24 sú tenké (124 a 98 obchodov, break-even
   0,0098 a 0,0089 %) a parametre vzišli z hľadania v ~16 000 kombináciách — odložený rok to prešiel, ale výsledok stojí
   najmä na volatilnejších rokoch.
3. **Čo treba dorobiť.** (a) Série v analytike stále počítajú obchody z prekrytia okien 2023/24 a 2024/25 (4. 9. –
   1. 10. 2024) dvakrát — séria 5 strát je v skutočnosti 3 (dvojice 18. 9. a 27. 9.). (b) Obchody s vstupom aj
   výstupom v tej istej minúte závisia od poradia SL/TP vnútri 1m sviečky — overiť forward testom alebo tickmi.
   (c) Skupina „bežný deň“ (96 %) nie je filter, to je len artefakt, že sviatkové dni sú lepšie; nič s ňou nerobiť.
4. **Čo otestovať ďalej.** Stres sklzu: `cli checkup --strategy ibsentrynet --profile tester/profiles/SMERNICE_CS_IBS_Entry_Zone_1.json
   --pair MNQ/USD --timeframe 3m --fee 3.51e-05 --no-write` (2× poplatok; break-even musí ostať nad ním vo všetkých
   piatich oknách, 22/23 a 23/24 sú tie, ktoré padnú prvé). Potom forward test na NT8 Sim101 / MT5 deme 4–8 týždňov
   a porovnanie obchod po obchode s webapp (`tester.ninjatrader compare`) — rozhodne, či sedí plnenie limitiek.
5. **Je to použiteľné? Áno** — najsilnejšia z IBS rodiny a s overenou paritou C# = Python. Na ostrý účet po forward
   teste; s rizikom do ~1 % účtu na obchod.
6. **Čo by som pridal.** Denný limit straty (2 stopy za deň) — straty prichádzajú v zhlukoch v jednom dni (18. 9. a 27. 9.
   2024 po dvoch) a pri prop pravidlách rozhoduje práve denná strata. Druhý nápad: filter obchodov v smere štruktúry je
   slabší (break-even 0,0142 % proti 0,0263 % proti trendu) — `useStructureFilter` skúsiť ako prepínač, nie hľadaním.

<!-- POSUDOK KONIEC -->
