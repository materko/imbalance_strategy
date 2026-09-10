# Základná analytika — IBS Imbalance Breakout (`ibs`)

Zmerané 2026-09-10 na `BTC/USDT:USDT` 3m, engine `freqtrade`, poplatok 0.0500 % na stranu, profil `docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibs \
   --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --timeframe 3m
```

## V čom je dobrá

- break-even 0.1046 % je nad poplatkom 0.0500 % (rezerva +0.0546 bodu)
- edge nad poplatkom v 96 % bootstrapových vzoriek
- drawdown drží: 95. percentil 23.8 %
- odlíšiteľná od náhody (+4.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 83. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20221001-20231001, 20231001-20241001 v strate)
- 27.5 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'do 0.2825 %' vlastnosti 'Vzdialenosť stopu': 38 obchodov (25.5 %), bez nej by break-even bol o +0.0570 lepší (riadi `minSlDistance`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 28 | +22.13 | 0.2072 | 7.8 | 39.3 | `20260910-075436-12a603` |
| 20221001-20231001 | 34 | -1.41 | 0.0444 | 12.0 | 32.4 | `20260910-075457-c68dce` |
| 20231001-20241001 | 37 | -1.54 | 0.0432 | 10.6 | 27.0 | `20260910-075519-f58c0c` |
| 20240904-20250904 | 28 | +11.70 | 0.1405 | 5.6 | 46.4 | `20260910-075541-0a9917` |
| 20250904-20260904 | 22 | +11.91 | 0.1568 | 3.8 | 54.5 | `20260910-075603-336da9` |

Zisková v **3 z 5** okien, obchodov spolu 149, break-even celkom 0.1046 %.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.73 ATR za 5 barov)
- medián držania 31 barov grafu
- winrate 38.26 %, payoff 2.241
- 0.08 obchodov za deň
- šikmosť výnosov +1.26

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 57.7 %, `session_end` 27.5 %, `roi` 14.8 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 0.2825 %' vlastnosti 'Vzdialenosť stopu': 38 obchodov (25.5 %), break-even 0.0214 % oproti 0.1046 % celku. Bez nej by break-even bol 0.1616 % (+0.0570). Filter na to postavit ide, ale najprv skus `minSlDistance` - parameter je lacnejsi a citatelnejsi nez model.


