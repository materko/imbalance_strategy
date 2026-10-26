# Základná analytika — SD ZÓNY EURUSD (C# jadro) (`sdeurnet`)

Zmerané 2026-10-26 na `6E/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `eurusd_6e_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sdeurnet \
   --profile eurusd_6e_5m \
   --pair 6E/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 828 obchodov spolu — na štatistiku dosť
- break-even 0.0032 % je nad poplatkom 0.0018 % (rezerva +0.0014 bodu)
- odlíšiteľná od náhody (+2.3 sigma proti náhodnému vstupu)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20240904-20250904, 20250904-20260904 v strate)
- edge nad poplatkom len v 70 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 74.6 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 31.1 % pri riziku, s akým beh bežal
- POZOR NA TREND: každé z 4 období je horšie než predchádzajúce (sklon -0.0035 na obdobie). Posledné je ešte v medziach (18. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 154 | +47.84 | 0.0079 | 49.4 | 44.8 | +5/-6 | `20261026-105513-ee555c` |
| 20221001-20231001 | 181 | +39.95 | 0.0063 | 30.3 | 43.6 | +5/-7 | `20261026-105519-2d6483` |
| 20231001-20241001 | 169 | +3.30 | 0.0020 | 35.5 | 42.0 | +5/-9 | `20261026-105534-3abeaa` |
| 20240904-20250904 | 157 | -1.11 | 0.0016 | 49.5 | 42.0 | +5/-11 | `20261026-105544-ddfc85` |
| 20250904-20260904 | 177 | -17.16 | 0.0000 | 47.9 | 40.7 | +6/-8 | `20261026-105556-9c27a1` |

Zisková v **3 z 5** okien, obchodov spolu 828, break-even celkom 0.0032 %. Okná sa prekrývajú, 10 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-1.83 ATR za 5 barov)
- medián držania 30.9 barov grafu
- winrate 42.63 %, payoff 1.394
- 0.46 obchodov za deň
- šikmosť výnosov +0.446

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `stop_loss` 56.2 %, `take_profit` 40.1 %, `session_end` 3.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0095 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.1184 % | 209 | 25.2 % | 32.1 | -0.0092 | 0.0127 | +0.0095 |
| 0.1565 % – 0.209 % | 207 | 25.0 % | 44.0 | 0.0086 | 0.0020 | -0.0012 |
| 0.1184 % – 0.1565 % | 206 | 24.9 % | 47.6 | 0.0131 | -0.0002 | -0.0034 |
| nad 0.209 % | 206 | 24.9 % | 47.1 | 0.0183 | 0.0012 | -0.0020 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 410 | 49.5 % | 41.0 | -0.0001 | 0.0065 | +0.0033 |
| short | 418 | 50.5 % | 44.3 | 0.0065 | -0.0001 | -0.0033 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.1071 | 208 | 25.1 % | 37.5 | -0.0063 | 0.0063 | +0.0031 |
| nad 0.5 | 201 | 24.3 % | 43.3 | 0.0031 | 0.0033 | +0.0001 |
| 0.3261 – 0.5 | 212 | 25.6 % | 43.9 | 0.0047 | 0.0027 | -0.0005 |
| 0.1071 – 0.3261 | 207 | 25.0 % | 45.9 | 0.0108 | 0.0006 | -0.0026 |

