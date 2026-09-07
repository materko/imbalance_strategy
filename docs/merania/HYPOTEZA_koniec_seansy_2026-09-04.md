# Prežijú obchody koniec seansy náhodou? (2026-09-04)

Zo sweepu RR vyšla nápadná štatistika: pri RR 5 tvorí celý čistý zisk 20 obchodov
zavretých na konci seansy a 18 z nich je ziskových. Tento zápis overuje, či to platí
aj inde a či sa to dá obchodovať.

## Naprieč rokmi to platí

| okno | obchodov | koniec seansy | **winrate** | podiel na hrubom zisku | ostatné výstupy |
|---|---|---|---|---|---|
| 2021-10 → 2022-10 | 209 | 17 | **82,4 %** | 126 % | 16,1 % |
| 2022-10 → 2023-10 | 248 | 21 | **95,2 %** | 13 % | 18,5 % |
| 2023-10 → 2024-10 | 212 | 17 | **94,1 %** | 844 % | 14,9 % |
| 2024-09 → 2025-09 | 181 | 16 | **81,2 %** | 123 % | 15,8 % |
| 2025-09 → 2026-09 | 176 | 20 | **90,0 %** | 95 % | 19,9 % |

Nikdy pod 81 %, kým ostatné výstupy majú 15–20 %. V štyroch z piatich rokov nesú
tieto obchody celý čistý zisk (podiel nad 100 % znamená, že zvyšok je stratový).

## Ale je to takmer celé tautológia

Obchod, ktorý trafí SL, zomrie **z definície** rýchlo — SL je blízko. „Prežil dlho"
a „nebol stratový" je preto čiastočne to isté tvrdenie. Rozhodujúca otázka znie inak:
**keď obchod prežije N minút, koľko zarobí od tej chvíle?**

| prežil aspoň | n | z toho ziskových | **zisk OD tej chvíle** | celý obchod |
|---|---|---|---|---|
| 15 min | 641 | 34,6 % | **+35,8** | +92,9 |
| 30 min | 512 | 39,8 % | **+38,6** | +136,2 |
| 60 min | 369 | 45,8 % | **+37,6** | +185,9 |
| 120 min | 218 | 57,3 % | **+42,1** | +245,9 |
| 240 min | 101 | 64,4 % | **−45,3** | +295,0 |

Zisk celého obchodu rastie z +93 na +295 bodov, ale **dopredný zisk je plochý na
~+38 bodoch** a po štyroch hodinách sa otočí do mínusu. +38 bodov pri cene ~80 000
je 0,05 % — teda **presne jeden round-trip poplatok**.

Keď obchod prežije, zisk už má *za sebou*, nie pred sebou. Držať ho ďalej zarobí
zhruba toľko, koľko stojí ho zavrieť. **Na vstupnú logiku sa to previesť nedá.**

## Čo z toho platí naozaj

Rozdelenie podľa dĺžky držania (1 026 obchodov, päť rokov, RR 5):

| držanie | n | WR | priemer (body) | spolu |
|---|---|---|---|---|
| < 15 min | 374 | 4,8 % | **−87,0** | −32 536 |
| 15–30 min | 137 | 12,4 % | **−86,8** | −11 889 |
| 30–60 min | 142 | 23,2 % | +2,5 | +356 |
| 60–120 min | 153 | 30,7 % | +114,5 | +17 512 |
| 120–240 min | 116 | 50,0 % | +205,8 | +23 874 |
| > 240 min | 104 | 64,4 % | +281,5 | +29 275 |

**Celá strata je v prvých 30 minútach** — 511 obchodov, −44 425 bodov. Všetko nad
30 minút zarobí dokopy +71 016. Vstupy sú teda v priemere okamžite zlé.

## Je SL príliš tesný? Áno — ale ukázalo sa to až na štyroch rokoch

Ak by nás tesný stop vyhadzoval z obchodov, ktoré by vyšli, širší SL by mal pomôcť.
`slLookback` berie najextrémnejší swing za N barov, takže väčšie N = širší stop
(a pri fixnom RR aj úmerne vzdialenejší TP).

Prvé dva behy si protirečili a vyzeralo to na šum:

| slLookback | 2025-09 → 2026-09 (ladené) | 2023-10 → 2024-10 |
|---|---|---|
| **10** (Pine default) | PF **1,515** | PF 1,022 |
| 20 | PF 1,329 | PF **1,169** |
| 30 | PF 1,218 | PF 1,145 |
| 50 | PF 1,155 | PF 1,036 |

Až po dobehnutí zvyšných rokov je vidieť, ktorý z tých dvoch je výnimka:

| okno | lb 10 | **lb 20** | |
|---|---|---|---|
| 2021-10 → 2022-10 | 0,0373 % | **0,0444 %** | lb 20 lepší |
| 2022-10 → 2023-10 | 0,0030 % | **0,0043 %** | lb 20 lepší |
| 2023-10 → 2024-10 | 0,0019 % | **0,0154 %** | lb 20 **8× lepší** |
| 2024-09 → 2025-09 | 0,0212 % | **0,0219 %** | remíza |
| **priemer OOS** | 0,0159 % | **0,0215 %** | **+36 %** |
| 2025-09 → 2026-09 (ladené) | **0,0375 %** | 0,0270 % | lb 10 lepší |

`slLookback 20` je lepší v **štyroch zo štyroch** out-of-sample rokov a horší práve
na tom jedinom, na ktorom sme celý čas pozerali. To je klasický obrázok toho, že
najlepšia hodnota nie je 10, ale že 10 sa nám na tom jednom roku páči.

Hypotéza teda **platí**: stop je tesnejší, než by mal byť. Efekt je ale malý —
priemerný break-even poplatok stúpne z 0,0159 % na 0,0215 %, teda stále **2,3× pod**
tým, čo berie Binance.

> **Poznámka k metóde:** prvá verzia tohto zápisu tvrdila opak („hypotéza sa
> nepotvrdila, `slLookback` je šum") na základe dvoch rokov. Dva roky na takýto
> záver nestačia — obzvlášť keď jeden z nich je ten, na ktorom sa hľadalo.

## Záver

1. Štatistika „koniec seansy = 90 % úspešnosť" **platí a je stabilná**, ale je to
   prežívací artefakt, nie obchodovateľný signál.
2. Dopredný výnos po prežití je ~jeden poplatok — držanie samo o sebe nezarába.
3. Strata je sústredená do prvých 30 minút po vstupe a **širší stop ju čiastočne
   zmierni** (`slLookback` 20 namiesto 10, +36 % k edge naprieč rokmi).
4. Ani tak to nestačí: 0,0215 % proti 0,05 %, ktoré berie Binance.
5. Ďalší zmysluplný test je odložiť vstup alebo pridať potvrdenie — nie ladiť
   ďalší prah. A merať to **na všetkých piatich rokoch naraz**, nie na jednom.
