# SPRÁVY (EUR/USD) — ako funguje

_Variant na EUR/USD (6E futures, EURUSD CFD): logika a parametre sú tie isté ako v `spravy` (zlato); iné sú len pravidlá
a zapnuté správy. Kalendár je spoločný a má aj rozhodnutie a tlačovku ECB (čas New York pre každý deň zvlášť)._

> V jednej vete: po vybraných správach USA a ECB stratégia zmeria prvý pohyb 6E a podľa pravidla tej správy vstúpi proti nemu (fade) alebo v jeho smere (trend) a pozíciu zavrie po stanovenom čase, na stope alebo v cieli.

## Čo ukázal výskum (21. 11. 2026, 6E 2016–2026, správy USA 2021–2026)
- Po **JOLTS, PPI, CPI, ISM služby, PCE a zápisnici FOMC** sa 6E vo väčšine prípadov **vracia** proti prvému pohybu
  (5–6 rokov zo 6, v dňoch bez správ v tom istom čase nie).
- Po **FOMC** a pri väčšom pohybe po **tlačovke ECB** prvý pohyb **pokračuje** (FOMC 6 / 6 rokov, tlačovka ECB 8 / 11).

## Pravidlá
Každé z 8 pravidiel má správu, smer (trend / fade), nohu (od → do v minútach od správy), čas vstupu, držanie, stop
(násobok nohy, 0 = za extrémom nohy + rezerva) a cieľ RR. Riziko na obchod 500 $ (veľkosť z rizika ku stopu,
podlaha stopu 2 ATR). Jeden obchod naraz.

## Stop a cieľ
- **Stop**: násobok nohy od vstupu (`rNStop`), pri 0 za extrémom nohy + rezerva `slBuffer`; podlaha stopu `sizeMinRisk` ATR.
- **Cieľ**: `rNRR` × riziko (0 = bez cieľa); kto ho nedosiahne, zavrie sa po čase `rNHold`.

## Kalendár
`tradebot/strategies/spravy/calendar.json` — ECB 2016–2028 (ecb.europa.eu; rozhodnutie 14:15, tlačovka 14:45 Frankfurt,
do 9. 6. 2022 13:45 / 14:30), správy USA 2021–2027. Presunutú správu opraví profil (`newsAdd`, `newsSkip`) alebo hub (ff_calendar).
