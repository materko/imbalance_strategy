# Základná analytika — VWAP ADX Pullback (C# jadro) (`vwapadxnet`)

Zmerané 2026-10-26 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tester/profiles/SMERNICE_CS_VWAP_ADX_Pullback_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy vwapadxnet \
   --profile tester/profiles/SMERNICE_CS_VWAP_ADX_Pullback_1.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 842 obchodov spolu — na štatistiku dosť
- break-even 0.0243 % je nad poplatkom 0.0018 % (rezerva +0.0225 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 4.2 %
- odlíšiteľná od náhody (+4.4 sigma proti náhodnému vstupu)

## Kde má chyby

- POZOR NA TREND: každé z 4 období je horšie než predchádzajúce (sklon -0.0083 na obdobie). Posledné je ešte v medziach (23. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 718 obchodov (85.3 %), bez nej by break-even bol o +0.0165 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 156 | +5.60 | 0.0409 | 0.8 | 73.1 | +10/-3 | `20261026-130309-6ac13f` |
| 20221001-20231001 | 183 | +3.77 | 0.0251 | 1.4 | 68.3 | +8/-5 | `20261026-130315-51af7d` |
| 20231001-20241001 | 181 | +4.01 | 0.0201 | 1.2 | 65.8 | +11/-6 | `20261026-130321-6b88fb` |
| 20240904-20250904 | 179 | +6.99 | 0.0293 | 2.9 | 63.1 | +10/-5 | `20261026-130327-0469bf` |
| 20250904-20260904 | 158 | +2.91 | 0.0120 | 2.6 | 67.1 | +13/-5 | `20261026-130335-feb30d` |

Zisková v **5 z 5** okien, obchodov spolu 842, break-even celkom 0.0243 %. Okná sa prekrývajú, 15 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (-0.22 ATR za 5 barov)
- medián držania 8.7 barov grafu
- winrate 67.46 %, payoff 0.692
- 0.47 obchodov za deň
- šikmosť výnosov +2.998

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `take_profit` 67.7 %, `stop_loss` 32.2 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 718 obchodov (85.3 %), break-even 0.0214 % oproti 0.0243 % celku. Bez nej by break-even bol 0.0408 % (+0.0165). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 718 | 85.3 % | 67.8 | 0.0214 | 0.0408 | +0.0165 |
| proti trendu | 124 | 14.7 % | 65.3 | 0.0408 | 0.0214 | -0.0029 |

**Vzdialenosť stopu** (riadi `slBars`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.2242 % – 0.3938 % | 211 | 25.1 % | 65.9 | 0.0004 | 0.0328 | +0.0085 |
| do 0.2242 % | 211 | 25.1 % | 43.1 | 0.0024 | 0.0325 | +0.0082 |
| 0.3938 % – 0.5996 % | 210 | 24.9 % | 79.0 | 0.0289 | 0.0228 | -0.0015 |
| nad 0.5996 % | 210 | 24.9 % | 81.9 | 0.0742 | 0.0099 | -0.0144 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| CPI | 33 | 3.9 % | 60.6 | 0.0008 | 0.0252 | +0.0009 |
| žiadna | 725 | 86.1 % | 66.9 | 0.0233 | 0.0309 | +0.0066 |
| NFP | 33 | 3.9 % | 75.8 | 0.0412 | 0.0236 | -0.0007 |
| FOMC | 47 | 5.6 % | 74.5 | 0.0467 | 0.0232 | -0.0011 |

Parametre, ktorými sa dá s tým niečo spraviť: `adxMin`, `exitHHMM`, `orEndHHMM`, `slBars`, `tpBars`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0243 % | 0.0013 % ± 0.0052 | +4.41 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0243 % | 0.0021 % ± 0.0057 | +3.91 | 100.0 |

Edge je odlisitelny od nahody (4.4 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 193 | 13.1 | 74.1 | 0.0404 | 86 |
| 2022-12 - 2024-03 | 215 | 14.6 | 67.0 | 0.0284 | 68 |
| 2024-03 - 2025-06 | 233 | 15.8 | 63.1 | 0.0236 | 51 |
| 2025-06 - 2026-09 | 201 | 13.7 | 66.7 | 0.0145 | 23 |

Hranice pre úsek veľkosti posledného obdobia: +0.0045 až +0.0486 % (medián 0.0232).

**POZOR NA TREND** — každé z 4 období je horšie než predchádzajúce (sklon -0.0083 na obdobie). Posledné je ešte v medziach (23. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 13** — 2025-10-17T16:42 až 2025-11-10T15:25, spolu +696.68.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-10-17T16:42 | 2025-10-17T16:50 | +112.25 | +0.23 | `take_profit` |
| 2 | 2025-10-17T18:42 | 2025-10-17T19:11 | +85.24 | +0.17 | `take_profit` |
| 3 | 2025-10-20T14:00 | 2025-10-20T14:04 | +32.73 | +0.06 | `take_profit` |
| 4 | 2025-10-22T05:00 | 2025-10-22T06:42 | +29.22 | +0.06 | `take_profit` |
| 5 | 2025-10-23T14:12 | 2025-10-23T14:36 | +124.73 | +0.25 | `take_profit` |
| 6 | 2025-10-23T14:45 | 2025-10-23T14:47 | +50.73 | +0.10 | `take_profit` |
| 7 | 2025-10-27T18:36 | 2025-10-27T18:43 | +15.18 | +0.03 | `take_profit` |
| 8 | 2025-10-30T20:27 | 2025-10-30T20:28 | +7.17 | +0.01 | `take_profit` |
| 9 | 2025-10-30T20:30 | 2025-10-30T20:30 | +4.17 | +0.01 | `take_profit` |
| 10 | 2025-10-30T20:33 | 2025-10-30T20:33 | +37.17 | +0.07 | `take_profit` |
| 11 | 2025-10-30T20:36 | 2025-10-30T20:37 | +22.67 | +0.04 | `take_profit` |
| 12 | 2025-11-05T15:15 | 2025-11-05T15:28 | +134.70 | +0.26 | `take_profit` |
| 13 | 2025-11-10T15:21 | 2025-11-10T15:25 | +40.70 | +0.08 | `take_profit` |

**Straty za sebou: 6** — 2023-12-19T17:27 až 2023-12-22T19:03, spolu -187.67.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-12-19T17:27 | 2023-12-19T18:10 | -39.19 | -0.12 | `stop_loss` |
| 2 | 2023-12-20T06:00 | 2023-12-20T06:38 | -14.20 | -0.04 | `stop_loss` |
| 3 | 2023-12-20T16:33 | 2023-12-20T16:33 | -7.20 | -0.02 | `stop_loss` |
| 4 | 2023-12-20T16:36 | 2023-12-20T17:32 | -20.20 | -0.06 | `stop_loss` |
| 5 | 2023-12-22T15:06 | 2023-12-22T16:00 | -63.19 | -0.19 | `stop_loss` |
| 6 | 2023-12-22T18:39 | 2023-12-22T19:03 | -43.69 | -0.13 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0243 %**, medián 0.0241 %, 90 % interval 0.0139–0.0354 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 2.4 %, 95. percentil 4.2 %, najhorší 11.9 %
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
<!-- POSUDOK cisla=8bed61dd -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „VWAP ADX 1 C#“ (`SMERNICE_CS_VWAP_ADX_Pullback_1`, kópia PREŠIEL
SMERNICAMI č. 1): pullback k VWAP po 8:45 CT, ADX ≥ 25, stop 20 a cieľ 40 barov spätne, `useTimeExit` vypnuté
(drží do SL/TP, aj cez noc), 1 kontrakt (`legacyPineSizing`)._

1. **Na čo sa to hodí a na čo nie.** MNQ **3m** (posudok Python predlohy uvádza 1m omylom — meria sa 3m), pullback
   v trende s cieľom ~0,7 R (payoff 0,69, WR 67 %), medián držania 8,7 baru. Malý účet znesie: na 1 MNQ 95. percentil
   drawdownu 4,2 % zo 60 000 $, séria 6–8 strát je normálna (najhoršia 6 v dec. 2023, len −188 $ — straty sú malé).
   Výsledok na rok je skromný (+2,9 až +7,0 %), takže stratégia sa hodí skôr ako doplnok portfólia než samostatne.
2. **Má to potenciál?** Áno, ale tesne. Vstupy sú **obchod po obchode tie isté ako v Python predlohe** `vwapadx`
   (156/183/181/179/158 obchodov, rovnaký WR) — parita C# drží. Čísla v peniazoch sa líšia, lebo predloha (11. 10.)
   ešte rátala veľkosť z rizika a profil teraz obchoduje 1 kontrakt: break-even 0,0194 → **0,0243 %**, ale posledný rok
   0,0146 → 0,0120 %. 5 z 5 okien v zisku, +4,4 σ proti náhode, 100 % bootstrapu nad poplatkom, rezerva ~13× poplatok.
   Proti: break-even po obdobiach rad za radom klesá 0,040 → 0,028 → 0,024 → 0,015 % (posledné na 23. percentile) —
   najčistejší „slabnúci“ priebeh v rodine.
3. **Čo treba dorobiť.** 85 % obchodov je „s trendom“ a tie sú horšie (0,021 %) než protitrendové (bez nich 0,041 %) —
   prekvapenie pri stratégii, ktorá trend vyžaduje cez ADX; treba skontrolovať, či definícia trendu v analytike sedí
   s tým, čo stratégia považuje za trend, a či `adxMin` nevyberá skôr koniec pohybu. Rozhodnúť držanie cez noc —
   `useTimeExit` je vypnuté, takže 15:55 výstup sa neuplatní (pozri `vwapadxneteod`).
4. **Čo otestovať ďalej.** 2× poplatok a 1 tick sklzu (`--fee 3.51e-05`) — pri rezerve 0,022 bodu a posledného roku
   0,012 % to rozhodne. `cli sweep --strategy vwapadxnet --space "adxMin=15:40:5"` — ak lepšie vyjde nižší ADX, potvrdí
   sa, že prah vyberá neskoré vstupy. Matrix na ES (`cli matrix --pairs ES/USD --timeframes 3m`) — jav trhu, alebo Nasdaqu.
5. **Je to použiteľné?** Podmienečne — áno ako menší doplnok k ORB/NOA (iný typ vstupu, malé straty), len ak prejde
   stresom 2× poplatku a sklzu; samostatne pri slabnúcom edge nie.
6. **Čo by som pridal.** Filter volatility dňa (ATR dňa proti 20-dňovému priemeru) — slabé roky 22/23 a 23/24 boli
   pokojné, a cieľ 40 barov spätne v pokojnom trhu je príliš blízko na pokrytie nákladov.

<!-- POSUDOK KONIEC -->
