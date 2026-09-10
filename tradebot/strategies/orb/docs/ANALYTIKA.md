# Základná analytika — ORB — Opening Range Breakout (`orb`)

Zmerané 2026-09-10 na `NAS100/USD` 15m, engine `multicharts`, poplatok 0.0000 % na stranu (zadané cez --fee), profil `tester/profiles/ORB_RRR1.0_15m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy orb \
   --profile tester/profiles/ORB_RRR1.0_15m.json \
   --pair NAS100/USD \
   --timeframe 15m \
   --fee 0.0
```

## V čom je dobrá

- 648 obchodov spolu — na štatistiku dosť
- edge drží aj v poslednom období (2025-06 - 2026-09 na 76. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20231001-20241001 v strate)
- náklad na tomto trhu nepoznáme, takže break-even sa proti ničomu neposudzuje — doplň ho do inštrumentu (`half_spread_ticks`)
- 95. percentil max drawdownu 30.0 % (namerané 14.6 % medián) — na účet to treba mať
- proti náhode len +1.3 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 129 | +0.57 | 0.0009 | 6.9 | 48.8 | `20260910-094634-4125f3` |
| 20221001-20231001 | 123 | +2.42 | 0.0033 | 7.3 | 52.0 | `20260910-094637-f2c606` |
| 20231001-20241001 | 131 | -8.23 | -0.0078 | 9.3 | 46.6 | `20260910-094640-c1ea5b` |
| 20240904-20250904 | 132 | +8.41 | 0.0078 | 5.7 | 56.1 | `20260910-094643-0bba25` |
| 20250904-20260904 | 133 | +13.70 | 0.0142 | 9.5 | 57.1 | `20260910-094646-0686fa` |

Zisková v **4 z 5** okien, obchodov spolu 648, break-even celkom 0.0038 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.44 ATR za 5 barov)
- medián držania 1.5 barov grafu
- winrate 52.16 %, payoff 0.976
- 0.36 obchodov za deň
- šikmosť výnosov -0.075

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 52 %, `stop_loss` 47.8 %, `force_exit` 0.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0075 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 14 h | 393 | 60.6 % | 50.1 | -0.0009 | 0.0113 | +0.0075 |
| 15 h | 233 | 36.0 % | 54.5 | 0.0094 | 0.0009 | -0.0029 |
| 16 h | 22 | 3.4 % | 63.6 | 0.0258 | 0.0028 | -0.0010 |

**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pondelok | 131 | 20.2 % | 48.1 | -0.0044 | 0.0061 | +0.0023 |
| piatok | 130 | 20.1 % | 48.5 | -0.0038 | 0.0056 | +0.0018 |
| štvrtok | 135 | 20.8 % | 50.4 | -0.0020 | 0.0051 | +0.0013 |
| utorok | 128 | 19.8 % | 54.7 | 0.0094 | 0.0025 | -0.0013 |
| streda | 124 | 19.1 % | 59.7 | 0.0195 | -0.0004 | -0.0042 |

**Mesiac**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 2022-01 | 10 | 1.5 % | 20.0 | -0.1101 | 0.0048 | +0.0010 |
| 2024-09 | 18 | 2.8 % | 22.2 | -0.0765 | 0.0059 | +0.0021 |
| 2026-07 | 10 | 1.5 % | 20.0 | -0.0591 | 0.0047 | +0.0009 |
| 2023-09 | 10 | 1.5 % | 20.0 | -0.0577 | 0.0049 | +0.0011 |
| … | | | | | | |
| 2021-12 | 9 | 1.4 % | 66.7 | 0.0697 | 0.0033 | -0.0005 |
| 2026-01 | 10 | 1.5 % | 90.0 | 0.0834 | 0.0024 | -0.0014 |
| 2025-04 | 8 | 1.2 % | 75.0 | 0.1116 | 0.0030 | -0.0008 |
| 2022-12 | 8 | 1.2 % | 75.0 | 0.1136 | 0.0031 | -0.0007 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0076 % | 0.0013 % ± 0.0049 | +1.28 | 90.4 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0076 % | 0.0012 % ± 0.0058 | +1.11 | 86.9 |

Naznak, ale nie dokaz (1.3 sigma, percentil 90.4). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 155 | 10.5 | 51.0 | 0.0060 | 63 |
| 2022-12 - 2024-03 | 157 | 10.7 | 48.4 | -0.0053 | 14 |
| 2024-03 - 2025-06 | 167 | 11.3 | 52.7 | 0.0036 | 52 |
| 2025-06 - 2026-09 | 169 | 11.5 | 56.2 | 0.0103 | 76 |

