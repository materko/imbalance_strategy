# Testovanie z príkazového riadku (aj pre AI)

Tento súbor je návod pre kohokoľvek — človeka aj jazykový model —, kto má na tomto
repozitári **spúšťať behy a vyhodnocovať ich**, nie meniť kód. Je písaný tak, aby stačil
sám o sebe: čo spustiť, čo to znamená a čomu neveriť.

`PY` = Python z `.venv` (`.venv\Scripts\python.exe` na Windows, `.venv/bin/python` inde).
Všetko sa spúšťa **z koreňa repozitára**.

---

## 1. Čo je čo

| | |
|---|---|
| **stratégia** | logika (`--strategy ibs`, `demo_breakout`). Zoznam: `PY -m tester.webapp.cli params --help` |
| **engine** | čím sa beh prehrá: `freqtrade` (backtest Freqtradu) alebo `multicharts` (emulátor MultiCharts — ten istý runner, čo beží v štúdii) |
| **pár** | čo sa obchoduje: `BTC/USDT:USDT`, `ETH/USDT:USDT`, `NAS100/USD`… |
| **profil** | parametre stratégie (JSON). Bez neho sa berú Pine defaulty. |
| **timerange** | `YYYYMMDD-YYYYMMDD` |

Tie štyri veci sú nezávislé: tá istá stratégia s tým istým profilom sa dá prehnať oboma
enginmi na ktoromkoľvek páre, pre ktorý sú dáta. Práve to je podstata porovnávacích behov.

## 2. Jeden beh

```bash
PY -m tester.webapp.cli run --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --timerange 20250904-20260904 --note "co tento beh testuje"
```

- **Vždy `--note`.** Bez poznámky je história na nič.
- `--set kluc=hodnota` mení jeden parameter (opakovateľné). Veľkostné polia sú
  `hodnota@jednotka` (`abs`, `ticks`, `atr`, `pct`), napr. `--set minSlDistance=0.25@pct`.
- `--engine freqtrade|multicharts` vyberie engine; bez neho sa vezme ten, pre ktorý sú dáta
  (pri Dukascopy symboloch emulátor, inak Freqtrade).
- `--pair`, `--timeframe`, `--fee`, `--wallet`, `--no-detail` podľa potreby.
- Ak beží webapp, beh ide do jej fronty a je vidno naživo; ak nebeží, CLI ho spustí priamo.
  Do histórie sa uloží tak či tak. **Beh spustený holým `freqtrade backtesting` sa do
  histórie nedostane.**

Zoznam parametrov stratégie s rozsahmi: `PY -m tester.webapp.cli params [filter]`.

## 3. Čítanie výsledkov

```bash
PY -m tester.webapp.cli list                       # posledné behy
PY -m tester.webapp.cli list "rrRatio>=4 pnl>0"    # rovnaká syntax ako hľadanie vo webapp
PY -m tester.webapp.cli show <run_id> [--json]
```

Kľúčové číslo je **break-even poplatok** (% na stranu): koľko smie burza brať, aby beh
vyšiel na nulu. Binance taker berie 0,05 %. PnL v % závisí od sizingu a peňaženky,
break-even nie.

## 4. Čomu neveriť

- **Jeden rok o stratégii nič nepovie.** Každý záver over na piatich referenčných oknách:
  `20211001-20221001`, `20221001-20231001`, `20231001-20241001`, `20240904-20250904`,
  `20250904-20260904`. Pozeraj **znamienko po rokoch**, nie súčet.
- **Beh s 0 obchodmi nie je výsledok.** Ak engine dal signály a nevznikol obchod, súhrn to
  napíše (`POZOR: …`) — typicky je malá peňaženka na profil s `legacyPineSizing`.
  Riešenie: `--wallet 1000000`, alebo profil s risk-based sizingom.
- **Profil musí sedieť s párom.** Prahy v bodoch (`abs`) platia pre podklad ako MNQ/NAS100;
  na ETH a forexe treba jednotku `atr`. BTC profil na ETH dá stovky nezmyselných obchodov —
  CLI aj webapp na to varujú, varovanie neignoruj.
- **Výsledky z rôznych enginov nie sú zameniteľné.** Signály sú rovnaké, fill model nie
  (Freqtrade vs. MultiCharts). Ladiť sa dá cez Freqtrade, ale záver pre MultiCharts over
  emulátorom — [docs/FREQTRADE.md §G](../docs/FREQTRADE.md).
- **Bez `--timeframe-detail 1m`** (CLI ho má zapnutý) sú fill ceny hrubé. `--no-detail` je
  len na rýchly odhad, nie do záverov.
- **Stratégiu nikdy nespúšťaj na 1m grafe** — limity `*MaxBars` sú v baroch, na 1m by to
  bola iná stratégia.

## 5. Interval okolo výsledku (Monte Carlo)

Backtest dá jedno číslo. Koľko z neho je edge a koľko vzorka, povie bootstrap nad
obchodmi hotového behu — bez ďalšieho backtestu, číta sa `runs/<id>/trades.json`:

