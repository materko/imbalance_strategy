"""IBSZones — IBS Imbalance Breakout so synchronizovanou detekciou zón.

Logika, parametre aj profily sú zhodné s `tradebot/strategies/ibs`. Jediný rozdiel je
v tom, KEDY sa detekcia zóny spustí: `ZoneSyncHTFFeeder` (`htf.py`) ju púšťa podľa
najnovšieho baru v okne detekčného TF, nie podľa toho, či bar grafu už patrí do novej
periódy. Vďaka tomu vyjdú zóny rovnako bez ohľadu na TF grafu — v `ibs` sa na 1m, 3m
a 4m grafe vyhodnocoval iný pattern.

`ibs` tú zmenu nedostal zámerne: má golden testy bar po bare proti TradingView a Pine
predloha sa správa po starom. Podrobné odôvodnenie je v `htf.py`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá

from ..base import StrategySpec
from ..ibs.engine import IBSEngine
from .config import CONFIG_DIR, IBSZonesConfig
from .htf import ZoneSyncHTFFeeder
from .hyperopt import IBSZonesHyperopt
from .meta import FEATURES, INERT_INPUTS, KIND_TITLES, LAYERS, PARAM_NOTES
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="ibszones",
    title="IBS plus zmena zón",
    config_cls=IBSZonesConfig,
    profile_dir=CONFIG_DIR,
    default_profile="golden_binance_btcusdt_3m",
    inert_inputs=INERT_INPUTS,
    param_meta=PARAMS,
    param_groups=GROUPS,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    kind_titles=KIND_TITLES,
    default_timeframe="3m",
    engine_factory=IBSEngine,
    logic_of="ibs",  # engine, state machine aj zóny sú z IBS; vlastný je len feeder
    freqtrade_class="IBSZonesStrategy",
    multicharts_class="IBSZonesSignal",
    multicharts_template="IBSZones_Signal.py",
    # "D" ako "1d" — Freqtrade pozná denný TF len pod týmto menom; ostatné ostávajú v minútach
    informative_tfs=lambda cfg: ["1d" if str(cfg.zoneDetectionTF) == "D" else f"{int(cfg.zoneDetectionTF)}m"],
    htf_feeder=ZoneSyncHTFFeeder,
    sl_kind="sl_box",
    tp_kind="tp_box",
    risk_field="maxLossDollar",
    fixed_size_field="legacyPineSizing",
    hyperopt_cls=IBSZonesHyperopt,
)

__all__ = ["SPEC", "IBSZonesConfig", "IBSZonesHyperopt", "ZoneSyncHTFFeeder", "CONFIG_DIR"]