Parametre, ktorými sa dá s tým niečo spraviť: `entryEndH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0077 % | -0.0004 % ± 0.0035 | +2.34 | 98.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0077 % | -0.0001 % ± 0.0035 | +2.23 | 98.6 |

Edge je odlisitelny od nahody (2.3 sigma, percentil 98.7).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 195 | 13.2 | 45.1 | 0.0094 | 83 |
| 2022-12 - 2024-03 | 222 | 15.1 | 42.8 | 0.0039 | 55 |
| 2024-03 - 2025-06 | 192 | 13.0 | 43.2 | 0.0031 | 51 |
| 2025-06 - 2026-09 | 219 | 14.8 | 39.7 | -0.0021 | 18 |

Hranice pre úsek veľkosti posledného obdobia: -0.0063 až +0.0134 % (medián 0.0032).

**POZOR NA TREND** — každé z 4 období je horšie než predchádzajúce (sklon -0.0035 na obdobie). Posledné je ešte v medziach (18. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2026-06-24T06:09 až 2026-07-01T20:44, spolu +3549.85.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-06-24T06:09 | 2026-06-24T08:12 | +540.00 | +0.19 | `take_profit` |
| 2 | 2026-06-25T06:34 | 2026-06-25T08:31 | +566.24 | +0.13 | `take_profit` |
| 3 | 2026-06-25T14:05 | 2026-06-25T14:19 | +631.21 | +0.09 | `take_profit` |
| 4 | 2026-06-29T08:52 | 2026-06-29T14:36 | +639.96 | +0.22 | `take_profit` |
| 5 | 2026-06-30T08:00 | 2026-06-30T14:52 | +752.45 | +0.26 | `take_profit` |
| 6 | 2026-07-01T13:45 | 2026-07-01T20:44 | +419.99 | +0.29 | `take_profit` |

**Straty za sebou: 11** — 2023-09-26T07:35 až 2023-10-18T10:13, spolu -4673.60, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-09-26T07:35 | 2023-09-26T08:22 | -463.99 | -0.12 | `stop_loss` |
| 2 | 2023-09-28T07:10 | 2023-09-28T08:16 | -493.52 | -0.09 | `stop_loss` |
| 3 | 2023-10-02T07:58 | 2023-10-02T09:05 | -459.30 | -0.17 | `stop_loss` |
| 4 | 2023-10-03T10:59 | 2023-10-03T14:00 | -471.71 | -0.18 | `stop_loss` |
| 5 | 2023-10-04T07:18 | 2023-10-04T07:42 | -407.58 | -0.10 | `stop_loss` |
| 6 | 2023-10-05T08:07 | 2023-10-05T15:38 | -409.26 | -0.16 | `stop_loss` |
| 7 | 2023-10-06T07:30 | 2023-10-06T09:42 | -493.57 | -0.09 | `stop_loss` |
| 8 | 2023-10-10T07:57 | 2023-10-10T08:27 | -434.31 | -0.16 | `stop_loss` |
| 9 | 2023-10-13T07:26 | 2023-10-13T07:53 | -388.92 | -0.10 | `stop_loss` |
| 10 | 2023-10-17T07:38 | 2023-10-17T11:11 | -371.79 | -0.14 | `stop_loss` |
| 11 | 2023-10-18T07:00 | 2023-10-18T10:13 | -279.65 | -0.21 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0032 %**, medián 0.0033 %, 90 % interval -0.0017–0.0083 %
- P(edge > poplatok) = **69.5 %**
- max drawdown: medián 74.6 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 11, 95. percentil 16 obchodov
- pravdepodobnosť ruiny účtu: 31.1 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **47** na obchod pri účte 10 000

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
<!-- POSUDOK cisla=d4e7af8f -->

**Posudok východiskového profilu `eurusd_6e_5m` (26. 10. 2026, pred hľadaním podľa smernice).**

1. **Na čo sa hodí a na čo nie.** Euro FX futures 6E / M6E (alebo CFD EURUSD), graf 5m, zóny na 1 h a vstup len v Londýne. Pri riziku 500 $ na obchod a stope ~12–25 pipov je to na 6E zvyčajne 1–2 kontrakty; na účet 10 000 je to priveľa (ruina 31 %, drawdown 75 % v mediáne) — na malý účet patrí M6E alebo riziko ~50 $. Na indexy ani zlato sa nastavenia neprenášajú, aj keď sú prahy v ATR: čas vzniku a okno vstupu sú forexové.
2. **Má potenciál?** Slabý. Edge je odlíšiteľný od náhody (+2,3 sigma, 98,7. percentil) a break-even 0,0032 % je nad poplatkom, ale len o 0,0014 % a nad poplatkom je len v 70 % bootstrapových vzoriek. Rozhoduje znamienko po rokoch: 21/22 a 22/23 výrazne v zisku, 23/24 nula, posledné dva roky v strate, s klesajúcim radom štyroch období. Predbežný výskum (2011–2026, zóny bez pohľadu dopredu) ukázal to isté: 2011–2015 jasne v pluse, 2016–2020 v mínuse, 2021–2026 okolo nuly. Je to skôr vlastnosť režimu trhu než stabilný jav.
3. **Čo dorobiť.** Filter režimu (volatilita / trend dňa) — protitrendový vstup do zóny dostáva rany v trende; obchody s najužším stopom (do 0,12 %) sú stratové (WR 32 %), takže spodná hranica výšky zóny (`minZoneHeight`) je prvý kandidát. Stratégia drží len jednu pozíciu a jednu čakajúcu limitku na najbližšiu zónu — druhá zóna dotknutá počas obchodu sa minie bez obchodu.
4. **Čo otestovať ďalej.** Hľadanie podľa smernice (beží od 26. 10. 2026 cez hub a Mac mini): TF zóny 15–120 min, rýchlosť a veľkosť odchodu, výška zóny, okno vzniku a vstupu, hĺbka limitky, RR, filter trendu a volatility. Rozhodne odložený rok 2025/26, ktorý je pri východisku v strate — nastavenie, ktoré ho nezvládne, nejde ďalej. Potom krok 8 na Dukascopy EURUSD.
5. **Použiteľné?** V tejto podobe **nie** — 3 z 5 okien a posledné dva roky v strate. Ostáva otvorené len cez konkrétny test: hľadanie podľa smernice; keď do rána nenájde nastavenie s PF ≥ 1,3 na ladení a ≥ 1,2 na odloženom roku, myšlienku na 6E v tejto podobe odložiť.
6. **Čo by som pridal.** Zónu z vyššieho TF potvrdiť nižším: vstup až po odmietnutí (pin bar / imbalance na 5m pri dotyku) namiesto slepej limitky, a sila zóny podľa toho, či odchod zlomil štruktúru (BOS) — vo výskume bez pohľadu dopredu pomáhala väčšia výška zóny, nie samotná rýchlosť odchodu.

<!-- POSUDOK KONIEC -->
