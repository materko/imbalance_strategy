# Agent B (Inžinier) — rozdelenie dát: Databento futures a BTC

*26. 11. 2026. Len čítanie. Meranie je `kritika/dq_scan.py` (nice 19, po jednom súbore, 37 s) → `kritika/data_kvalita.json`,
k tomu iCloud `OOS-STARE-ROKY/data/dbq.json`. V `data/` som nič nemenil a nič som nesťahoval.*

**Metóda:**
- **Pokrytie** = počet 1m sviečok v jadre seansy / (dni s dátami × dĺžka okna). Okná v UTC sedia v lete aj v zime:
  - US indexy 14:30–20:00,
  - 6E a MGC 8:00–16:00 (Londýn + NY),
  - BTC 24/7.
- **„krátke“** = dni s < 50 % okna (sviatky a skrátené dni).
- **Zlé tiky** = skok > max(25 × medián |výnosu|, 0,3 %), ktorý sa hneď nasledujúcou minútou vráti.
- **Veľký rozsah** = (H − L) / C > 40 × medián.
- **Rolovanie** = skok medzi kontraktmi v deň rolovania (archív nie je back-adjustovaný).

---

## 1. Kvalita po trhoch

### MNQ (Databento, 5. 5. 2019 – 9. 11. 2026)
| rok | pokrytie | krátke dni | zlé tiky | problémy | použiteľné |
|---|---|---|---|---|---|
| 2019 (od 5/5) | 98,1 % | 3 | 5 | kontrakt vznikol 5/2019 | ladenie aj trezor |
| 2020 | 98,7 % | 3 | 36 | covid (skoky sú skutočné) | áno |
| 2021–2024 | 98,3–98,8 % | 3–4 | 1–6 | — | áno |
| 2025 | 98,3 % | 4 | 45 | apríl 2025 clá (skutočné), 9. 1. Carter, 28. 11. výpadok CME | áno |
| 2026 (do 9/11) | 98,7 % | 4 | 1 | — | rok A (do 3/9), potom C |

Bez duplicít, NaN aj nelogických sviečok, objem nikde 0. **Rolovanie: medián 0,92 %, max 1,43 %**, najväčšie
zo všetkých trhov.

### MYM (Databento, 2. 6. 2019 – 9. 11. 2026)
Pokrytie 97,7–98,8 % každý rok, zlé tiky 0–4 (2020: 56, 2025: 23, oba trhové udalosti). Rolovanie 0,53 % / 1,18 %.
**Celé obdobie je čisté.**

### ES (Databento, 6. 6. 2010 – 19. 10. 2026)
| roky | pokrytie | zlé tiky | problémy | použiteľné |
|---|---|---|---|---|
| 2010–2019 | 98,1–99,5 % | 0–3 / rok | 2012 a 2013 skok na prelome roka 1,7 % a 1,35 % (sviatky a rolovanie, overiť) | áno |
| 2020 | 98,7 % | 28 | covid | áno |
| 2021–2024 | 98,3–98,8 % | 0–2 | — | áno |
| 2025 | 98,3 % | 30 | apríl 2025 | áno |
| 2026 (do 19/10) | 98,6 % | 3 | archív končí 19. 10. | A, potom C (treba doplniť) |

Rolovanie 0,40 % / 1,73 %. **16,3 roka čistých dát**, je to náš najlepší trh.

### MGC (Databento, 3. 10. 2010 – 16. 9. 2026)
| rok | pokrytie | krátke dni | použiteľné |
|---|---|---|---|
| 2010 | 8 % | 64 z ~65 | **nie** |
| 2011–2015 | 31–39 % | 206–247 | **nie** (seansa má väčšinou diery) |
| 2016–2017 | 64–66 % | 11–49 | **nie** |
| 2018 | 77 % | 2 | **nie** |
| 2019 | 92 % | 0 | **nie** (pod 95 %), nanajvýš denný alebo 4h TF ako informácia |
| 2020–2026 | 99,5–100 % | 0–1 | áno |

Rolovanie 0,31 % / max **2,08 %**. **Čisté je len 1/2020 – 9/2026 (6,7 roka).** MTK ORB (ladená 2010–2024) aj
test SPRÁV na 2010–2021 (07) stoja na riedkych dátach.

