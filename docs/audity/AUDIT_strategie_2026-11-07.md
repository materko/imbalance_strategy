# Audit stratégií na stránke výsledkov — 2026-11-07

Bod 5 týždenného zadania (31. 10.–8. 11. 2026): stratégie zo stránky TradeBot výsledky roztriedené podľa toho, či fungujú (kroky smernice 4–9) a na aký trh sa najlepšie hodia. Čísla sú najlepšie nastavenie stratégie, 1 kontrakt, s poplatkom; ladenie 10/2021–9/2025, odložený rok 9/2025–9/2026.

## A — funguje (forward test / live)

Funguje — prešla smernicou, iný trh, 2× poplatok aj oneskorený vstup držia, odložený rok PF ≥ 1,4, žiadny rok ladenia pod 1,2. Na forward test / live.

| stratégia | trh | PF ladenie | najhorší rok | PF odložený rok | obch/rok | WR | max DD $ | iný trh (krok 8) | live | prečo nie A |
|---|---|---|---|---|---|---|---|---|---|---|
| SPRÁVY (MGC) (`spravy`) | Zlato (MGC) | 4,20 | 3,03 | 3,18 | 38 | 72 % | 729 | nebežal PF – (–/5) |  | – |
| IBS Entry Zone (`ibsentry`) | Nasdaq (MNQ) | 1,47 | 1,22 | 1,81 | 152 | 75 % | 7,150 | NAS100 PF 1.33 (4/5) | ● beží | – |
| TKS 1.0 (NQ Kompas) (`tks`) | Nasdaq (MNQ) | 1,48 | 1,22 | 1,74 | 170 | 73 % | 2,667 | NAS100 PF 1.31 (5/5) | ● beží | – |
| SIGMA (MGC) (`sigmamgc`) | Zlato (MGC) | 1,37 | 1,24 | 1,74 | 186 | 51 % | 1,163 | XAU/USD PF 1.26 (4/5) |  | – |
| SIGMA (MNQ) (`sigma`) | Nasdaq (MNQ) | 1,33 | 1,23 | 1,67 | 170 | 56 % | 3,424 | NAS100 PF 1.34 (5/5) |  | – |
| NOA 1.0 (`noa`) | Nasdaq (MNQ) | 1,94 | 1,62 | 1,56 | 156 | 41 % | 1,324 | NAS100 PF 1.61 (5/5) | ● beží | – |
| VWAP ORB (`vwaporb`) | Nasdaq (MNQ) | 1,55 | 1,21 | 1,53 | 165 | 74 % | 3,213 | NAS100 PF 1.13 (4/5) | ● beží | – |
| WILLIAMS %R (MNQ) (`wpr`) | Nasdaq (MNQ) | 1,34 | 1,27 | 1,50 | 182 | 66 % | 463 | NAS100 PF 1.15 (4/5) |  | – |
| Volt Break (`voltbreak`) | Nasdaq (MNQ) | 1,45 | 1,41 | 1,43 | 156 | 55 % | 1,148 | NAS100 PF 1.31 (5/5) |  | – |
| IBS EZ ES (`ibsentryes`) | S&P 500 (ES) | 1,32 | 1,23 | 1,40 | 174 | 74 % | 8,517 | US500 PF 1.12 (4/5) | ● beží | – |

## B — funguje s výhradou

Funguje s výhradou — prešla smernicou, ale jedna z podmienok A chýba (je vypísaná). Forward test, menšia veľkosť.