```bash
PY -m tester.montecarlo                       # posledný beh v histórii
PY -m tester.montecarlo <run_id> --fee 0.05   # poplatok na stranu (default: ten z behu)
PY -m tester.montecarlo <run_id> --json
```

Výpis má tri bloky:

- **break-even poplatok** — nameraný, medián a 90 % interval, plus `P(edge > poplatok)`.
  Toto je hlavné číslo: pri 161 obchodoch za päť rokov vyšiel break-even 0,0995 % s
  intervalom 0,044–0,155 % a pravdepodobnosťou 93 %, že edge prevýši 0,05 % taker.
- **čistý PnL** pri zvolenej sadzbe — ten istý rozptyl v mene účtu.
- **max drawdown** z permutácie poradia: tie isté obchody v inom poradí. Nameraný
  drawdown je jedna cesta a spravidla nie tá najhoršia.

Čo z toho **nevyplýva**: bootstrap nemeria pretrénovanie. Obchody preladenej konfigurácie
naozaj ziskové boli, chyba bola vo výbere najlepšej z dvesto epoch — proti tomu chránia
len dáta, ktoré optimalizátor nevidel (§4, päť okien). Rovnako predpokladá nezávislé
obchody, takže zhlukovanie strát nemodeluje, a počíta bez zloženého úročenia.

Pod 30 obchodov výpis sám napíše, že interval je príliš široký na akýkoľvek záver.

To isté je vo webapp v detaile behu — rozbaľovacia sekcia **Monte Carlo** s histogramom
rozdelenia ([docs/WEBAPP.md](../docs/WEBAPP.md)).

## 6. Porovnávacie behy

```bash
# engine offline nad burzovými dátami alebo surovým Dukascopy CSV (bez Freqtrade aj bez MultiCharts)
PY -m tester.compare.scan_trades --exchange binance --profile golden_binance_btcusdt_3m
PY -m tester.compare.scan_trades --csv C:/dukas/NAS100_M1_10Y.csv \
    --profile docs/profily_archiv/ibs/nas100_dukas_3m.json --from 2025-01-01 --to 2025-01-31

# obchody zo skutočnej MultiCharts štúdie a ich spárovanie so simulátorom
PY -m tester.compare.mc_log_trades --from 2025-01-01 --to 2025-01-31
PY -m tester.compare.mc_compare --csv … --profile … --from … --to …

# parita s TradingView (golden testy) a s Pine zdrojom
PY -m pytest tester/tests/test_golden_tv_binance.py tester/tests/test_pine_parity.py
```

Ak padnú golden testy, kód alebo dáta nesedia s referenciou — **nahlás to, neopravuj
referenciu**.

## 7. Hyperopt (len engine Freqtrade)

```bash
./deploy/freqtrade/scripts/hyperopt.sh 20260601-20260904 200
```

Čo treba vedieť, inak dostaneš nezmysel: `--analyze-per-epoch` je povinné (bez neho majú
všetky epochy identický výsledok), počet obchodov musí byť strážený loss funkciou
(`IBSHyperOptLoss`), sizing musí byť rovnaký ako v porovnávanom behu, a výsledok **vždy**
over na inom okne než na tom, na ktorom si ladil. Priestor má 10 parametrov a stratégia
robí 150–200 obchodov za rok — pretrénovanie je reálne a už sa raz stalo
([docs/merania/HYPEROPT_btcusdt_2026-09-04.md](../docs/merania/HYPEROPT_btcusdt_2026-09-04.md)).

Poradie, v ktorom to dáva zmysel: hyperopt nájde parametre → out-of-sample okná rozhodnú,
či to prežije → `tester.montecarlo` (§5) dá k prežitému číslu interval. Monte Carlo
hyperopt **nenahrádza** ani neodhalí jeho pretrénovanie; sú to dve rôzne otázky.

Dukascopy symboly potrebujú pred hyperoptom sviečky pre Freqtrade:

```bash
PY -m tester.dukas_import C:/dukas/NAS100_M1_10Y.csv --symbol NAS100 --target freqtrade
```

Podrobne: [docs/FREQTRADE.md §C a §G](../docs/FREQTRADE.md).

## 8. FreqAI

Kód je súčasťou Freqtradu, chýbajú závislosti: `pip install "freqtrade[freqai]"`.
Stratégia je deterministický stavový automat a jeho parita s Pine je zmyslom celého portu,
takže model ju **nenahrádza** — dáva sa nad ňu ako filter (engine nájde setup, model
predpovie, či ho brať). Detaily a riziká: [docs/FREQTRADE.md §G](../docs/FREQTRADE.md).

## 9. Čo nerobiť

- Needituj `tradebot/core`, adaptéry ani referenčné profily kvôli tomu, aby beh „vyšiel".
- Nesťahuj dáta z burzy pri bežnom testovaní — páry a obdobia sú tie, čo sú v archíve
  ([docs/DATA.md](../docs/DATA.md)).
- Nezapisuj závery z jedného okna. Ak nemáš päť okien, napíš, že ich nemáš.
