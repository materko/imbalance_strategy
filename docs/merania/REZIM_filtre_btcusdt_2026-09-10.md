# Režimové filtre na BINANCE:BTCUSDT.P (3m) — 2026-09-10

Analytika po pridaní stavu trhu (`tester.regime`) ukázala na zliatych 1247 obchodoch dve
silné zistenia: obchody **s trendom** majú trojnásobne lepší break-even než proti nemu
a vstupy pri **vrchu rozsahu** päťnásobne lepší než pri spodku. Toto meranie ich overuje
po jednotlivých referenčných oknách — a **nepotvrdzuje ich ako všeobecnú vlastnosť**.

## Ako sa to overovalo

Zliate čísla sa nekontrolujú zliatím ešte väčšieho celku. Vybrali sa dve **nezávislé** sady
behov, každá s jedným profilom na všetkých piatich referenčných oknách:

| sada | konfigurácia | obchodov na okno |
|---|---|---|
| A | `btcusdt_3m_binance_ny_sl_risk1` — Long only, NY seansa, štruktúrny filter zapnutý | 21–37 |
| B | Pine defaulty + víťaz hyperoptu (`rrRatio 4,7`, `slLookback 40`) — oba smery, bez filtra | 143–181 |

Delí sa pevnou hranicou (0,5 pre polohu v rozsahu), nie kvantilmi — inak by malo každé okno
inú hranicu a čísla by sa medzi oknami nedali porovnať. Hodnotí sa **znamienko po oknách**,
nie súčet.

## Sada A: efekt drží vo všetkých oknách

```
okno                 obchodov       s trendom     proti trendu
20211001-20221001          27    +0.1762 (21)     -0.1654 (6)
20221001-20231001          28    +0.1366 (20)     -0.0302 (8)
20231001-20241001          37    +0.1452 (21)    +0.0849 (16)
20240904-20250904          27    +0.2211 (21)     +0.0123 (6)
20250904-20260904          21    +0.1614 (16)     -0.1210 (5)
                        -> s trendom lepsie v 5 z 5 okien, median +0.2088

okno                 obchodov    vrch rozsahu   spodok rozsahu
20211001-20221001          27    +0.2142 (18)     -0.1302 (9)
20221001-20231001          28    +0.1266 (23)     -0.1018 (5)
20231001-20241001          37    +0.1894 (22)    +0.0183 (15)
20240904-20250904          27    +0.2044 (22)     +0.0408 (5)
                        -> vrch lepsi v 4 z 4 okien, median +0.1997
```

## Sada B: efekt nedrží

```
okno                 obchodov       s trendom     proti trendu
20211001-20221001         143    -0.0151 (83)    -0.0038 (60)
20221001-20231001         181   +0.0425 (116)    +0.0033 (65)
20231001-20241001         172    +0.0217 (99)    +0.0502 (73)
20240904-20250904         168   +0.0675 (102)    -0.0001 (66)
20250904-20260904         167   +0.0758 (113)    +0.0455 (54)
                        -> s trendom lepsie v 3 z 5 okien, median +0.0303

okno                 obchodov    vrch rozsahu   spodok rozsahu
20211001-20221001         143    -0.0336 (87)    +0.0262 (56)
20221001-20231001         181   +0.0669 (111)    -0.0323 (70)
20231001-20241001         172   +0.0333 (109)    +0.0346 (63)
20240904-20250904         168   +0.0404 (106)    +0.0419 (62)
20250904-20260904         167   +0.1123 (106)    -0.0149 (61)
                        -> vrch lepsi v 2 z 5 okien, median -0.0013
```

## Predbežný záver (pred overením na viacerých trhoch)

**Zistenie sa nepotvrdilo ako vlastnosť stratégie.** Drží na konfigurácii A vo všetkých
oknách a na konfigurácii B nedrží ani v polovici — pričom B má **šesťkrát viac obchodov na
okno**, teda je spoľahlivejšia. Keby bol efekt všeobecný, na B by musel byť vidieť lepšie,
nie horšie.

Možné čítania sú dve a z týchto dát sa medzi nimi rozhodnúť nedá — rozhodlo sa to až
overením na desiatich trhoch o sekciu nižšie:

1. Efekt je vlastnosťou **konfigurácie A** (Long only + NY seansa + štruktúrny filter), nie
   stratégie ako takej.
2. Konzistencia v A je artefakt malej vzorky. Menšinová skupina má v A päť až deväť
   obchodov a break-even z piatich obchodov je takmer šum; 5 z 5 rovnakých znamienok má
   pri hode mincou pravdepodobnosť 3 %, čo je málo, ale nie zanedbateľne.

**Pôvodné číslo (3× a 5×) neplatí.** Vzniklo zliatím desiatich behov rôznych konfigurácií
dokopy — a zliatie mieša populácie, ktoré sa chovajú inak. To je presne tá chyba, pred
ktorou analytika varuje pri zmiešaných pároch; pri zmiešaných *konfiguráciách* nevarovala.

## Overenie na desiatich trhoch: jedno zistenie drží, druhé nie

