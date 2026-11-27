# Agent B (Inžinier) — rozdelenie rokov len z dát, ktoré máme

*26. 11. 2026. Len `data/archive/tester/`, nič stiahnuté ani vyčistené. Odhad obchodov je pri 100 / 150 za rok.*

## Overené proti súborom
| trh (súbor) | prvá / posledná 1m sviečka | použiteľné | dôvod (`data_kvalita.json`, `data_noc_roly.json`) |
|---|---|---|---|
| ES `databento/futures/ES_USD-1m` | 2010-06-06 22:00 / **2026-10-19** | celé | jadro 98,1–99,5 %, noc 96–100 %, zlé tiky 0–30 za rok |
| MNQ `…/MNQ_USD-1m` | 2019-05-05 22:03 / **2026-11-09** | celé | jadro 98,1–98,8 %, noc 98–100 % |
| MYM `…/MYM_USD-1m` | 2019-06-02 22:00 / **2026-11-09** | deň celé, **noc bez 2019 a 2024** | noc 86,5 % (2019) a 94,8 % (2024) |
| MGC `…/MGC_USD-1m` | 2010-10-03 / **2026-09-16** | **len 2020-01-01 →** | 2010–19 jadro 8–92 %, noc 2–80 %, v januári 2011 kontrakty tam a späť |
| 6E `…/6E_USD-1m` | 2010-06-06 / **2026-09-28** | **len 2016-01-03 →** | 2010–15 má 220–636 zlých tikov za rok; od 2016 jadro ≥ 99,7 %, noc ≥ 95,7 % |
| BTC `binance/futures/BTC_USDT_USDT-1m-futures` | 2019-09-08 17:57 / **2026-09-04** | celé | 99,3–100 %, 0 dier |

- **Spálený pre všetkých:** rok A 2025-09-04 – 2026-09-03, len ako negatívna kontrola.
- **C** začína dňom po commite hraníc. Medzi koncom archívu (ES 19. 10., MGC 16. 9., 6E 28. 9., BTC 4. 9.) a C je
  diera, ktorú treba doplniť z rovnakého zdroja.

**Čo majú dnešné stratégie spálené** (`glsearch.py` IS/OOS/PERIODS, `OOS-STARE-ROKY/data/oos_all.tsv`, 145 behov):
- **Predvolene** sa ladí 2021-10-01 – 2025-09-04 a rok A je OOS.
- **EUR_KEYS** (`wpreur`, `asiasweepeur`, `mtkzoneeur`, `lliqeur`, `silverbulleteur`, `ibsentryeur`,
  `sweepengulfeur`) sa ladia 2016-01 – 2021-10, OOS majú 2021-10 – 2026-09.
- **`mtkorb`** sa ladí 2010-11 – 2024-09.
- **Triedením 26. 11. spálené:** ES 2010–21, MGC 2020–21, MNQ/MYM 2019–21, BTC 2019–21 a 6E 2016–21 pre rodiny
  v `oos_all.tsv`: IBS EZ (všetky), NOA (všetky), TKS, VWAP ORB, VWAP ADX, ORB 15/5, IVB, Sigma, Fibo, MTK ORB/Zone/EMAS,
  Williams R, SPRÁVY, CRT, JSS, Mag7, SVP, Noc + pondelok, ON bias ORB, Volt Break, Flash ORB, Range BTC, Sweep engulf,
  Daily open, M2 MNQ, NQ Precision MGC, LLIQ MGC.
- **Štúdie:** prieskum Nasdaqu `nocpon` MNQ 2019–26, KLZAKY (MTK EMAS) a SPRÁVY MGC 2010–21 (07).

---

## ES — 16,3 roka, najlepší trh
| oblasť | dátumy | roky | obch. 100 / 150 |
|---|---|---|---|
| L + WF 24/6 (~10 kúskov) | 2010-06-06 – 2017-09-30 | 7,3 | 730 / 1 100 |
| trezor B | 2017-10-01 – 2021-09-30 | 4,0 | 400 / 600 |
| (B2 len rodiny bez behu tam) | 2021-10-01 – 2025-09-03 | 3,9 | 390 / 585 |
| A spálený · C | 2025-09-04 – 2026-09-03 · od commitu | | |

- **Nové hypotézy:** ✅ je možné. B obsahuje Volmageddon 2018, Q4 2018 a covid.
- **Dnešné:**
  - rodiny z triedenia (IBS EZ ES, NY VA, ORB 15/5 ES, IVB ES, Williams R ES, MTK EMAS ES) → **len 🟡**, ostáva im C,
  - rodiny, ktoré na ES 2010–21 nikdy nebežali (`noaes`, `m2`, `flashorbes`, `nqpreces`), smú raz použiť
    B = 2010-06 – 2021-09 (11,3 r, ~1 100) → **✅ je možné**.

