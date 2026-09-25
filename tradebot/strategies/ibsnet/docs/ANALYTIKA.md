# Základná analytika — IBSNet Imbalance Breakout (C# jadro) (`ibsnet`)

Zmerané 2026-09-19 na `BTC/USDT:USDT` 3m, engine `freqtrade`, poplatok 0.0500 % na stranu (Binance USDⓈ-M taker, VIP 0), profil `docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibsnet \
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
| 20211001-20221001 | 28 | +22.13 | 0.2072 | 7.8 | 39.3 | `20260919-221507-5a56f2` |
| 20221001-20231001 | 34 | -1.41 | 0.0444 | 12.0 | 32.4 | `20260919-221528-3546a6` |
| 20231001-20241001 | 37 | -1.54 | 0.0432 | 10.6 | 27.0 | `20260919-221550-d060fc` |
| 20240904-20250904 | 28 | +11.70 | 0.1405 | 5.6 | 46.4 | `20260919-221612-da46dd` |
| 20250904-20260904 | 22 | +11.91 | 0.1568 | 3.8 | 54.5 | `20260919-221634-76e6db` |

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

**S trendom, alebo proti** (riadi `useStructureFilter`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 46 | 31.5 % | 34.8 | 0.0274 | 0.1410 | +0.0352 |
| s trendom | 100 | 68.5 % | 39.0 | 0.1410 | 0.0274 | -0.0784 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 22 | 34 | 23.3 % | 32.4 | 0.0167 | 0.1334 | +0.0276 |
| 16 – 22 | 32 | 21.9 % | 34.4 | 0.0684 | 0.1162 | +0.0104 |
| do 7 | 38 | 26.0 % | 42.1 | 0.1556 | 0.0855 | -0.0203 |
| 7 – 16 | 42 | 28.8 % | 40.5 | 0.1633 | 0.0860 | -0.0198 |

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

Chýba. Napíše ho AI: prečíta čísla vyššie a odpovie na týchto šesť otázok. Text patrí **medzi značky** nižšie, aby ho ďalší `cli checkup` preniesol ďalej.

1. **Na čo sa to hodí a na čo nie** — trh, timeframe, režim, veľkosť účtu; kde by to isté číslo znamenalo niečo iné.
2. **Má to potenciál?** Čo z čísel hovorí, že za tým je skutočný jav, a čo hovorí, že je to vlastnosť vzorky.
3. **Čo treba dorobiť** v samotnej stratégii — filtre, výstupy, sizing, sviatky a seansy, chýbajúce parametre.
4. **Čo otestovať ďalej** — konkrétne príkazy (`cli sweep`, `cli matrix`, `cli hyperopt`, druhý engine) a čo by ich výsledok rozhodol.
5. **Je to použiteľné, alebo je to o ničom?** Odpoveď má byť jednoznačná; „ešte uvidíme" je odpoveď len vtedy, keď je za ňou konkrétny test.
6. **Čo by som pridal** — nápad, ktorý v stratégii nie je a z týchto čísel dáva zmysel.
<!-- POSUDOK cisla=576f2d49 -->

**Zhrnutie:** toto **nie je nová stratégia, ale IBS s iným motorom** — a čísla to potvrdzujú: päť
okien, 146 obchodov, break-even 0,1058 %, 4,6 sigma, bootstrap aj Monte Carlo vyšli do posledného
miesta rovnako ako v [analytike IBS](../../ibs/docs/ANALYTIKA.md) (tabuľky skupín sa líšia len preto,
že analytika medzičasom pribrala vlastnosť „s trendom / proti"). Nie je to náhoda ani šťastie vzorky:
C# jadro dáva na každom bare to isté čo Python engine, na rovnosť
([meranie parity](../../../../docs/merania/PARITA_ibsnet_2026-09-20.md)). Verdikt o myšlienke je
preto ten istý ako pri IBS — použiteľný kandidát s edge dvojnásobným oproti poplatku a s tenkou
vzorkou (≈30 obchodov za rok). Čo je tu naozaj otvorené, nie je stratégia, ale **platforma**: dôvod,
prečo IBSNet existuje, je NinjaTrader, a tam ešte nebežala ani raz.

**1. Na čo sa to hodí a na čo nie.** Pod Freqtrade presne na to, na čo IBS: BTC futures 3m v NY
seanse, účet, ktorý znesie ~25 % drawdown (95. percentil 23,9 %) a rok bez zisku (2022/23 −1,4 %,
2023/24 −1,5 %); nie na trh s poplatkom nad ~0,1 % na stranu a nie na účet, ktorý potrebuje
pravidelný výnos (0,08 obchodu za deň). Navyše sa hodí tam, kam IBS nemôže: **NinjaTrader 8**, teda
futures cez brokera (MNQ, NQ, ES) — na to je tu profil `multicharts_mnq_3m` s prahmi v bodoch MNQ.
Pozor na zámenu: tieto čísla sú z BTC perpetuálu s poplatkom v percentách; na MNQ je náklad tick
spreadu plus provízia a **o MNQ tento dokument nehovorí nič**. Pod Freqtrade ju nemá zmysel
uprednostniť pred `ibs` kvôli výsledku (je rovnaký); dôvod je len rýchlosť (ročný beh 15 s proti 23 s)
a to, že sa ňou skúša presne ten kód, ktorý pôjde do NinjaTradera.

**2. Má to potenciál?** Za jav hovorí to isté čo pri IBS: odstup od náhody je rovnaký proti `anytime`
(+4,56 sigma) aj `session` (+4,71), takže edge nie je „obchoduj v NY"; charakter je učebnicové
prerazenie (vstup +0,77 ATR po pohybe, winrate 37,7 %, payoff 2,31 — sedí to navzájom); P(edge >
poplatok) 96,1 %; posledné obdobie je na 82. percentile vlastnej minulosti. Nová vlastnosť pridáva
jeden argument pre aj proti: obchody **s trendom** (100 zo 146) majú break-even 0,141 %, **proti
trendu** (46) len 0,027 % — edge teda sedí v dvoch tretinách obchodov a tretina ho len riedi. Proti
hovorí vzorka: 90 % interval break-evenu 0,054–0,160 % je široký, rok 2021/22 (+22 %) nesie neúmerne
veľa a stredné dve obdobia (2023-01 – 2025-06) boli na 18. a 22. percentile.

**3. Čo treba dorobiť.** V stratégii to isté čo v IBS, v tomto poradí: (a) `minSlDistance` — štvrtina
obchodov so stopom pod 0,28 % ceny má break-even 0,019 % a bez nej by celok bol 0,165 %; (b) smer
voči trendu — skupina „proti trendu" je druhá najväčšia páka (+0,035) a riadi ju existujúci
`useStructureFilter`, netreba nový filter; (c) `closeAtSessionEnd` — 26,7 % výstupov je na čase, nie
na pláne, a nikto nezmeral, či to pomáha. **Špecifické pre IBSNet** a dôležitejšie než všetky tri:
(d) prvý beh v NinjaTraderi — adaptér sa prekladá proti jeho DLL, ale Strategy Analyzer ho ešte
nevidel; treba porovnať počet zón a vstupov proti Freqtrade behu na tých istých dátach; (e) trailing
sa v NinjaTrader adaptéri posúva na zatvorení baru, kým Freqtrade ho vie z 1m detailu — pri zapnutom
`enableTrailing` sa výsledky rozídu a treba vedieť o koľko; (f) disciplína dvoch jadier: každá zmena
v `ibs` musí ísť aj do C#, inak parita potichu zmizne (stráži ju `test_csharp_parity.py`, ale len
keď ho niekto pustí).

**4. Čo otestovať ďalej.**

```bash
# a) po KAŽDEJ zmene logiky: sú jadrá stále to isté? (bar po bare, všetko zapnuté)
PY -m tester.compare.csharp_parity --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --from 2024-09-04 --to 2026-09-04 --set showElliott=true --set enableTrailing=true \
   --set tradeDirection=Indicator --set indAdx=true
