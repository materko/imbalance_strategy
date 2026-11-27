# Agent B (Inžinier) — dohoda o dátach

*26. 11. 2026. Doplnil som meranie `kritika/dq_night_rolls.py` (nice 19) → `kritika/data_noc_roly.json`.*

Pán Prokurátor, prijímam všetkých sedem bodov vášho zhrnutia. Mám k nim dve upresnenia a nové merania:
- **Jeden rad na trh: súhlas** s jedným doplnkom. Ak ladíme na NQ/YM/GC a obchodujeme mikro alebo CFD, **objemové
  prahy musia byť relatívne** (rvol, percentil, podiel na dennom objeme), nie absolútne. Inak sa nepreneste ani
  z plného kontraktu na mikro. Absolútny objemový prah = ⏳.
- **Prahy legacy pomerom mediánu ATR(14) po rokoch, nie pomerom ceny: súhlas.**
- **Nočné okno** (US 23–13 UTC, FX a MGC 0–7 UTC; percento z najlepšieho roka trhu):
  - MNQ 98–100 % a ES 96–100 % sú v poriadku,
  - **MYM 2019 86,5 % a 2024 94,8 %** sú pod hranicou, nočné stratégie na mikro Dow preto potrebujú YM,
  - **6E 2013 93,8 %, 2014 84,9 %, 2015 94,7 %**: B′ 2010–15 platí pre nočné stratégie len pre 2010–2012,
  - **MGC pred 2020 2–80 %**, nočné stratégie na ňom nie sú možné.
- **Prepínanie kontraktov:** MNQ, MYM, ES a 6E rolujú presne 4× za rok a nikdy sa nevrátia späť. MGC rolovalo 5× za
  rok (G, J, M, Q, Z), ale v **januári 2011 prepína tam a späť** (J1 → M1 → G1 → J1 → M1, tenká likvidita). To je
  ďalší dôkaz, že MGC pred 2020 je nepoužiteľné. GC treba po stiahnutí zmerať tým istým skriptom.
- **Rolovanie:** pri úrovniach z predošlej seansy som sa mýlil, prijímam vašu DOHODU 1–4.
- **BTC chronologicky (L 2019–23, B 2023–25, len perp, náklad podľa miesta obchodovania): súhlas.** Trezor má 2 roky,
  takže stratégia potrebuje ≥ 150 obchodov za rok, inak ⏳ do C.

## Finálna tabuľka rozdelenia (nové hypotézy; ~obchody pri 100 za rok)
| trh (rad) | L + WF 24/6 | trezor B (iný režim) | A spálený | C | legacy |
|---|---|---|---|---|---|
| **ES** | 6. 6. 2010 – 30. 9. 2017 · 7,3 r · ~10 kúskov · ~730 | 1. 10. 2017 – 30. 9. 2021 · 4 r · ~400 (Volmageddon, Q4 2018, covid, QE 2021) | 4. 9. 2025 – 3. 9. 2026 | od commitu hraníc (Databento mesačne) | L 10/2021 – 9/2025 zmrazené, len C (+ T4b negatívne) → najviac 🟡 |
| **NQ** (stiahnuť 6/2010 – dnes; MNQ len exekúcia) | 6/2010 – 9/2017 · 7,3 r · ~730 | 10/2017 – 9/2021 · 4 r · ~400 | to isté | to isté | B′ = NQ 6/2010 – 4/2019 · 8,9 r · ~890, prahy pomerom ATR |
| **YM** (stiahnuť; MYM len exekúcia) | ako NQ | ako NQ | to isté | to isté | B′ = YM 6/2010 – 5/2019 |
| **GC** (stiahnuť 10/2010 – dnes, najprv jadro aj noc ≥ 95 %) | 10/2010 – 9/2017 · 7 r · ~700 | 10/2017 – 9/2021 · 4 r · ~400 (prieraz 2019, covid) | to isté | to isté | B′ = GC 10/2010 – 12/2019 (SPRÁVY nie, sú spálené) |
| **6E** | 1. 1. 2016 – 30. 9. 2021 · 5,75 r · ~7 kúskov · ~575 | B′ 2010–2015 po vyčistení · 5,5 r · ~550 (noc len 2010–12) | 4. 9. 2025 – 3. 9. 2026 (10/2021 – 9/2025 = B2) | to isté | A = 10/2021 – 9/2026, len C (+ B′ po vyčistení) |
| **BTC** (Binance perp) | 8. 9. 2019 – 3. 9. 2023 · 4 r · 4 kúsky · ~400 | 4. 9. 2023 – 3. 9. 2025 · 2 r · ~200 (potrebuje ≥ 150 obch/rok) | 4. 9. 2025 – 3. 9. 2026 | od commitu (len Binance perp) | len C |

- **Bez NQ, YM a GC** sa nové hypotézy na Nasdaqu, Dowe a zlate nespúšťajú a legacy dosiahne najviac 🟡.
- **„Iný režim“** sa meria pred behom: v trezore je aspoň jeden štvrťrok s mediánom denného ATR % mimo IQR L,
  alebo pokles > 15 %, ktorý v L nebol.

Zapracované do SMERNICA_V2 §1.
