# Základná analytika — WILLIAMS %R LONG 1.0 (C# jadro) (`wprnet`)

Zmerané 2026-11-07 na `MNQ/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `PRESIEL_SMERNICAMI_WILLIAMS_R_MNQ_1`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy wprnet \
   --profile PRESIEL_SMERNICAMI_WILLIAMS_R_MNQ_1 \
   --pair MNQ/USD \
   --timeframe 1m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 894 obchodov spolu — na štatistiku dosť
- break-even 0.0083 % je nad poplatkom 0.0018 % (rezerva +0.0065 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 10.5 %
- odlíšiteľná od náhody (+2.1 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 60. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: protitrendová (mean reversion) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- 89.5 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 168 | +8.69 | 0.0110 | 2.1 | 67.9 | +11/-6 | `20261107-152657-d57096` |
| 20221001-20231001 | 161 | +5.16 | 0.0077 | 2.5 | 64.0 | +6/-5 | `20261107-152715-70ea39` |
| 20231001-20241001 | 197 | +6.10 | 0.0061 | 3.5 | 67.5 | +27/-3 | `20261107-152733-745ddc` |
| 20240904-20250904 | 200 | +7.20 | 0.0060 | 4.2 | 65.5 | +9/-3 | `20261107-152751-82e2be` |
| 20250904-20260904 | 177 | +18.44 | 0.0115 | 6.1 | 66.7 | +10/-4 | `20261107-152810-d48380` |

Zisková v **5 z 5** okien, obchodov spolu 894, break-even celkom 0.0083 %. Okná sa prekrývajú, 9 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota dobrá)

- vstup proti poslednému pohybu (-1.61 ATR za 5 barov)
- medián držania 17 barov grafu
- winrate 66.33 %, payoff 0.709
- 0.5 obchodov za deň
- šikmosť výnosov +5.299

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `session_end` 89.5 %, `stop_loss` 10.4 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0053 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 794 | 88.8 % | 66.0 | 0.0077 | 0.0136 | +0.0053 |
| NFP | 29 | 3.2 % | 62.1 | 0.0107 | 0.0082 | -0.0001 |
| CPI | 39 | 4.4 % | 69.2 | 0.0124 | 0.0081 | -0.0002 |
| FOMC | 30 | 3.4 % | 73.3 | 0.0166 | 0.0080 | -0.0003 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 794 | 88.8 % | 66.0 | 0.0077 | 0.0136 | +0.0053 |
| po vyhlásení | 60 | 6.7 % | 70.0 | 0.0134 | 0.0080 | -0.0003 |
| pred vyhlásením | 40 | 4.5 % | 67.5 | 0.0138 | 0.0081 | -0.0002 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 4 h | 266 | 29.8 % | 65.0 | -0.0008 | 0.0122 | +0.0039 |
| 4 h – 11 h | 212 | 23.7 % | 63.7 | 0.0057 | 0.0091 | +0.0008 |
| 11 h – 18 h | 217 | 24.3 % | 70.0 | 0.0151 | 0.0061 | -0.0022 |
| nad 18 h | 199 | 22.3 % | 66.8 | 0.0159 | 0.0062 | -0.0021 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0083 % | 0.0012 % ± 0.0033 | +2.13 | 97.4 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0083 % | 0.0012 % ± 0.0033 | +2.13 | 97.4 |

Edge je odlisitelny od nahody (2.1 sigma, percentil 97.4).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 198 | 13.4 | 67.7 | 0.0096 | 67 |
| 2022-12 - 2024-03 | 237 | 16.1 | 66.2 | 0.0081 | 51 |
| 2024-03 - 2025-06 | 229 | 15.5 | 67.2 | 0.0070 | 44 |
| 2025-06 - 2026-09 | 230 | 15.6 | 64.3 | 0.0089 | 60 |

Hranice pre úsek veľkosti posledného obdobia: +0.0008 až +0.0181 % (medián 0.0075).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 60. percentile, teda v medziach +0.0008 až +0.0181 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 27** — 2023-10-31T18:25 až 2023-12-07T20:13, spolu +402.93.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-31T18:25 | 2023-10-31T18:37 | +21.99 | +0.08 | `session_end` |
| 2 | 2023-11-01T17:34 | 2023-11-01T17:41 | +45.48 | +0.16 | `session_end` |
| 3 | 2023-11-02T03:33 | 2023-11-02T03:48 | +2.46 | +0.01 | `session_end` |
| 4 | 2023-11-02T04:33 | 2023-11-02T05:12 | +4.96 | +0.02 | `session_end` |
| 5 | 2023-11-03T17:14 | 2023-11-03T17:32 | +16.93 | +0.06 | `session_end` |
| 6 | 2023-11-03T17:46 | 2023-11-03T17:54 | +33.94 | +0.11 | `session_end` |
| 7 | 2023-11-06T11:29 | 2023-11-06T11:41 | +17.93 | +0.06 | `session_end` |
| 8 | 2023-11-07T17:04 | 2023-11-07T17:23 | +11.92 | +0.04 | `session_end` |
| 9 | 2023-11-10T16:32 | 2023-11-10T16:44 | +20.92 | +0.07 | `session_end` |
| 10 | 2023-11-10T21:52 | 2023-11-12T23:00 | +22.91 | +0.07 | `session_end` |
| 11 | 2023-11-13T19:53 | 2023-11-13T20:20 | +12.41 | +0.04 | `session_end` |
| 12 | 2023-11-14T04:10 | 2023-11-14T04:21 | +6.41 | +0.02 | `session_end` |
| 13 | 2023-11-15T02:08 | 2023-11-15T02:16 | +10.88 | +0.03 | `session_end` |
| 14 | 2023-11-17T00:17 | 2023-11-17T00:31 | +1.88 | +0.01 | `session_end` |
| 15 | 2023-11-17T12:59 | 2023-11-17T13:04 | +24.38 | +0.08 | `session_end` |
| 16 | 2023-11-17T18:52 | 2023-11-17T18:59 | +28.88 | +0.09 | `session_end` |
| 17 | 2023-11-17T19:41 | 2023-11-17T19:58 | +15.38 | +0.05 | `session_end` |
| 18 | 2023-11-21T02:28 | 2023-11-21T02:37 | +5.87 | +0.02 | `session_end` |
| 19 | 2023-11-23T09:06 | 2023-11-23T09:29 | +13.87 | +0.04 | `session_end` |
| 20 | 2023-11-27T11:18 | 2023-11-27T11:32 | +5.88 | +0.02 | `session_end` |
| 21 | 2023-12-01T18:31 | 2023-12-01T18:51 | +3.88 | +0.01 | `session_end` |
| 22 | 2023-12-04T23:35 | 2023-12-04T23:56 | +2.89 | +0.01 | `session_end` |
| 23 | 2023-12-06T02:23 | 2023-12-06T02:39 | +6.88 | +0.02 | `session_end` |
| 24 | 2023-12-06T04:23 | 2023-12-06T04:51 | +6.38 | +0.02 | `session_end` |
| 25 | 2023-12-07T11:16 | 2023-12-07T11:18 | +13.89 | +0.04 | `session_end` |
| 26 | 2023-12-07T17:45 | 2023-12-07T17:55 | +26.87 | +0.08 | `session_end` |
| 27 | 2023-12-07T19:45 | 2023-12-07T20:13 | +16.87 | +0.05 | `session_end` |

**Straty za sebou: 6** — 2022-08-12T10:03 až 2022-09-06T02:09, spolu -197.87.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-08-12T10:03 | 2022-08-12T10:31 | -10.94 | -0.04 | `session_end` |
| 2 | 2022-08-25T15:01 | 2022-08-25T15:14 | -52.42 | -0.20 | `stop_loss` |
| 3 | 2022-08-26T03:50 | 2022-08-26T04:26 | -9.92 | -0.04 | `session_end` |
| 4 | 2022-08-30T01:42 | 2022-08-30T02:17 | -53.88 | -0.22 | `stop_loss` |
| 5 | 2022-09-05T23:05 | 2022-09-05T23:39 | -14.35 | -0.06 | `session_end` |
| 6 | 2022-09-06T01:42 | 2022-09-06T02:09 | -56.36 | -0.23 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0083 %**, medián 0.0081 %, 90 % interval 0.0043–0.0128 %
- P(edge > poplatok) = **99.8 %**
- max drawdown: medián 5.6 %, 95. percentil 10.5 %, najhorší 25.5 %
- najdlhšia séria strát: medián 6, 95. percentil 7 obchodov
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
<!-- POSUDOK cisla=cd2a1d7b -->

**Posudok (7. 11. 2026, C# jadro Williams %R Long, profil PRESIEL_SMERNICAMI_WILLIAMS_R_MNQ_1, MNQ 1m, 1 kontrakt.)**

1. **Na čo sa hodí a na čo nie.** Krátkodobý návrat k priemeru na Nasdaq futures (MNQ / NQ), len long, 1m graf s filtrom trendu (len v smere EMA) a limitkou — jediná rangeová stratégia triedy A. Nie na silný medvedí trh bez filtra trendu.
2. **Má potenciál?** Áno, ale tenký: zisková v 5 z 5 okien, 894 obchodov, +2,1 sigma proti náhode, prepad drží (95. percentil 10,5 %), edge v poslednom období na 60. percentile. Break-even 0,0083 % je len ~4,6× poplatok — citlivé na sklz; Sortino 1,28 je pod hranicou 2 (preto červené S).
3. **Čo dorobiť.** Pravidlo vypnutia naživo; pri 1m a limitke sledovať naživo, koľko limitiek sa naozaj vyplní (emulátor plní pri dotyku).
4. **Čo otestovať ďalej.** Forward test na deme 4–8 týždňov (`wprnet`), kvalita plnenia na karte Live; krok 9 s 1 tickom sklzu navyše.
5. **Použiteľné?** Áno ako rangeový doplnok portfólia (nekorelovaný s trendovými Nasdaq stratégiami), s menšou veľkosťou — C# jadro sedí s Pythonom bar po bare na všetkých 4 profiloch (`test_csharp_parity_wpr.py`).
6. **Čo by som pridal.** Výstup na %R −50 a vstup len nad dennou EMA 200 (Connorsova úprava), aby sa zdvihol pomer zisku k strate.

<!-- POSUDOK KONIEC -->
