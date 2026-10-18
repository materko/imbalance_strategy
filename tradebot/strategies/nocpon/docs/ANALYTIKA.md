# Základná analytika — NOC + PONDELOK 1.0 (`nocpon`)

Zmerané 2026-10-18 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mnq_databento_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy nocpon \
   --profile mnq_databento_5m \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 811 obchodov spolu — na štatistiku dosť
- break-even 0.0335 % je nad poplatkom 0.0018 % (rezerva +0.0317 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 8.3 %
- edge drží aj v poslednom období (2025-06 - 2026-09 na 83. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20211001-20221001 v strate)
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.1 sigma) — výber vstupu nepridáva nič
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 99.6 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'NFP' vlastnosti 'Makro udalosť v ten deň': 29 obchodov (3.6 %), bez nej by break-even bol o +0.0514 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 85 | -0.71 | -0.0066 | 2.2 | 48.2 | +4/-6 | `20261018-182839-1c854e` |
| 20221001-20231001 | 157 | +3.23 | 0.0240 | 2.0 | 51.6 | +7/-6 | `20261018-182845-db0132` |
| 20231001-20241001 | 199 | +8.81 | 0.0383 | 2.3 | 57.8 | +8/-5 | `20261018-182851-560757` |
| 20240904-20250904 | 187 | +9.83 | 0.0380 | 3.3 | 55.1 | +7/-6 | `20261018-182857-f82f5b` |
| 20250904-20260904 | 193 | +14.73 | 0.0438 | 4.4 | 54.4 | +11/-7 | `20261018-182904-4ba4b9` |

Zisková v **4 z 5** okien, obchodov spolu 811, break-even celkom 0.0335 %. Okná sa prekrývajú, 10 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.02 ATR za 5 barov)
- medián držania 132 barov grafu
- winrate 54.13 %, payoff 1.137
- 0.45 obchodov za deň
- šikmosť výnosov -0.179

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `session_end` 99.6 %, `force_exit` 0.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'NFP' vlastnosti 'Makro udalosť v ten deň': 29 obchodov (3.6 %), break-even -0.006 % oproti 0.0335 % celku. Bez nej by break-even bol 0.035 % (+0.0514). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| NFP | 29 | 3.6 % | 41.4 | -0.0060 | 0.0350 | +0.0015 |
| žiadna | 732 | 90.3 % | 53.5 | 0.0280 | 0.0849 | +0.0514 |
| CPI | 30 | 3.7 % | 66.7 | 0.0751 | 0.0319 | -0.0016 |
| FOMC | 20 | 2.5 % | 75.0 | 0.2289 | 0.0285 | -0.0050 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 732 | 90.3 % | 53.5 | 0.0280 | 0.0849 | +0.0514 |
| po vyhlásení | 79 | 9.7 % | 59.5 | 0.0849 | 0.0280 | -0.0055 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.2074 | 202 | 24.9 % | 51.0 | -0.0039 | 0.0461 | +0.0126 |
| 0.0567 – 0.1226 | 203 | 25.0 % | 54.7 | 0.0316 | 0.0342 | +0.0007 |
| do 0.0567 | 203 | 25.0 % | 51.7 | 0.0441 | 0.0300 | -0.0035 |
| 0.1226 – 0.2074 | 203 | 25.0 % | 59.1 | 0.0625 | 0.0239 | -0.0096 |

Parametre, ktorými sa dá s tým niečo spraviť: `nightExitH`, `useMonday`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0335 % | 0.0764 % ± 0.0377 | -1.14 | 13.4 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0335 % | 0.0817 % ± 0.0364 | -1.32 | 9.2 |

