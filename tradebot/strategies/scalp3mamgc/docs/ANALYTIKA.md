# Základná analytika — Scalping 3MA (MGC) (`scalp3mamgc`)

Zmerané 2026-10-26 na `MGC/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/scalp3mamgc/configs/WK_scalp3ma_MGC_156obch_WR40_R2_0.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy scalp3mamgc \
   --profile tradebot/strategies/scalp3mamgc/configs/WK_scalp3ma_MGC_156obch_WR40_R2_0.json \
   --pair MGC/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 671 obchodov spolu — na štatistiku dosť
- break-even 0.0125 % je nad poplatkom 0.0018 % (rezerva +0.0107 bodu)
- edge nad poplatkom v 99 % bootstrapových vzoriek
- drawdown drží: 95. percentil 4.6 %
- odlíšiteľná od náhody (+2.2 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 47. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- _nič, čo by vyčnievalo_

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 164 | +1.92 | 0.0095 | 2.4 | 36.0 | +6/-11 | `20261026-132400-f6dacb` |
| 20221001-20231001 | 158 | +2.88 | 0.0135 | 1.9 | 38.6 | +4/-10 | `20261026-132406-30982e` |
| 20231001-20241001 | 168 | +1.91 | 0.0090 | 1.8 | 38.1 | +6/-11 | `20261026-132412-b1b5f1` |
| 20240904-20250904 | 140 | +2.84 | 0.0164 | 1.0 | 39.3 | +4/-7 | `20261026-132418-a25550` |
| 20250904-20260904 | 50 | +1.14 | 0.0174 | 1.2 | 40.0 | +5/-6 | `20261026-132424-05690b` |

Zisková v **5 z 5** okien, obchodov spolu 671, break-even celkom 0.0125 %. Okná sa prekrývajú, 9 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.29 ATR za 5 barov)
- medián držania 16.7 barov grafu
- winrate 38.15 %, payoff 1.967
- 0.38 obchodov za deň
- šikmosť výnosov +0.614

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 61.8 %, `take_profit` 38.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0075 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Hodina vstupu (UTC)** (riadi `tradeStartH`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 14 h – 15 h | 241 | 35.9 % | 32.4 | -0.0014 | 0.0200 | +0.0075 |
| do 14 h | 351 | 52.3 % | 40.7 | 0.0196 | 0.0052 | -0.0073 |
| nad 15 h | 79 | 11.8 % | 44.3 | 0.0215 | 0.0110 | -0.0015 |

**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 359 | 53.5 % | 35.6 | 0.0067 | 0.0187 | +0.0062 |
| short | 312 | 46.5 % | 41.0 | 0.0187 | 0.0067 | -0.0058 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.651 – 0.7732 | 168 | 25.0 % | 32.1 | -0.0034 | 0.0182 | +0.0057 |
| nad 0.8675 | 167 | 24.9 % | 34.7 | 0.0062 | 0.0142 | +0.0017 |
| do 0.651 | 168 | 25.0 % | 42.9 | 0.0204 | 0.0094 | -0.0031 |
| 0.7732 – 0.8675 | 168 | 25.0 % | 42.9 | 0.0258 | 0.0082 | -0.0043 |

Parametre, ktorými sa dá s tým niečo spraviť: `requireMaOrder`, `rrRatio`, `rsiExit`, `slAtr`, `tradeDirection`, `tradeStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0127 % | 0.0002 % ± 0.0055 | +2.25 | 98.8 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0127 % | -0.0001 % ± 0.0057 | +2.23 | 99.0 |

Edge je odlisitelny od nahody (2.2 sigma, percentil 98.8).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 195 | 13.3 | 34.9 | 0.0061 | 24 |
| 2022-12 - 2024-03 | 212 | 14.4 | 40.1 | 0.0155 | 64 |
| 2024-03 - 2025-06 | 175 | 11.9 | 39.4 | 0.0168 | 68 |
| 2025-06 - 2026-08 | 89 | 6.1 | 38.2 | 0.0113 | 47 |

Hranice pre úsek veľkosti posledného obdobia: -0.0079 až +0.0334 % (medián 0.0124).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 47. percentile, teda v medziach -0.0079 až +0.0334 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je. Signálov pritom ubudlo: z 13.28 na 6.06 obchodov za mesiac. To je úpadok tiež, len v break-evene ho vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2022-05-16T13:42 až 2022-05-25T15:50, spolu +844.66, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-05-16T13:42 | 2022-05-16T14:29 | +132.73 | +0.37 | `take_profit` |
| 2 | 2022-05-16T14:51 | 2022-05-16T18:55 | +138.73 | +0.38 | `take_profit` |
| 3 | 2022-05-17T13:57 | 2022-05-17T18:13 | +150.72 | +0.41 | `take_profit` |
| 4 | 2022-05-24T13:30 | 2022-05-24T13:38 | +129.39 | +0.17 | `take_profit` |
| 5 | 2022-05-24T14:18 | 2022-05-24T15:23 | +166.04 | +0.30 | `take_profit` |
| 6 | 2022-05-25T14:18 | 2022-05-25T15:50 | +127.06 | +0.23 | `take_profit` |

