# Stratégie v TradeBote — ako pridať ďalšiu

TradeBot je rámec pre viac stratégií: každá má vlastný Pine zdroj, vlastný config
(parametre), vlastný engine, vlastné profily a vlastné vrstvy v grafe webapp. Freqtrade,
MultiCharts aj webapp pracujú len cez registry `tradebot.strategies.STRATEGIES`, takže
pridanie stratégie je pridanie jedného balíka a jedného riadku do registry.

Dnes sú v registry dve:

| kľúč | názov | Pine zdroj | na čo |
|---|---|---|---|
| `ibs` | IBS Imbalance Breakout | `pine/imbalance_strategy_FULL.pine` (115 vstupov) | ostrá stratégia, golden testy proti TradingView |
| `demo_breakout` | Demo Donchian Breakout | `pine/demo_breakout.pine` (8 vstupov) | ukážka, ktorá overuje rámec end-to-end; nie je to obchodné odporúčanie |

## Čo je kde

```
tradebot/
  core/                 generické jadro: Bar, InstrumentSpec, SizeSpec, BarHistory, SessionClock,
                        StrategyConfig (báza configu + load_profile), Engine protokol + EngineOutput,
                        OrderIntent/StateEvent/MarketContext, TradePlan, DrawCommand + DrawKind registr
  strategies/
    __init__.py         STRATEGIES = {"ibs": …, "demo_breakout": …}, get_spec(), spec_for_config()
    base.py             StrategySpec (popis stratégie), ChartLayer (vrstva grafu)
    <key>/              jedna stratégia (viď checklist nižšie)
  adapters/freqtrade/   TradebotStrategyBase (generická IStrategy), EngineRunner, export_chart
  adapters/multicharts/ TradebotSignal (generická študia), MCRunner, MCDrawSink
  configs/<key>/        profily = JSON s odchýlkami od Pine defaultov + _strategy, _instrument, _title
  webapp/               tester: výber stratégie, formulár z Pine metadát, história, graf s vrstvami
pine/<key>.pine         zdroj pravdy pre parametre stratégie
platforms/freqtrade/user_data/strategies/<FreqtradeTrieda>.py   shim (Freqtrade resolver)
platforms/multicharts/<Nazov>_Signal.py                          šablóna študie
docs/profily_archiv/<key>/                                       archivované profily
```

## Checklist: nová stratégia `moja`

1. **Pine zdroj** `pine/moja.pine` — všetky vstupy ako `x = input.<typ>(default, "Titulok", minval=…,
   maxval=…, options=[…], tooltip="…", group="…")`. Z tohto sa parsuje formulár webapp
   (titulky, tooltipy, skupiny, rozsahy) a test parity stráži, že config sedí s Pine.