# b) adaptér NinjaTrader: preklad proti DLL, potom inštalácia a beh v Strategy Analyzeri (MNQ 3m)
PY -m tradebot.adapters.ninjatrader check && PY -m tradebot.adapters.ninjatrader install
# c) ten istý C# engine emulátorom MultiCharts na NAS100 — referencia, s ktorou sa NinjaTrader porovná
PY -m tester.webapp.cli run --strategy ibsnet --engine multicharts --pair NAS100/USD \
   --profile docs/profily_archiv/ibs/nas100_dukas_3m.json --timerange 20240904-20250904 --note "referencia pre NinjaTrader"
# d) dve páky v stratégii, rovnako ako pri IBS
PY -m tester.webapp.cli sweep --strategy ibsnet --param minSlDistance=0.20:0.40:0.05@pct --goal break_even \
   --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json --timerange 20240904-20250904
PY -m tester.webapp.cli sweep --strategy ibsnet --param useStructureFilter=true,false --goal break_even \
   --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json --timerange 20240904-20250904
```

Čo by výsledok rozhodol: (a) či sa dá C# jadru ďalej veriť bez toho, aby sa meralo odznova; (b) či
adaptér v NinjaTraderi vôbec obchoduje to, čo engine chce — rozdiel v počte vstupov proti (c) má mať
vysvetlenie vo fill modeli, nie v signáloch; (d) či +0,059 a +0,035 break-evenu sú skutočné zlepšenia,
alebo tvar jedného okna.

**5. Je to použiteľné, alebo je to o ničom?** Pod Freqtrade **áno, presne v tej miere ako IBS**:
kandidát na malé riziko — pri účte 10 000 najviac 109 na obchod, aby 95 % ciest zostalo nad −20 % —,
nie hotový systém, a rok tichého behu je pri ňom normálny stav. Pre NinjaTrader je odpoveď **zatiaľ
nie**, a nie kvôli stratégii: signály sú overené, ale cesta od signálu k orderu u brokera nie. Kým
neprebehne bod 4b a jeho čísla nesadnú proti 4c, je NinjaTrader vetva preložený kód, nie overený
nástroj — a na živý účet nepatrí.

**6. Čo by som pridal.** K stratégii to isté čo pri IBS (veľkosť pozície škálovaná vzdialenosťou
stopu, posun stopu na nulu po 1R kvôli sériám 8–12 strát). K IBSNet jednu vec navyše, ktorá
z týchto čísel plynie priamo: **paritný test ako brána**, nie ako voliteľný nástroj — spúšťať
`csharp_parity` na jednom referenčnom okne v rámci `pytest` vždy, keď sú v sklade dáta (dnes beží len
golden okno a syntetické bary), a k NinjaTraderu rovnaký nástroj: export zoznamu zón a vstupov zo
Strategy Analyzera a jeho porovnanie s behom emulátora, tak ako sa IBS porovnáva s TradingView. Bez
toho sa o rozdiele medzi platformami dozvieme až z účtu.

<!-- POSUDOK KONIEC -->
