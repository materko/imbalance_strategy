# Základná analytika — ORBNet Opening Range Breakout (C# jadro) (`orbnet`)

Zmerané 2026-09-24 na `NAS100/USD` 15m, engine `multicharts`, poplatok 0.0000 % na stranu (zadané cez --fee), profil `tester/profiles/NINJA_ORB_RRR1.0_15m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy orbnet \
   --profile tester/profiles/NINJA_ORB_RRR1.0_15m.json \
   --pair NAS100/USD \
   --timeframe 15m \
   --fee 0.0
```

## V čom je dobrá

- 648 obchodov spolu — na štatistiku dosť
- edge drží aj v poslednom období (2025-06 - 2026-09 na 76. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20231001-20241001 v strate)
- náklad na tomto trhu nepoznáme, takže break-even sa proti ničomu neposudzuje — doplň ho do inštrumentu (`half_spread_ticks`)
- 95. percentil max drawdownu 30.0 % (namerané 14.6 % medián) — na účet to treba mať
- proti náhode len +1.2 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 129 | +0.57 | 0.0009 | 6.7 | 48.8 | +5/-9 | `20260924-205107-1f4cc8` |
| 20221001-20231001 | 123 | +2.42 | 0.0033 | 6.7 | 52.0 | +5/-4 | `20260924-205111-7cd48a` |
| 20231001-20241001 | 131 | -8.23 | -0.0078 | 9.2 | 46.6 | +4/-5 | `20260924-205115-88c837` |
| 20240904-20250904 | 132 | +8.41 | 0.0078 | 5.7 | 56.1 | +7/-5 | `20260924-205119-9a6258` |
| 20250904-20260904 | 133 | +13.70 | 0.0142 | 7.9 | 57.1 | +12/-6 | `20260924-205123-1f8e47` |

Zisková v **4 z 5** okien, obchodov spolu 648, break-even celkom 0.0038 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.44 ATR za 5 barov)
- medián držania 1.5 barov grafu
- winrate 52.16 %, payoff 0.976
- 0.36 obchodov za deň
- šikmosť výnosov -0.075

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 52 %, `stop_loss` 47.8 %, `force_exit` 0.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0075 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 14 h | 393 | 60.6 % | 50.1 | -0.0009 | 0.0113 | +0.0075 |
| 15 h | 233 | 36.0 % | 54.5 | 0.0094 | 0.0009 | -0.0029 |
| 16 h | 22 | 3.4 % | 63.6 | 0.0258 | 0.0028 | -0.0010 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň po sviatku | 15 | 2.3 % | 40.0 | -0.0285 | 0.0044 | +0.0006 |
| bežný deň | 609 | 94.0 % | 51.9 | 0.0032 | 0.0100 | +0.0062 |
| deň pred sviatkom | 10 | 1.5 % | 70.0 | 0.0554 | 0.0031 | -0.0007 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.2773 % – 0.4051 % | 161 | 24.8 % | 47.2 | -0.0170 | 0.0080 | +0.0042 |
| do 0.1954 % | 163 | 25.2 % | 47.9 | -0.0028 | 0.0095 | +0.0057 |
| 0.1954 % – 0.2773 % | 163 | 25.2 % | 60.1 | 0.0212 | -0.0017 | -0.0055 |
| nad 0.4051 % | 161 | 24.8 % | 53.4 | 0.0228 | 0.0011 | -0.0027 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0076 % | 0.0016 % ± 0.0048 | +1.24 | 89.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0076 % | 0.0008 % ± 0.0060 | +1.14 | 86.7 |

Naznak, ale nie dokaz (1.2 sigma, percentil 89.3). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 155 | 10.5 | 51.0 | 0.0060 | 63 |
| 2022-12 - 2024-03 | 157 | 10.7 | 48.4 | -0.0053 | 14 |
| 2024-03 - 2025-06 | 167 | 11.3 | 52.7 | 0.0036 | 52 |
| 2025-06 - 2026-09 | 169 | 11.5 | 56.2 | 0.0103 | 76 |

Hranice pre úsek veľkosti posledného obdobia: -0.0106 až +0.0190 % (medián 0.0042).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 76. percentile, teda v medziach -0.0106 až +0.0190 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 12** — 2026-01-07T15:30 až 2026-02-09T16:12, spolu +1071.88.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-01-07T15:30 | 2026-01-07T15:35 | +91.79 | +0.12 | `take_profit` |
| 2 | 2026-01-09T15:30 | 2026-01-09T18:41 | +104.08 | +0.41 | `take_profit` |
| 3 | 2026-01-12T15:00 | 2026-01-12T16:15 | +50.21 | +0.20 | `take_profit` |
| 4 | 2026-01-19T15:00 | 2026-01-19T16:07 | +79.19 | +0.16 | `take_profit` |
| 5 | 2026-01-20T15:30 | 2026-01-20T15:42 | +52.72 | +0.21 | `take_profit` |
| 6 | 2026-01-21T15:00 | 2026-01-21T15:45 | +139.96 | +0.56 | `take_profit` |
| 7 | 2026-01-23T15:00 | 2026-01-23T15:04 | +64.23 | +0.13 | `take_profit` |
| 8 | 2026-01-26T15:00 | 2026-01-26T15:20 | +88.77 | +0.17 | `take_profit` |
| 9 | 2026-01-27T15:00 | 2026-01-27T23:00 | +66.47 | +0.26 | `take_profit` |
| 10 | 2026-02-02T15:00 | 2026-02-02T15:06 | +73.78 | +0.29 | `take_profit` |
| 11 | 2026-02-06T16:15 | 2026-02-06T20:42 | +144.60 | +0.58 | `take_profit` |
| 12 | 2026-02-09T15:15 | 2026-02-09T16:12 | +116.07 | +0.46 | `take_profit` |

