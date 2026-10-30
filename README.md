# TradeBot — stratégie z TradingView a videí do Pythonu a C#, backtest aj obchod naživo

Repozitár sú **dva celky**:

| | čo to je | kde |
|---|---|---|
| **TradeBot** | produkt, ktorý obchoduje: generické jadro, registry stratégií a tenké adaptéry — **Freqtrade** (krypto), **MultiCharts** (Python študia), **NinjaTrader 8** a **MetaTrader 5** (stratégie s jadrom v C#). Runtime je v Pythone aj v C# (`tradebot/core/`, `tradebot/core/ports/csharp/`) a C# verzia stratégie leží pri Python predlohe (`strategies/<key>/ports/csharp/`); jadro ani adaptéry nepoznajú stratégiu menom — všetko ide cez `StrategySpec`. | [`tradebot/`](tradebot) |
| **TradeBot Tester** | čím sa to skúša: dáta, backtesty do zdieľanej histórie, webová aplikácia, analytika a smernica testovania, porovnania platforiem, **hub** na počítanie na viac strojoch a **Live** karta s telemetriou bežiacich stratégií. | [`tester/`](tester) |

Závislosť ide jedným smerom — Tester importuje `tradebot`, produkt o Testeri nevie.

```
TradingView / video / zadanie ──► tradebot/strategies/<key>  (Python predloha)
                                         │  parita bar po bare
                                         ▼
                                  tradebot/strategies/<key>/ports/csharp  (C# 5, runtime v core/ports/csharp)
                                         │
              ┌──────────────────────────┼───────────────────────────┐
         NinjaTrader 8             MetaTrader 5 (EA)          Freqtrade / webapp (most)
              └──────── telemetria (spool) ──► hub ──► webapp, karta Live ───┘
```

---

## Stratégie

V registry je **69 stratégií** (vrátane C# prepisov a ich EOD kópií pre prop účty). Úplný
zoznam s popisom a počtom parametrov: [docs/STRATEGIE.md](docs/STRATEGIE.md); ako sa
pridáva ďalšia, kontrakt enginu a definícia hotového tamtiež. Webapp ich triedi podľa trhu
a typu (`STRATEGIA_TRH_TYP` v [`settings.js`](tester/webapp/static/js/settings.js)):

| trh | trendové | skalpovacie | rangeové | **LIVE** (C# jadro → NT8, MT5) |
|---|---|---|---|---|
| **NASDAQ** (MNQ, NAS100) | `structure` `orb` `range` `breakout` `trendlines` `vwapadx` `voltbreak` `onbiasorb` `vwapop` `vwaporb` `jss` `fibo` `mag7` `dailyopen` `noa` `tks` `nocpon` `nb` `ivb` | `ibs` `ibszones` `ibsentry` `ibsfvg` `scalp3ma` `fvgpolarity` `silverbullet` `m2mnq` | `gap` `sdzone` `divergence` `liquidity` `vwapdrift` `crt` `svp` `percoco` `fpc` `sweepfvg` `sweepengulf` `varev` | `ibsnet` `orbnet` `ibsentrynet` `vwaporbnet` `vwapadxnet` `noanet` `tksnet` (päť z nich aj ako `…eod`) |
| **ZLATO** (MGC) | `fibomgc` `spravy` | `ibsentrymgc` `fvgpolaritymgc` `scalp3mamgc` `m2mgc` | | `fibomgcnet` `spravynet` |
| **S&P 500** (ES) | `nyvaes` | `ibsentryes` `m2` | | `ibsentryesnet` `nyvaesnet` |
| **EURUSD** (6E) | | `m2eur` | `sdeur` `asiasweep` | `sdeurnet` |

Mimo trhov je len ukážková `demo_breakout`. Staré kľúče `ibsninja`, `orbninja` a
`trendline` sú aliasy (`tradebot.strategies.ALIASES`), história sa neprepisuje.

Každá stratégia sa píše **pre oba Python enginy** (Freqtrade aj emulátor MultiCharts) a má
vlastnú základnú analytiku s posudkom (`tradebot/strategies/<key>/docs/ANALYTIKA.md`,
[docs/ANALYTIKA.md](docs/ANALYTIKA.md)). Do **LIVE** ide stratégia prepisom do C# jadra,
ktorý musí s Python predlohou sedieť bar po bare ([docs/NINJATRADER.md](docs/NINJATRADER.md)).

---

## Rýchly štart

### Tester — webová aplikácia

**macOS jedným príkazom** (doinštaluje Homebrew, Python, TA-Lib, spýta sa kam klonovať
a aké meno testera použiť, postaví prostredie, zloží dáta, dá spúšťač na Plochu):

```bash
curl -fsSL https://raw.githubusercontent.com/materko/imbalance_strategy/main/install-macos.sh | bash
```

**Inak** potrebuješ Python 3.11+ (64-bit) a git; na macOS ešte `brew install ta-lib`. Prvé
spustenie postaví prostredie (~10 min) a otvorí prehliadač na http://127.0.0.1:8765.

```powershell
.\webapp.ps1        # Windows (alebo dvojklik na webapp.cmd)
```
```bash
./webapp.sh         # macOS / Linux
```

Prvá karta **Stratégie** je katalóg: každá stratégia s profilmi (prešli smernicou / repozitár /
vlastné) a najlepším behom z histórie. Vo webapp vyberieš stratégiu (podľa trhu a typu), nastavíš parametre, pár a obdobie,
spustíš backtest a vidíš výsledky, graf výnosnosti, graf páru so všetkým, čo engine
nakreslil, a zoznam obchodov. Ďalej sweep, hyperopt, analytika, diverzifikácia (aj živých behov),
karta **Hub** (výpočty na iných strojoch) a **Live** (bežiace stratégie v NT8 / MT5).
História behov sa zdieľa cez git a hľadá sa v nej podľa parametrov.
Podrobne: [docs/WEBAPP.md](docs/WEBAPP.md), z príkazového riadku [tester/AI_TESTING.md](tester/AI_TESTING.md).

### Vývojár — venv, testy, backtest z príkazového riadku

```powershell
.\deploy\freqtrade\scripts\setup.ps1             # .venv + freqtrade + tradebot (Windows)
.venv\Scripts\python.exe -m tester.webapp.cli run --strategy ibs --note "čo testujem"
```
```bash
./deploy/freqtrade/scripts/setup.sh              # macOS / Linux
.venv/bin/python -m pytest -q                    # ~4000 testov vrátane golden a C# parity
python -m tradebot.adapters.csharp.build --force # preklad C# jadra (csc.exe / Mono)
```

Pred pushom musí prejsť lint z [`.github/workflows/lint.yml`](.github/workflows/lint.yml):
`ruff check .`, ESLint skriptov webapp a preklad C# jadra.

### Dáta

Archív sviečok je po rokoch v [`data/archive/tester/`](data/archive/tester), len oficiálne
timeframy zdrojov; vyššie TF si Tester dopočíta z 1m sám
([`tester/timeframes.json`](tester/timeframes.json)):

| zdroj | čo | importér |
|---|---|---|
| Binance, Coinbase | BTC, ETH — futures perpetuály aj spot | sťahuje Freqtrade |
| Databento | CME futures `MNQ`, `MGC`, `ES`, `6E` — front-month podľa objemu | `./bento-import.sh` · `.\bento-import.ps1` |
| Dukascopy | CFD: indexy (NAS100, US500, DJ30, DAX, JP225), forex, zlato, komodity | `./dukas-import.sh` · `.\dukas-import.ps1` |
| IBKR | americké akcie Mag7, 1m RTH | `./ibkr-import.sh` · `.\ibkr-import.ps1` |

Sviečky a obchody stratégií naživo drží hub a uzavreté mesiace pushne do `data/live/`.
Celá cesta dát: [docs/DATA.md](docs/DATA.md), [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md).

---

## Rozcestník dokumentácie

| chcem… | kam |
|---|---|
| spúšťať backtesty, pozerať a zdieľať históriu | [docs/WEBAPP.md](docs/WEBAPP.md) |
| testovať z CLI (aj pre AI) | [tester/AI_TESTING.md](tester/AI_TESTING.md) |
| volať webapp zo skriptu alebo z AI | [docs/API.md](docs/API.md) |
| pridať ďalšiu stratégiu, zoznam stratégií | [docs/STRATEGIE.md](docs/STRATEGIE.md) |
| vedieť, kedy stratégia prešla (smernica testovania) | [docs/SMERNICA_TESTOVANIA.md](docs/SMERNICA_TESTOVANIA.md) |
| čo tá stratégia je, v čom je dobrá, kde má chyby | [docs/ANALYTIKA.md](docs/ANALYTIKA.md), [docs/TYPY_STRATEGII.md](docs/TYPY_STRATEGII.md) |
| hľadať parametre (sweep, hyperopt, FreqAI) | [docs/HYPEROPT.md](docs/HYPEROPT.md) |
| krypto: prostredie, backtest, Docker, server | [docs/FREQTRADE.md](docs/FREQTRADE.md) |
| MultiCharts: študia, QuoteManager, emulátor | [docs/MULTICHARTS.md](docs/MULTICHARTS.md) |
| NinjaTrader 8 a C# jadro | [docs/NINJATRADER.md](docs/NINJATRADER.md) |
| MetaTrader 5 nad tým istým C# jadrom | [docs/MT5.md](docs/MT5.md) |
| stratégia v NinjaTraderi, ordery v MT5 | [docs/ROUTING.md](docs/ROUTING.md) |
| telemetria bežiacich stratégií (karta Live) | [docs/LIVE.md](docs/LIVE.md) |
| zdieľať trhy medzi NT8 a MT5 (návrh) | [docs/FEED.md](docs/FEED.md) |
| počítať na viac strojoch (hub, agenti, pluginy) | [docs/HUB.md](docs/HUB.md), [deploy/agent/](deploy/agent/README.md) |
| dáta: archív, importy, nový symbol | [docs/DATA.md](docs/DATA.md) |
| prehľad architektúry a cesty dát | [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md), návrh portu [docs/ARCHITECTURE_port.md](docs/ARCHITECTURE_port.md) |
| kde čo beží (venv, Docker, Windows) | [docs/RUNNING.md](docs/RUNNING.md) |
| čo kam patrí v repozitári (adresáre) | [docs/DIRECTORIES.md](docs/DIRECTORIES.md) |
| čísla z meraní | [docs/merania/](docs/merania/README.md) |
| prieskum trhov a stratégií (zlato, S&P 500, videá) | [docs/prieskum/](docs/prieskum/README.md) |

Audity: [architektúra 2026-10-25](docs/audity/AUDIT_architektura_2026-10-25.md),
[smerovanie NT → MT5 2026-10-26](docs/audity/AUDIT_routing_2026-10-26.md),
[main 2026-09-17](docs/audity/AUDIT_main_2026-09-17.md), [Pine 2026-09-05](docs/audity/AUDIT_pine_2026-09-05.md).

---

## Mapa repozitára

Koncept, čo kam patrí, a podrobná mapa: [docs/DIRECTORIES.md](docs/DIRECTORIES.md). V skratke:

| | |
|---|---|
| [`tradebot/`](tradebot) | celý produkt — `core/` runtime (Python, prepis do C# v `ports/csharp/`), `strategies/<key>/` jeden sebestačný balík na stratégiu (Python kód, prepisy v `ports/<jazyk>/`, profily, dokumenty), `adapters/` (Freqtrade, MultiCharts, most do C#, NinjaTrader, MT5), `live/` telemetria a nasadenie |
| [`tester/`](tester) | Tester — webapp, hub a agenti, analytika, importy dát; jeho dáta v gite: `runs/`, `profiles/`, `archive/`, `sweeps/`, `analytics/` |
| [`deploy/`](deploy), [`docker/`](docker) | čo sa inštaluje do platforiem (Freqtrade, MultiCharts, NinjaTrader, MT5, agent) a kontajnery |
| [`data/`](data) | všetky dáta — v gite `archive/` (sviečky po rokoch zo zdrojov) a `live/` (uzavreté mesiace z naživo), ostatné sa dopočíta lokálne |
| [`docs/`](docs) | príručky naprieč stratégiami; datované v `merania/`, `audity/`, `prieskum/` |
| spúšťače v koreni | `webapp.*`, `dukas-import.*`, `bento-import.*`, `ibkr-import.*`, `install-macos.sh` |

---

## Kde sme (2026-10-30)

- **Výber stratégií** ide cez [smernicu testovania](docs/SMERNICA_TESTOVANIA.md) — séria
  skúšok, ktoré môžu stratégiu „zabiť" (päť okien, náhoda, Monte Carlo, náklady, …).
  Nastavenia, ktoré prešli, sú profily `PRESIEL_SMERNICAMI_*` a webapp ich označí
  „✓ smernica" (VWAP ORB, VWAP ADX, Volt Break, Volume Profile POC, Fibo MGC, NY VA ES, IBS EZ ES, …).
- **Naživo**: stratégie s C# jadrom bežia v NinjaTraderi 8 a MetaTraderi 5 a hlásia sa na
  kartu Live cez hub ([docs/LIVE.md](docs/LIVE.md)). Smerovanie „stratégia v NT, ordery v MT5"
  má hotovú fázu 1, exekútor a AddOn sú napísané, ale **na MT5 účte ešte neoverené**
  ([docs/ROUTING.md](docs/ROUTING.md), audit [2026-10-26](docs/audity/AUDIT_routing_2026-10-26.md)).
- **Správy**: stratégia **SPRÁVY 3.0** (zlato po červených správach USA, Python aj C# jadro) má pre každú správu vlastné
  pravidlo (8 pravidiel, prepínače, ktoré správy obchodovať) a kalendár 12 typov správ v čase New York
  (`tradebot/strategies/spravy/calendar.json`) s prevodom pre každý deň — štítky ukazujú čas SK aj NY.
  Smernica má od 29. 10. krok 9 Robustnosť (`python -m tester.robust`, len informácia).
- **IVB 1.0** (`ivb`): prepis cudzej Rust stratégie (Initial Volatility Breakout, prieraz IB 9:30–10:00 NY pri stlačenom IB
  a náraste objemu) 1 : 1 len na porovnanie; na MNQ 5m s defaultmi predlohy zisková v 5 z 5 okien (PF 1,13–1,60).
- **Parita**: Python port sedí s TradingView na cent (golden test,
  [GOLDEN_binance_2026-08-24](docs/audity/GOLDEN_binance_2026-08-24.md)); C# jadro sedí s Python
  predlohou bar po bare (`tester/tests/test_csharp_parity*.py`).
- **Pôvodná IBS na krypte** (BTC/ETH, september 2026): filtre NY seansy a tesného SL
  zdvihli break-even poplatok z 0,005 % na 0,141 %; s risk sizingom 1 % BTC +42,8 % a ETH
  +40,5 % za päť rokov. Celý príbeh po rokoch: [docs/merania/](docs/merania/README.md),
  posledný prepočet po audite [PREPOCET_po_audite_2026-10-26](docs/merania/PREPOCET_po_audite_2026-10-26.md).

---

## Pravidlá práce s repozitárom

- **Backtest vždy s `--timeframe-detail 1m` a `--cache none`** (skripty to robia samy);
  stratégiu nikdy nespúšťať priamo na 1m grafe (limity `*MaxBars` sú v baroch).
- **Parita pred optimalizáciou**: zmena jadra musí prejsť golden testom
  (`pytest tester/tests/test_golden_tv_binance.py`), zmena logiky stratégie s C# prepisom
  tú istú zmenu v C# a paritu bar po bare. Rozšírenia mimo Pine majú default zhodný s Pine
  (`PORT_ONLY_FIELDS`).
- **Dáta** sa sťahujú len v oficiálnych timeframoch a commitujú sa po rokoch; dopočítané
  do archívu nejdú ([docs/DATA.md](docs/DATA.md)).
- **Merania** sú datované dokumenty v `docs/merania/` s číslami po rokoch na piatich
  referenčných oknách — jeden rok o stratégii nič nepovie.
- **História behov** sa nemaže hromadne; staré behy sa odkladajú `cli archive` (vratné).
- **README sa aktualizuje pri každej významnej zmene** — nová stratégia, platforma,
  adaptér, služba, zdroj dát alebo dokument v rozcestníku; spolu s tým zmeniť aj
  dátum v „Kde sme".
- **Adresáre** podľa [docs/DIRECTORIES.md](docs/DIRECTORIES.md): koreň má pevný zoznam položiek a
  všetko o jednej stratégii je v jej balíku `tradebot/strategies/<key>/`.
  Python je hlavná implementácia, ostatné jazyky v `ports/<jazyk>/`; slovník runtime / stratégia / platforma / simulátor je tam tiež.
