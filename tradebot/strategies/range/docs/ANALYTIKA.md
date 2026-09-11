# Základná analytika — Range Breakout — konsolidácia a jej prerazenie (`range`)

Zmerané 2026-09-11 na `NAS100/USD` 3m, engine `multicharts`, poplatok 0.0001 % na stranu (1 tick na stranu pri cene 13914.3 = 0.00007 %; odhad: polovica spreadu = 1 tick, nezmerané (Dukascopy export má len bid, spread v ňom nie je)), profil `tradebot/strategies/range/configs/nas100_dukascopy_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy range \
   --profile tradebot/strategies/range/configs/nas100_dukascopy_3m.json \
   --pair NAS100/USD \
   --timeframe 3m
```

## V čom je dobrá

- 1301 obchodov spolu — na štatistiku dosť
- break-even 0.0059 % je nad poplatkom 0.0001 % (rezerva +0.0058 bodu)
- edge nad poplatkom v 99 % bootstrapových vzoriek
- odlíšiteľná od náhody (+3.2 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 94. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20211001-20221001 v strate)
- 95. percentil max drawdownu 39.5 % (namerané 19.5 % medián) — na účet to treba mať

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 260 | -16.65 | -0.0050 | 33.3 | 26.1 | `20260911-124654-5d8627` |
| 20221001-20231001 | 260 | +6.67 | 0.0015 | 14.7 | 28.9 | `20260911-124657-36fc17` |
| 20231001-20241001 | 260 | +45.95 | 0.0070 | 12.5 | 34.6 | `20260911-124700-1836a2` |
| 20240904-20250904 | 260 | +33.25 | 0.0073 | 16.2 | 32.7 | `20260911-124703-7ff4e3` |
| 20250904-20260904 | 261 | +63.96 | 0.0176 | 20.9 | 37.5 | `20260911-124706-010e4f` |

Zisková v **4 z 5** okien, obchodov spolu 1301, break-even celkom 0.0059 %.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.34 ATR za 5 barov)
- medián držania 35.3 barov grafu
- winrate 31.98 %, payoff 2.491
- 0.72 obchodov za deň
- šikmosť výnosov +1.413

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 68 %, `take_profit` 32 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0042 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň pred sviatkom | 18 | 1.4 % | 22.2 | -0.0096 | 0.0061 | +0.0002 |
| bežný deň | 1195 | 91.9 % | 31.7 | 0.0054 | 0.0101 | +0.0042 |
| deň po sviatku | 34 | 2.6 % | 38.2 | 0.0176 | 0.0055 | -0.0004 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 630 | 48.4 % | 29.8 | 0.0021 | 0.0096 | +0.0037 |
| long | 671 | 51.6 % | 34.0 | 0.0096 | 0.0021 | -0.0038 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 256 | 19.7 % | 25.8 | -0.0043 | 0.0088 | +0.0029 |
| s trendom | 1045 | 80.3 % | 33.5 | 0.0088 | -0.0043 | -0.0102 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0075 % | -0.0003 % ± 0.0024 | +3.23 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0075 % | -0.0001 % ± 0.0025 | +3.02 | 99.7 |