| stratégia | trh | PF ladenie | najhorší rok | PF odložený rok | obch/rok | WR | max DD $ | iný trh (krok 8) | live | prečo nie A |
|---|---|---|---|---|---|---|---|---|---|---|
| WILLIAMS %R (MGC) (`wprmgc`) | Zlato (MGC) | 1,49 | 1,30 | 2,05 | 173 | 69 % | 616 | XAU/USD PF 1.73 (3/5) |  | iný trh (XAU/USD) neprešiel |
| WILLIAMS %R (ES) (`wpres`) | S&P 500 (ES) | 1,64 | 1,32 | 2,01 | 157 | 72 % | 3,354 | US500 PF 0.96 (3/5) |  | iný trh (US500) neprešiel |
| IVB (ES) (`ivbes`) | S&P 500 (ES) | 1,70 | 1,29 | 1,79 | 165 | 92 % | 7,322 | US500 PF 1.41 (3/5) |  | iný trh (US500) neprešiel |
| LONDON IFVG (ES) (`lliqes`) | S&P 500 (ES) | 1,38 | 0,93 | 1,77 | 187 | 88 % | 4,004 | US500 PF 1.23 (3/5) |  | iný trh (US500) neprešiel; najhorší rok ladenia PF 0.93 |
| ORB 15/5 (MNQ) (`orb15`) | Nasdaq (MNQ) | 1,36 | 1,11 | 1,70 | 150 | 64 % | 2,636 | NAS100 PF 1.39 (5/5) |  | najhorší rok ladenia PF 1.11 |
| NQ PRECISION (MNQ) (`nqprec`) | Nasdaq (MNQ) | 1,44 | 1,06 | 1,68 | 189 | 92 % | 575 | NAS100 PF 0.82 (1/5) |  | iný trh (NAS100) neprešiel; vstup o sviečku neskôr nedrží; najhorší rok ladenia PF 1.06 |
| IVB (MNQ) (`ivb`) | Nasdaq (MNQ) | 1,51 | 1,26 | 1,63 | 207 | 92 % | 902 | NAS100 PF 1.24 (4/5) |  | vstup o sviečku neskôr nedrží |
| ORB 15/5 (MGC) (`orb15mgc`) | Zlato (MGC) | 1,31 | 1,11 | 1,61 | 176 | 37 % | 1,499 | XAU/USD PF 1.43 (4/5) |  | najhorší rok ladenia PF 1.11 |
| Volume Profile POC (`svp`) | Nasdaq (MNQ) | 1,46 | 1,03 | 1,59 | 161 | 50 % | 1,755 | NAS100 PF 1.18 (4/5) |  | najhorší rok ladenia PF 1.03 |
| LONDON IFVG (MGC) (`lliqmgc`) | Zlato (MGC) | 1,30 | 0,91 | 1,58 | 150 | 28 % | 823 | XAU/USD PF 1.2 (3/5) |  | iný trh (XAU/USD) neprešiel; najhorší rok ladenia PF 0.91 |
| Fibo 1.0 (MGC) (`fibomgc`) | Zlato (MGC) | 1,34 | 1,22 | 1,55 | 170 | 64 % | 1,380 | XAU/USD PF 0.0 (0/5) | ● beží | iný trh (XAU/USD) neprešiel |
| JSS (`jss`) | Nasdaq (MNQ) | 1,41 | 1,33 | 1,53 | 150 | 39 % | 1,985 | NAS100 PF 1.1 (3/5) |  | iný trh (NAS100) neprešiel |
| NY VA BREAKOUT ES (`nyvaes`) | S&P 500 (ES) | 1,40 | 1,28 | 1,40 | 152 | 73 % | 4,318 | US500 PF 1.09 (3/5) | ● beží | iný trh (US500) neprešiel; vstup o sviečku neskôr nedrží; odložený rok PF 1.40 < 1,4 |
| DAILY OPEN (`dailyopen`) | Nasdaq (MNQ) | 1,51 | 1,10 | 1,38 | 154 | 91 % | 1,109 | NAS100 PF 1.43 (5/5) |  | odložený rok PF 1.38 < 1,4; najhorší rok ladenia PF 1.10 |
| ORB 15/5 (ES) (`orb15es`) | S&P 500 (ES) | 1,43 | 1,23 | 1,38 | 178 | 73 % | 15,189 | US500 PF 1.31 (5/5) |  | odložený rok PF 1.38 < 1,4 |
| CRT + TBS (`crt`) | Nasdaq (MNQ) | 1,30 | 1,25 | 1,35 | 167 | 55 % | 1,333 | NAS100 PF 1.01 (3/5) |  | iný trh (NAS100) neprešiel; odložený rok PF 1.35 < 1,4 |
| IVB (MGC) (`ivbmgc`) | Zlato (MGC) | 1,34 | 1,27 | 1,33 | 158 | 74 % | 314 | XAU/USD PF 1.21 (4/5) |  | odložený rok PF 1.33 < 1,4 |
| VWAP ADX Pullback (`vwapadx`) | Nasdaq (MNQ) | 1,48 | 1,24 | 1,32 | 174 | 68 % | 2,177 | NAS100 PF 0.93 (2/5) | ● beží | iný trh (NAS100) neprešiel; 2× poplatok nedrží; odložený rok PF 1.32 < 1,4 |
| FLASH ORB (MNQ) (`flashorb`) | Nasdaq (MNQ) | 1,38 | 1,18 | 1,32 | 158 | 56 % | 4,033 | NAS100 PF 1.37 (5/5) |  | odložený rok PF 1.32 < 1,4; najhorší rok ladenia PF 1.18 |
| SPX sila (`mag7`) | Nasdaq (MNQ) | 1,35 | 1,31 | 1,31 | 151 | 39 % | 1,543 | NAS100 PF 1.21 (5/5) |  | odložený rok PF 1.31 < 1,4 |