Hranice pre úsek veľkosti posledného obdobia: -0.0106 až +0.0190 % (medián 0.0042).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 76. percentile, teda v medziach -0.0106 až +0.0190 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0038 %**, medián 0.0038 %, 90 % interval -0.0037–0.0112 %
- P(edge > poplatok) = **79.8 %**
- max drawdown: medián 14.6 %, 95. percentil 30.0 %, najhorší 71.4 %
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
<!-- POSUDOK cisla=3cfe0a11 -->

**1. Na čo sa to hodí a na čo nie.**
Na `NAS100` 15m v newyorskej seanse — a prakticky nikde inde. Nižšie timeframy sú namerane
mŕtve: ten istý set dal na 1m–5m profit factor 0.96–1.11, až 15m dá 1.72. Krypto vypadáva
z princípu, nie náhodou: BTC a ETH bežia 24/7, takže „otvorenie seansy" je tam ľubovoľná
hodina a range nemá o čo oprieť (nulltest tam dal +1.5 sigma). Londýnska seansa na NAS100
je stratová (PF 0.76) — index bez americkej účasti nemá kto hýbať. Veľkosť účtu je tu bez
problému, `NAS100` má point value 1.0, takže riziko 0.5 % sa nastaviť dá; na `WTI`
(point value 1000) alebo `XAU` (100) už nie a minimálny kontrakt prebije akékoľvek riziko.

**2. Má to potenciál?**
Za skutočným javom hovorí: zisková v 4 z 5 okien, 648 obchodov, úpadok edge v dátach vidieť
nie je (posledné obdobie na 76. percentile) a žiadna skupina obchodov výsledok výrazne
nekazí. Proti hovorí to podstatnejšie: **+1.28 / +1.11 sigma proti náhode je náznak, nie
dôkaz** — náhodné vstupy za tých istých pravidiel dajú takmer to isté. A hlavne: break-even
je **0.0038 %**, čo je zhruba spread na `NAS100` CFD (~1 bod z 23 800 = 0.004 %). Čísla
vyššie sú merané s poplatkom 0. **Pri reálnom náklade je edge zjedený celý.**
Winrate po oknách rastie (48.8 → 52.0 → 46.6 → 56.1 → 57.1 %), čo skôr než zlepšovanie
naznačuje závislosť na režime — posledné dva roky indexu priali.

**3. Čo treba dorobiť.**
Predovšetkým **náklad na trh** (`half_spread_ticks` do inštrumentu) — bez neho sa
break-even nemá proti čomu posudzovať a všetky závery visia vo vzduchu. Ďalej kalendár
sviatkov a skrátených seans (poldni po Dni vďakyvzdania sa opening range správa inak).
A chýba filter režimu: rozptyl winrate 46.6–57.1 % po rokoch pýta niečo, čo rozpozná,
kedy sa prerazenia platia a kedy nie.

**4. Čo otestovať ďalej.**
- `cli matrix --pairs all --timeframes 15m` — spravené, prešiel len `WTI` (+2.5 sigma);
  zlato, SP500, DJ30, DAX aj forex vypadli.
- `cli run --engine freqtrade` — čísla sú z emulátora MultiCharts; fill model sa líši
  a pri stratégii, ktorej edge je na úrovni spreadu, to rozhodne.
- `cli hyperopt --param rrRatio=1.0:2.0:0.1 --param slRangePct=10:60:5` s povinným
  overením na ďalších oknách. Rozhodne, či sa dá RRR zdvihnúť nad 1 bez straty winrate.
- Zopakovať checkup s reálnym poplatkom. To je test, po ktorom je jasno.

**5. Je to použiteľné, alebo je to o ničom?**
**Ako samostatná stratégia na prop účet použiteľné nie je.** Dôvod je jeden a je tvrdý:
edge veľkosti 0.0038 % break-even proti spreadu ~0.004 % znamená nulu, a +1.1 sigma proti
session náhode znamená, že to isté dostaneš hodom mincou v tom istom okne. Zmysel má ako
**referenčný bod** — ukazuje, koľko z výsledku inej stratégie je „len breakout v dobrom
čase". Presne na to sa tu použil a IBS proti nemu obstála (+5.0 sigma oproti +1.1).

**6. Čo by som pridal.**
Overnight gap. Rozdiel medzi včerajším close a dnešným open leží vo vnútri opening rangu
a nesie informáciu, ktorú range sám zahodí: meraný na 2 791 dňoch `NQ` má tiny gap
(< 0.3 ATR) **77.8 % pravdepodobnosť výplne** a s potvrdením prvej 15m sviečky až 93 %.
Prerazenie rangu **proti** nevyplnenej medzere je štatisticky slabšie než prerazenie
smerom k nej. Ako filter (alebo ako smerový bias) je to jeden riadok kódu a je to
nezávislý zdroj informácie — na rozdiel od ďalšieho ladenia tých istých prahov, ktoré
podľa `hyperopt.py` na tejto rodine stratégií out-of-sample neprežilo.

<!-- POSUDOK KONIEC -->