Edge je odlisitelny od nahody (3.2 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 320 | 21.7 | 25.3 | -0.0068 | 1 |
| 2022-12 - 2024-03 | 320 | 21.7 | 31.2 | 0.0038 | 32 |
| 2024-03 - 2025-06 | 339 | 23.0 | 34.8 | 0.0100 | 83 |
| 2025-06 - 2026-09 | 322 | 21.8 | 36.3 | 0.0138 | 94 |

Hranice pre úsek veľkosti posledného obdobia: -0.0021 až +0.0143 % (medián 0.0059).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 94. percentile, teda v medziach -0.0021 až +0.0143 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0059 %**, medián 0.0059 %, 90 % interval 0.0020–0.0099 %
- P(edge > poplatok) = **99.4 %**
- max drawdown: medián 19.5 %, 95. percentil 39.5 %, najhorší 100.0 %
- najdlhšia séria strát: medián 17, 95. percentil 24 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **65** na obchod pri účte 10 000

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
<!-- POSUDOK cisla=8c4b533e -->

**1. Na čo sa to hodí a na čo nie**

Sedí na **likvidné indexy a zlato na 3m grafe** s rizikom počítaným z účtu, nie na pevný počet
kusov. Charakter je jednoznačne prerazenie: winrate 32 %, payoff 2,49, 68 % obchodov končí na
stope. Účet to musí uniesť psychicky aj číselne — 95. percentil max drawdownu je 39,5 %, takže
pri 1 % rizika na obchod treba počítať s poklesom, ktorý trvá mesiace.

Kde by to isté číslo znamenalo niečo iné: **na prop účte.** Break-even 0,0059 % je slušný, ale
limit straty 10 % na FTMO a najmä trailing 3,5 % na Tradeify sú tesnejšie než prirodzený pokles
tejto stratégie. Na vlastnom účte je to obchodovateľné, na prop výzve v tejto podobe nie —
to treba zmerať zvlášť, nie odhadnúť.

**2. Má to potenciál?**

Za skutočným javom hovoria tri veci: **+3,2 sigma proti náhodnému vstupu** (percentil 100 pri
`anytime` aj 99,7 pri `session`, takže to nie je len drift trhu), **1301 obchodov** naprieč
piatimi oknami, a to, že edge **neslabne** — posledné obdobie je na 94. percentile vlastného
rozdelenia.

Proti hovorí jedna vec, a je vážna: **rok 2021-10 až 2022-10 je v strate (−16,65 %, break-even
−0,0050)** a to isté obdobie je v teste slabnutia na 1. percentile. To nie je šum — je to celý
rok, v ktorom stratégia nefungovala. Zvyšné štyri okná idú monotónne hore (+6,7 → +45,9 → +33,3
→ +64,0 %), čo pri breakoute zvyčajne znamená, že posledné roky boli na prerazenia priaznivé.
Nevieme, či je to vlastnosť stratégie alebo vlastnosť obdobia.

**3. Čo treba dorobiť**

- **Filter režimu.** Rozdelenie „s trendom / proti trendu" ukazuje, že obchody proti trendu
  (256, teda pätina) majú break-even −0,0043 a bez nich by celok stúpol o +0,0029. Stratégia
  dnes nemá žiadny prepínač, ktorý by ich vypol — treba pridať filter smeru podľa vyššieho TF.
- **Shorty sú horšie než longy** (break-even 0,0021 proti 0,0096). Za pozretie stojí, či to nie
  je vlastnosť rastúceho trhu 2023–2026; ak áno, netreba shorty vypínať, ale vedieť to.
- **Sviatky.** Deň pred sviatkom má winrate 22 % a záporný break-even. Je to len 18 obchodov,
  takže to zatiaľ nemá váhu, ale prepínač na vynechanie dňa pred sviatkom je lacný.
- **Medián držania 35 barov** (cez hodinu a pol na 3m) — `maxHoldBars` v stratégii je, ale
  default 0 ho vypína; stálo by za to zmerať, či časový stop pomôže.

**4. Čo otestovať ďalej**

```
cli matrix --strategy range --pairs all --timeframes 3m,5m
cli sweep --strategy range --param maxWidthAtr=1.5:3.5:0.25 --goal break_even
cli hyperopt --strategy range --suggested --timerange 20211001-20241001
cli nulltest --strategy range "pair=XAU/USD"
cli run --strategy range --engine freqtrade …
```

Matica rozhodne, či je edge vlastnosťou zlata a indexov, alebo len týchto dvoch trhov.
Hyperopt na **starších** oknách (2021–2024) a overenie na novších rozhodne otázku z bodu 2:
ak parametre naladené na zlom období obstoja na dobrom, je za tým mechanizmus. Beh cez
Freqtrade rozhodne, či výsledok drží aj s iným fill modelom — celé ladenie bežalo na emulátore.

**5. Je to použiteľné, alebo je to o ničom?**

**Použiteľné, ale zatiaľ len ako doplnok portfólia, nie samostatne.** Za tým stoja konkrétne
čísla: edge je odlíšiteľný od náhody na 3,2 sigma, drží v čase a je postavený na 1301 obchodoch.
Proti stojí jeden celý stratový rok a drawdown, ktorý v 95. percentile presahuje tretinu účtu.

Test, ktorý by ma presvedčil o samostatnom nasadení: **hyperopt naladený na 2021–2024 a overený
na 2024–2026**. Ak víťaz z horšieho obdobia obstojí na novšom, je to stratégia. Ak nie, je to
záznam o tom, že prerazenia fungovali v rokoch 2023–2026.

**6. Čo by som pridal**

**Filter šírky rangu relatívne k jeho vlastnej minulosti, nie k ATR.** Dnes sa tesnosť meria
ako `range_width ≤ M × ATR`, čiže proti volatilite posledných 14 barov. Silnejší signál je
**kontrakcia**: range, ktorý je užší než predchádzajúcich N rangov na tom istom grafe. To je
presne to, čo odlišuje „trh sa zastavil a stláča sa" od „trh je celý deň pokojný" — a pri
prerazení je to rozdiel medzi uvoľnenou energiou a nudou. Pridal by som parameter
`contractionRatio` (aktuálna šírka ≤ X-násobok mediánu posledných N šírok) a zmeral ho ako
prvý, lebo z tabuľky „ktorá skupina kazí výsledok" vyplýva, že vopred známe vlastnosti obchodov
už nič nevysvetľujú — rozdiel musí byť v tom, **ktorý range** sa vôbec obchoduje.

<!-- POSUDOK KONIEC -->
