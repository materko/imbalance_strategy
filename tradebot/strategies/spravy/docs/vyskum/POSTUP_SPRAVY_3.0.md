# SPRÁVY 3.0 — presný postup (29. 10. 2026)

Commity: `2394a2cee` (stratégia 3.0), `950b69f0b` (283 behov výskumu v histórii webapp). Všetko je na GitHube (main).

## 1. Čo stratégia robí
Zlato (MGC 5m) obchoduje len po červených správach USA. Každá správa má vlastné pravidlo. Obchod je vždy len jeden naraz.

| # | správa | čo robí | noha (min od správy) | vstup | výstup | stop | RRR |
|---|---|---|---|---|---|---|---|
| 1 | FOMC | **PRED** — proti pohybu hodinu pred správou | −60 → 0 | 14:00 NY = **19:00 / 20:00 SK** | 16:55 NY | poistka 10 × noha | bez cieľa |
| 2 | *(vypnuté)* | tlačovka FOMC v smere 14:00 → 14:25 | 0 → 25 | 14:30 NY | 16:55 NY | za extrémom | bez cieľa |
| 3 | CPI | proti prvej hodine | 0 → 60 | T + 60 | po 1 h | poistka 10 × | bez cieľa |
| 4 | PPI | proti prvým 15 min | 0 → 15 | T + 15 | po 3 h | **za extrémom + 1 ATR** | **1 : 3** |
| 5 | PCE | v smere nohy | 15 → 60 | T + 60 | po 4 h | za extrémom | bez cieľa |
| 6 | JOLTS | proti prvej hodine | 0 → 60 | T + 60 | po 1 h | poistka 10 × | bez cieľa |
| 7, 8 | *(voľné)* | | | | | | |

Výsledok (1 kontrakt, päť okien): **PF 1,34 · 1,09 · 1,49 · 1,86 · 3,97**, 276 obchodov, **+11 114 $**, +4,8 sigma proti náhode.
Posledný rok (9/2025–9/2026): 52 obchodov, WR 63 %, PF 3,97, +7 922 $.
Porovnanie: 1.0 = 1,19 · 1,06 · 2,27 · 2,13 · 3,20, +9 050 $.

## 2. Webapp — kde čo nastavíš
Webapp → Nový beh → stratégia **SPRÁVY 3.0** (alebo **SPRÁVY 3.0 (C# jadro)** v ZLATO › LIVE), profil `mgc_databento_5m`, pár MGC/USD, TF 5m.
- **✅ Obchodované správy** — zaškrtni, ktoré správy obchodovať (12 typov). Pravidlo platí len pre zapnutú správu.
  Vypnutie napr. CPI = žiadny obchod po CPI, pravidlá sa nemenia.
- **📰 Pravidlo 1–8** — každé má: Správa (prázdne = vypnuté), Režim (trend / fade), Noha od / do (záporné = pred správou),
  Vstup v T + (najskôr koniec nohy), Držať (min), **RRR 1 : (0 = bez cieľa)**, Stop (× noha, 0 = za extrémom nohy + rezerva).
- **Tlačovku FOMC zapneš** v Pravidle 2: Správa = FOMC (a v Pravidle 1 zmeň Držať na 25, aby sa obchod pred správou zavrel o 14:25).
- **RRR inde:** v pravidle zadaj napr. 2 (= 1 : 2). Pri pravidlách so stopom „poistka 10 ×“ daj Stop = 0, inak je 2R tak ďaleko, že sa nikdy nedosiahne.
  RRR najmenej 0,5. Kto cieľ nedosiahne, zavrie sa po čase Držať.
- **Riziko na obchod:** vypni „pevný počet kontraktov“ a nastav Riziko ($) — alebo profil `mgc_databento_5m_riziko500`.
- **Presunutá správa** (shutdown, sviatok): Kalendár → Pridať „2026-11-26 08:30 PPI“, Vynechať „2026-11-13 PPI“ (čas New York).

## 3. Testovanie (vždy päť okien)
```
.venv/bin/python -m tester.webapp.cli run --strategy spravy --profile mgc_databento_5m --pair MGC/USD --engine multicharts \
  --timeframe 5m --fee 1.755e-05 --timerange 20250904-20260904 --set r4RR=2 --note "SPRAVY 3.0: PPI 1:2"
```
Okná: 20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904.
Jedno pravidlo samostatne: vypni ostatné správy, napr. `--set useFOMC=false --set useCPI=false --set usePCE=false --set useJOLTS=false`.
Hotové série: `skripty/spravy_rrr.sh` (RRR po pravidlách), `skripty/spravy2_overenie.sh` (každé pravidlo samostatne), `skripty/spravy_vstup.sh` (časy vstupu).
Analytika po zmene: `.venv/bin/python -m tester.webapp.cli checkup --strategy spravy --profile mgc_databento_5m --pair MGC/USD --timeframe 5m --fee 1.755e-05 --wallet 100000`
(a to isté so `spravynet`), potom posudok v `tradebot/strategies/<kľúč>/docs/ANALYTIKA.md`.

## 4. Nasadenie naživo
- C# jadro `spravynet`: NinjaTrader 8 `deploy/ninjatrader/SpravyNet.cs`, MetaTrader 5 `deploy/mt5/SpravyNet.mq5` (postup docs/NINJATRADER.md, docs/MT5.md).
- Najprv `git pull` a `python -m tradebot.adapters.csharp.build --force`, potom profil `spravynet/configs/mgc_databento_5m.json` (alebo `…_riziko500`).
- Stratégia počíta v UTC, na časovom pásme platformy nezáleží. V dôvode obchodu je čas SK aj NY a číslo pravidla
  („FOMC 19:00 SK / 14:00 NY · pravidlo 1: PRED short …“).

## 5. Kalendár správ — aby sa nič nepokazilo
- `tradebot/strategies/spravy/calendar.json`, čas **New York**, prevod pre každý deň zvlášť (posuny času USA vs. SK sedia: FOMC 28. 10. 2026 = 19:00 SK).
- **Pokrytie:** FOMC, CPI, NFP, PPI, ISM, CLAIMS a zápisnica FOMC do **12/2027** (oficiálne federalreserve.gov a bls.gov).
  **JOLTS, PCE, GDP, RETAIL len do 12/2026** — úrady 2027 ešte nezverejnili. **Doplniť v novembri / decembri 2026**:
  JOLTS bls.gov/schedule/news_release/jolts.htm, PCE a GDP bea.gov/news/schedule (záložka 2027), Retail census.gov/retail/release_schedule.html.
- Po zmene `calendar.json`: `.venv/bin/python -m tradebot.strategies.spravy.calendar --cs` (vygeneruje C# kalendár), pytest, commit, push.
- **Pripomienka:** test `test_kalendar_pokryva_buducnost` padne 21 dní pred posledným termínom niektorej správy (JOLTS od 10. 11. 2026).
- **Kontrola na dátach:** `skripty/kalendar_kontrola.py` overí, že výbuch volatility na 1m MGC je presne v čase správy
  (29. 10.: FOMC a NFP 100 %, CPI 99 %, žiadna správa posunutá o hodinu; slabé správy JOLTS / GDP občas bez reakcie — to nie je chyba dátumu).
- **Kontrola proti ForexFactory** (tento týždeň): FOMC 28. 10. 14:00 a GDP + PCE 29. 10. 8:30 sedia; tlačovku 14:30 kalendár nemá (pokrýva ju pravidlo 2).

## 6. Čo ďalej (návrh)
Pozri `OTVORENE_ULOHY.md`.