## C — nefunguje (zatiaľ)

Nefunguje (zatiaľ) — neprešla smernicou (odložený rok, plató alebo počet obchodov). Nie na live.

| stratégia | trh | PF ladenie | najhorší rok | PF odložený rok | obch/rok | WR | max DD $ | iný trh (krok 8) | live | prečo nie A |
|---|---|---|---|---|---|---|---|---|---|---|
| FLASH ORB (ES) (`flashorbes`) | S&P 500 (ES) | 1,41 | 1,19 | 1,16 | 153 | 72 % | 9,242 | – |  | kandidát — neprešiel odloženým rokom |
| NQ PRECISION (ES) (`nqpreces`) | S&P 500 (ES) | 1,45 | 1,20 | 1,13 | 153 | 89 % | 1,447 | – |  | kandidát — neprešiel odloženým rokom |
| SIGMA (ES) (`sigmaes`) | S&P 500 (ES) | 1,38 | 1,21 | 1,10 | 158 | 29 % | 14,139 | – |  | kandidát — neprešiel odloženým rokom |
| NQ PRECISION (MGC) (`nqprecmgc`) | Zlato (MGC) | 1,29 | 1,16 | – | 166 | 57 % | 481 | – |  | najlepší na ladení — odložený rok ešte nebežal |
| T-MEAN REV (MNQ) (`tmr`) | Nasdaq (MNQ) | 1,07 | 0,93 | – | 52 | 53 % | 1,471 | – |  | najlepší na ladení — odložený rok ešte nebežal |
| T-MEAN REV (ES) (`tmres`) | S&P 500 (ES) | 1,04 | 0,74 | – | 52 | 48 % | 25,345 | – |  | najlepší na ladení — odložený rok ešte nebežal |
| T-MEAN REV (MGC) (`tmrmgc`) | Zlato (MGC) | 0,93 | 0,74 | – | 52 | 46 % | 1,067 | – |  | najlepší na ladení — odložený rok ešte nebežal |
| FLASH ORB (MGC) (`flashorbmgc`) | Zlato (MGC) | 1,43 | 1,09 | – | 163 | 73 % | 676 | – |  | kandidát — plató pod 80 % |
| LONDON IFVG (MNQ) (`lliq`) | Nasdaq (MNQ) | 1,32 | 0,96 | – | 185 | 28 % | 1,344 | – |  | kandidát — plató pod 80 % |

