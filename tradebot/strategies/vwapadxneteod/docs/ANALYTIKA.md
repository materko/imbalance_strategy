# Základná analytika — VWAP ADX Pullback (C# jadro EOD) (`vwapadxneteod`)

Zmerané 2026-10-26 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tester/profiles/SMERNICE_CS_EOD_VWAP_ADX_Pullback_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy vwapadxneteod \
   --profile tester/profiles/SMERNICE_CS_EOD_VWAP_ADX_Pullback_1.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 776 obchodov spolu — na štatistiku dosť
- break-even 0.0208 % je nad poplatkom 0.0018 % (rezerva +0.0190 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 3.9 %
- odlíšiteľná od náhody (+4.8 sigma proti náhodnému vstupu)

## Kde má chyby

- POZOR NA TREND: každé z 4 období je horšie než predchádzajúce (sklon -0.0051 na obdobie). Posledné je ešte v medziach (34. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 671 obchodov (86.5 %), bez nej by break-even bol o +0.0220 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 146 | +3.45 | 0.0275 | 1.0 | 68.5 | +10/-3 | `20261026-130352-060f1f` |
| 20221001-20231001 | 172 | +2.93 | 0.0211 | 1.0 | 66.3 | +9/-5 | `20261026-130400-11ac94` |
| 20231001-20241001 | 168 | +2.70 | 0.0150 | 0.8 | 63.1 | +10/-6 | `20261026-130406-6946c9` |
| 20240904-20250904 | 161 | +5.14 | 0.0244 | 2.3 | 64.6 | +11/-5 | `20261026-130414-dc2a97` |
| 20250904-20260904 | 141 | +3.54 | 0.0157 | 1.8 | 66.0 | +11/-8 | `20261026-130422-d446a6` |

Zisková v **5 z 5** okien, obchodov spolu 776, break-even celkom 0.0208 %. Okná sa prekrývajú, 12 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (-0.22 ATR za 5 barov)
- medián držania 7.7 barov grafu
- winrate 65.72 %, payoff 0.734
- 0.43 obchodov za deň
- šikmosť výnosov -0.431

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `take_profit` 60.8 %, `stop_loss` 27.3 %, `session_end` 11.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 671 obchodov (86.5 %), break-even 0.0174 % oproti 0.0208 % celku. Bez nej by break-even bol 0.0428 % (+0.0220). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 671 | 86.5 % | 66.2 | 0.0174 | 0.0428 | +0.0220 |
| proti trendu | 105 | 13.5 % | 62.9 | 0.0428 | 0.0174 | -0.0034 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| CPI | 30 | 3.9 % | 53.3 | -0.0190 | 0.0224 | +0.0016 |
| žiadna | 664 | 85.6 % | 64.9 | 0.0189 | 0.0324 | +0.0116 |
| FOMC | 47 | 6.1 % | 72.3 | 0.0462 | 0.0194 | -0.0014 |
| NFP | 31 | 4.0 % | 83.9 | 0.0638 | 0.0189 | -0.0019 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 664 | 85.6 % | 64.9 | 0.0189 | 0.0324 | +0.0116 |
| po vyhlásení | 91 | 11.7 % | 70.3 | 0.0321 | 0.0193 | -0.0015 |
| pred vyhlásením | 21 | 2.7 % | 71.4 | 0.0342 | 0.0204 | -0.0004 |

Parametre, ktorými sa dá s tým niečo spraviť: `adxMin`, `exitHHMM`, `orEndHHMM`, `slBars`, `tpBars`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0208 % | 0.0007 % ± 0.0042 | +4.83 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0208 % | 0.0013 % ± 0.0046 | +4.25 | 100.0 |

Edge je odlisitelny od nahody (4.8 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 183 | 12.4 | 70.5 | 0.0325 | 87 |
| 2022-12 - 2024-03 | 200 | 13.6 | 65.0 | 0.0208 | 53 |
| 2024-03 - 2025-06 | 215 | 14.6 | 63.3 | 0.0192 | 45 |
| 2025-06 - 2026-09 | 178 | 12.1 | 64.6 | 0.0161 | 34 |

Hranice pre úsek veľkosti posledného obdobia: +0.0024 až +0.0398 % (medián 0.0206).

**POZOR NA TREND** — každé z 4 období je horšie než predchádzajúce (sklon -0.0051 na obdobie). Posledné je ešte v medziach (34. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 11** — 2025-02-13T18:36 až 2025-03-14T15:00, spolu +1238.93, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-02-13T18:36 | 2025-02-13T19:04 | +116.46 | +0.27 | `take_profit` |
| 2 | 2025-02-13T19:06 | 2025-02-13T19:06 | +16.95 | +0.04 | `take_profit` |
| 3 | 2025-02-14T15:21 | 2025-02-14T15:56 | +40.95 | +0.09 | `take_profit` |
| 4 | 2025-02-14T17:51 | 2025-02-14T18:11 | +64.94 | +0.15 | `take_profit` |
| 5 | 2025-02-28T18:45 | 2025-02-28T20:04 | +209.05 | +0.51 | `take_profit` |
| 6 | 2025-02-28T20:21 | 2025-02-28T20:28 | +77.04 | +0.19 | `take_profit` |
| 7 | 2025-03-06T15:27 | 2025-03-06T15:39 | +153.56 | +0.38 | `take_profit` |
| 8 | 2025-03-07T18:03 | 2025-03-07T18:05 | +159.09 | +0.40 | `take_profit` |
| 9 | 2025-03-11T13:57 | 2025-03-11T14:01 | +150.13 | +0.38 | `take_profit` |
| 10 | 2025-03-11T18:33 | 2025-03-11T18:41 | +67.13 | +0.17 | `take_profit` |
| 11 | 2025-03-14T14:39 | 2025-03-14T15:00 | +183.63 | +0.47 | `take_profit` |

**Straty za sebou: 8** — 2026-05-15T18:18 až 2026-05-26T15:36, spolu -834.71.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-05-15T18:18 | 2026-05-15T18:31 | -204.56 | -0.35 | `stop_loss` |
| 2 | 2026-05-20T16:00 | 2026-05-20T16:21 | -202.56 | -0.35 | `stop_loss` |
| 3 | 2026-05-21T18:03 | 2026-05-21T19:54 | -115.07 | -0.19 | `session_end` |
| 4 | 2026-05-25T14:09 | 2026-05-25T14:32 | -77.10 | -0.13 | `stop_loss` |
| 5 | 2026-05-25T15:18 | 2026-05-25T22:35 | -109.60 | -0.18 | `stop_loss` |
| 6 | 2026-05-26T15:24 | 2026-05-26T15:24 | -15.61 | -0.03 | `stop_loss` |
| 7 | 2026-05-26T15:27 | 2026-05-26T15:30 | -54.61 | -0.09 | `stop_loss` |
| 8 | 2026-05-26T15:36 | 2026-05-26T15:36 | -55.61 | -0.09 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0208 %**, medián 0.0208 %, 90 % interval 0.0119–0.0299 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 2.2 %, 95. percentil 3.9 %, najhorší 7.7 %
- najdlhšia séria strát: medián 7, 95. percentil 9 obchodov
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
<!-- POSUDOK cisla=4639369d -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „VWAP ADX 1 C# EOD“ (`SMERNICE_CS_EOD_VWAP_ADX_Pullback_1`): tie
isté parametre ako `vwapadxnet` (ADX ≥ 25, stop 20 / cieľ 40 barov, 1 kontrakt), navyše `EodCloseEngine` — všetko
zatvorené najneskôr o 15:59 NY (prop účty)._

1. **Na čo sa to hodí a na čo nie.** MNQ 3m na prop účte bez držania cez noc. Na rozdiel od ORB tu EOD stojí málo:
   break-even 0,0243 → **0,0208 %** (−14 %), 11,9 % obchodov končí o 15:59, obchodov je o 66 menej (pozícia z noci
   neblokuje ráno, ale ani nevzniknú neskoré vstupy). Drawdown je dokonca nižší (95. percentil 3,9 %, najhorší 7,7 %
   vs. 11,9 %) — odpadli straty cez noc. Pozor na sériu 8 strát (máj 2026, −835 $) — pri dennom limite prop výzvy
   je to rozložené na 7 dní, nie jeden.
2. **Má to potenciál?** Áno, rovnako tesne ako bez EOD: 5 z 5 okien v zisku (+3,45/+2,93/+2,70/+5,14/+3,54 %),
   +4,8 σ proti náhode (viac než bez EOD), 100 % bootstrapu nad poplatkom, rezerva ~11× poplatok. Slabnutie je miernejšie
   (0,033 → 0,021 → 0,019 → 0,016 %, posledné na 34. percentile), ale smer je ten istý.
3. **Čo treba dorobiť.** To isté ako `vwapadxnet`: overiť, prečo sú obchody „s trendom“ (86 %) horšie ako proti
   trendu (bez nich by break-even bol 0,043 %), a či `adxMin` nevyberá koniec pohybu. Pre prop: zapnúť `useTimeExit`
   s `exitHHMM` 1555 by dalo takmer to isté ako EOD obal — dve poistky proti sebe nevadia, ale jednu z nich treba
   v profile mať ako zámer, nie náhodou.
4. **Čo otestovať ďalej.** Prop simulácia (karta Prop / `/api/prop`) s pravidlami výzvy — pri +3 až +5 % ročne zo
   60 000 $ na 1 MNQ je otázka, či cieľ výzvy vôbec stihne v čase; rozhodne o počte kontraktov. 2× poplatok
   (`--fee 3.51e-05`) — rezerva 0,019 bodu je najmenšia v rodine.
5. **Je to použiteľné?** Podmienečne áno — ako prop variant je na tom lepšie ako `vwaporbneteod` v tom, čo EOD vezme
   (−14 % namiesto −57 %), ale absolútny edge je malý; samostatne na výzvu s cieľom 6–10 % na 1 kontrakte nestačí,
   ako doplnok k inej stratégii áno.
6. **Čo by som pridal.** Škálovanie veľkosti podľa ADX (silnejší trend = celý kontrakt, hraničný ADX 25–30 = žiadny
   obchod) — ak sa potvrdí, že slabé obchody sú pri hraničnom ADX, zvýši to edge bez nových parametrov vstupu.

<!-- POSUDOK KONIEC -->
