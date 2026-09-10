# Základná analytika — Market Structure BOS / CHoCH (`structure`)

Zmerané 2026-09-10 na `BTC/USDT:USDT` 5m, engine `freqtrade`, poplatok 0.0500 % na stranu (Binance USDⓈ-M taker, VIP 0), profil `binance_btcusdt_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy structure \
   --profile binance_btcusdt_5m \
   --timeframe 5m
```

## V čom je dobrá

- 2606 obchodov spolu — na štatistiku dosť
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0078 % je pod poplatkom 0.0500 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 100.0 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.3 sigma) — výber vstupu nepridáva nič
- najhoršia skupina 'sviatok v USA (Deň M. L. Kinga)' vlastnosti 'Sviatok na burze v USA': 8 obchodov (0.3 %), bez nej by break-even bol o +0.0207 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 566 | -67.47 | -0.0083 | 71.2 | 32.7 | `20260910-113600-b3415b` |
| 20221001-20231001 | 414 | -55.54 | 0.0080 | 61.3 | 34.5 | `20260910-113816-7b47d3` |
| 20231001-20241001 | 580 | -98.53 | -0.0574 | 98.6 | 30.3 | `20260910-114036-f76eaa` |
| 20240904-20250904 | 630 | -92.79 | -0.0034 | 93.6 | 32.1 | `20260910-114252-353759` |
| 20250904-20260904 | 416 | -58.94 | 0.0060 | 60.9 | 33.9 | `20260910-114512-e6f6b0` |

Zisková v **0 z 5** okien, obchodov spolu 2606, break-even celkom -0.0078 %.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.71 ATR za 5 barov)
- medián držania 54 barov grafu
- winrate 32.5 %, payoff 1.633
- 1.45 obchodov za deň
- šikmosť výnosov +1.106

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 50.2 %, `roi` 32.5 %, `trailing_stop_loss` 17.1 %, `force_exit` 0.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'sviatok v USA (Deň M. L. Kinga)' vlastnosti 'Sviatok na burze v USA': 8 obchodov (0.3 %), break-even -0.2947 % oproti -0.0078 % celku. Bez nej by break-even bol -0.007 % (+0.0207). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| sviatok v USA (Deň M. L. Kinga) | 8 | 0.3 % | 12.5 | -0.2947 | -0.0070 | +0.0008 |
| polovičný deň (deň pred Dňom nezávislosti) | 9 | 0.3 % | 22.2 | -0.1728 | -0.0073 | +0.0005 |
| polovičný deň (deň po Vďakyvzdaní) | 11 | 0.4 % | 27.3 | -0.0584 | -0.0075 | +0.0003 |
| sviatok v USA (Deň nezávislosti) | 13 | 0.5 % | 23.1 | -0.0131 | -0.0078 | +0.0000 |
| deň pred sviatkom | 50 | 1.9 % | 30.0 | -0.0119 | -0.0077 | +0.0001 |
| bežný deň | 2421 | 92.9 % | 32.5 | -0.0093 | 0.0129 | +0.0207 |
| deň po sviatku | 63 | 2.4 % | 44.4 | 0.1469 | -0.0116 | -0.0038 |

