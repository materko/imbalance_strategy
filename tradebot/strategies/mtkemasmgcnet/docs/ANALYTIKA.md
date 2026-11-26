# Základná analytika — MTK EMAS 1.0 MGC (C# jadro) (`mtkemasmgcnet`)

Zmerané 2026-11-26 na `MGC/USD` 4h, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/mtkemasmgcnet/configs/mgc_databento_4h.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy mtkemasmgcnet \
   --profile tradebot/strategies/mtkemasmgcnet/configs/mgc_databento_4h.json \
   --timeframe 4h \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- break-even 0.2503 % je nad poplatkom 0.0018 % (rezerva +0.2485 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- edge drží aj v poslednom období (2025-01 - 2026-02 na 92. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- 95. percentil max drawdownu 39.1 % (namerané 16.8 % medián) — na účet to treba mať
- proti náhode len +0.8 sigma: náznak, nie dôkaz
- 54.1 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina '4 h – 12 h' vlastnosti 'Hodina vstupu (UTC)': 43 obchodov (29.1 %), bez nej by break-even bol o +0.1163 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 14 | +57.47 | 0.2630 | 5.9 | 28.6 | +1/-3 | `20261126-074227-487e52` |
| 20221001-20231001 | 21 | +28.16 | 0.1047 | 11.1 | 23.8 | +2/-7 | `20261126-074230-77ab6e` |
| 20231001-20241001 | 41 | +161.94 | 0.2829 | 5.0 | 21.9 | +2/-6 | `20261126-074233-b93ad0` |
| 20240904-20250904 | 49 | +33.98 | 0.0633 | 26.6 | 26.5 | +2/-10 | `20261126-074236-fe919d` |
| 20250904-20260904 | 25 | +156.70 | 0.8319 | 3.1 | 24.0 | +2/-6 | `20261126-074239-a56cfd` |

Zisková v **5 z 5** okien, obchodov spolu 148, break-even celkom 0.2503 %. Okná sa prekrývajú, 2 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.04 ATR za 5 barov)
- medián držania 4 barov grafu
- winrate 25 %, payoff 8.828
- 0.09 obchodov za deň
- šikmosť výnosov +4.559

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 54.1 %, `stop_loss` 34.5 %, `trailing_stop` 10.8 %, `force_exit` 0.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '4 h – 12 h' vlastnosti 'Hodina vstupu (UTC)': 43 obchodov (29.1 %), break-even -0.01 % oproti 0.2503 % celku. Bez nej by break-even bol 0.3666 % (+0.1163). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 4 h – 12 h | 43 | 29.1 % | 25.6 | -0.0100 | 0.3666 | +0.1163 |
| do 4 h | 39 | 26.4 % | 23.1 | 0.1035 | 0.2992 | +0.0489 |
| 12 h – 16 h | 45 | 30.4 % | 24.4 | 0.4200 | 0.1687 | -0.0816 |
| nad 16 h | 21 | 14.2 % | 28.6 | 0.7823 | 0.1801 | -0.0702 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.4437 % – 0.5232 % | 37 | 25.0 % | 18.9 | -0.0047 | 0.3502 | +0.0999 |
| nad 0.6866 % | 36 | 24.3 % | 22.2 | 0.2046 | 0.2574 | +0.0071 |
| do 0.4437 % | 38 | 25.7 % | 34.2 | 0.3807 | 0.1787 | -0.0716 |
| 0.5232 % – 0.6866 % | 37 | 25.0 % | 24.3 | 0.3890 | 0.2091 | -0.0412 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 6 | 38 | 25.7 % | 13.2 | -0.0138 | 0.3398 | +0.0895 |
| 6 – 15 | 38 | 25.7 % | 28.9 | 0.2662 | 0.2455 | -0.0048 |
| 15 – 25 | 38 | 25.7 % | 34.2 | 0.3551 | 0.2094 | -0.0409 |
| nad 25 | 34 | 23.0 % | 23.5 | 0.3940 | 0.2061 | -0.0442 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.2332 % | 0.1573 % ± 0.1013 | +0.75 | 78.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.2332 % | 0.1637 % ± 0.1066 | +0.65 | 75.0 |

Neodlisitelne od nahody (+0.8 sigma, percentil 78.0). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-11 | 15 | 1.2 | 33.3 | 0.2924 | 58 |
| 2022-11 - 2023-12 | 31 | 2.4 | 19.4 | 0.1412 | 36 |
| 2023-12 - 2025-01 | 48 | 3.7 | 20.8 | 0.1592 | 29 |
| 2025-01 - 2026-02 | 54 | 4.2 | 29.6 | 0.4472 | 92 |

Hranice pre úsek veľkosti posledného obdobia: +0.0218 až +0.4897 % (medián 0.2352).

**DRZI** — posledné obdobie (2025-01 - 2026-02) je na 92. percentile, teda v medziach +0.0218 až +0.4897 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 2** — 2022-11-29T04:00 až 2022-12-15T00:00, spolu +7065.09, rovnako dlhých sérií 4.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-11-29T04:00 | 2022-12-12T16:00 | +6055.89 | +1.63 | `session_end` |
| 2 | 2022-12-13T08:00 | 2022-12-15T00:00 | +1009.20 | +0.22 | `session_end` |

**Straty za sebou: 10** — 2023-05-02T16:00 až 2023-11-20T11:08, spolu -15454.99, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-05-02T16:00 | 2023-05-03T04:00 | -30.79 | -0.01 | `session_end` |
| 2 | 2023-05-03T16:00 | 2023-05-05T12:39 | -1384.43 | -0.34 | `trailing_stop` |
| 3 | 2023-05-09T20:00 | 2023-05-10T00:00 | -583.61 | -0.15 | `session_end` |
| 4 | 2023-05-11T12:00 | 2023-05-11T13:21 | -1970.59 | -0.51 | `stop_loss` |
| 5 | 2023-06-01T16:00 | 2023-06-02T12:30 | -2034.00 | -0.51 | `stop_loss` |
| 6 | 2023-07-28T04:00 | 2023-08-01T15:10 | -1883.15 | -0.59 | `stop_loss` |
| 7 | 2023-08-04T16:00 | 2023-08-07T04:00 | -1667.33 | -0.34 | `session_end` |
| 8 | 2023-11-15T12:00 | 2023-11-15T13:39 | -1935.70 | -0.36 | `stop_loss` |
| 9 | 2023-11-16T16:00 | 2023-11-19T23:00 | -1948.01 | -0.43 | `stop_loss` |
| 10 | 2023-11-20T04:00 | 2023-11-20T11:08 | -2017.38 | -0.41 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.2503 %**, medián 0.2459 %, 90 % interval 0.1120–0.4030 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 16.8 %, 95. percentil 39.1 %, najhorší 100.0 %
- najdlhšia séria strát: medián 10, 95. percentil 16 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 177** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=91108f4a -->

1. **Na čo sa to hodí a na čo nie.** zlato MGC 4h (cena × DEMA 183 + EMA 200, len longy): pomalé sledovanie trendu na 1h–4h, obchody trvajú dni, zisk robí
   pár veľkých pohybov (WR 20–35 %). Hodí sa ako **časť portfólia** viacerých trhov (MNQ, zlato, ES, MYM, BTC), nie ako
   samostatná stratégia — na jednom trhu je obchodov málo. Na CFD treba prirátať swap za držanie cez noc a víkend.
   Percentá v tabuľkách sú pri riziku 2 000 $ na obchod a účte 60 000 $ — rozhoduje PF a znamienko po rokoch.
2. **Má to potenciál?** Čísla: PF 2,94 (roky 2,1–5,9), 34 obchodov za rok, WR 25 %, zisková v 5 z 5 okien. Výhrada: proti náhode +0,8 sigma — zlato 2023–2026 silno rástlo, väčšina zisku je jeho rast. Edge je teda skutočný,
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