## MNQ — 7,5 roka, z toho 6,3 pred A
| variant | L + WF | trezor B | obch. v B 100 / 150 |
|---|---|---|---|
| **M1 (odporúčam pri 100–150 obch/rok)** | 2019-05-05 – 2022-09-30 · 3,4 r · WF 18/6 = 4 kúsky | 2022-10-01 – 2025-09-03 · 2,9 r | **290** / 435 |
| M2 (pri ≥ 150 obch/rok) | 2019-05-05 – 2023-09-30 · 4,4 r · WF 24/6 = 5 kúskov | 2023-10-01 – 2025-09-03 · 1,9 r | 190 / **285** |

- **Prečo M1:** M2 nesplní „≥ 2 roky“ a pri 150 obchodoch za rok ani 300. M1 nesplní 300 obchodov tesne pri 100 za
  rok (290), preto potrebuje **≥ 105 obchodov za rok**.
- **Režimy v M1:** L má covid, býka 2021 a pád v prvej polovici 2022. B má nízku volatilitu 2023–24 a pád v apríli
  2025. Iný režim treba zmerať (štvrťrok ATR mimo IQR L), pravdepodobne ho splní nízka volatilita 2023–24.
- **Čo M1 stráca:**
  - L má len 3,4 roka a WF beží s učením 18 mesiacov namiesto 24, takže kandidát sa učí z kratších dejín,
  - trezor je jediná cesta 2,9 roka, takže t ≥ 2 pri PF 1,2 potrebuje ~500 obchodov a tie M1 nemá. **✅ je možné
    len pri PF ≳ 1,3 po nákladoch alebo pri ≥ 170 obchodoch za rok.**
- **Nové:** ✅ je možné za podmienok vyššie.
- **Dnešné:**
  - rodiny z triedenia a `nocpon` → **len 🟡**, C ako trezor (≥ 2 r) by dalo ✅ najskôr 12/2028,
  - rodiny bez behu na 2019–21 smú raz B = 2019-05-05 – 2021-09-30 (2,4 r, 240 / 360) → ✅ pri ≥ 125 obch/rok.

## MYM — ako MNQ, s nočnou výhradou
- **Denné stratégie:** rovnaké dátumy a závery ako MNQ (M1, ≥ 105 obch/rok).
- **Nočné stratégie** (Noc + pondelok MYM a ďalšie): 2019 a 2024 sú pod 95 %, takže L by malo len 2020 – 9/2022 a B
  2022-10 – 2023-12 + 2025-01 – 2025-09. To je ~2 roky s dierou a 200 / 300 obchodov. **→ len 🟡.**
- **Dnešné:** `ibsentrymym`, `nocponmym`, `sigmamym` boli v triedení → len 🟡.

## MGC — 5,7 roka pred A (2020-01-01 – 2025-09-03)
| variant | L + WF | trezor B | obch. v B 100 / 150 |
|---|---|---|---|
| **G1 (najlepší kompromis)** | 2020-01-01 – 2022-12-31 · 3,0 r · WF 18/6 = 3 kúsky | 2023-01-01 – 2025-09-03 · 2,7 r | 270 / **400** |
| G2 | 2020-01-01 – 2023-09-30 · 3,75 r · WF 24/6 = 3 kúsky | 2023-10-01 – 2025-09-03 · 1,9 r | 190 / 285 |

- **Otvorene:** zlato pravidlo „≥ 2 roky a ≥ 300 obchodov a iný režim“ pri 100 obchodoch za rok **nesplní**. G1
  ho splní od ~112 obchodov za rok.
- **Režimy v G1:** L má covid, vrchol 2020 a pokles 2022 (−20 %). B je takmer celý jeden býk (+80 %), takže
  „pokles, ktorý v L nebol“ nesplní. Iný režim môže dať len vyššie ATR v roku 2025, treba ho zmerať.
- **Čo G1 stráca:**
  - len 3 WF kúsky, teda WF je slabý dôkaz,
  - trezor je jednosmerný trh, takže stratégia s longmi môže len zbierať rast (povinný test „kúp a drž“ z trend CFD
    smernice ostáva).
- **Nové:** ✅ je možné len pri ≥ 115 obchodoch za rok, ak sa iný režim potvrdí a ak stratégia porazí kúp a drž.
  Inak len 🟡 a dôkaz príde z C.
