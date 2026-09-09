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
- **Freqtrade beží na fiktívnej burze Tester** (`tester/ftexchange.py`), ktorá pozná naše
  páry aj všetky timeframy. Nie je to skutočný trh: poplatok zadávaš cez `--fee`, funding je
  nula a likvidácia sa nepočíta. Na porovnanie s reálnou burzou sú configy `config.binance*.json`.
- **Bez `--timeframe-detail 1m`** (CLI ho má zapnutý) sú fill ceny hrubé. `--no-detail` je
  len na rýchly odhad, nie do záverov.
- **Stratégiu nikdy nespúšťaj na 1m grafe** — limity `*MaxBars` sú v baroch, na 1m by to
  bola iná stratégia.

## 5. Monte Carlo: interval okolo výsledku a veľkosť účtu

Backtest dá jedno číslo. Koľko z neho je edge a koľko vzorka — a aký veľký musí byť účet,
aby ho séria strát neodpísala — povie bootstrap nad obchodmi hotového behu. Bez ďalšieho
backtestu, číta sa `runs/<id>/trades.json`:

```bash
PY -m tester.montecarlo                          # posledný beh v histórii
PY -m tester.montecarlo <run_id> --fee 0.05      # poplatok na stranu (default: ten z behu)
PY -m tester.montecarlo <run_id> --risk 250      # 250 USD rizika na obchod
PY -m tester.montecarlo <run_id> --account 25000 --limits 10,20,30
PY -m tester.montecarlo <run_id> --risk-pct 1    # riziko ako % z equity (zložené úročenie)
PY -m tester.montecarlo <run_id> --block 1       # nezávislé obchody namiesto blokov
```

Losuje sa **po blokoch** desiatich po sebe idúcich obchodov (`--block`). Straty totiž
nechodia rovnomerne: jeden režim trhu vyrobí päť SL za sebou a losovanie obchod po obchode
by takú sériu skoro nikdy nevyrobilo — a práve tá zabíja účet. Na tom istom behu je
rozdiel vidno: 95. percentil drawdownu 28,9 % pri `--block 1` a 32,9 % pri blokoch.

**Edge:** break-even poplatok — nameraný, medián, 90 % interval a `P(edge > poplatok)`.
Pri 161 obchodoch za päť rokov: 0,0995 %, interval 0,037–0,163 %, edge nad taker 0,05 %
s pravdepodobnosťou 90 %.

**Účet:** max drawdown (% z vrcholu), ako často účet klesne pod hranice −10/−20/−30/−50 %
počiatočného zostatku, pravdepodobnosť ruiny, najdlhšia séria strát, najdlhšie čakanie na
nové maximum a konečný zostatok. Veľkosť pozície sa preškáluje z rizika behu
(`maxLossDollar`) na `--risk`, takže rovnaká stratégia sa dá prepočítať na iný účet.
Na záver vypíše, **koľko sa smie riskovať**, aby 95 % ciest zostalo nad hranicou −20 %
(na spomínanom behu 71 USDT na obchod pri účte 10 000 a riziku 100).

Profil s `legacyPineSizing` (pevný počet kontraktov) sa preškálovať nedá — vtedy sa
počíta veľkosť z behu tak, ako je, a odporúčanie k riziku sa nevypíše.

Čo z toho **nevyplýva**:

- **Pretrénovanie to nemeria.** Obchody preladenej konfigurácie naozaj ziskové boli, chyba
  bola vo výbere najlepšej z dvesto epoch — proti tomu chránia len dáta, ktoré optimalizátor
  nevidel (§4, päť okien).
- **Počíta len uzavreté obchody.** Pozícia, ktorá išla hlboko proti a nakoniec vyšla na TP,
  je neviditeľná — pre margin a likvidáciu pri páke je pritom rozhodujúca.
- Nie sú tu denné limity strát (séria nemá dátumy), zmena režimu trhu ani korelácia medzi
  viacerými účtami na tej istej stratégii.

Pod 30 obchodov výpis sám napíše, že interval je príliš široký na akýkoľvek záver.

To isté je vo webapp v detaile behu — rozbaľovacia sekcia **Monte Carlo** s oboma
histogramami a poľami na účet a riziko ([docs/WEBAPP.md](../docs/WEBAPP.md)).

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

## 7. Sweep: hľadanie parametra bez písania kódu

Mriežka behov cez hodnoty jedného či viacerých parametrov. Každý bod je **obyčajný
backtest** — uloží sa do histórie, dá sa otvoriť, porovnať aj prehnať Monte Carlom.

