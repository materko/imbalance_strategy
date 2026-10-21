# Zlato (MGC) — prieskum stratégií (MacBook, 21. 10. 2026)

> **21. 10. 2026 večer: kompletný prieskum trhu MGC (len kvalitné dáta 2020+) je v `TRH_MGC.md`** — dáta MGC pred 2019 sú zlé
> (nižšie skoršie testy brali aj 2017–2018). Najsilnejší jav: SD zóny (63 % vs 34 % náhoda), zlato mierne návratové, prierazy nefungujú.


Dáta: Databento MGC 1m (husté od 2017; denné od 2011), bez dní s rolovaním kontraktu. Ladenie 2017–2022 (denné 2011–2022),
overenie 2023 – 2025-09; **odložený rok 2025/26 nepoužitý**. Náklady 0,45 bodu na obchod (MGC 10 $ / bod). Skripty v `skripty/`
(prep.py → seg.py, strat.py, rev.py, daily.py, trendf.py; cesty na MacBook repo, na Mac mini zmeň na ~/IBS).

## Čo NEfunguje (PF < 1 takmer každý rok, pred nákladmi ~0)
- Sezónnosť seáns (Ázia / Londýn / COMEX / poobede): rádovo 1 bps — pod nákladmi.
- ORB intradenne s výstupom v ten istý deň (COMEX 8:20, NY 9:30, Londýn 3:00, Ázia range): PF 0,74–0,95.
- Pásmo šumu (NOA) na COMEX / Londýne / NY: PF 0,66–0,97.
- Fade od VWAP (2–3 sd), sweep včerajšieho COMEX high/low: PF 0,45–0,9.
- Denný trend (Donchian 20/55, SMA 20/100, 50/200, momentum 60/120/250): v 2011–22 okolo nuly, zarába len v býčích 2023–25.
→ Zlato sa na horizonte minút až hodín správa ako náhodná prechádzka; náskok Nasdaqu (trend dňa) tu nie je.

## Kandidát
**ORB 30m (Londýn + NY, range 15 min, SL opačná strana, TP 3R, max 2/deň, zatvoriť na konci seansy) + smer len podľa
SMA 50 denných zavretí** (long nad, short pod). Beh 20260921-111532-26ae3b (pôvodne bez poplatkov) prerátaný s nákladmi
a filtrom: 1 075 obch (2011 – 2025-09, ~72/rok), 2011–22 PF 1,13, 2023–25/9 PF 1,41, PF > 1 v 11/15 rokoch
(aj 2012–13 v medvedom trhu). Slabé a málo obchodov (smernica chce 150/rok) — filter vybraný z 3 variantov (SMA 50/100/200).
Bez filtra s nákladmi PF 0,99 (zarábajú len longy v rokoch rastu).

## Ďalej (Mac mini, smernica)
1. `orb` na MGC 30m s `trendFilter=with`, `trendTF=1440`, `trendEmaLen` 30–100 a `closeAtSessionEnd=true` — smernica,
   ladenie 2021-10 – 2025-09, poplatok realisticky, potom odložený rok raz.
2. Nápady: reakcia na správy USA (8:30 CPI / NFP, 14:00 FOMC — kalendár ForexFactory je v hube), long-bias stratégie s denným
   filtrom trendu, MGC Kompas (piatok — viď [[mgc-plan-friday]]: trend dňa na zlate pravdepodobne slabý, ORB/NOA to naznačujú).

## 21. 10. 2026 — čo už na MGC máme (prehľad všetkých profilov vo webapp) → odrazový mostík
Vo webapp **ZLATO** (varianty stratégií s logikou predlohy, len profily na MGC; všetko z víkendového hľadania 2.–5. 10.,
**bez nákladov**, PF po rokoch 25/26 · 24/25 · 23/24 · 22/23 · 21/22 = rok, ktorý hľadanie nevidelo):
| stratégia (ZLATO ›) | profil | TF | RR | PF po rokoch | roky v zisku |
|---|---|---|---|---|---|
| **Scalping 3MA (MGC)** › SKALPOVACIE | WK_scalp3ma_MGC_159obch_WR57_R0_9 | 15m | 0,9 | 1,23 · 1,32 · 1,33 · 1,32 · 1,30 | **5/5** |
| | WK_scalp3ma_MGC_161obch_WR54_R1_2 | 15m | 1,2 | 1,44 · 1,39 · 1,34 · 1,21 · 1,26 | **5/5** |
| | WK_scalp3ma_MGC_156obch_WR40_R2_0 | 3m | 2,0 | 1,33 · 1,42 · 1,21 · 1,28 · 1,14 | **5/5** |
| | WK_scalp3ma_MGC_169obch_WR49_R1_4 | 15m | 1,4 | 1,33 · 1,32 · 1,27 · 1,21 · 1,03 | **5/5** |
| **Fibo 1.0 (MGC)** › TRENDOVÉ | WK_fibo_MGC_155obch_WR63_R0_9 | 3m | 0,9 | 1,50 · 1,21 · 1,77 · 1,30 · 1,21 | **5/5** |
| | WK_fibo_MGC_166obch_WR60_R1_0 | 3m | 1,0 | 1,55 · 1,30 · 1,46 · 1,21 · 1,09 | **5/5** |
| FVG POLARITY (MGC) › SKALPOVACIE | WK_fvgpolarity_MGC_161obch_WR61_R1_1 | 3m | 1,1 | 1,80 · 1,30 · 0,98 · 1,17 · 1,11 | 4/5 (SL 2 b. — citlivé na náklady) |
| | WK_fvgpolarity_MGC_221obch_WR65_R0_9 | 3m | 0,9 | 1,72 · 1,07 · 1,04 · 1,10 · 0,91 | 4/5 (SL 2 b.) |
| IBS EZ MGC (Mac mini) | východiskový profil | 3m | | posl. rok PF 0,73 | — |
Scalping 3MA má SL 1,5–3 ATR (15m), Fibo SL podľa nohy pohybu → náklady (~0,3–0,45 b./obch) sú malá časť rizika.
**Nezaradené (slabé):** Fibo ostatných 10 a Scalping 3MA ostatných 15 profilov (posledný rok vybraný hľadaním, staršie roky
okolo nuly) — ostali pri pôvodných stratégiách v `tester/profiles`; profily `R1_*` (Divergence, Liquidity, ORB, SD Zones,
Structure, Trendlines, VWAP OP) majú len 2 roky a predošlý rok WR 42–59 % pri RR 1 (≈ PF ≤ 1) — nepoužiteľné.
**Ďalší krok:** prepočet s nákladmi (poplatok + 1 tick sklz) a smernica na Mac mini pre Scalping 3MA (MGC) a Fibo 1.0 (MGC);
potom ORB 30m + smer podľa SMA 50 denných (kandidát z prieskumu vyššie).