Predošlá časť skončila tým, že sa medzi čítaniami 1 a 2 rozhodnúť nedá, lebo menšinová
skupina má v konfigurácii A päť obchodov. Rozhodlo sa to tak, že sa tá istá konfigurácia
pustila na **desiatich trhoch × piatich oknách** (50 behov, matice `20260910-075*`).
Bunka ide do súčtu len vtedy, keď má **obe** skupiny aspoň päť obchodov.

Znamienkový test berie každú bunku ako jedno pozorovanie: keby efekt nebol, kladné
a záporné znamienko sú rovnako pravdepodobné.

### S trendom vs. proti trendu — **potvrdené**

```
trh                buniek  kladnych    median
BTC/USD                 4         3   +0.1519
BTC/USDT:USDT           5         5   +0.2041
DJ30/USD                1         1   +0.0091
ETH/USD                 5         5   +0.1220
ETH/USDT:USDT           5         4   +0.0429
NAS100/USD              2         2   +0.1099
NGAS/USD                2         2   +0.2031
WTI/USD                 1         1   +0.2680
XAU/USD                 1         0   -0.0029
                     ----      ----
spolu                  26        23   +0.1054     p = 0,00004
```

Kladné na **ôsmich z deviatich trhov** a v 23 z 26 buniek. Obchody s trendom majú
break-even v mediáne o **0,105 percentuálneho bodu** vyšší než obchody proti trendu — to
je pri poplatku 0,05 % rozdiel medzi „vyjde to" a „nevyjde".

### Vrch vs. spodok rozsahu — **nepotvrdené**

```
trh                buniek  kladnych    median
BTC/USDT:USDT           5         5   +0.1906
DJ30/USD                1         1   +0.1774
WTI/USD                 1         1   +0.1476
ETH/USDT:USDT           5         3   +0.0628
BTC/USD                 4         1   -0.0105
ETH/USD                 5         2   -0.0325
NAS100/USD              1         0   -0.0545
NGAS/USD                3         1   -0.0714
                     ----      ----
spolu                  25        14   +0.0628     p = 0,345
```

14 z 25 je prakticky hod mincou. A je tu jeden detail, ktorý to rozhoduje: **BTC/USDT:USDT
má 5 z 5, ale BTC/USD 1 zo 4.** To je ten istý podkladový trh z dvoch rôznych zdrojov
(Binance perpetuál a Dukascopy CFD). Keby bol efekt vlastnosťou trhu, musel by vyjsť na
oboch. Vyšiel na jednom, teda je to vlastnosť **tej jednej série** — buď jej
mikroštruktúry, alebo náhody v nej.

Práve na tomto sa vidí, načo je matica trhov dobrá: na jednom páre by to päť z piatich
okien vyzeralo ako zistenie.

### Čo to znamená pre stratégiu

Filter „obchoduj s trendom" je podložený a v IBS ho už zapína `useStructureFilter`;
konfigurácia A ho zapnutý má. Číslo hore hovorí, koľko ten filter stojí, keď sa vypne.

Filter na polohu v rozsahu podložený **nie je** a stavať na ňom sa nedá.

### Čomu ani toto číslo neverí

- **Bunky nie sú nezávislé.** Osem trhov v tom istom kalendárnom období sú korelované
  (obzvlášť BTC/USD s BTC/USDT:USDT a ETH/USD s ETH/USDT:USDT sú takmer tá istá vec), takže
  skutočný počet nezávislých pozorovaní je menší než 26 a `p` je optimistické. Aj po tomto
  zohľadnení ale ostáva rozdiel medzi 88 % a 56 % taký, že sa medzi tými dvoma zisteniami
  rozhodnúť dá.
- **Dve referenčné okná sa prekrývajú** o mesiac (`20231001-20241001` a `20240904-20250904`).
- **Menšinová skupina je stále malá** — v mnohých bunkách 5 až 10 obchodov. Preto sa
  nepočíta veľkosť efektu z jednej bunky, ale medián a znamienko naprieč bunkami.

## Čo z toho vypadlo ako oprava

`regime_pos` meral **surovú** polohu v rozsahu, nie polohu v smere obchodu. Pre short je
spodok rozsahu to isté, čo pre long vrch, takže na konfigurácii s polovicou shortov (B) sa
tie dve skupiny navzájom prekrývali a efekt sa rušil. Po oprave sú jednotlivé okná v B
výraznejšie (napr. 2025-26: +0,1123 oproti −0,0149), ale konzistencia naprieč oknami sa
neobjavila — takže to bola chyba merania, nie príčina záveru.

## Čo ďalej

- Analytike by pomohlo varovanie pri **zmiešaných konfiguráciách** rovnako, ako ho už má pri
  zmiešaných pároch. Práve zliatie desiatich behov rôznych konfigurácií vyrobilo pôvodné
  čísla 3× a 5×, ktoré neplatia.
- Zmerať, **koľko** filter „s trendom" prináša ako celok: `useStructureFilter` zapnutý
  oproti vypnutému na tých istých desiatich trhoch. Číslo hore je rozdiel medzi skupinami
  obchodov, nie rozdiel medzi dvoma behmi — to druhé je to, čo sa naozaj obchoduje.