**Straty za sebou: 11** — 2022-07-22T16:00 až 2022-09-05T16:37, spolu -899.95, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-07-22T16:00 | 2022-07-22T17:00 | -79.82 | -0.15 | `stop_loss` |
| 2 | 2022-07-28T14:06 | 2022-07-28T14:21 | -50.62 | -0.29 | `stop_loss` |
| 3 | 2022-08-03T13:18 | 2022-08-03T13:31 | -64.88 | -0.12 | `stop_loss` |
| 4 | 2022-08-03T15:42 | 2022-08-03T16:18 | -57.25 | -0.16 | `stop_loss` |
| 5 | 2022-08-08T15:21 | 2022-08-09T01:20 | -85.90 | -0.16 | `stop_loss` |
| 6 | 2022-08-09T13:27 | 2022-08-09T14:06 | -71.27 | -0.20 | `stop_loss` |
| 7 | 2022-08-11T14:24 | 2022-08-11T14:33 | -94.91 | -0.17 | `stop_loss` |
| 8 | 2022-08-16T14:09 | 2022-08-16T14:48 | -94.89 | -0.18 | `stop_loss` |
| 9 | 2022-08-16T15:45 | 2022-08-16T16:43 | -82.51 | -0.12 | `stop_loss` |
| 10 | 2022-08-25T14:18 | 2022-08-25T17:01 | -91.86 | -0.17 | `stop_loss` |
| 11 | 2022-09-05T15:36 | 2022-09-05T16:37 | -126.04 | -0.07 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0125 %**, medián 0.0126 %, 90 % interval 0.0049–0.0202 %
- P(edge > poplatok) = **99.1 %**
- max drawdown: medián 2.6 %, 95. percentil 4.6 %, najhorší 10.2 %
- najdlhšia séria strát: medián 12, 95. percentil 17 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **712** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=efe85833 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „WK_scalp3ma_MGC_156obch_WR40_R2_0“ (víkendové hľadanie: RR 2, SL 2 ATR,
riziko 100 $), MGC 3m. Prvý checkup bežal omylom na predvolenom 15m (2 z 5 okien, −1,4 σ); profil bol nájdený na 3m,
čísla vyššie sú z 3m._

1. **Na čo sa to hodí a na čo nie.** Na mikro zlato (MGC) 3m, jeden kontrakt, aj malý účet: 95. percentil drawdownu
   4,6 % zo 60 000 $, ~0,38 obchodu denne, winrate 38 % pri payoffe 1,97 — séria 11–17 strát je normálna. Nehodí sa
   tam, kde poplatok so sklzom presiahne ~0,01 % na stranu: break-even 0,0125 % má nad poplatkom rezervu len 0,011 bodu,
   takže pri 3m skalpovaní rozhoduje exekúcia. Na iný trh sa nastavenie neprenáša — scalp3ma na MNQ 5m je na nule.
2. **Má to potenciál?** Áno, skromný. Za: 5 z 5 okien v pluse (break-even 0,0095–0,0174 %), +2,2 σ proti náhode,
   99 % bootstrapových vzoriek nad poplatkom a žiadna skupina obchodov nevyčnieva. Proti: profil vzišiel z víkendového
   hľadania cez mnoho kombinácií a 2,2 σ je na hranici toho, čo výber z mnohých vyrobí sám.
3. **Čo treba dorobiť.** Sizing. Okno 2025/26 má 50 obchodov, kým beh z 21. 10. s tým istým profilom
   (`20261021-101334-3b25d4`, zlomky kontraktu 0,65–1,19) mal 156; od januára 2026 sú to 1–3 obchody mesačne. Príčina
   nie je edge, ale strop straty (N-LIVE-20): pri 100 $ riziku a stope 2 ATR je stop na 1 MGC pri dnešnej volatilite
   zlata drahší než 100 $ a obchod vypadne. Treba rozhodnúť riziko (200–300 $, Monte Carlo pripúšťa do 712 $), alebo
   `legacyPineSizing` (1 kontrakt) a väčšiu stratu na obchode — inak stratégia naživo na zlate takmer neobchoduje.
4. **Čo otestovať ďalej.** `cli checkup --strategy scalp3mamgc --profile tradebot/strategies/scalp3mamgc/configs/WK_scalp3ma_MGC_156obch_WR40_R2_0.json --pair MGC/USD --timeframe 3m --set riskDollar=300`
   — vráti sa počet obchodov v 2026 a ostane break-even okolo 0,012 %? `--fee 3.51e-05` (2× poplatok) — break-even musí
   ostať nad ním. `cli matrix --pairs MGC/USD --timeframes 3m,5m` — ak 5m nedrží, je to vlastnosť TF z hľadania.
5. **Je to použiteľné?** Podmienečne áno: po vyriešení sizingu a po strese 2× poplatkom. V dnešnom nastavení by naživo
   obchodovala 1–3× mesačne.
6. **Čo by som pridal.** Stop s horným limitom v bodoch namiesto čistého 2 ATR (pri výbuchu volatility radšej vynechať
   než zväčšiť riziko) a vynechanie makro dní (CPI, FOMC), keď zlato preskakuje stopy.

<!-- POSUDOK KONIEC -->
