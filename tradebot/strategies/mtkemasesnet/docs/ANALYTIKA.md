# Základná analytika — MTK EMAS 1.0 ES (C# jadro) (`mtkemasesnet`)

Zmerané 2026-11-26 na `ES/USD` 1h, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/mtkemasesnet/configs/es_databento_1h.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy mtkemasesnet \
   --profile tradebot/strategies/mtkemasesnet/configs/es_databento_1h.json \
   --timeframe 1h \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- break-even 0.0872 % je nad poplatkom 0.0018 % (rezerva +0.0854 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- odlíšiteľná od náhody (+2.0 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 25. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- 95. percentil max drawdownu 57.0 % (namerané 25.5 % medián) — na účet to treba mať
- 27.3 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina '0.0587 – 0.1058' vlastnosti 'Trend alebo rozsah': 43 obchodov (25.0 %), bez nej by break-even bol o +0.0402 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 49 | +284.46 | 0.1328 | 12.0 | 36.7 | +3/-5 | `20261126-074307-60dacc` |
| 20221001-20231001 | 35 | +85.86 | 0.0585 | 24.9 | 37.1 | +3/-4 | `20261126-074310-3b830c` |
| 20231001-20241001 | 17 | +115.06 | 0.1112 | 11.7 | 35.3 | +2/-7 | `20261126-074313-503785` |
| 20240904-20250904 | 25 | +79.93 | 0.0727 | 23.5 | 36.0 | +3/-9 | `20261126-074316-86d323` |
| 20250904-20260904 | 47 | +154.66 | 0.0612 | 28.8 | 31.9 | +4/-9 | `20261126-074319-c62766` |

Zisková v **5 z 5** okien, obchodov spolu 172, break-even celkom 0.0872 %. Okná sa prekrývajú, 1 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.07 ATR za 5 barov)
- medián držania 3.3 barov grafu
- winrate 35.47 %, payoff 4.287
- 0.1 obchodov za deň
- šikmosť výnosov +2.236

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `trailing_stop` 43.6 %, `stop_loss` 28.5 %, `session_end` 27.3 %, `force_exit` 0.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '0.0587 – 0.1058' vlastnosti 'Trend alebo rozsah': 43 obchodov (25.0 %), break-even -0.0405 % oproti 0.0872 % celku. Bez nej by break-even bol 0.1274 % (+0.0402). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.0587 – 0.1058 | 43 | 25.0 % | 23.3 | -0.0405 | 0.1274 | +0.0402 |
| do 0.0587 | 44 | 25.6 % | 36.4 | 0.0884 | 0.0868 | -0.0004 |
| 0.1058 – 0.1743 | 43 | 25.0 % | 39.5 | 0.1136 | 0.0776 | -0.0096 |
| nad 0.1743 | 42 | 24.4 % | 42.9 | 0.1804 | 0.0562 | -0.0310 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.3258 % – 0.4274 % | 43 | 25.0 % | 30.2 | 0.0074 | 0.1090 | +0.0218 |
| nad 0.4274 % | 42 | 24.4 % | 30.9 | 0.0854 | 0.0875 | +0.0003 |
| 0.258 % – 0.3258 % | 43 | 25.0 % | 39.5 | 0.1087 | 0.0790 | -0.0082 |
| do 0.258 % | 44 | 25.6 % | 40.9 | 0.1181 | 0.0689 | -0.0183 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.015 – 1.168 | 43 | 25.0 % | 23.3 | 0.0339 | 0.1055 | +0.0183 |
| nad 1.168 | 42 | 24.4 % | 38.1 | 0.0409 | 0.0998 | +0.0126 |
| 0.844 – 1.015 | 43 | 25.0 % | 32.6 | 0.0618 | 0.0961 | +0.0089 |
| do 0.844 | 44 | 25.6 % | 47.7 | 0.1991 | 0.0459 | -0.0413 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0747 % | 0.0152 % ± 0.0293 | +2.03 | 97.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0747 % | 0.0152 % ± 0.0293 | +2.03 | 97.3 |

Edge je odlisitelny od nahody (2.0 sigma, percentil 97.3).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 60 | 4.1 | 35.0 | 0.1168 | 77 |
| 2022-12 - 2024-03 | 32 | 2.2 | 46.9 | 0.1284 | 77 |
| 2024-03 - 2025-06 | 30 | 2.0 | 30.0 | 0.0432 | 23 |
| 2025-06 - 2026-09 | 50 | 3.4 | 32.0 | 0.0583 | 25 |

Hranice pre úsek veľkosti posledného obdobia: +0.0192 až +0.1610 % (medián 0.0866).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 25. percentile, teda v medziach +0.0192 až +0.1610 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 4** — 2026-04-07T20:00 až 2026-07-07T14:11, spolu +41659.98.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-04-07T20:00 | 2026-04-08T14:55 | +20347.74 | +2.04 | `trailing_stop` |
| 2 | 2026-06-14T23:00 | 2026-06-16T20:15 | +8618.19 | +1.15 | `trailing_stop` |
| 3 | 2026-06-29T18:00 | 2026-07-01T07:10 | +3443.84 | +0.31 | `trailing_stop` |
| 4 | 2026-07-02T19:00 | 2026-07-07T14:11 | +9250.21 | +0.62 | `trailing_stop` |

**Straty za sebou: 9** — 2025-03-27T15:00 až 2025-04-23T01:37, spolu -25207.96, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-03-27T15:00 | 2025-03-27T15:32 | -4860.77 | -0.28 | `stop_loss` |
| 2 | 2025-04-14T08:00 | 2025-04-14T09:00 | -1194.17 | -0.22 | `session_end` |
| 3 | 2025-04-14T11:00 | 2025-04-14T11:00 | -1394.16 | -0.26 | `session_end` |
| 4 | 2025-04-14T13:00 | 2025-04-14T13:44 | -3544.17 | -0.65 | `stop_loss` |
| 5 | 2025-04-14T15:00 | 2025-04-14T15:28 | -3694.16 | -0.67 | `stop_loss` |
| 6 | 2025-04-14T19:00 | 2025-04-14T19:00 | -1819.13 | -0.33 | `session_end` |
| 7 | 2025-04-15T08:00 | 2025-04-15T08:00 | -1153.72 | -0.14 | `session_end` |
| 8 | 2025-04-15T14:00 | 2025-04-15T14:20 | -4153.71 | -0.51 | `stop_loss` |
| 9 | 2025-04-22T23:00 | 2025-04-23T01:37 | -3393.95 | -0.63 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0872 %**, medián 0.0861 %, 90 % interval 0.0498–0.1247 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 25.5 %, 95. percentil 57.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 9, 95. percentil 14 obchodov
- pravdepodobnosť ruiny účtu: 0.2 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 904** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=42d8c84a -->

1. **Na čo sa to hodí a na čo nie.** ES 1h (cena × RMA 200 + EMA 200, len longy): pomalé sledovanie trendu na 1h–4h, obchody trvajú dni, zisk robí
   pár veľkých pohybov (WR 20–35 %). Hodí sa ako **časť portfólia** viacerých trhov (MNQ, zlato, ES, MYM, BTC), nie ako
   samostatná stratégia — na jednom trhu je obchodov málo. Na CFD treba prirátať swap za držanie cez noc a víkend.
   Percentá v tabuľkách sú pri riziku 5 000 $ na obchod a účte 60 000 $ — rozhoduje PF a znamienko po rokoch.
2. **Má to potenciál?** Čísla: PF 2,36 (roky 1,66–6,99), 35 obchodov za rok, WR 35 %, zisková v 5 z 5 okien. Výhrada: pokles je s rizikom 5 000 $ na obchod pri účte 60 000 $ veľký (95. percentil 57 %) — veľkosť treba zmenšiť. Edge je teda skutočný,
   ale zväčša je to **zisk z rastu trhu** zachytený longami — rozhodne porovnanie s „kúp a drž“.
3. **Čo treba dorobiť.** Swap a spread CFD do nákladov; rolovanie futures (dáta nie sú upravené, štúdia áno);
   veľkosť pozície podľa portfólia (spoločné riziko všetkých trhov); výstup pri opačnom krížení sa v emulátore
   označuje ako „session_end“ (nie je to koniec seansy, len zatvorenie pri signáli).
4. **Čo otestovať ďalej.** Podľa iCloud SMERNICA_TREND_CFD: plató (`cli sweep` dĺžka priemeru ±20 %, stop 1–2 ATR,
   trailing ±1 ATR), porovnanie s kúp a drž v tom istom období, roky 2016–2019 (zlato, ES), iný trh s tým istým
   nastavením, 2× poplatok a vstup o sviečku neskôr. Ak plató drží a stratégia má lepší zisk / pokles než kúp a drž,
   ide do portfólia.
5. **Je to použiteľné, alebo je to o ničom?** Použiteľné ako trendový doplnok portfólia — ale až po kroku „kúp a drž“;
   samostatne na jednom trhu nie (málo obchodov, slabý test proti náhode).
6. **Čo by som pridal.** Režim trhu: obchodovať len keď je EMA 200 rastúca (sklon), a portfóliové obmedzenie —
   najviac 2–3 otvorené trhy naraz, aby korelované indexy (MNQ, ES, MYM) nezdvojnásobili riziko.

<!-- POSUDOK KONIEC -->