HORSIE nez nahoda (-1.1 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 86 | 5.8 | 47.7 | -0.0085 | 8 |
| 2022-12 - 2024-03 | 242 | 16.4 | 54.1 | 0.0313 | 45 |
| 2024-03 - 2025-06 | 233 | 15.8 | 54.9 | 0.0243 | 28 |
| 2025-06 - 2026-09 | 250 | 16.9 | 55.6 | 0.0497 | 83 |

Hranice pre úsek veľkosti posledného obdobia: +0.0055 až +0.0621 % (medián 0.0331).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 83. percentile, teda v medziach +0.0055 až +0.0621 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 11** — 2025-11-19T20:55 až 2025-12-08T07:55, spolu +3107.49.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-11-19T20:55 | 2025-11-20T07:55 | +832.75 | +1.68 | `session_end` |
| 2 | 2025-11-21T20:55 | 2025-11-24T07:55 | +371.29 | +0.76 | `session_end` |
| 3 | 2025-11-24T14:30 | 2025-11-25T07:55 | +783.76 | +1.60 | `session_end` |
| 4 | 2025-11-25T20:55 | 2025-11-26T07:55 | +195.23 | +0.39 | `session_end` |
| 5 | 2025-11-26T20:55 | 2025-11-27T07:55 | +30.72 | +0.06 | `session_end` |
| 6 | 2025-11-27T23:05 | 2025-11-28T13:30 | +118.22 | +0.23 | `session_end` |
| 7 | 2025-12-01T14:30 | 2025-12-02T07:55 | +205.72 | +0.41 | `session_end` |
| 8 | 2025-12-02T20:55 | 2025-12-03T07:55 | +112.70 | +0.22 | `session_end` |
| 9 | 2025-12-03T20:55 | 2025-12-04T07:55 | +13.20 | +0.03 | `session_end` |
| 10 | 2025-12-04T20:55 | 2025-12-05T07:55 | +250.20 | +0.49 | `session_end` |
| 11 | 2025-12-05T20:55 | 2025-12-08T07:55 | +193.69 | +0.38 | `session_end` |

**Straty za sebou: 7** — 2025-12-22T14:30 až 2026-01-01T23:00, spolu -668.64.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-12-22T14:30 | 2025-12-23T07:55 | -220.81 | -0.43 | `session_end` |
| 2 | 2025-12-23T20:55 | 2025-12-24T07:55 | -41.81 | -0.08 | `session_end` |
| 3 | 2025-12-25T23:05 | 2025-12-26T07:55 | -47.82 | -0.09 | `session_end` |
| 4 | 2025-12-26T20:55 | 2025-12-29T07:55 | -124.81 | -0.24 | `session_end` |
| 5 | 2025-12-29T14:30 | 2025-12-30T07:55 | -9.80 | -0.02 | `session_end` |
| 6 | 2025-12-30T20:55 | 2025-12-31T07:55 | -183.80 | -0.36 | `session_end` |
| 7 | 2025-12-31T20:55 | 2026-01-01T23:00 | -39.79 | -0.08 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0335 %**, medián 0.0334 %, 90 % interval 0.0174–0.0496 %
- P(edge > poplatok) = **99.9 %**
- max drawdown: medián 4.6 %, 95. percentil 8.3 %, najhorší 20.4 %
- najdlhšia séria strát: medián 8, 95. percentil 11 obchodov
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
<!-- POSUDOK cisla=d44e6669 -->

**1. Na čo sa to hodí a na čo nie.** Na Nasdaq futures (MNQ / NQ) s držaním cez noc, na účte, ktorý znesie
gap pri otvorení a víkend (prop firmy to často nedovolia — overiť pravidlá). Je to štrukturálny jav amerických
akcií (zisk vzniká mimo seansy, výsledky firiem po 16:00), nie vzor v sviečkach: na kryptách, forexe alebo
na CFD bez nočného obchodovania to isté číslo neznamená nič. TF grafu je len mriežka času (5m / 15m dávajú to isté).

**2. Má to potenciál?** Áno, ale menší, než sa zdá. Za skutočným javom hovorí: zisk v 4 z 5 okien, break-even
0,0335 % pri poplatku 0,0018 %, bootstrap 99,9 % nad poplatkom, posledné obdobie na 83. percentile (neslabne)
a prieskum 18. 10. ukázal, že ten istý čas na RTH (deň) dáva PF 1,03, noc 1,14 — jav je naozaj v noci.
Proti: **test proti náhode −1,1 sigma** — náhodný long s rovnakou dĺžkou držania v tých istých oknách dopadol
lepšie. Veľkú časť výsledku teda nesie samotný long Nasdaqu v rastovom trende (filter SMA 100), nie presný čas
vstupu. Rok 2021/22 (85 obchodov, PF 0,93) ukazuje, že v padajúcom trhu jav nedrží.

**3. Čo treba dorobiť.** (a) Sviatky: pri Thanksgiving / skrátených seansách vstup padne na 18:00 namiesto
15:55 — buď vynechať, alebo vstúpiť na poslednom bare seansy. (b) Ochranný stop proti gapu je len % poistka —
otestovať stop podľa ATR dňa. (c) Filter dní NFP (29 obchodov, break-even záporný) — malá vzorka, len ako test.
(d) Roll: v ostrom obchodovaní roll riešiť prechodom na ďalší kontrakt, nie vynechaním noci.

**4. Čo otestovať ďalej.** Hľadanie podľa smernice (`glsearch.py`, skupiny `nocpon`): čas vstupu 15:30–15:55,
výstup 0:00–9:30, SMA 50–200, okno rollu a stop. Rozhoduje, či plató drží (susedia ≥ 80 % PF) a či
21/22 vyjde aspoň 0,9. Potom krok 8 NAS100 (`glnas100.py` — Dukascopy CFD má nočné obchodovanie) a forward
test; odložený rok 25/26 bol pri prieskume viditeľný, preto má forward test väčšiu váhu než zvyčajne.

**5. Je to použiteľné?** Áno ako doplnok portfólia — iný čas (noc) a iný typ (držanie podľa času) než ostatné
stratégie, takže diverzifikuje. Ako samostatná „výberová“ stratégia nie: výber vstupu nad náhodný long nepridáva,
výhoda je v tom, *kedy* byť v trhu (noc, pondelok, nad SMA), nie v presnom momente.

**6. Čo by som pridal.** Pondelok večer (15:55 → 18:00 mal v prieskume PF 1,80) a deň po veľkom poklese
(> 1 ATR, long RTH, PF 1,39) ako ďalšie časové okná; veľkosť pozície podľa volatility (menej kontraktov,
keď je ATR dňa vysoko nad priemerom), aby jedna zlá noc nebrala viac než bežná.

<!-- POSUDOK KONIEC -->
