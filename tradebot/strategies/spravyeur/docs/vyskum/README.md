# SPRÁVY na EUR/USD (6E) — výskum a ladenie (od 21. 11. 2026)

Pokračovanie výskumu SPRÁV zo zlata (`tradebot/strategies/spravy/docs/vyskum/`) na EUR/USD; zadanie používateľa 21. 11. 2026.

## Dáta a kalendár
- 6E 1m (Databento, front-month) od 2016; EUR/USD CFD (Dukascopy) na krok 8.
- **ECB** 2016–2028 (ecb.europa.eu, archív rozhodnutí a budúci kalendár; `skripty/ecb_raw.txt`). Čas rozhodnutia
  **14:15 Frankfurt, tlačovka 14:45**; do 9. 6. 2022 **13:45 / 14:30** — zmena overená na 6E (najväčší pohyb minúty sa
  presunul od 21. 7. 2022). V `calendar.json` je čas New York pre každý deň (`times`), lebo Európa a USA menia letný čas v iné týždne.
- Správy **USA** z kalendára SPRÁV (2021–2027).

## Výsledky výskumu (`study.csv`, `skripty/study.py`)
Noha close(T+a) → close(T+b), pokračovanie h minút; PF po poplatku, t-štatistika, roky; kontrola v tých istých časoch dní bez správ.
- **Návrat (fade)** po JOLTS (15→60, 6/6 rokov, t −3,6), PPI (0→5 / 0→15, 5–6/6), CPI (0→30, 6/6), ISM služby, PCE,
  zápisnici FOMC, NFP (pozor: NFP aj v kontrolných dňoch — čas dňa), ECB rozhodnutie (9/11, časť je čas dňa).
- **Trend** po FOMC (0→60 pri pohybe ≥ 0,3 ATR, 6/6) a tlačovke ECB (0→60 pri pohybe ≥ 0,3 ATR, 8/11, kontrola nie).

## Stratégia a ladenie
`spravyeur` / `spravyeurnet` = kópie SPRÁV; východisko `configs/6e_databento_5m.json` (FOMC a tlačovka ECB trend, CPI, PPI,
JOLTS, ISM služby fade; riziko 500 $, podlaha stopu 2 ATR). Bez ladenia PF po oknách 1,72 · 1,23 · 1,32 · 2,33 · posledný
rok 1,44. Ladenie `skripty/ladenie.py` (kópia ladenia zlata: A pravidlá, B nové správy, C zloženie, D spoločné, E overenie EUR/USD CFD).
