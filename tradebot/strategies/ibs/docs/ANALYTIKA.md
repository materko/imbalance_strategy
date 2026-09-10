# Základná analytika — IBS Imbalance Breakout (`ibs`)

Zmerané 2026-09-10 na `BTC/USDT:USDT` 3m, engine `freqtrade`, poplatok 0.0500 % na stranu (Binance USDⓈ-M taker, VIP 0), profil `docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibs \
   --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --timeframe 3m
```

## V čom je dobrá

- break-even 0.1058 % je nad poplatkom 0.0500 % (rezerva +0.0558 bodu)
- edge nad poplatkom v 96 % bootstrapových vzoriek
- drawdown drží: 95. percentil 23.9 %
- odlíšiteľná od náhody (+4.6 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 82. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20221001-20231001, 20231001-20241001 v strate)
- 26.7 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'do 0.2825 %' vlastnosti 'Vzdialenosť stopu': 37 obchodov (25.3 %), bez nej by break-even bol o +0.0590 lepší (riadi `minSlDistance`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 28 | +22.13 | 0.2072 | 7.8 | 39.3 | `20260910-075436-12a603` |
| 20221001-20231001 | 34 | -1.41 | 0.0444 | 12.0 | 32.4 | `20260910-075457-c68dce` |
| 20231001-20241001 | 37 | -1.54 | 0.0432 | 10.6 | 27.0 | `20260910-075519-f58c0c` |
| 20240904-20250904 | 28 | +11.70 | 0.1405 | 5.6 | 46.4 | `20260910-075541-0a9917` |
| 20250904-20260904 | 22 | +11.91 | 0.1568 | 3.8 | 54.5 | `20260910-075603-336da9` |

Zisková v **3 z 5** okien, obchodov spolu 146, break-even celkom 0.1058 %. Okná sa prekrývajú, 3 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.77 ATR za 5 barov)
- medián držania 30.3 barov grafu
- winrate 37.67 %, payoff 2.309
- 0.08 obchodov za deň
- šikmosť výnosov +1.245

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 58.2 %, `session_end` 26.7 %, `roi` 15.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 0.2825 %' vlastnosti 'Vzdialenosť stopu': 37 obchodov (25.3 %), break-even 0.0188 % oproti 0.1058 % celku. Bez nej by break-even bol 0.1648 % (+0.0590). Filter na to postavit ide, ale najprv skus `minSlDistance` - parameter je lacnejsi a citatelnejsi nez model.