### 6E (Databento, 6. 6. 2010 – 28. 9. 2026)
| roky | pokrytie | zlé tiky / rok | veľký rozsah / rok | použiteľné |
|---|---|---|---|---|
| 2010–2015 | 99,1–100 % | **220–636** | **957–3 906** | **nie v tomto stave**. Po vyčistení (filter „skok a späť“) kandidát na trezor B′ |
| 2016–2026 | 99,7–100 % | 0–3 | 0–18 | áno |

Rolovanie 0,35 % / 0,80 %. Čistých je **10,7 roka (2016+)**. Roky 2010–15 zaťažuje ~1 600 zlých tikov.

### BTC — výber zdroja
| zdroj | obdobie | pokrytie | diery > 2 h | zlé tiky / rok | objem 0 | poznámka |
|---|---|---|---|---|---|---|
| **Binance futures BTC/USDT perp** | 8. 9. 2019 – 4. 9. 2026 | 99,3–100 % | **0** | 8–31 (2020: 141, marec) | 0–0,2 % | k tomu funding a mark (1h) |
| Binance spot BTC/USDT | 8. 9. 2019 – 5. 9. 2026 | 99,8–100 % | 2–5 / rok v 2019–21 | 5–30 (2020: 92) | ~0 % | — |
| Coinbase BTC/USD | 1. 8. – 4. 9. 2026 | 98,1 % | 0 | 1 | 0 % | len 1 mesiac |
| Dukascopy BTC/USD (CFD) | 5/2017 – 9/2026 | 77–86 % (2017–20), 92–99,6 % potom | 54–113 / rok v 2017–20 | 75–348 | **97–100 % od 2021** | bez objemu, diery |

**Vyberám Binance futures BTC/USDT perp:**
- je najkompletnejší (nula dier v seanse, pokrytie 100 % od 2020) a má skutočný objem (stratégie s VWAP a objemom),
- je to najlikvidnejší BTC trh na svete, takže sa najmenej odchyľuje od ceny, ktorú dostane akýkoľvek broker
  vrátane CFD,
- naše BTC kópie počítali s poplatkom Binance (`FEE_KEY` 0,02 % maker), teda sedí s tým, kde sa malo obchodovať,
- funding je v archíve, takže ho pri držaní cez 8 h vieme započítať (pri spote nie je, pri CFD je swap).

Spot slúži ako kontrola (rovnaké obdobie, 2019–21 má pár dier). Dukascopy a Coinbase sa nepoužívajú. **Archív BTC
končí 4. 9. 2026**, takže pre C treba dopĺňať (hub `livedata`).

---

## 2. Princípy rozdelenia (dohodnuté + čo z nich vyplýva)
- **Walk-forward 24/6** potrebuje L ≥ 4 roky (24 mesiacov učenia + ≥ 4 testovacie kúsky).
- **Trezor** musí mať ≥ 2 roky **a** ≥ 300 obchodov a aspoň jeden iný režim. **Pri 100 obchodoch za rok to znamená
  ≥ 3 roky**, takže 2 roky stačia len stratégiám s ≥ 150 obchodmi za rok.
- **A** (4. 9. 2025 – 3. 9. 2026) je spálený pre všetkých. Pre EUR legacy je spálené celé 10/2021 – 9/2026.
- **C** začína dňom po commite hraníc (cieľ 1. 12. 2026). Potrebuje živé dopĺňanie archívu (ES končí 19. 10.,
  MGC 16. 9., 6E 28. 9., BTC 4. 9.).
- **Legacy rodiny** (všetko z webapp k 26. 11.) majú L 10/2021 – 9/2025 zmrazené. Staré roky z triedenia
  26. 11. majú spálené (ES 2010–21, MGC 2020–21, MNQ/MYM/BTC 2019–21, 6E 2016–21 je ich L). Čistý im ostáva
  **len B′ (nové dáta) a C**.
- **Nové hypotézy** smú dostať chronologické rozdelenie so starším L a dvoma trezormi, ak ich rodina na tých
  obdobiach nikdy nebežala (register to overí).

---

## 3. Návrh rozdelenia po trhoch

