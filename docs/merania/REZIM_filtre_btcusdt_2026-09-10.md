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

## Záver

**Zistenie sa nepotvrdilo ako vlastnosť stratégie.** Drží na konfigurácii A vo všetkých
oknách a na konfigurácii B nedrží ani v polovici — pričom B má **šesťkrát viac obchodov na
okno**, teda je spoľahlivejšia. Keby bol efekt všeobecný, na B by musel byť vidieť lepšie,
nie horšie.

Možné čítania sú dve a rozhodnúť medzi nimi z týchto dát nejde:

1. Efekt je vlastnosťou **konfigurácie A** (Long only + NY seansa + štruktúrny filter), nie
   stratégie ako takej.
2. Konzistencia v A je artefakt malej vzorky. Menšinová skupina má v A päť až deväť
   obchodov a break-even z piatich obchodov je takmer šum; 5 z 5 rovnakých znamienok má
   pri hode mincou pravdepodobnosť 3 %, čo je málo, ale nie zanedbateľne.

**Pôvodné číslo (3× a 5×) neplatí.** Vzniklo zliatím desiatich behov rôznych konfigurácií
dokopy — a zliatie mieša populácie, ktoré sa chovajú inak. To je presne tá chyba, pred
ktorou analytika varuje pri zmiešaných pároch; pri zmiešaných *konfiguráciách* nevarovala.

## Čo z toho vypadlo ako oprava

`regime_pos` meral **surovú** polohu v rozsahu, nie polohu v smere obchodu. Pre short je
spodok rozsahu to isté, čo pre long vrch, takže na konfigurácii s polovicou shortov (B) sa
tie dve skupiny navzájom prekrývali a efekt sa rušil. Po oprave sú jednotlivé okná v B
výraznejšie (napr. 2025-26: +0,1123 oproti −0,0149), ale konzistencia naprieč oknami sa
neobjavila — takže to bola chyba merania, nie príčina záveru.

## Čo ďalej

- Pustiť to isté na konfigurácii A s **dlhším oknom** alebo na viacerých trhoch, aby mala
  menšinová skupina viac než päť obchodov. Bez toho sa medzi čítaniami 1 a 2 rozhodnúť nedá.
- Analytike by pomohlo varovanie pri **zmiešaných konfiguráciách** rovnako, ako ho už má pri
  zmiešaných pároch.