**Vzdialenosť stopu** (riadi `minSlDistance`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.2825 % | 37 | 25.3 % | 27.0 | 0.0188 | 0.1648 | +0.0590 |
| 0.3951 % – 0.5596 % | 36 | 24.7 % | 41.7 | 0.1455 | 0.0963 | -0.0095 |
| 0.2825 % – 0.3951 % | 37 | 25.3 % | 40.5 | 0.1679 | 0.0813 | -0.0245 |
| nad 0.5596 % | 36 | 24.7 % | 41.7 | 0.1883 | 0.0946 | -0.0112 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.4698 | 37 | 25.3 % | 24.3 | -0.0208 | 0.1543 | +0.0485 |
| 0.6809 – 0.8089 | 36 | 24.7 % | 38.9 | 0.0832 | 0.1130 | +0.0072 |
| 0.4698 – 0.6809 | 37 | 25.3 % | 43.2 | 0.1797 | 0.0789 | -0.0269 |
| nad 0.8089 | 36 | 24.7 % | 44.4 | 0.2016 | 0.0793 | -0.0265 |

**Trend alebo rozsah** (riadi `useStructureFilter`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.0434 | 37 | 25.3 % | 29.7 | 0.0017 | 0.1469 | +0.0411 |
| nad 0.1547 | 36 | 24.7 % | 33.3 | 0.0672 | 0.1161 | +0.0103 |
| 0.0951 – 0.1547 | 36 | 24.7 % | 33.3 | 0.1363 | 0.0958 | -0.0100 |
| 0.0434 – 0.0951 | 37 | 25.3 % | 54.0 | 0.2217 | 0.0653 | -0.0405 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `sess2TradeStartH`, `state2MaxBars`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.1445 % | 0.0004 % ± 0.0316 | +4.56 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.1445 % | 0.0009 % ± 0.0305 | +4.71 | 100.0 |

Edge je odlisitelny od nahody (4.6 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 37 | 2.5 | 40.5 | 0.1758 | 86 |
| 2023-01 - 2024-03 | 38 | 2.6 | 28.9 | 0.0435 | 18 |
| 2024-03 - 2025-06 | 46 | 3.2 | 30.4 | 0.0630 | 22 |
| 2025-06 - 2026-08 | 25 | 1.7 | 60.0 | 0.1782 | 82 |

Hranice pre úsek veľkosti posledného obdobia: -0.0294 až +0.2339 % (medián 0.1031).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 82. percentile, teda v medziach -0.0294 až +0.2339 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.1058 %**, medián 0.1051 %, 90 % interval 0.0537–0.1597 %
- P(edge > poplatok) = **96.1 %**
- max drawdown: medián 11.9 %, 95. percentil 23.9 %, najhorší 57.6 %
- najdlhšia séria strát: medián 8, 95. percentil 12 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **109** na obchod pri účte 10 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

<!-- POSUDOK cisla=76d0e005 -->

**Zhrnutie:** použiteľný kandidát s edge dvojnásobným oproti poplatku, ale s takou tenkou
vzorkou (≈30 obchodov za rok), že každý ďalší záver o nej trvá roky dát. Nie je to
„o ničom" — 4,6 sigma proti náhode (losovanej z tých istých piatich okien, nie z celej
histórie páru) a rovnaký odstup aj proti náhode v tých istých hodinách hovorí, že za tým
je jav, nie časovanie seansy. Ale ani to nie je hotová stratégia: dva z piatich rokov sú
v miernej strate a polovica edge sedí v jednej odfiltrovateľnej skupine obchodov.
(Vzorka je 146 obchodov: tri, ktoré ležali v prekryve okien 2023-10→2024-10
a 2024-09→2025-09, sa počítajú raz.)

**1. Na čo sa to hodí a na čo nie.** Sedí na BTC futures 3m v NY seanse, s účtom, ktorý
znesie 25 % drawdown a rok bez zisku (2022/23 a 2023/24 boli −1,4 % a −1,5 %). Nehodí sa
na malý účet, ktorý potrebuje pravidelný výnos — 0,08 obchodu za deň znamená jeden obchod
za dva týždne, takže aj rok je štatisticky krátky. Nehodí sa ani na trh s vyšším
poplatkom než ~0,1 % na stranu: tam z edge neostane nič. Prahy sú v tomto profile
percentuálne a v ATR, takže prenos na iný trh je technicky možný — či drží aj tam, ale
zmerané nie je (matica sa nespúšťala).

**2. Má to potenciál?** Za skutočný jav hovoria štyri veci: odstup od náhody je rovnaký
proti `anytime` aj `session` (edge teda nie je len „obchoduj v NY"), charakter je
učebnicové prerazenie (vstup +0,77 ATR po pohybe, winrate 38 %, payoff 2,31 — to sedí
navzájom), break-even je nad poplatkom v 96 % bootstrapových vzoriek, a posledné obdobie
(2025-06 – 2026-08) je na 82. percentile vlastnej minulosti, teda úpadok v dátach vidieť
nie je. Proti hovorí
vzorka: 146 obchodov spolu a 90 % interval break-evenu 0,054–0,160 % je stále široký,
plus rok 2021/22 (+22 %) nesie neúmerne veľa. Rozdiel medzi „edge" a „vlastnosť vzorky"
tu zatiaľ rozhodnúť nevieme; vieme len, že náhoda to nevysvetlí.

**3. Čo treba dorobiť.** Po poradí dôležitosti: (a) **`minSlDistance`** — obchody so
stopom pod 0,28 % ceny majú break-even 0,019 % oproti 0,106 % celku a je ich štvrtina;
prah je dnes 0,20 %, posunúť ho je zmena jedného čísla, nie nový filter. (b) **Stav trhu
pri vstupe** — toto je nové a je to druhá najväčšia páka: vstupy v spodnej štvrtine
50-barového rozsahu (v smere obchodu) majú break-even −0,021 % a vstupy v najplochšom
trhu (efektivita pohybu pod 0,043) 0,002 %; každá z tých skupín je štvrtina obchodov
a bez nej by break-even bol o +0,04 až +0,05 lepší. Obe sú známe pri vstupe, takže je to
filter, nie pohľad dozadu — a `useStructureFilter` je práve ten parameter, ktorý trend
stráži; treba zmerať, či ho zapnutie nahradí. (c) **Koniec seansy** — 26,7 % obchodov
nekončí na pláne, ale na čase (`closeAtSessionEnd`); treba vedieť, či to výsledku pomáha
alebo škodí, dnes to nie je zmerané. (d) **Frekvencia** — 30 obchodov za rok je hlavná
prekážka overovania; buď širšie okno seansy (London), alebo viac párov naraz.

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
# e) nahradí štruktúrny filter to, čo ukazuje stav trhu (poloha v rozsahu, plochý trh)?
PY -m tester.webapp.cli sweep --param useStructureFilter=true,false --param structureSwingLen=5,10,20 \
   --goal break_even --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json --timerange 20240904-20250904
```

Čo by ich výsledok rozhodol: (a) či je +0,059 break-evenu skutočné zlepšenie alebo len
tvar jedného okna; (b) či je to stratégia, alebo vlastnosť BTC; (c) či je vetva pre
MultiCharts vôbec použiteľná (fill model je iný); (d) či je štvrtina výstupov na čase
chyba alebo cena za to, že sa cez noc nedrží; (e) či existujúci parameter pokryje
najhoršie skupiny stavu trhu, alebo treba nový filter na polohu v rozsahu.

**5. Je to použiteľné?** Áno, ale ako **kandidát na malé riziko**, nie ako hotový systém.
Jedna vec z testu úpadku stojí za sledovanie: break-even posledného obdobia je pekný
(0,1782 %), ale **signálov ubudlo** — 1,7 obchodu za mesiac oproti 2,5–3,4 v predošlých
obdobiach. Na verdikt to nestačí (test si všíma až pokles pod polovicu), pri 25 obchodoch
v období je to skôr šum; ale keby to pokračovalo, je to úpadok rovnako ako klesajúci
break-even, len ho v ňom vidieť nie je.
Monte Carlo hovorí: pri účte 10 000 riskuj najviac 109 na obchod, aby 95 % ciest zostalo
nad −20 %. Pri tom riziku je to obchodovateľné a rok tichého behu je normálny stav, nie
signál, že sa niečo pokazilo. Za „hotové" to bude možné vyhlásiť až vtedy, keď prejde
bodmi (a)–(c) vyššie — hlavne maticou trhov, lebo edge, ktorý drží presne na jednom páre,
je s vysokou pravdepodobnosťou vlastnosť toho páru.

**6. Čo by som pridal.** Chýba jej **vedomé riešenie tesných setupov**: dnes ich buď
odfiltruje prah, alebo sa obchodujú v plnej veľkosti. Prirodzenejšie je škálovať veľkosť
podľa vzdialenosti stopu (menší setup = menší podiel rizika), lebo poplatok je percento
z nominálu a pri tesnom stope zožerie väčšiu časť očakávanej hodnoty. Druhý nápad: keďže
58,2 % obchodov končí na stope a payoff je 2,3, stojí za skúšku posun stopu na nulu po
1R — nie preto, aby stúpol winrate, ale aby sa skrátila séria strát, ktorá je dnes
mediánovo 8 a v 5 % prípadov 12 obchodov po sebe.

<!-- POSUDOK KONIEC -->