### ES
| oblasť | nové hypotézy | roky | obchody pri 100/rok | režimy |
|---|---|---|---|---|
| L (+ WF 24/6, ~12 kúskov) | 6. 6. 2010 – 30. 9. 2018 | 8,3 | ~830 | 2011 kríza eura, 2015–16, nízka volatilita 2017 |
| B | 1. 10. 2018 – 30. 9. 2021 | 3,0 | ~300 | výpredaj Q4 2018, covid 2020 |
| B2 | 1. 10. 2021 – 3. 9. 2025 (len rodiny, ktoré tam nebežali) | 3,9 | ~390 | bear 2022, rast 2023–24 |
| A | 4. 9. 2025 – 3. 9. 2026 | 1 | — | spálený |
| C | od 1. 12. 2026 | — | — | demo |

- **Legacy ES** (IBS EZ ES, NY VA, ORB 15/5, IVB, Williams R, NOA ES, M2): L 10/2021 – 9/2025, B 2010–21 spálený
  → **len C**.
- **T4b** (ORB 15/5) je negatívna kontrola na spálenom B.
- **Námietka k L 2010–18:** trh mal vtedy menej mikrokontraktov a algo flow. Pri novej hypotéze treba v hlavičke
  zapísať, prečo by mala platiť dnes.

### MNQ a MYM (Nasdaq a Dow)
**Dnes, bez nových dát:** L 10/2021 – 9/2025 (4 roky, WF 4 kúsky, ~400 obchodov). B 6/2019 – 9/2021 má len 2,3 roka
a ~230 obchodov, **teda menej než 300**. Pre stratégie so 100 obchodmi za rok **nestačí**, prejsť by mohli len tie
so ≥ 130 za rok.

**Po stiahnutí NQ a YM (odporúčanie):** rovnaká schéma ako pri ES, jednotná pre všetky indexy USA.
| oblasť | nové hypotézy | roky | ~obchody | |
|---|---|---|---|---|
| L | NQ/YM 6/2010 – 9/2018 | 8,3 | ~830 | prahy v ATR alebo %, NQ v roku 2010 na ~1 800 bodoch |
| B | NQ/YM 10/2018 – 4/2019 + MNQ/MYM 5/2019 – 9/2021 | 3,0 | ~300 | Q4 2018, covid |
| B2 | MNQ/MYM 10/2021 – 9/2025 (rodiny, ktoré tam nebežali) | 3,9 | ~390 | 2022 |
| A, C | ako pri ES | | | |

**Legacy Nasdaq a Dow** (NOA, TKS, IBS EZ, VWAP ORB, VWAP ADX, Volt Break, Noc + pondelok…): **B′ = NQ/YM
6/2010 – 4/2019** (8,9 roka, ~890 obchodov, režimy 2011, 2015–16, 2018). Je to jediný čistý trezor, ktorý im vieme
dať pred C. T1 a T6 sekundárne bežia tam.

### MGC (zlato)
**Dnes:** čisté len 1/2020 – 9/2026. Legacy L 10/2021 – 9/2025, B 1/2020 – 9/2021 má 1,75 roka a ~175 obchodov,
**nestačí**, a navyše je spálený.

**Po stiahnutí GC 2010–2019 (odporúčanie; GC je likvidný, pokrytie treba najprv zmerať ≥ 95 %):**
| oblasť | nové hypotézy | roky | ~obchody |
|---|---|---|---|
| L | GC 10/2010 – 9/2018 | 8 | ~800 (vrchol 2011, pád 2013, ploché 2014–18) |
| B | GC 10/2018 – 12/2019 + MGC 1/2020 – 9/2021 | 3 | ~300 (covid, rekord 2020) |
| B2 | MGC 10/2021 – 9/2025 (rodiny, ktoré tam nebežali) | 3,9 | ~390 |

- **Legacy zlato** (Fibo, Sigma MGC, NOA MGC, MTK ORB, IVB MGC, SPRÁVY): B′ = GC 2010–2019, okrem SPRÁV, ktoré
  ten podklad a obdobie už videli (07).
- MTK ORB sa ladila na riedkom MGC 2010–2024, a preto jej výsledok z ladenia treba brať ako nespoľahlivý.

