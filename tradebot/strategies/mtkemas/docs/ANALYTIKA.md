# Základná analytika — MTK EMAS 1.0 (`mtkemas`)

Zmerané 2026-11-26 na `MNQ/USD` 4h, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/mtkemas/configs/mnq_databento_4h.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy mtkemas \
   --profile tradebot/strategies/mtkemas/configs/mnq_databento_4h.json \
   --timeframe 4h \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 203 obchodov spolu — na štatistiku dosť
- break-even 0.1334 % je nad poplatkom 0.0018 % (rezerva +0.1316 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- edge drží aj v poslednom období (2025-06 - 2026-09 na 39. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- 95. percentil max drawdownu 26.4 % (namerané 13.1 % medián) — na účet to treba mať
- proti náhode len +1.1 sigma: náznak, nie dôkaz
- 61.6 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'do 0.6891 %' vlastnosti 'Vzdialenosť stopu': 51 obchodov (25.1 %), bez nej by break-even bol o +0.0596 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 20 | +17.54 | 0.1408 | 7.8 | 45.0 | +3/-3 | `20261126-074208-33faf9` |
| 20221001-20231001 | 41 | +42.60 | 0.1654 | 15.3 | 34.1 | +4/-8 | `20261126-074211-bad44a` |
| 20231001-20241001 | 50 | +45.37 | 0.1033 | 13.4 | 26.0 | +2/-12 | `20261126-074214-34628c` |
| 20240904-20250904 | 51 | +43.87 | 0.1139 | 6.1 | 31.4 | +3/-7 | `20261126-074217-7baafd` |
| 20250904-20260904 | 44 | +48.59 | 0.1674 | 7.9 | 22.7 | +2/-10 | `20261126-074220-8871d9` |

Zisková v **5 z 5** okien, obchodov spolu 203, break-even celkom 0.1334 %. Okná sa prekrývajú, 3 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.44 ATR za 5 barov)
- medián držania 5 barov grafu
- winrate 30.05 %, payoff 4.818
- 0.11 obchodov za deň
- šikmosť výnosov +2.283

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 61.6 %, `trailing_stop` 19.2 %, `stop_loss` 18.7 %, `force_exit` 0.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 0.6891 %' vlastnosti 'Vzdialenosť stopu': 51 obchodov (25.1 %), break-even 0.0265 % oproti 0.1334 % celku. Bez nej by break-even bol 0.193 % (+0.0596). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.6891 % | 51 | 25.1 % | 27.4 | 0.0265 | 0.1930 | +0.0596 |
| nad 1.0723 % | 50 | 24.6 % | 30.0 | 0.0533 | 0.1477 | +0.0143 |
| 0.6891 % – 0.8651 % | 51 | 25.1 % | 25.5 | 0.1890 | 0.1125 | -0.0209 |
| 0.8651 % – 1.0723 % | 51 | 25.1 % | 37.2 | 0.2961 | 0.0884 | -0.0450 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.0493 – 0.1173 | 51 | 25.1 % | 17.6 | -0.0208 | 0.1811 | +0.0477 |
| nad 0.245 | 50 | 24.6 % | 34.0 | 0.0441 | 0.1703 | +0.0369 |
| 0.1173 – 0.245 | 51 | 25.1 % | 43.1 | 0.2549 | 0.0941 | -0.0393 |
| do 0.0493 | 51 | 25.1 % | 25.5 | 0.2781 | 0.0909 | -0.0425 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.9262 | 50 | 24.6 % | 34.0 | 0.0316 | 0.1746 | +0.0412 |
| 0.6049 – 0.7855 | 51 | 25.1 % | 25.5 | 0.1106 | 0.1402 | +0.0068 |
| do 0.6049 | 51 | 25.1 % | 23.5 | 0.1962 | 0.1160 | -0.0174 |
| 0.7855 – 0.9262 | 51 | 25.1 % | 37.2 | 0.2123 | 0.1050 | -0.0284 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.1330 % | 0.0557 % ± 0.0699 | +1.11 | 87.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.1330 % | 0.0653 % ± 0.0701 | +0.97 | 85.0 |

Naznak, ale nie dokaz (1.1 sigma, percentil 87.3). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 25 | 1.7 | 40.0 | 0.1131 | 46 |
| 2023-01 - 2024-03 | 61 | 4.2 | 34.4 | 0.1598 | 66 |
| 2024-03 - 2025-06 | 57 | 3.9 | 29.8 | 0.1345 | 51 |
| 2025-06 - 2026-09 | 60 | 4.1 | 21.7 | 0.1113 | 39 |

Hranice pre úsek veľkosti posledného obdobia: +0.0151 až +0.2607 % (medián 0.1329).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 39. percentile, teda v medziach +0.0151 až +0.2607 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 4** — 2023-05-15T08:00 až 2023-06-04T20:00, spolu +16561.51.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-05-15T08:00 | 2023-05-17T04:00 | +1051.11 | +0.36 | `session_end` |
| 2 | 2023-05-17T12:00 | 2023-05-23T08:00 | +8088.47 | +2.49 | `session_end` |
| 3 | 2023-05-25T12:00 | 2023-05-31T08:00 | +6540.06 | +2.93 | `session_end` |
| 4 | 2023-06-01T20:00 | 2023-06-04T20:00 | +881.87 | +0.44 | `session_end` |

**Straty za sebou: 12** — 2024-03-25T16:00 až 2024-05-17T18:05, spolu -10224.94.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-03-25T16:00 | 2024-03-26T16:00 | -1414.39 | -0.48 | `session_end` |
| 2 | 2024-04-01T00:00 | 2024-04-01T00:00 | -390.44 | -0.13 | `session_end` |
| 3 | 2024-04-01T08:00 | 2024-04-01T08:00 | -1001.73 | -0.30 | `session_end` |
| 4 | 2024-04-04T16:00 | 2024-04-04T18:15 | -1762.58 | -0.68 | `stop_loss` |
| 5 | 2024-04-09T00:00 | 2024-04-09T04:00 | -313.70 | -0.14 | `session_end` |
| 6 | 2024-04-09T12:00 | 2024-04-09T14:41 | -1895.48 | -0.74 | `stop_loss` |
| 7 | 2024-04-09T20:00 | 2024-04-10T12:30 | -1882.70 | -0.85 | `stop_loss` |
| 8 | 2024-04-11T16:00 | 2024-04-12T12:58 | -10.72 | -0.00 | `trailing_stop` |
| 9 | 2024-04-15T08:00 | 2024-04-15T12:00 | -835.68 | -0.38 | `session_end` |
| 10 | 2024-05-13T12:00 | 2024-05-13T12:00 | -536.64 | -0.13 | `session_end` |
| 11 | 2024-05-14T20:00 | 2024-05-15T04:00 | -160.13 | -0.05 | `session_end` |
| 12 | 2024-05-15T16:00 | 2024-05-17T18:05 | -20.75 | -0.01 | `trailing_stop` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.1334 %**, medián 0.1325 %, 90 % interval 0.0686–0.1980 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 13.1 %, 95. percentil 26.4 %, najhorší 66.9 %
- najdlhšia séria strát: medián 13, 95. percentil 21 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **2 066** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=d8aa9b64 -->

1. **Na čo sa to hodí a na čo nie.** MNQ 4h (cena × HMA 100 + EMA 200, len longy): pomalé sledovanie trendu na 1h–4h, obchody trvajú dni, zisk robí
   pár veľkých pohybov (WR 20–35 %). Hodí sa ako **časť portfólia** viacerých trhov (MNQ, zlato, ES, MYM, BTC), nie ako
   samostatná stratégia — na jednom trhu je obchodov málo. Na CFD treba prirátať swap za držanie cez noc a víkend.
   Percentá v tabuľkách sú pri riziku 2 000 $ na obchod a účte 60 000 $ — rozhoduje PF a znamienko po rokoch.
2. **Má to potenciál?** Čísla: PF 2,07 (roky 1,45–2,41), 42 obchodov za rok, WR 30 %, zisková v 5 z 5 okien. Výhrada: proti náhode len +1,1 sigma — výber vstupu pridáva málo; zisk ťahá hlavne trend Nasdaqu 2021–2026. Edge je teda skutočný,
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