- **Dnešné:**
  - všetky MGC rodiny majú L 10/2021 – 9/2025, triedenie spálilo 2020–21, `mtkorb` ladila na 2010–24 a SPRÁVY
    videli 2010–21 → **len 🟡**,
  - rodiny mimo triedenia (`ibsentrymgc`, `scalp3mamgc`, `flashorbmgc`, `orb15mgc` je v triedení) majú voľných
    len 2020-01 – 2021-09 (1,75 r) → stále len 🟡.

## 6E — 9,7 roka pred A (2016-01-03 – 2025-09-03)
| oblasť | dátumy | roky | obch. 100 / 150 |
|---|---|---|---|
| L + WF 24/6 (~7 kúskov) | 2016-01-03 – 2021-09-30 | 5,75 | 575 / 860 |
| trezor B | 2021-10-01 – 2025-09-03 | 3,9 | 390 / 585 |
| A · C | 2025-09-04 – 2026-09-03 · od commitu | | |

- **Nové:** ✅ je možné. B má zvyšovanie sadzieb v roku 2022 a paritu EUR/USD, čo je jasne iný režim než nízka
  volatilita 2016–19.
- **Dnešné:**
  - EUR_KEYS majú L 2016–21 aj 2021–26 spálené → **len 🟡**,
  - `sdeur` a `m2eur` sa ladili predvolene (10/2021 – 9/2025) a v triedení neboli, takže **2016-01 – 2021-09
    (5,75 r) smú raz použiť ako trezor → ✅ je možné**,
  - `spravyeur` → 🟡, lebo kalendár pred 2021 obsahuje len ECB.

## BTC (Binance perp) — 6,0 roka pred A (2019-09-08 – 2025-09-03)
| variant | L + WF | trezor B | obch. v B 100 / 150 |
|---|---|---|---|
| **K1 (pri 100–150 obch/rok)** | 2019-09-08 – 2022-09-30 · 3,1 r · WF 18/6 = 3 kúsky | 2022-10-01 – 2025-09-03 · 2,9 r | 290 / 435 |
| K2 (pri ≥ 150, dohoda 11) | 2019-09-08 – 2023-09-03 · 4,0 r · WF 24/6 = 4 kúsky | 2023-09-04 – 2025-09-03 · 2,0 r | 200 / **300** |

- **Režimy:** K1 má v B pád FTX (11/2022) a býka po ETF 2024. K2 má v B len býka a apríl 2025, takže iný režim
  treba zmerať.
- **Nové:** K1 dáva ✅ pri ≥ 105 obchodoch za rok, K2 pri ≥ 150. Krypto stratégie 24/7 mávajú viac obchodov, preto
  K2, ak to hypotéza unesie.
- **Dnešné:**
  - `flashorbbtc`, `noabtc`, `rangebtc`, `sweepengulfbtc` boli v triedení → **len 🟡**,
  - BTC kópie mimo triedenia smú raz použiť B = 2019-09-08 – 2021-09-30 (2,1 r, 210 / 315) → ✅ pri ≥ 145 obch/rok.

---

## Súhrn
| trh | nové hypotézy | dnešné stratégie |
|---|---|---|
| ES | **✅** (L 7,3 r, B 4 r) | 🟡 rodiny z triedenia · **✅** `noaes`, `m2`, `flashorbes`, `nqpreces` (B 2010–21) |
| MNQ | ✅ pri ≥ 105 obch/rok (M1), WF slabší | 🟡 (✅ len pre rodiny bez behu na 2019–21, ≥ 125/rok) |
| MYM | denné ako MNQ, **nočné len 🟡** | 🟡 |
| MGC | ✅ len pri ≥ 115/rok, iný režim nutné zmerať, inak 🟡 | **🟡 všetky** |
| 6E | **✅** (L 5,75 r, B 3,9 r) | 🟡 EUR_KEYS · **✅** `sdeur`, `m2eur` (B 2016–21) |
| BTC | ✅ pri ≥ 105 (K1) alebo ≥ 150 (K2) | 🟡 (✅ BTC kópie mimo triedenia pri ≥ 145/rok) |

**Kompromisy a čo stoja:**
- Na MNQ, MYM, MGC a BTC sa ladenie skracuje na 3–3,4 roka a WF na 18/6 (3–4 kúsky). Trezor je jeden blok
  2,7–2,9 roka, takže dôkaz unesie len stratégia s vyšším PF alebo počtom obchodov.
- Kde trezor nestačí, ostáva **WF ako hlavný dôkaz + C ≥ 2 roky** a stav do vtedy 🟡.
- Dnešné stratégie z triedenia (všetky, ktoré dnes bežia naživo) nemajú v dátach, ktoré máme, **žiadny čistý
  trezor**. Najviac dostanú 🟡 a ✅ najskôr z C (12/2028).