**Hodina vstupu (UTC)** (riadi `useSession`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 6 h – 13 h | 691 | 26.5 % | 28.6 | -0.0386 | 0.0046 | +0.0124 |
| do 6 h | 659 | 25.3 % | 33.7 | -0.0010 | -0.0104 | -0.0026 |
| 13 h – 18 h | 665 | 25.5 % | 33.4 | 0.0021 | -0.0105 | -0.0027 |
| nad 18 h | 591 | 22.7 % | 34.7 | 0.0139 | -0.0140 | -0.0062 |

**Kalendárny mesiac**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 01 | 217 | 8.3 % | 26.7 | -0.0761 | -0.0011 | +0.0067 |
| 07 | 316 | 12.1 % | 28.5 | -0.0630 | -0.0009 | +0.0069 |
| 10 | 219 | 8.4 % | 29.7 | -0.0367 | -0.0046 | +0.0032 |
| 09 | 243 | 9.3 % | 30.0 | -0.0352 | -0.0051 | +0.0027 |
| … | | | | | | |
| 12 | 128 | 4.9 % | 35.2 | 0.0215 | -0.0093 | -0.0015 |
| 11 | 198 | 7.6 % | 36.4 | 0.0320 | -0.0116 | -0.0038 |
| 04 | 193 | 7.4 % | 38.3 | 0.0470 | -0.0124 | -0.0046 |
| 08 | 238 | 9.1 % | 36.1 | 0.0568 | -0.0128 | -0.0050 |

Parametre, ktorými sa dá s tým niečo spraviť: `exitMode`, `slBuffer`, `tradeDirection`, `useSession`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0049 % | 0.0001 % ± 0.0142 | -0.35 | 35.6 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0049 % | 0.0001 % ± 0.0142 | -0.35 | 35.6 |

Neodlisitelne od nahody (-0.3 sigma, percentil 35.6). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 645 | 43.7 | 31.8 | -0.0202 | 30 |
| 2022-12 - 2024-03 | 594 | 40.3 | 32.3 | -0.0123 | 43 |
| 2024-03 - 2025-06 | 795 | 53.9 | 34.0 | 0.0073 | 78 |
| 2025-06 - 2026-09 | 572 | 38.8 | 31.5 | -0.0073 | 52 |

Hranice pre úsek veľkosti posledného obdobia: -0.0455 až +0.0278 % (medián -0.0084).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 52. percentile, teda v medziach -0.0455 až +0.0278 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0078 %**, medián -0.0079 %, 90 % interval -0.0248–0.0089 %
- P(edge > poplatok) = **0.0 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 18, 95. percentil 25 obchodov
- pravdepodobnosť ruiny účtu: 100.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **4** na obchod pri účte 10 000

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
<!-- POSUDOK cisla=319ed8ae -->

**Zhrnutie:** stratégia **funguje ako kód a nefunguje ako obchod** — a to druhé sa dá povedať
oveľa presnejšie než „nezarába". Pri `rrRatio = 2` je hranica ziskovosti pred nákladmi
winrate **33,3 %**; nameraných je **32,5 %** na 2 606 obchodoch. Výber vstupu podľa štruktúry
teda dáva presne to, čo dá geometria RR 2 sama od seba, a test proti náhode to potvrdzuje
nezávisle (−0,35 sigma, 35,6. percentil). Break-even −0,0078 % proti poplatku 0,0500 %
nie je „skoro tam": je to nula.

**Nie je to vlastnosť jedného nastavenia.** Zmerané sú **obidve rodiny výstupov a všetky tri
varianty vstupu, každý na piatich referenčných oknách** — break-even (% na stranu, latka 0,0500):

| variant | 2021-22 | 2022-23 | 2023-24 | 2024-25 | 2025-26 |
|---|---|---|---|---|---|
| `choch` + RR 2 (profil) | −0,0083 | **+0,0080** | −0,0574 | −0,0034 | **+0,0060** |
| `bos` + RR 2 | −0,0245 | **+0,0036** | −0,0372 | −0,0159 | **+0,0287** |
| `sweep` + RR 2 | **+0,0025** | −0,0005 | −0,0160 | **+0,0001** | −0,0054 |
| `sweep` + stop 1,5 ATR | −0,0078 | −0,0007 | **+0,0034** | **+0,0005** | −0,0050 |
| `choch` + `exitMode=structure` | **+0,0127** | **+0,0021** | **+0,0086** | −0,0013 | −0,0030 |

Dvadsaťpäť meraní sa zmestí do pásma ±0,03 % okolo nuly a znamienka sa striedajú bez
pravidla. To nie je „raz vyšla, raz nie" — to je rozdelenie okolo nuly.

**1. Na čo sa to hodí a na čo nie.** Na BTC/USDT futures 5m na obchodovanie **nie**, a je
jedno, s akým účtom. Ako **nástroj** sa balík hodí na tri veci: je to druhý archetyp v
registry (protitrendový `sweep` vedľa IBS prerazenia), je to **negatívna kontrola** vedľa
`demo_breakout` (tá je záporná, táto je nulová — sú to dva rôzne druhy „nefunguje") a je to
**referenčná implementácia potvrdeného swingu**, ktorú si môže požičať každá ďalšia
štruktúrna myšlienka. Sizing profilu (100 $ rizika na účte 10 000) sa na obchodovanie nehodí
ani teoreticky: Monte Carlo dáva pravdepodobnosť ruiny 100 % a odporúča **≤ 4 $ na obchod**.
Pri 1,45 obchodu denne a nulovom edge je to matematika, nie smola.

**2. Má to potenciál?** Na BTC nie, a hovoria to tri nezávislé merania: nula z piatich okien,
−0,35 sigma proti náhodným vstupom a P(edge > poplatok) = 0,0 %. Test úpadku hlási `DRZI`,
čo tu neznamená „drží sa", ale „nič sa nemení" — posledné obdobie je na 52. percentile
vlastnej minulosti, teda presne tam, kde všetky ostatné: pod poplatkom.

**Jedno miesto, kde potenciál vidieť je, ale je to inde:** matica trhov (okno
2024-09 → 2025-09, 3m, 16 trhov) dala **kladný break-even na 10 z nich** a nie sú to náhodné
trhy — sú to tie **pomalšie**: COFFEE +0,1031 %, COCOA +0,0765 %, ETH/USD (spot) +0,0339 %,
NGAS +0,0246 %, US500 +0,0240 %, XAU +0,0215 %. Krypto futures, na ktorých je celá analytika
vyššie, sú v tom rebríčku takmer na konci (BTC +0,0079 %). Dáva to zmysel: štruktúra je
tvrdenie o tom, že pohyb má pokračovanie, a na 5m krypte je pokračovania najmenej. **Je to
jedno okno a jeden TF, takže je to hypotéza, nie zistenie** — ale je to jediná hypotéza,
ktorú tieto čísla ponúkajú, a je lacné ju rozhodnúť (bod 4).

**3. Čo treba dorobiť.** Nie doladiť — chýbajú celé mechanizmy:

- **Žiadny filter režimu.** Štruktúrny prielom v rozsahovom trhu je falošný takmer vždy, a
  práve tie tvoria väčšinu z tých ~500 obchodov ročne. Toto je najväčšia diera a v tabuľke
  vlastností je vidieť jej okraj: hodiny 6–13 UTC (ázijsko-európske pásmo, najužší rozsah dňa)
  majú break-even −0,0386 % oproti −0,0078 % celku, kým hodiny nad 18 UTC +0,0139 %.
- **Prielom sa nemeria.** Zavretie o tick nad úrovňou a zavretie o 2 ATR nad ňou sú dnes tá
  istá udalosť. Prah „o koľko musí bar zavrieť za úrovňou" v `atr` chýba.
- **Nič nebráni okamžitému znovuvstupu.** Po strate je štruktúra stále prerazená a ďalšia
  udalosť príde o pár barov.
- **`minSwingSize` je vypnutý** (default 0) a nikdy sa nemeral. Je to jediný existujúci
  filter šumu a nevie sa, či niečo robí.
- **Sizing profilu.** Viď bod 1; navyše to **kazí aj meranie**: pri účte 10 000 sa stake
  oreže, keď peňaženka klesne, riziko na obchod prestane byť konštantné a break-even sa
  posunie. V okne 2023-24 je to rozdiel −0,0574 % (účet 10 000) proti **−0,0301 %**
  (ten istý beh s peňaženkou 1 000 000, `20260910-131305-d167d2`). Verdikt to nemení, ale
  číslo v tabuľke vyššie je v tom jednom okne pesimistickejšie, než edge naozaj je.

**4. Čo otestovať ďalej.** V tomto poradí; prvé dva sú lacné a rozhodnú, či má zmysel tretí:

```bash
# a) Drží ten kladný break-even na pomalých trhoch aj mimo jedného okna? Toto je
#    jediná otázka, ktorá môže zmeniť odpoveď na bod 5.
for W in 20211001-20221001 20221001-20231001 20231001-20241001 20240904-20250904 20250904-20260904; do
  PY -m tester.webapp.cli run --strategy structure --profile binance_btcusdt_5m \
     --pair XAU/USD --timeframe 15m --timerange $W --wallet 1000000 --note "struktura: zlato, $W"
done
# b) Je edge otázkou timeframu? Štruktúra na 5m krypte môže byť len šum barov.
PY -m tester.webapp.cli matrix --strategy structure --profile binance_btcusdt_5m \
   --pairs BTC/USDT:USDT,ETH/USDT:USDT,XAU/USD,US500/USD --timeframes 5m,15m,30m,1h \
   --timerange 20240904-20250904 --note "struktura: pomaha vyssi TF?"
# c) Robí filter šumu vôbec niečo? (default je 0 = vypnutý a nikdy sa nemeral)
PY -m tester.webapp.cli sweep --strategy structure --param minSwingSize=0,0.5,1,1.5,2 \
   --profile binance_btcusdt_5m --timeframe 5m --timerange 20240904-20250904 --goal break_even
```

Čo by rozhodli: (a) päť okien na zlate — keby bol break-even kladný vo väčšine z nich, je to
prvá skutočná stopa a stratégia patrí na CFD vetvu (MultiCharts), nie na krypto; keby nie, je
matica len rozptylom jedného okna a odpoveď na bod 5 je definitívna. (b) či je vinník TF (na
5m sú „swingy" šum) alebo myšlienka. (c) či `minSwingSize` posúva break-even monotónne — ak
áno, chýba filter režimu presne tam, kde ho bod 3 hľadá. **Hyperopt zatiaľ nemá čo hľadať**:
priestor, v ktorom je všetko nula, mu dá to, čo v okne náhodou bolo.

**5. Je to použiteľné?** **Nie.** Na BTC 5m je to overené na 2 606 obchodoch, piatich oknách,
troch variantoch vstupu a dvoch rodinách výstupov — a je to nula, nie záporné číslo, ktoré by
sa dalo otočiť. Jediná vetva, ktorá ešte nie je uzavretá, je matica: pomalé trhy (zlato,
US500, kakao) majú kladný break-even, ale zatiaľ na jednom okne. Kým to nerozhodne test (4a),
je odpoveď „nie" — nie „ešte uvidíme".

**6. Čo by som pridal.** Jednu vec, a plynie priamo z čísel: **prah prielomu v ATR**. Dnes je
BOS aj CHoCH binárne — zavretie o tick za úrovňou váži rovnako ako zavretie o 2 ATR za ňou.
Winrate 32,5 % proti potrebným 33,3 % znamená, že setup nie je zlý, len sa **v tej istej
vrecke miešajú prielomy s prepichnutiami**. Jeden parameter (`minBreakSize` v `atr`, default 0
= dnešné správanie) by tie dve veci oddelil a dal by sa zmerať sweepom rovnako ako `minSwingSize`.
Až keby to nepomohlo ani na jednom z 16 trhov, je myšlienka „štruktúra ako signál" vyčerpaná.

**Čo z toho platí pre IBS a pre rámec.** Dve veci, ktoré s touto stratégiou nesúvisia a našli
sa pri nej: (1) `cli matrix` účtoval poplatok **referenčného** páru všetkým bunkám, takže CFD
na kávu platilo Binance taker 0,05 % (opravené, poradie buniek to nemení — break-even od
poplatku nezávisí — ale PnL a profit factor cudzích buniek boli nezmysel); (2) odvodené
timeframy sa prerábali len keď **chýbali**, takže po pregenerovaní 1m zdroja ostala na disku
stará 5m séria a backtest ticho bežal na inej sérii, než akou sa plnili ordre (opravené aj
s testom). Prvé behy na syntetickom trhu boli práve preto neplatné; tie v tabuľke nižšie sú
už z opravených dát.

**Syntetický trh (bod 10 zadania, opravené dáta).** Break-even po oknách: −0,0130 / −0,0098 /
+0,0241 / −0,0096 / +0,0103 %, pri 609–810 obchodoch na okno — teda porovnateľná vzorka ako na
skutočnom BTC (414–630) a znamienka sa striedajú okolo nuly. **Na premiešanom trhu edge nie je**,
takže pohľad dopredu v engine nie je; potvrdenie swingu funguje tak, ako má.

<!-- POSUDOK KONIEC -->
