# Fiktívna burza Tester vs Binance — 2026-09-09

Freqtrade kontroluje beh proti burze z ccxt: timeframe musí byť v jej zozname, pár v jej
trhoch. Preto pribudla **fiktívna burza Tester** ([`tester/ftexchange.py`](../../tester/ftexchange.py)),
ktorá páry aj timeframy berie z nášho vlastného skladu. Otázka merania je jediná: dá tá istá
stratégia na tých istých dátach cez ňu **presne to isté**, čo cez skutočnú Binance?

## Postup

Ten istý pár, profil, obdobie a poplatok; líši sa len `--exchange`:

```bash
PY -m tester.webapp.cli run --engine freqtrade --exchange tester \
   --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --timerange 20250904-20260904 --note "porovnanie burz: tester"
PY -m tester.webapp.cli run --engine freqtrade --exchange binance … --note "porovnanie burz: binance"
```

Behy: `20260909-174120-e99eab` (Tester) a `20260909-174140-85fa3c` (Binance).

## Výsledok: zhoda do posledného obchodu

| | Tester | Binance |
|---|---|---|
| obchodov | 22 | 22 |
| PnL | +11,91 % (+1 191 USDT) | +11,91 % (+1 191 USDT) |
| profit factor | 1,922 | 1,922 |
| winrate | 54,55 % | 54,55 % |
| max drawdown | 3,83 % | 3,83 % |
| break-even poplatok | 0,1568 % | 0,1568 % |

Porovnanie obchod po obchode (`trades.json`, polia čas vstupu a výstupu, vstupná a výstupná
cena, množstvo, PnL, páka, stake, dôvod výstupu, tag) je **zhodné vo všetkých 22 riadkoch**.
V súhrne behu sa líši jediná položka — meno výsledkového zipu, teda čas spustenia.

To dáva zmysel: burza dodáva len **popis trhu** (tick, krok množstva, limity, zoznam
timeframov) a ten je v oboch prípadoch ten istý — čísla v `InstrumentSpec` sú z Binance.
Sviečky, fill model aj poplatok (`--fee`) sú na burze nezávislé.

## Čo z toho platí

* **Predvolená je Tester.** Pridáva len to, čo skutočná burza nedovolí: 2m a 4m timeframy
  (Binance ich nemá) a Dukascopy CFD bez požičanej nosnej burzy. Na výsledok nemá vplyv.
* **Binance ostáva v ponuke** — presne na takéto kontroly a na prípad, že by sa niečo
  v pravidlách trhu rozišlo (nové limity, iný krok množstva).
* Čo burza Tester **nemá**: poplatky (zadáva ich beh cez `--fee`), funding (nula),
  likvidáciu a leverage tiery. Pre backtest na uzavretých obchodoch to nič nemení; pre
  úvahy o margin volaniach áno — tie nepatria do backtestu, ale do
  [`tester.montecarlo`](../../tester/montecarlo.py) a do reálneho účtu.

Overuje to aj `tester/tests/test_ftexchange.py` — najmä to, že burza spĺňa, čo Freqtrade
od burzy vyžaduje (`EXCHANGE_HAS_REQUIRED`), a že páry sedia s registrom inštrumentov.
