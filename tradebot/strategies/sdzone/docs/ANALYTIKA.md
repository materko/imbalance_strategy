# Základná analytika — SD Zones — supply/demand z bázy a impulzu (`sdzone`)

Zmerané 2026-09-11 na `XAU/USD` 15m, engine `multicharts`, poplatok 0.0006 % na stranu (1 tick na stranu pri cene 1810 = 0.00055 %; odhad: polovica spreadu = 1 tick, nezmerané (Dukascopy export má len bid, spread v ňom nie je)), profil `tradebot/strategies/sdzone/configs/xau_dukascopy_15m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sdzone \
   --profile tradebot/strategies/sdzone/configs/xau_dukascopy_15m.json \
   --pair XAU/USD \
   --timeframe 15m
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 2405 obchodov spolu — na štatistiku dosť
- break-even 0.0267 % je nad poplatkom 0.0006 % (rezerva +0.0261 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 6.3 %
- odlíšiteľná od náhody (+8.9 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 94. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'proti trendu' vlastnosti 'S trendom, alebo proti': 1138 obchodov (47.3 %), bez nej by break-even bol o +0.0134 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 511 | +28.35 | 0.2077 | 195.1 | 25.4 | `20260911-183158-f72e6c` |
| 20221001-20231001 | 454 | +343.09 | 2.0619 | 113.7 | 28.2 | `20260911-183202-3db4e7` |
| 20231001-20241001 | 468 | +16.46 | 0.1343 | 274.7 | 28.2 | `20260911-183205-c6aaeb` |
| 20240904-20250904 | 500 | +184.72 | 0.6722 | 410.2 | 24.4 | `20260911-183208-75b650` |
| 20250904-20260904 | 472 | +2773.71 | 6.7581 | 478.2 | 29.9 | `20260911-183211-d493c1` |

Zisková v **5 z 5** okien, obchodov spolu 2405, break-even celkom 0.0267 %.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (-0.15 ATR za 5 barov)
- medián držania 10.2 barov grafu
- winrate 27.15 %, payoff 3.397
- 1.34 obchodov za deň
- šikmosť výnosov +2.561

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `stop_loss` 72.8 %, `take_profit` 27 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'proti trendu' vlastnosti 'S trendom, alebo proti': 1138 obchodov (47.3 %), break-even 0.0116 % oproti 0.0267 % celku. Bez nej by break-even bol 0.0401 % (+0.0134). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 1138 | 47.3 % | 25.0 | 0.0116 | 0.0401 | +0.0134 |
| s trendom | 1267 | 52.7 % | 29.1 | 0.0401 | 0.0116 | -0.0151 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 1175 | 48.9 % | 25.3 | 0.0176 | 0.0355 | +0.0088 |
| long | 1230 | 51.1 % | 28.9 | 0.0355 | 0.0176 | -0.0091 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.247 | 602 | 25.0 % | 22.6 | 0.0017 | 0.0352 | +0.0085 |
| 0.247 – 0.5 | 601 | 25.0 % | 26.1 | 0.0171 | 0.0299 | +0.0032 |
| nad 0.7607 | 601 | 25.0 % | 31.6 | 0.0386 | 0.0227 | -0.0040 |
| 0.5 – 0.7607 | 601 | 25.0 % | 28.3 | 0.0501 | 0.0191 | -0.0076 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0267 % | 0.0001 % ± 0.0030 | +8.92 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0267 % | 0.0001 % ± 0.0030 | +8.92 | 100.0 |

Edge je odlisitelny od nahody (8.9 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 624 | 42.3 | 25.6 | 0.0066 | 11 |
| 2022-12 - 2024-03 | 547 | 37.1 | 29.6 | 0.0152 | 28 |
| 2024-03 - 2025-06 | 644 | 43.7 | 25.6 | 0.0096 | 16 |
| 2025-06 - 2026-09 | 590 | 40.0 | 28.1 | 0.0530 | 94 |

Hranice pre úsek veľkosti posledného obdobia: +0.0011 až +0.0548 % (medián 0.0258).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 94. percentile, teda v medziach +0.0011 až +0.0548 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0267 %**, medián 0.0265 %, 90 % interval 0.0132–0.0412 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 3.6 %, 95. percentil 6.3 %, najhorší 14.1 %
- najdlhšia séria strát: medián 21, 95. percentil 30 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **552** na obchod pri účte 10 000

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
<!-- POSUDOK cisla=392e4986 -->

**Najprv varovanie k tabuľke vyššie.** Stĺpce „PnL %" a „max DD %" sú v tomto prípade
**skreslené sizingom** — profil má pevné riziko 100 $ na obchod pri peňaženke 10 000 $,
takže ako účet rastie, percentá strácajú zmysel (PnL +2 773 % a drawdown 478 % nie sú
reálne čísla, je to pomer k počiatočnému kapitálu na účte, ktorý medzitým narástol
28-násobne). Čítať treba **break-even**, ktorý od sizingu nezávisí, a čísla z ladenia
pri pevnom riziku 300 $ na obchod: **2 373 obchodov, WR 27,2 %, RRR 3,40, očakávanie
+0,20R, max pokles 19 895 $.**

**1. Na čo sa to hodí a na čo nie**

Na **zlato na 15m**. To nie je preferencia, to je meranie: na NAS100 aj US500 som otestoval
vyše 30 variantov a **ani jeden nebol ziskový** — na NAS100 bolo najlepšie očakávanie
−0,07R. Na zlate je +0,20R až +0,31R. Rozdiel je taký veľký, že to nie je ladenie, ale iný
trh.

Charakter je zmes (istota priemerná): 72,8 % obchodov končí na stope, 27 % na cieli, medián
držania 10 barov (2,5 hodiny), 1,34 obchodu za deň. Účet musí uniesť dlhé série strát —
najdlhšia bola 23 obchodov za sebou.

**2. Má to potenciál?**

Za skutočným javom hovorí viac než pri ktorejkoľvek inej stratégii v tomto repozitári:
**+8,9 sigma** proti náhodnému vstupu (pre porovnanie Range má +3,2), **zisková v 5 z 5**
referenčných okien, **2 405 obchodov**, break-even 0,0267 % proti nákladu 0,0006 % — teda
44-násobná rezerva. Edge **neslabne**: posledné obdobie je na 94. percentile vlastného
rozdelenia.

Proti hovorí jedna vec: rozdelenie výnosov má šikmosť **+2,56**, čiže výsledok stojí na
menšine veľmi dobrých obchodov. Pri takom rozdelení je priemer krehký — stačí, aby tie
najlepšie obchody v budúcom období nenastali, a stratégia bude vyzerať úplne inak, hoci
sa nič nepokazilo.

**3. Čo treba dorobiť**

- **Obchody proti trendu.** Je ich 47,3 % a bez nich by bol break-even o **+0,0134 lepší**,
  teda o polovicu. Filter trendu v stratégii **je** (`useTrendFilter`), ale v ladení
  výsledok **zhoršil** (+0,18R proti +0,20R). To je rozpor, ktorý treba rozpliesť:
  analytika hovorí, že skupina je zlá, ale môj filter ju nevie odseknúť. Pravdepodobne
  je kĺzavý priemer zlá definícia trendu pre tento účel — skúsil by som štruktúru
  (BOS/CHoCH) z existujúcej stratégie `structure`.
- **Dve populácie v jednom.** Charakter je označený ako zmes s priemernou istotou. Stojí
  za to rozdeliť obchody podľa formácie (RBR/DBD vs DBR/RBD) a merať ich zvlášť —
  v ladení vyšli obratové formácie lepšie (+0,26R proti +0,11R pokračovacím).
- **PFZ režim je prakticky nepoužitý.** V ladení vždy prehral s WFZ. Buď je definícia
  úzkej zóny zlá, alebo na 15m grafe nemá zmysel. Treba zmerať prečo, nie ho len nechať.

**4. Čo otestovať ďalej**

```
cli matrix --strategy sdzone --pairs all --timeframes 15m,1h
cli sweep --strategy sdzone --param impulseMinBodyAtr=0.4:2.0:0.2 --goal break_even
cli hyperopt --strategy sdzone --suggested --timerange 20211001-20241001
cli nulltest --strategy sdzone "pair=XAU/USD"
cli run --strategy sdzone --engine freqtrade …
```

Matica rozhodne, či je edge vlastnosťou zlata alebo komodít vôbec (striebro, ropa).
Hyperopt na **starších** oknách a overenie na novších rozhodne otázku zo šikmosti:
ak parametre naladené na 2021–2024 obstoja na 2024–2026, je za tým mechanizmus.
Beh cez Freqtrade rozhodne, či to drží aj s iným fill modelom — celé ladenie bežalo
na emulátore a stratégia vstupuje trhovo, takže sklz je reálna otázka.

**5. Je to použiteľné, alebo je to o ničom?**

**Použiteľné — a je to najlepší výsledok, aký v tomto repozitári zatiaľ je.** Za tým stojí
5 z 5 ziskových okien, 8,9 sigma, 2 405 obchodov a 44-násobná rezerva nad nákladom. Žiadna
iná stratégia tu nemá všetky štyri naraz.

S jednou podmienkou: **len na zlate**. Na indexoch je to zmerané ako stratové a nasadiť to
tam by bola chyba.

Čo by ma presvedčilo o nasadení bez výhrad: hyperopt naladený na 2021–2024, ktorý obstojí
na 2024–2026, a beh cez Freqtrade s reálnym sklzom. Do tej doby by som to bral ako silného
kandidáta do portfólia, nie ako hotovú vec.

**6. Čo by som pridal**

**Meranie toho, ako ďaleko cena od zóny odišla, ako signál sily — a použiť ho na veľkosť
pozície, nie na filter.** Dnes `impulseMinMoveAtr` rozhoduje binárne: buď formácia platí,
alebo nie. Ale zóna, od ktorej cena odišla o 4 ATR, hovorí o niečom inom než zóna s odchodom
2 ATR — a šikmosť +2,56 naznačuje, že tie výnimočné obchody niekde majú spoločný znak.
Pridal by som pole `sizeByImpulse` (veľkosť pozície škálovaná silou impulzu v rozsahu napr.
0,5× až 1,5×) a zmeral, či sa tým dá tá šikmosť využiť namiesto toho, aby bola rizikom.
Je to lacná zmena a odpovedá presne na to, čo je na tejto stratégii najkrehkejšie.

<!-- POSUDOK KONIEC -->
