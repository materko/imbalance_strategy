# Parita ORBNinja (C# jadro) s ORB (Python) — 2026-09-24

`orbninja` je prepis stratégie `orb` (Opening Range Breakout) do C# (`csharp/TradeBot.Strategies/OrbNinja`
nad `csharp/TradeBot.Core`), aby tá istá logika bežala natívne v NinjaTraderi 8 (šablóna
`deploy/ninjatrader/ORBNinja.cs` nad generickým adaptérom) a zároveň pod Freqtrade cez most
`tradebot/adapters/csharp` ([NINJATRADER.md](../NINJATRADER.md)). Parametre, profily a kresby sú zhodné
s ORB. Otázka merania: **dáva C# jadro to isté čo Python engine?**

Odpoveď: **áno, bez jediného rozdielu** — bar po bare aj obchod po obchode.

## 1. Engine proti enginu, bar po bare

`python -m tester.compare.csharp_parity --python orb --csharp orbninja` — oba enginy v tom istom
`EngineRunner`, na každom bare sa na rovnosť porovnajú ordery (vrátane plánu: vstup, SL, TP, veľkosť,
trailing), kresby, koniec seansy a riadok signálu. Profil `nas100_dukascopy_3m`, 3m graf, celá história
skladu, 21 variantov: všetky kombinácie `entryMode` (close / retest / stop) × `slMode` (opposite, mid,
range_pct, atr, break_candle) s tromi `tpMode`, trailing + volume filter + 3 obchody denne, long-only
Londýn s 30/60-min rangom, short-only New York bez zatvárania na konci seansy, Pine sizing + `minSlDistance`
+ víkendy, voľné filtre s retestom a 5 obchodmi denne.

| dáta | barov | vstupov spolu | rozdielov |
|---|---|---|---|
| NAS100 Dukascopy (`--exchange nas100`), 2021-01 – 2026-09 | 647 400 na variant | 40 863 | **0** |
| MNQ Databento (`--exchange mnq`) | celý sklad | 53 606 | **0** |

**Doplnené 2026-09-25** po zmene ORB na `main` (dĺžka rangu 1–60 min, EMA v štyroch rolách: filter
smeru, filter dňa, výstup, kreslenie): matica rozšírená na 25 variantov (EMA 20/50/100/200, všetky
roly aj naraz, rangy 1, 5, 7, 42 min) — NAS100 72 425 vstupov, MNQ 95 128 vstupov, **0 rozdielov**.
EMA je v C# jadre `TradeBot.Core.Ema` (zrkadlo `tradebot/core/ma.py`).

Prvý pokus mal jeden rozdiel (variant s volume filtrom, NAS100 2022-12-22): Python predloha počíta
priemer objemu cez `sum(...)`, čo je od Pythonu 3.12 **kompenzovaná (Neumaierova) suma**, nie cyklus
zľava doprava. Na hrane `volume >= avg * volMultiplier` sa posledný bit preklopil. C# jadro má na to
`TradeBot.Core.PyMath.Sum` (verný prepis CPython `builtin_sum_impl`); Python ORB sa nemenil.

## 2. Backtesty v histórii Testera

`cli run`, `--timeframe-detail 1m`, profil `nas100_dukascopy_3m`; porovnanie
`csharp_parity --runs` obchod po obchode (časy, ceny, veľkosť, zisk, dôvod výstupu, stop):

| engine | pár | obdobie | ORB | ORBNinja | obchodov | výsledok |
|---|---|---|---|---|---|---|
| Freqtrade | BTC/USDT:USDT | 20250904-20260904 | `20260924-204222-4e65a7` | `20260924-204302-247942` | 434 | **zhoda** |
| Freqtrade | BTC/USDT:USDT | 20211001-20260904 | `20260924-204414-205cab` | `20260924-204641-5c8cb6` | 2 152 | **zhoda** |
| emulátor MultiCharts | NAS100/USD | 20250904-20260904 | `20260924-204346-2999a5` | `20260924-204350-554412` | 360 | **zhoda** |

Čísla behov sú pre obe stratégie totožné (napr. 5 rokov na BTC: PF 0,861, −70,6 %, break-even
0,0223 %) — profil je NAS100 východisko, nie ladené nastavenie; o edge ORB toto meranie nehovorí.

## 3. NinjaTrader 8 — Strategy Analyzer

Šablóna `ORBNinja` nad generickým adaptérom, MNQ 12-26 3m, 2026-03-01 – 2026-09-10 (dáta importované
z nášho skladu, `mnq_databento`), profil `nas100_dukascopy_3m`, Order fill resolution Standard,
jemná 1m séria adaptéra na plnenie. Export signálov proti Testeru
(`python -m tester.ninjatrader compare --strategy orbninja --profile nas100_dukascopy_3m`):

| | NinjaTrader | Tester |
|---|---|---|
| vstupy (bar, cena, SL, TP, veľkosť) | 207 | 207 — **zhodných 207** |
| obchodov | 207 | 206 (emulátor MultiCharts, `20260924-214202-429ad7`) |
| čistý zisk (bez poplatkov) | −4 572 $ | −4 379 $ |
| profit factor / WR | 0,84 / 43,5 % | 0,845 / 43,2 % |

Signály sedia úplne; výsledok sa líši len fill modelom (ako pri IBSNinja). Adaptér poslal aj 51
zatvorení na konci seansy (`CLOSE`). Neoverené ostáva `entryMode=stop` (stop-market vstup,
`EnterLong/ShortStopMarket`) v NinjaTraderi a živý graf.

## 4. Testy

- Pytest: `tester/tests/test_csharp_parity_orb.py` (syntetické bary, 5 variantov, oba transporty,
  okno NAS100 keď sú dáta).