```bash
PY -m tester.webapp.cli sweep --param rrRatio=2:6:1    --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json    --timerange 20250904-20260904 --goal break_even --min-trades 20

PY -m tester.webapp.cli sweep --param rrRatio=3,5 --param slLookback=10,20,30    --goal winrate --max-dd 15 --timerange 20250904-20260904
```

Hodnoty sú buď rozsah `od:do:krok` (vrátane hornej hranice), alebo zoznam `a,b,c`
(aj `true,false`, `Long only,Both`, `0.25@pct`). `--param` sa dá opakovať — vznikne
kartézsky súčin. Strop `--max-runs` (default 300) je poistka proti preklepu v kroku, nie
výkonový limit; skutočná cena je čas — každý bod je celý backtest, rok je asi 30 sekúnd,
takže 40 bodov na piatich referenčných oknách je hodina a pol.

**Kritérium hovorí, čo je lepšie** — bez neho sa „optimálne" nedá určiť:

| `--goal` | vyberá | kedy |
|---|---|---|
| `break_even` | najvyšší break-even poplatok | prednastavené; nezávisí od sizingu ani peňaženky |
| `profit` | najvyšší zisk v % | keď ide o výnos a drawdown stráži limit |
| `winrate` | najvyšší podiel ziskových | keď má byť séria strát krátka |
| `drawdown` | najnižší max drawdown | keď je hranicou účet, nie výnos |

K tomu mantinely `--max-dd` (strop na drawdown v %) a `--min-trades`. Body, ktoré ich
porušia, sa nezahodia — ukážu sa pod čiarou s dôvodom, nech je vidno, že optimum tam je,
len je mimo dohodnutých hraníc.

Výsledok je tabuľka zoradená podľa kritéria a id najlepšieho behu. **Než z neho spravíš
profil, prežeň ho ostatnými referenčnými oknami** (§4) — mriežka vie len to okno, na ktorom
bežala.

Parametre, ktoré rozbijú paritu s TradingView (sizing, STATE timeouty), sú označené
a sweep na ne upozorní; zakázané nie sú — ak ich chceš ladiť vedome, ladia sa.

## 8. Hyperopt (len engine Freqtrade)

```bash
./deploy/freqtrade/scripts/hyperopt.sh 20260601-20260904 200
```

Čo treba vedieť, inak dostaneš nezmysel: `--analyze-per-epoch` je povinné (bez neho majú
všetky epochy identický výsledok), počet obchodov musí byť strážený loss funkciou
(`IBSHyperOptLoss`), sizing musí byť rovnaký ako v porovnávanom behu, a výsledok **vždy**
over na inom okne než na tom, na ktorom si ladil. Priestor má 10 parametrov a stratégia
robí 150–200 obchodov za rok — pretrénovanie je reálne a už sa raz stalo
([docs/merania/HYPEROPT_btcusdt_2026-09-04.md](../docs/merania/HYPEROPT_btcusdt_2026-09-04.md)).

Na jeden–dva parametre je čitateľnejší **sweep** (§7): prejde mriežku obyčajných backtestov, ktoré ostanú v histórii. Hyperopt sa oplatí až pri troch a viac.

Poradie, v ktorom to dáva zmysel: hyperopt nájde parametre → out-of-sample okná rozhodnú,
či to prežije → `tester.montecarlo` (§5) dá k prežitému číslu interval. Monte Carlo
hyperopt **nenahrádza** ani neodhalí jeho pretrénovanie; sú to dve rôzne otázky.

Dukascopy symboly potrebujú pred hyperoptom sviečky pre Freqtrade:

```bash
PY -m tester.dukas_import C:/dukas/NAS100_M1_10Y.csv --symbol NAS100 --target freqtrade
```

Podrobne: [docs/FREQTRADE.md §C a §G](../docs/FREQTRADE.md).

## 9. FreqAI

Kód je súčasťou Freqtradu, chýbajú závislosti: `pip install "freqtrade[freqai]"`.
Stratégia je deterministický stavový automat a jeho parita s Pine je zmyslom celého portu,
takže model ju **nenahrádza** — dáva sa nad ňu ako filter (engine nájde setup, model
predpovie, či ho brať). Detaily a riziká: [docs/FREQTRADE.md §G](../docs/FREQTRADE.md).

## 10. Čo nerobiť

- Needituj `tradebot/core`, adaptéry ani referenčné profily kvôli tomu, aby beh „vyšiel".
- Nesťahuj dáta z burzy pri bežnom testovaní — páry a obdobia sú tie, čo sú v archíve
  ([docs/DATA.md](../docs/DATA.md)).
- Nezapisuj závery z jedného okna. Ak nemáš päť okien, napíš, že ich nemáš.