**Vzdialenosť stopu** (riadi `minSlDistance`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.2825 % | 38 | 25.5 % | 28.9 | 0.0214 | 0.1616 | +0.0570 |
| 0.3951 % – 0.5607 % | 38 | 25.5 % | 39.5 | 0.1264 | 0.0992 | -0.0054 |
| 0.2825 % – 0.3951 % | 37 | 24.8 % | 40.5 | 0.1679 | 0.0802 | -0.0244 |
| nad 0.5607 % | 36 | 24.2 % | 44.4 | 0.2064 | 0.0912 | -0.0134 |

**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| piatok | 32 | 21.5 % | 21.9 | 0.0056 | 0.1328 | +0.0282 |
| štvrtok | 22 | 14.8 % | 36.4 | 0.0386 | 0.1169 | +0.0123 |
| pondelok | 30 | 20.1 % | 33.3 | 0.0749 | 0.1123 | +0.0077 |
| streda | 30 | 20.1 % | 50.0 | 0.1784 | 0.0877 | -0.0169 |
| utorok | 35 | 23.5 % | 48.6 | 0.2125 | 0.0726 | -0.0320 |

**Hodina vstupu (UTC)** (riadi `sess2TradeStartH`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 16 h | 15 | 10.1 % | 53.3 | 0.0850 | 0.1068 | +0.0022 |
| do 14 h | 48 | 32.2 % | 33.3 | 0.0945 | 0.1098 | +0.0052 |
| 14 h – 15 h | 62 | 41.6 % | 37.1 | 0.1110 | 0.1003 | -0.0043 |
| 15 h – 16 h | 24 | 16.1 % | 41.7 | 0.1232 | 0.1012 | -0.0034 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `sess2TradeStartH`, `state2MaxBars`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.1415 % | -0.0026 % ± 0.0338 | +4.26 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.1415 % | 0.0012 % ± 0.0357 | +3.92 | 100.0 |

Edge je odlisitelny od nahody (4.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 37 | 2.5 | 40.5 | 0.1758 | 86 |
| 2023-01 - 2024-03 | 38 | 2.6 | 28.9 | 0.0435 | 15 |
| 2024-03 - 2025-06 | 49 | 3.4 | 32.6 | 0.0612 | 24 |
| 2025-06 - 2026-08 | 25 | 1.7 | 60.0 | 0.1782 | 83 |

Hranice pre úsek veľkosti posledného obdobia: -0.0275 až +0.2434 % (medián 0.1006).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 83. percentile, teda v medziach -0.0275 až +0.2434 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.1046 %**, medián 0.1037 %, 90 % interval 0.0532–0.1573 %
- P(edge > poplatok) = **96.1 %**
- max drawdown: medián 12.0 %, 95. percentil 23.8 %, najhorší 54.8 %
- najdlhšia séria strát: medián 8, 95. percentil 12 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **110** na obchod pri účte 10 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

<!-- POSUDOK cisla=ef298f1a -->

**Zhrnutie:** použiteľný kandidát s edge dvojnásobným oproti poplatku, ale s takou tenkou
vzorkou (≈30 obchodov za rok), že každý ďalší záver o nej trvá roky dát. Nie je to
„o ničom" — 4,3 sigma proti náhode a rovnaký odstup aj proti náhode v tých istých
hodinách hovorí, že za tým je jav, nie časovanie seansy. Ale ani to nie je hotová
stratégia: dva z piatich rokov sú v miernej strate a polovica edge sedí v jednej
odfiltrovateľnej skupine obchodov.

**1. Na čo sa to hodí a na čo nie.** Sedí na BTC futures 3m v NY seanse, s účtom, ktorý
znesie 25 % drawdown a rok bez zisku (2022/23 a 2023/24 boli −1,4 % a −1,5 %). Nehodí sa
na malý účet, ktorý potrebuje pravidelný výnos — 0,08 obchodu za deň znamená jeden obchod
za dva týždne, takže aj rok je štatisticky krátky. Nehodí sa ani na trh s vyšším
poplatkom než ~0,1 % na stranu: tam z edge neostane nič. Prahy sú v tomto profile
percentuálne a v ATR, takže prenos na iný trh je technicky možný — či drží aj tam, ale
zmerané nie je (matica sa nespúšťala).

**2. Má to potenciál?** Za skutočný jav hovoria štyri veci: odstup od náhody je rovnaký
proti `anytime` aj `session` (edge teda nie je len „obchoduj v NY"), charakter je
učebnicové prerazenie (vstup +0,73 ATR po pohybe, winrate 38 %, payoff 2,24 — to sedí
navzájom), break-even je nad poplatkom v 96 % bootstrapových vzoriek, a posledné obdobie
(2025-06 – 2026-08) je na 83. percentile vlastnej minulosti, teda úpadok v dátach vidieť
nie je. Proti hovorí
vzorka: 149 obchodov spolu a 90 % interval break-evenu 0,053–0,157 % je stále široký,
plus rok 2021/22 (+22 %) nesie neúmerne veľa. Rozdiel medzi „edge" a „vlastnosť vzorky"
tu zatiaľ rozhodnúť nevieme; vieme len, že náhoda to nevysvetlí.

**3. Čo treba dorobiť.** Po poradí dôležitosti: (a) **`minSlDistance`** — obchody so
stopom pod 0,28 % ceny majú break-even 0,021 % oproti 0,105 % celku a je ich štvrtina;
prah je dnes 0,20 %, posunúť ho je zmena jedného čísla, nie nový filter. (b) **Koniec
seansy** — 27,5 % obchodov nekončí na pláne, ale na čase (`closeAtSessionEnd`); treba
vedieť, či to výsledku pomáha alebo škodí, dnes to nie je zmerané. (c) **Frekvencia** —
30 obchodov za rok je hlavná prekážka overovania; buď širšie okno seansy (London), alebo
viac párov naraz. (d) Piatok vyzerá zle (break-even 0,006 %, winrate 22 %), ale je to 32
obchodov — to je nápad na test, nie na filter.

**4. Čo otestovať ďalej.**

```bash
# a) prah tesných stopov na všetkých piatich oknách
PY -m tester.webapp.cli sweep --param minSlDistance=0.20:0.40:0.05@pct --goal break_even \
   --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json --timerange 20240904-20250904
# b) drží myšlienka aj mimo BTC? (prahy sa prepočítajú na atr)
PY -m tester.webapp.cli matrix --pairs all --timeframes 3m --timerange 20240904-20250904
# c) ten istý profil druhým enginom — záver pre MultiCharts patrí emulátoru
PY -m tester.webapp.cli run --engine multicharts --profile docs/profily_archiv/ibs/nas100_dukas_3m.json \
   --pair NAS100/USD --timerange 20240904-20250904 --note "druhy engine"
# d) pomáha zatváranie na konci seansy, alebo berie zisk?
PY -m tester.webapp.cli sweep --param closeAtSessionEnd=true,false --goal break_even --timerange 20240904-20250904
```

Čo by ich výsledok rozhodol: (a) či je +0,057 break-evenu skutočné zlepšenie alebo len
tvar jedného okna; (b) či je to stratégia, alebo vlastnosť BTC; (c) či je vetva pre
MultiCharts vôbec použiteľná (fill model je iný); (d) či je štvrtina výstupov na čase
chyba alebo cena za to, že sa cez noc nedrží.

**5. Je to použiteľné?** Áno, ale ako **kandidát na malé riziko**, nie ako hotový systém.
Jedna vec z testu úpadku stojí za sledovanie: break-even posledného obdobia je pekný
(0,1782 %), ale **signálov ubudlo** — 1,7 obchodu za mesiac oproti 2,5–3,4 v predošlých
obdobiach. Na verdikt to nestačí (test si všíma až pokles pod polovicu), pri 25 obchodoch
v období je to skôr šum; ale keby to pokračovalo, je to úpadok rovnako ako klesajúci
break-even, len ho v ňom vidieť nie je.
Monte Carlo hovorí: pri účte 10 000 riskuj najviac 110 na obchod, aby 95 % ciest zostalo
nad −20 %. Pri tom riziku je to obchodovateľné a rok tichého behu je normálny stav, nie
signál, že sa niečo pokazilo. Za „hotové" to bude možné vyhlásiť až vtedy, keď prejde
bodmi (a)–(c) vyššie — hlavne maticou trhov, lebo edge, ktorý drží presne na jednom páre,
je s vysokou pravdepodobnosťou vlastnosť toho páru.

**6. Čo by som pridal.** Chýba jej **vedomé riešenie tesných setupov**: dnes ich buď
odfiltruje prah, alebo sa obchodujú v plnej veľkosti. Prirodzenejšie je škálovať veľkosť
podľa vzdialenosti stopu (menší setup = menší podiel rizika), lebo poplatok je percento
z nominálu a pri tesnom stope zožerie väčšiu časť očakávanej hodnoty. Druhý nápad: keďže
57,7 % obchodov končí na stope a payoff je 2,2, stojí za skúšku posun stopu na nulu po
1R — nie preto, aby stúpol winrate, ale aby sa skrátila séria strát, ktorá je dnes
mediánovo 8 a v 5 % prípadov 12 obchodov po sebe.

<!-- POSUDOK KONIEC -->