## Podľa trhu

- **Nasdaq (MNQ):** IBS Entry Zone (A), TKS 1.0 (NQ Kompas) (A), SIGMA (MNQ) (A), NOA 1.0 (A), VWAP ORB (A), WILLIAMS %R (MNQ) (A), Volt Break (A), ORB 15/5 (MNQ) (B), NQ PRECISION (MNQ) (B), IVB (MNQ) (B), Volume Profile POC (B), JSS (B), DAILY OPEN (B), CRT + TBS (B), VWAP ADX Pullback (B), FLASH ORB (MNQ) (B), SPX sila (B), T-MEAN REV (MNQ) (C), LONDON IFVG (MNQ) (C)
- **S&P 500 (ES):** IBS EZ ES (A), WILLIAMS %R (ES) (B), IVB (ES) (B), LONDON IFVG (ES) (B), NY VA BREAKOUT ES (B), ORB 15/5 (ES) (B), FLASH ORB (ES) (C), NQ PRECISION (ES) (C), SIGMA (ES) (C), T-MEAN REV (ES) (C)
- **Zlato (MGC):** SPRÁVY (MGC) (A), SIGMA (MGC) (A), WILLIAMS %R (MGC) (B), ORB 15/5 (MGC) (B), LONDON IFVG (MGC) (B), Fibo 1.0 (MGC) (B), IVB (MGC) (B), NQ PRECISION (MGC) (C), T-MEAN REV (MGC) (C), FLASH ORB (MGC) (C)

## Rovnaká logika na viacerých trhoch — kde sa hodí najlepšie

| stratégia | najlepší trh | poradie (trh · trieda · PF odloženého roka) |
|---|---|---|
| Flash ORB | Nasdaq (MNQ) | Nasdaq (MNQ) B 1,32 · S&P 500 (ES) C 1,16 · Zlato (MGC) C – |
| IBS Entry Zone | Nasdaq (MNQ) | Nasdaq (MNQ) A 1,81 · S&P 500 (ES) A 1,40 |
| IVB | S&P 500 (ES) | S&P 500 (ES) B 1,79 · Nasdaq (MNQ) B 1,63 · Zlato (MGC) B 1,33 |
| London IFVG | S&P 500 (ES) | S&P 500 (ES) B 1,77 · Zlato (MGC) B 1,58 · Nasdaq (MNQ) C – |
| NQ Precision | Nasdaq (MNQ) | Nasdaq (MNQ) B 1,68 · S&P 500 (ES) C 1,13 · Zlato (MGC) C – |
| NY VA Breakout | S&P 500 (ES) | S&P 500 (ES) B 1,40 |
| ORB 15/5 | Nasdaq (MNQ) | Nasdaq (MNQ) B 1,70 · Zlato (MGC) B 1,61 · S&P 500 (ES) B 1,38 |
| Sigma Breakout | Zlato (MGC) | Zlato (MGC) A 1,74 · Nasdaq (MNQ) A 1,67 · S&P 500 (ES) C 1,10 |
| T-Mean Reversion | Nasdaq (MNQ) | Nasdaq (MNQ) C – · S&P 500 (ES) C – · Zlato (MGC) C – |
| Williams %R | Nasdaq (MNQ) | Nasdaq (MNQ) A 1,50 · Zlato (MGC) B 2,05 · S&P 500 (ES) B 2,01 |

## Poznámky

- Deflated Sharpe (krok 9) neprejde žiadna stratégia — pri desiatkach tisíc skúšaných kombinácií je to očakávané; je to len informácia (smernica, 29. 10.), nie kritérium triedy.
- Trieda C neznamená, že logika je zlá: T-Mean Reversion má z princípu ~25–40 obchodov za rok (hranica 150), ostatné C neprešli odloženým rokom alebo plató.
- Pred live: forward test 4–8 týždňov (krok 10) aj pre triedu A.