### 6E (euro)
| oblasť | nové hypotézy | roky | ~obchody |
|---|---|---|---|
| L (+ WF ~7 kúskov) | 1. 1. 2016 – 30. 9. 2021 | 5,75 | ~575 (Brexit 2016, záporné sadzby, covid) |
| B2 | 1. 10. 2021 – 3. 9. 2025 (rodiny, ktoré tam nebežali) | 3,9 | ~390 (rast sadzieb 2022, parita) |
| B′ | 2010–2015 **po vyčistení zlých tikov** | 5,5 | ~550 (kríza eura 2010–12, 2014–15 QE) |
| A | 4. 9. 2025 – 3. 9. 2026 | | spálený |

- **Legacy EUR** (Williams R, SPRÁVY EUR, Asia sweep…): L 2016–21, A 10/2021 – 9/2026 spálený, takže dnes **len C**.
  Po vyčistení 2010–2015 dostanú B′.
- Čistenie nie je sťahovanie: znamená nový import cez `tester.bento_import` s filtrom „skok a hneď späť“.
- Odporúčam ho, ale len so zápisom, koľko sviečok filter zmenil (cieľ: ≤ 0,5 % sviečok).

### BTC (Binance futures perp)
| oblasť | nové hypotézy | roky | ~obchody |
|---|---|---|---|
| L | 1. 10. 2021 – 3. 9. 2025 | 3,9 | ~390 (bear 2022, FTX, rast 2023–24) |
| B | 8. 9. 2019 – 30. 9. 2021 | 2,1 | ~210 (covid, bublina 2021) — **pod 300** |
| B′ | Binance **spot** 8/2017 – 9/2019 (stiahnuť) | 2,1 | ~210 (bubble 2017, bear 2018) |

- B + B′ spolu dajú ~4,2 roka a ~420 obchodov, ale ide o dva zdroje (spot je bez fundingu), takže výsledky treba
  uvádzať zvlášť.
- **Legacy BTC kópie:** B spálený, takže len B′ (spot 2017–19) a C.

---

## 4. Kde dát nestačí a čo stiahnuť (len odporúčanie, sťahuje používateľ)
| trh | problém | odporúčanie | čo dá |
|---|---|---|---|
| **MNQ / Nasdaq** | čisté len od 5/2019, B 2,3 roka < 300 obchodov, legacy bez trezoru | Databento `GLBX.MDP3`, `ohlcv-1m`, `NQ.FUT` 6/2010 – 5/2019 ako `nq_databento` | B′ 8,9 roka pre všetky Nasdaq stratégie |
| **MYM / Dow** | to isté | `YM.FUT` 6/2010 – 6/2019 | B′ 9 rokov |
| **MGC / zlato** | pred 2020 pokrytie 8–92 % | `GC.FUT` 10/2010 – 12/2019 (najprv zmerať pokrytie) | B′ 9 rokov |
| **6E** | 2010–15 zlé tiky | nové dáta netreba, stačí vyčistiť import | B′ 5,5 roka |
| **BTC** | futures len od 9/2019 | Binance spot BTCUSDT 1m 8/2017 – 9/2019 (data.binance.vision) | B′ 2 roky s medvedím trhom 2018 |
| **všetky** | archív končí 9–11/2026 | dopĺňať živo (hub `livedata` / mesačný push) | trezor C |

**Rolovanie:** skoky 0,3–0,9 % (max 2,1 %) bez back-adjustu. Pri intraday stratégiách nevadia (nové kontrakty sa
neprekrývajú v rámci dňa), ale stratégie s dlhou pamäťou (EMA 200 na 4h, SMA 100 dní, `nocpon` SMA 100) potrebujú
`skipRoll` alebo back-adjustovaný rad. Inak je signál v deň rolovania falošný.

## 5. Zhrnutie pre Prokurátora
- **Čisté dáta:** ES 2010+, 6E 2016+, MGC 2020+, MNQ a MYM 2019+, BTC (Binance perp) 9/2019+.
- **Legacy stratégie** dnes nemajú žiadny čistý trezor okrem C. Jediná cesta k B′ vedie cez nové dáta (NQ, YM, GC,
  BTC spot) alebo vyčistené 6E 2010–15.
- **Nové hypotézy:** ES má hneď schému L 2010–18 / B 2018–21 / B2 2021–25. MNQ, MYM a MGC ju dostanú až po stiahnutí
  NQ/YM/GC.
- Pravidlo „trezor ≥ 2 roky“ je pri 100 obchodoch za rok v skutočnosti ≥ 3 roky. Dnešné MNQ, MYM, MGC aj BTC B ho
  nesplnia.
