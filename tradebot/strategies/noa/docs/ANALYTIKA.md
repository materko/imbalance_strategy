# Základná analytika — NOA 1.0 — Noise Area (Concretum) (`noa`)

Zmerané 2026-10-18 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/noa_PRESIEL_SMERNICAMI_NOA_1_0_1_2026-10-18.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy noa \
   --profile .nightsearch/checkup/noa_PRESIEL_SMERNICAMI_NOA_1_0_1_2026-10-18.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 752 obchodov spolu — na štatistiku dosť
- break-even 0.0429 % je nad poplatkom 0.0018 % (rezerva +0.0411 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 4.4 %
- odlíšiteľná od náhody (+5.0 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 19. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- 82.2 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 741 obchodov (98.5 %), bez nej by break-even bol o +0.1464 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 168 | +8.96 | 0.0432 | 1.2 | 41.1 | +5/-6 | `20261018-040448-d07a3a` |
| 20221001-20231001 | 166 | +5.39 | 0.0312 | 1.2 | 43.4 | +5/-6 | `20261018-040451-245d65` |
| 20231001-20241001 | 121 | +9.91 | 0.0562 | 1.1 | 38.8 | +3/-7 | `20261018-040454-b3bde2` |
| 20240904-20250904 | 140 | +15.46 | 0.0654 | 1.8 | 42.1 | +5/-6 | `20261018-040457-757550` |
| 20250904-20260904 | 157 | +9.65 | 0.0274 | 2.2 | 38.9 | +4/-8 | `20261018-040501-2fe31c` |

Zisková v **5 z 5** okien, obchodov spolu 752, break-even celkom 0.0429 %.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.00 ATR za 5 barov)
- medián držania 4.6 barov grafu
- winrate 40.96 %, payoff 2.684
- 0.42 obchodov za deň
- šikmosť výnosov +8.774

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 82.2 %, `stop_loss` 17.8 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 741 obchodov (98.5 %), break-even 0.0407 % oproti 0.0429 % celku. Bez nej by break-even bol 0.1893 % (+0.1464). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 741 | 98.5 % | 40.9 | 0.0407 | 0.1893 | +0.1464 |
| proti trendu | 11 | 1.5 % | 45.5 | 0.1893 | 0.0407 | -0.0022 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 655 | 87.1 % | 40.3 | 0.0360 | 0.0892 | +0.0463 |
| CPI | 34 | 4.5 % | 47.1 | 0.0474 | 0.0427 | -0.0002 |
| FOMC | 18 | 2.4 % | 44.4 | 0.0534 | 0.0426 | -0.0003 |
| NFP | 44 | 5.9 % | 45.5 | 0.1323 | 0.0368 | -0.0061 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 16 | 2.1 % | 37.5 | 0.0052 | 0.0436 | +0.0007 |
| bez udalosti | 655 | 87.1 % | 40.3 | 0.0360 | 0.0892 | +0.0463 |
| po vyhlásení | 81 | 10.8 % | 46.9 | 0.1037 | 0.0353 | -0.0076 |

Parametre, ktorými sa dá s tým niečo spraviť: `hardStopPct`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0409 % | 0.0018 % ± 0.0078 | +5.00 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0409 % | 0.0034 % ± 0.0084 | +4.46 | 100.0 |

Edge je odlisitelny od nahody (5.0 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 213 | 14.6 | 41.3 | 0.0443 | 59 |
| 2023-01 - 2024-03 | 182 | 12.5 | 39.6 | 0.0177 | 15 |
| 2024-03 - 2025-06 | 164 | 11.2 | 45.7 | 0.0977 | 96 |
| 2025-06 - 2026-09 | 193 | 13.2 | 37.8 | 0.0208 | 19 |

Hranice pre úsek veľkosti posledného obdobia: +0.0091 až +0.0885 % (medián 0.0367).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 19. percentile, teda v medziach +0.0091 až +0.0885 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2022-09-02T17:31 až 2022-09-07T19:55, spolu +380.69, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-09-02T17:31 | 2022-09-02T18:25 | +4.58 | +0.02 | `session_end` |
| 2 | 2022-09-02T19:00 | 2022-09-02T19:55 | +16.13 | +0.07 | `session_end` |
| 3 | 2022-09-06T17:19 | 2022-09-06T17:20 | +11.90 | +0.04 | `session_end` |
| 4 | 2022-09-07T16:57 | 2022-09-07T16:55 | +44.81 | +0.11 | `session_end` |
| 5 | 2022-09-07T18:17 | 2022-09-07T19:55 | +303.26 | +0.36 | `session_end` |

**Straty za sebou: 8** — 2026-03-27T14:00 až 2026-04-07T15:15, spolu -1126.92.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-03-27T14:00 | 2026-03-27T15:00 | -73.33 | -0.11 | `session_end` |
| 2 | 2026-03-27T15:23 | 2026-03-27T15:25 | -124.11 | -0.26 | `session_end` |
| 3 | 2026-03-31T14:37 | 2026-03-31T14:48 | -197.63 | -0.26 | `stop_loss` |
| 4 | 2026-03-31T15:20 | 2026-03-31T15:25 | -72.81 | -0.11 | `session_end` |
| 5 | 2026-04-02T13:45 | 2026-04-02T13:51 | -199.00 | -0.28 | `stop_loss` |
| 6 | 2026-04-06T14:02 | 2026-04-06T14:05 | -57.16 | -0.14 | `session_end` |
| 7 | 2026-04-07T14:16 | 2026-04-07T14:23 | -202.16 | -0.22 | `stop_loss` |
| 8 | 2026-04-07T15:11 | 2026-04-07T15:15 | -200.72 | -0.32 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0429 %**, medián 0.0418 %, 90 % interval 0.0234–0.0655 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 2.5 %, 95. percentil 4.4 %, najhorší 11.6 %
- najdlhšia séria strát: medián 9, 95. percentil 12 obchodov
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
<!-- POSUDOK cisla=08bf12d2 -->

_Posudok (Claude, 18. 10. 2026) — nastavenie „NOA 1“ (PREŠIEL SMERNICAMI č. 1): pásmo 15 dní × 1,245 s gapom, kontrola
každých 13 min, filter trendu EMA 70 na 50m, vstup limitkou 53 % sviečky späť po potvrdení IBS imbalance / pin bar._

1. **Na čo sa to hodí a na čo nie.** Na index futures Nasdaq (MNQ / NQ) a ich CFD počas newyorskej seansy, graf 5m,
   jeden obchod naraz. Drží aj na NAS100 (Dukascopy CFD, s poplatkom ~1 bod): 813 obchodov, PF 1,67, všetkých 5 rokov
   v pluse (1,71 / 1,62 / 1,54 / 2,23 / 1,31) — myšlienka teda nie je vlastnosť jedného zdroja dát. Nehodí sa na trhy
   bez výraznej seansy a otvorenia (krypto 24/7, FX) — pásmo šumu sa počíta od otvorenia 9:30 NY. Malý účet: na 1 MNQ
   je max. drawdown okolo 1 100–1 500 $ za rok (95. percentil Monte Carlo 4,4 % zo 60 000 $), séria strát 8–12 obchodov
   je normálna (winrate ~40 %). Webapp pri limitke a potvrdení prepočítava veľkosť na rovnaké riziko (zlomky kontraktu);
   s celým 1 kontraktom, ako sa obchoduje naživo, je PF po rokoch 1,88 / 1,75 / 1,76 / 2,14 / 1,53 — záver sa nemení.
2. **Má to potenciál?** Áno. Za javom hovorí: zisk v 5 z 5 okien, +5,0 sigma proti náhodnému vstupu, break-even
   0,043 % je 24× nad poplatkom a 100 % bootstrapových vzoriek je nad poplatkom; je to známa publikovaná anomália
   (Zarattini, Aziz, Barbon 2024) a drží aj na inom zdroji dát. Za vzorkou hovorí: nastavenie vzišlo z >10 000
   skúšaných kombinácií (preto smernica chcela na odloženom roku PF ≥ 1,3 — dostal 1,55, s 1 kontraktom 1,53),
   posledné obdobie je na 19. percentile (slabšie, ale v medziach) a rok 23/24 má len 117 obchodov.
3. **Čo treba dorobiť.** (a) Výstupy sú z 82 % „session_end“ — to sú zatvorenia na kontrolách cez VWAP / hranicu
   a o 16:00, nie chyba; v analytike by sa mali volať vlastným menom (výstup na kontrole), aby sa dali oddeliť od 16:00.
   (b) Sviatky a skrátené seansy (pred sviatkom zatvára trh o 13:00) — dnes sa pozícia zatvorí až na prvom bare ďalšieho
   dňa. (c) Vrstvy (limitka + potvrdenie) menia veľkosť na zlomky — pre živé nasadenie treba celé kontrakty.
   (d) C# port pre NinjaTrader / MT5 neexistuje; naživo dnes len cez TradingView (Pine) alebo Freqtrade.
4. **Čo otestovať ďalej.** Krok 9 smernice: forward test 4–8 týždňov na papierovom účte (TradingView Pine s týmito
   parametrami), každý týždeň obchod po obchode proti webapp — rozhodne, či sedia vstupy aj sklz. Doplnkovo:
   `cli run --strategy noa --profile PRESIEL_SMERNICAMI_NOA_1_0_1 --fee 3.51e-05` (2× poplatok; PF musí ostať > 1,0)
   a walk-forward (ladiť 2 roky, testovať 6 mesiacov) — rozhodne, či výber z 10 000 kombinácií nebol náhoda.
   `cli matrix --pairs all --timeframes 5m` na ES / S&P ukáže, či ide o vlastnosť trhu, alebo len Nasdaqu.
5. **Je to použiteľné?** Áno — prešla krokmi 1–8 smernice (naživo = história, ladenie, plató 80 %+, odložený rok,
   analytika, NAS100). Na ostrú prevádzku chýba len forward test (krok 9); dovtedy nie s reálnymi peniazmi.
6. **Čo by som pridal.** Filter dní podľa šírky pásma: v úzkom pásme (pokojné ráno) sú falošné úniky najdrahšie —
   neobchodovať, keď je σ pod svojím 20-dňovým priemerom. A obchody po makro správach (NFP, CPI, FOMC) majú
   2–3× lepší break-even než bežné dni — pri obmedzenom riziku by stálo za to zväčšiť veľkosť práve v tie dni.

<!-- POSUDOK KONIEC -->