**Straty za sebou: 10** — 2024-09-13T14:45 až 2024-09-25T15:52, spolu -769.26.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-09-13T14:45 | 2024-09-16T10:26 | -54.09 | -0.28 | `stop_loss` |
| 2 | 2024-09-13T14:45 | 2024-09-16T10:26 | -54.09 | -0.28 | `stop_loss` |
| 3 | 2024-09-16T14:15 | 2024-09-16T14:20 | -94.60 | -0.24 | `stop_loss` |
| 4 | 2024-09-16T14:15 | 2024-09-16T14:20 | -94.60 | -0.24 | `stop_loss` |
| 5 | 2024-09-19T14:30 | 2024-09-19T15:00 | -72.81 | -0.37 | `stop_loss` |
| 6 | 2024-09-19T14:30 | 2024-09-19T15:00 | -72.81 | -0.37 | `stop_loss` |
| 7 | 2024-09-23T14:30 | 2024-09-23T14:39 | -74.28 | -0.19 | `stop_loss` |
| 8 | 2024-09-23T14:30 | 2024-09-23T14:39 | -74.28 | -0.19 | `stop_loss` |
| 9 | 2024-09-25T14:00 | 2024-09-25T15:52 | -88.86 | -0.22 | `stop_loss` |
| 10 | 2024-09-25T14:00 | 2024-09-25T15:52 | -88.86 | -0.22 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0038 %**, medián 0.0038 %, 90 % interval -0.0037–0.0112 %
- P(edge > poplatok) = **79.8 %**
- max drawdown: medián 14.6 %, 95. percentil 30.0 %, najhorší 71.4 %
- najdlhšia séria strát: medián 8, 95. percentil 11 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **78** na obchod pri účte 10 000

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
<!-- POSUDOK cisla=c89ed299 -->

**0. Vzťah k ORB.**
ORBNet je prepis `orb` do C#, nie nová stratégia: päť referenčných okien dalo **ten istý počet
obchodov, PnL, winrate aj break-even** ako checkup `orb` z 2026-09-10 (129/123/131/132/133 obchodov,
+0.57/+2.42/−8.23/+8.41/+13.70 %). Iný max DD a sigma sú rozdiel verzie reportu a náhodných vstupov
v teste proti náhode, nie stratégie — bar po bare a obchod po obchode je zhoda overená
([merania/PARITA_orbnet_2026-09-24.md](../../../../docs/merania/PARITA_orbnet_2026-09-24.md)).
Všetko, čo platí o edge ORB, platí preto aj tu; posudok nižšie je posudok ORB.

**1. Na čo sa to hodí a na čo nie.**
Na `NAS100` 15m v newyorskej seanse. Nižšie timeframy dali na ORB profit factor okolo 1,
krypto nemá „otvorenie seansy" (24/7) a londýnska seansa na NAS100 je stratová. Pridaná hodnota
ORBNet je platforma: tá istá logika beží natívne v NinjaTraderi 8 na futures (MNQ/NQ), kde
risk-based sizing s point value inštrumentu funguje; na nástrojoch s veľkou hodnotou bodu
(CL, GC) minimálny kontrakt prebije riziko.

**2. Má to potenciál?**
Za javom hovorí zisk v 4 z 5 okien, 648 obchodov a edge, ktorý v poslednom období neslabne
(76. percentil). Proti hovorí podstatnejšie: **+1.2 sigma proti náhode je náznak, nie dôkaz**
a break-even pri nulovom poplatku je rádovo spread NAS100 CFD. Pri reálnom náklade je edge
zjedený. Winrate po rokoch (48.8 → 57.1 %) skôr ukazuje závislosť na režime než zlepšovanie.

**3. Čo treba dorobiť.**
Náklad trhu (`half_spread_ticks` inštrumentu), kalendár skrátených seáns a filter režimu.
Každá zmena logiky ide do `orb` aj do `csharp/…/OrbNet` naraz a musí prejsť paritou
(`tester/tests/test_csharp_parity_orb.py`).

**4. Čo otestovať ďalej.**
- Strategy Analyzer v NinjaTraderi na MNQ s exportom signálov a
  `python -m tester.ninjatrader compare --strategy orbnet …` — overí adaptér vrátane
  `entryMode=stop` (stop-market vstup, ktorý IBSNet nepoužíva).
- `cli run --engine freqtrade` a checkup s reálnym poplatkom — rozhodne, či edge prežije náklad.
- `cli hyperopt --strategy orbnet --param rrRatio=1.0:2.0:0.1 --param slRangePct=10:60:5`
  s overením na ďalších oknách.

**5. Je to použiteľné, alebo je to o ničom?**
**Ako samostatná obchodná stratégia nie** — z rovnakého dôvodu ako ORB: break-even na úrovni
spreadu a +1.2 sigma. **Ako technický výsledok áno**: druhá stratégia s C# jadrom, overená
na rovnosť proti Python predlohe, a referenčný breakout na porovnávanie v NinjaTraderi.

**6. Čo by som pridal.**
Overnight gap ako filter smeru: prerazenie rangu proti nevyplnenej medzere je slabšie než
prerazenie k nej. Je to nezávislý zdroj informácie, nie ďalšie ladenie tých istých prahov.

<!-- POSUDOK KONIEC -->
