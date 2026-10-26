# Základná analytika — VWAP ORB 1.5 (C# jadro) (`vwaporbnet`)

Zmerané 2026-10-26 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tester/profiles/SMERNICE_CS_VWAP_ORB_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy vwaporbnet \
   --profile tester/profiles/SMERNICE_CS_VWAP_ORB_1.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 776 obchodov spolu — na štatistiku dosť
- break-even 0.0718 % je nad poplatkom 0.0018 % (rezerva +0.0700 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 8.0 %
- odlíšiteľná od náhody (+5.0 sigma proti náhodnému vstupu)

## Kde má chyby

- POZOR NA TREND: každé z 4 období je horšie než predchádzajúce (sklon -0.0203 na obdobie). Posledné je ešte v medziach (23. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'do 0.6343 %' vlastnosti 'Vzdialenosť stopu': 195 obchodov (25.1 %), bez nej by break-even bol o +0.0294 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 174 | +18.14 | 0.1140 | 3.2 | 76.4 | +11/-4 | `20261026-130024-bf9f3f` |
| 20221001-20231001 | 167 | +10.67 | 0.0744 | 2.1 | 73.7 | +15/-3 | `20261026-130032-2296f8` |
| 20231001-20241001 | 172 | +16.50 | 0.0815 | 1.8 | 77.3 | +9/-4 | `20261026-130040-6a8a4a` |
| 20240904-20250904 | 148 | +6.62 | 0.0333 | 4.8 | 66.9 | +14/-5 | `20261026-130048-f59f40` |
| 20250904-20260904 | 127 | +15.58 | 0.0706 | 6.3 | 71.7 | +12/-3 | `20261026-130056-e74937` |

Zisková v **5 z 5** okien, obchodov spolu 776, break-even celkom 0.0718 %. Okná sa prekrývajú, 12 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.44 ATR za 5 barov)
- medián držania 42.8 barov grafu
- winrate 73.32 %, payoff 0.562
- 0.43 obchodov za deň
- šikmosť výnosov -0.589

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 73.3 %, `stop_loss` 26.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 0.6343 %' vlastnosti 'Vzdialenosť stopu': 195 obchodov (25.1 %), break-even -0.0067 % oproti 0.0718 % celku. Bez nej by break-even bol 0.1012 % (+0.0294). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.6343 % | 195 | 25.1 % | 65.6 | -0.0067 | 0.1012 | +0.0294 |
| 0.9353 % – 1.3546 % | 194 | 25.0 % | 73.7 | 0.0560 | 0.0769 | +0.0051 |
| 0.6343 % – 0.9353 % | 194 | 25.0 % | 78.3 | 0.0680 | 0.0730 | +0.0012 |
| nad 1.3546 % | 193 | 24.9 % | 75.7 | 0.1860 | 0.0378 | -0.0340 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 16 – 23 | 187 | 24.1 % | 70.0 | 0.0210 | 0.0879 | +0.0161 |
| nad 23 | 187 | 24.1 % | 71.7 | 0.0540 | 0.0774 | +0.0056 |
| 8 – 16 | 204 | 26.3 % | 74.0 | 0.0900 | 0.0650 | -0.0068 |
| do 8 | 198 | 25.5 % | 77.3 | 0.1182 | 0.0564 | -0.0154 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.8171 – 0.9193 | 194 | 25.0 % | 72.2 | 0.0269 | 0.0864 | +0.0146 |
| do 0.8171 | 195 | 25.1 % | 71.8 | 0.0382 | 0.0828 | +0.0110 |
| 0.9193 – 0.9708 | 195 | 25.1 % | 72.3 | 0.0818 | 0.0683 | -0.0035 |
| nad 0.9708 | 192 | 24.7 % | 77.1 | 0.1385 | 0.0495 | -0.0223 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0718 % | -0.0023 % ± 0.0149 | +4.99 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0718 % | -0.0030 % ± 0.0142 | +5.26 | 100.0 |

Edge je odlisitelny od nahody (5.0 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 206 | 14.0 | 75.7 | 0.1123 | 87 |
| 2022-12 - 2024-03 | 204 | 13.9 | 76.0 | 0.0729 | 53 |
| 2024-03 - 2025-06 | 198 | 13.4 | 72.7 | 0.0718 | 52 |
| 2025-06 - 2026-08 | 168 | 11.4 | 67.9 | 0.0449 | 23 |

Hranice pre úsek veľkosti posledného obdobia: +0.0133 až +0.1348 % (medián 0.0722).

**POZOR NA TREND** — každé z 4 období je horšie než predchádzajúce (sklon -0.0203 na obdobie). Posledné je ešte v medziach (23. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 15** — 2023-06-01T15:03 až 2023-06-21T14:50, spolu +2075.41.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-06-01T15:03 | 2023-06-01T15:36 | +102.99 | +0.36 | `take_profit` |
| 2 | 2023-06-01T15:39 | 2023-06-01T16:20 | +138.49 | +0.48 | `take_profit` |
| 3 | 2023-06-01T16:21 | 2023-06-02T13:30 | +209.48 | +0.72 | `take_profit` |
| 4 | 2023-06-06T14:30 | 2023-06-06T14:49 | +61.48 | +0.21 | `take_profit` |
| 5 | 2023-06-06T14:51 | 2023-06-07T13:32 | +91.47 | +0.31 | `take_profit` |
| 6 | 2023-06-07T14:48 | 2023-06-07T16:22 | +183.99 | +0.63 | `take_profit` |
| 7 | 2023-06-07T16:24 | 2023-06-08T06:13 | +279.99 | +0.97 | `take_profit` |
| 8 | 2023-06-08T16:00 | 2023-06-09T13:30 | +168.48 | +0.58 | `take_profit` |
| 9 | 2023-06-12T19:21 | 2023-06-13T03:34 | +171.95 | +0.57 | `take_profit` |
| 10 | 2023-06-14T13:48 | 2023-06-14T14:05 | +43.44 | +0.14 | `take_profit` |
| 11 | 2023-06-14T14:06 | 2023-06-14T14:21 | +68.44 | +0.23 | `take_profit` |
| 12 | 2023-06-14T14:24 | 2023-06-14T15:23 | +88.43 | +0.29 | `take_profit` |
| 13 | 2023-06-15T14:09 | 2023-06-15T15:38 | +135.93 | +0.45 | `take_profit` |
| 14 | 2023-06-15T15:39 | 2023-06-15T18:55 | +208.42 | +0.68 | `take_profit` |
| 15 | 2023-06-21T14:33 | 2023-06-21T14:50 | +122.44 | +0.41 | `take_profit` |

**Straty za sebou: 5** — 2025-01-29T19:06 až 2025-02-03T15:24, spolu -1423.07.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-01-29T19:06 | 2025-01-30T01:14 | -376.51 | -0.88 | `stop_loss` |
| 2 | 2025-01-30T17:18 | 2025-01-30T20:02 | -261.52 | -0.61 | `stop_loss` |
| 3 | 2025-01-30T20:45 | 2025-01-30T21:30 | -268.52 | -0.62 | `stop_loss` |
| 4 | 2025-01-31T17:12 | 2025-01-31T18:34 | -277.03 | -0.63 | `stop_loss` |
| 5 | 2025-02-03T15:12 | 2025-02-03T15:24 | -239.49 | -0.57 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0718 %**, medián 0.0716 %, 90 % interval 0.0442–0.1007 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 4.6 %, 95. percentil 8.0 %, najhorší 17.6 %
- najdlhšia séria strát: medián 5, 95. percentil 6 obchodov
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
<!-- POSUDOK cisla=225633b3 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „VWAP ORB 1 C#“ (`SMERNICE_CS_VWAP_ORB_1`, kópia PREŠIEL SMERNICAMI č. 1):
range prvých 5 min po 9:30 NY, RR 0,5, bez trailingu a bez VWAP stopu/cieľa, `closeAtSessionEnd` vypnuté, 1 kontrakt
(`legacyPineSizing`)._

1. **Na čo sa to hodí a na čo nie.** MNQ 3m, prieraz otváracieho rozsahu NY s VWAP, scalp s cieľom 0,5 R (payoff 0,56,
   WR 73 %), medián držania ~43 barov — pozícia **môže ísť cez noc** (seansa sa nezatvára, napr. vstup 1. 6. 2023 16:21 →
   TP 2. 6. 13:30). Preto nepatrí na prop účet so zákazom držania cez noc — na ten je `vwaporbneteod`, ktorý vychádza
   výrazne slabšie. Účet: na 1 MNQ 95. percentil drawdownu 8,0 % zo 60 000 $, najhorší bootstrap 17,6 %; séria 5 strát
   po ~250–380 $ (jan./feb. 2025, spolu −1 423 $) je normálna.
2. **Má to potenciál?** Áno. C# jadro dáva **okno po okne to isté, čo Python predloha** `vwaporb` (174/167/172/148/127
   obchodov, +18,14/+10,67/+16,50/+6,62/+15,58 %) — parita drží aj po opravách N-CORE-1/2/3. 5 z 5 okien v zisku,
   +5,0 σ proti náhode (+5,3 σ v tých istých hodinách — edge je vo výbere vstupu), break-even 0,072 % je ~40× poplatok,
   100 % bootstrapu nad poplatkom. Proti: break-even po obdobiach klesá 0,112 → 0,073 → 0,072 → 0,045 % (posledné na
   23. percentile, ešte v norme) a obchodov ubúda (14 → 11 za mesiac) — sklon −0,020 na obdobie treba sledovať.
3. **Čo treba dorobiť.** Najslabšia štvrtina má stop do 0,63 % (WR 66 %, break-even −0,007 %) — chýba minimálna
   vzdialenosť stopu (v ATR alebo bodoch); bez nej by break-even bol 0,101 %. Rozhodnúť sa, či je držanie cez noc zámer:
   so stopom 0,6–1,4 % je gap cez noc menšie riziko než pri tesnom scalpe, ale v živom prevádzke cez NT8/MT5 to znamená
   bežiaci stroj a platnú maržu cez noc.
4. **Čo otestovať ďalej.** `cli run --strategy vwaporbnet --profile SMERNICE_CS_VWAP_ORB_1 --pair MNQ/USD --timeframe 3m
   --fee 3.51e-05` (2× poplatok) — rezerva je veľká, malo by ostať > 0,05 %. `cli sweep` s `minSlDistance`-typom filtra
   (ak sa doplní) — rozhodne, či tesné stopy sú vada vstupu alebo len šum. Forward 4–8 týždňov na Sim101 / MT5 deme
   proti webapp obchod po obchode (krok 9 smernice) — rozhodne o sklze na prieraze.
5. **Je to použiteľné?** Áno — najsilnejší z VWAP rodiny podľa rezervy na náklady; na živý účet po forward teste.
   Nie na prop účet so zákazom noci (tam `vwaporbneteod`).
6. **Čo by som pridal.** Filter šírky otváracieho rozsahu v ATR (tesné stopy = úzky rozsah = falošné prierazy) a denný
   limit dvoch strát — straty prichádzajú v zhlukoch po 4–5 v rade.

<!-- POSUDOK KONIEC -->