2. **Balík** `tradebot/strategies/moja/`:
   - `drawing.py` — druhy kresieb: `MOJ_DRUH = DrawKind.register("moj_druh", "MOJ_DRUH")`.
     Generické druhy (`tp_box`, `sl_box`, `entry`, `exit`, `session`) registruje jadro.
   - `config.py` — `@dataclass class MojaConfig(StrategyConfig)` s poľami pomenovanými presne ako
     Pine identifikátory a s tabuľkami ako `ClassVar`: `SIZE_FIELDS` (polia so `SizeSpec` a ich
     Pine jednotka), `ENUM_FIELDS`, `CONSTRAINTS` (Pine `minval`/`maxval`), `PORT_ONLY_FIELDS`
     (polia, ktoré Pine nemá, napr. `leverage`). Vlastné pravidlá do `_problems()`.
     `CONFIG_DIR = CONFIGS_ROOT / "moja"`.
   - `engine.py` — trieda s `__init__(cfg, inst, chart_tf_minutes)`, atribútom `required_history`,
     `on_bar(bar, htf, ctx) -> EngineOutput` (ordery `OrderIntent` s `TradePlan`, kresby
     `DrawBox/DrawLine/DrawLabel/DrawBg`, `close_session=True` = zavri pozíciu za trh) a
     `final_drawings(bar)`. Engine je čistý: bez I/O, všetko v `self`.
   - `meta.py` — `REMOVED_INPUTS`, `INTENTIONAL_DEFAULT_DIFFS`, `PORT_ONLY_META` (titulok a
     tooltip polí mimo Pine), `FEATURES` (prepínač → podnastavenia, ktoré formulár skryje),
     `PARAM_NOTES`, `LAYERS` (`ChartLayer(id, titulok, druhy, farba, hollow_kinds=…)`),
     `KIND_TITLES`.
   - `freqtrade.py` — `class MojaStrategy(TradebotStrategyBase)`: `STRATEGY_KEY = "moja"`,
     `ENTRY_TAG_PREFIX`, `timeframe`; háky podľa potreby (`_after_profile`, `_feed_informative`,
     `_apply_hyperopt_params`, `_trailing_stop`, `custom_exit`).
   - `multicharts.py` — `class MojaSignal(TradebotSignal)`: `STRATEGY_KEY = "moja"`.
   - `__init__.py` — najprv `from . import drawing`, potom `SPEC = StrategySpec(key="moja", …)`
     so všetkým z hora (`pine_path`, `pine_input_count`, `engine_factory`, `freqtrade_class`,
     `multicharts_class`, `multicharts_template`, `default_timeframe`, `informative_tfs`,
     `htf_feeder`, `layers`, `kind_titles`, `features`, `profile_dir`, `default_profile`).
3. **Registry**: v `tradebot/strategies/__init__.py` pridaj import a riadok do `STRATEGIES`.
4. **Profil** `tradebot/configs/moja/<default_profile>.json` s `_title`, `_strategy: "moja"`,
   `_instrument` (kľúč z `tradebot.core.types.INSTRUMENTS`) a len odchýlkami od Pine defaultov.
5. **Shim** `platforms/freqtrade/user_data/strategies/MojaStrategy.py` — prázdna podtrieda
   (Freqtrade resolver berie len triedu, ktorej `__module__` == názov súboru).
6. **Šablóna** `platforms/multicharts/Moja_Signal.py` — import študie + prázdna podtrieda.
7. **Testy**: `pytest tradebot/tests/test_registry.py tradebot/tests/test_pine_parity.py` — registry
   test skontroluje profil, Pine súbor, shim, šablónu, druhy vo vrstvách a FEATURES; parity test
   porovná config s Pine (názvy, defaulty, rozsahy). Pridaj test enginu na syntetických baroch
   (vzor: `tradebot/tests/test_demo_engine.py`).

## Informatívny timeframe

Stratégia, ktorá potrebuje vyšší TF (IBS: detekčný TF zón), deklaruje `informative_tfs(cfg)`
a `htf_feeder(cfg, chart_tf)`. Feeder má `load(bars, extra)` pre Freqtrade (predpočítané z
informative dataframe), `feed(bar)` pre MultiCharts (Data2 po jednom) a `window_for(ts)`,
ktoré vráti to, čo engine dostane ako `htf`. Vzor: `tradebot/strategies/ibs/htf.py`.
Stratégia bez informatívneho TF dá `None` a engine dostáva `htf=None`.

## Ako to používajú adaptéry a webapp

- **Freqtrade**: `TRADEBOT_PROFILE` (názov z `configs/<key>/` alebo cesta k JSON), trieda
  zo shimu, `--timeframe` z webapp/CLI; stĺpce `tb_*`, `enter_tag` s prefixom stratégie.
- **MultiCharts**: šablóna študie, profil cez `PROFILE` v šablóne alebo `TRADEBOT_PROFILE`;
  Data2 len ak stratégia má informatívny TF; ordery `tb_sl`, `tb_tp`, `tb_session_end`.
- **Webapp**: select Stratégia prekreslí formulár a profily, beh nesie `settings.strategy`,
  história má stĺpec Stratégia (hľadanie `strat=moja`), graf berie vrstvy zo `SPEC.layers`.
- **CLI**: `python -m tradebot.webapp.cli run --strategy moja --profile <nazov|cesta> …`,
  `params --strategy moja`.
