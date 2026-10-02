"""CRT + TBS — Candle Range Theory s Turtle Body Soup.

Sviečka vyššieho TF (4h) je range; ďalšia jednu jeho stranu vyberie (telom = TBS) a cena sa vráti
dovnútra; po vstupnom modeli na grafe (model 1, CISD, MSS + FVG) obchod proti výberu so stopom
za extrémom výberu a cieľom v strede alebo na opačnom konci rangu. Stratégia nemá Pine predlohu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, CrtConfig, EntryModel, SweepKind, TpMode, TradeDirection
from .engine import CrtEngine
from .hyperopt import CrtHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="crt",
    title="CRT + TBS 1.0",
    config_cls=CrtConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mnq_databento_5m",
    pine_path=None,
    pine_input_count=0,
    removed_inputs=REMOVED_INPUTS,
    intentional_default_diffs=INTENTIONAL_DEFAULT_DIFFS,
    param_meta=PARAMS,
    param_groups=GROUPS,
    features=tuple(FEATURES),
    param_notes=PARAM_NOTES,
    layers=LAYERS,
    sl_kind="sl_box",
    tp_kind="tp_box",
    kind_titles=KIND_TITLES,
    default_timeframe="5m",
    engine_factory=CrtEngine,
    freqtrade_class="CrtStrategy",
    multicharts_class="CrtSignal",
    multicharts_template="Crt_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=CrtHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "CrtConfig", "CrtEngine", "SweepKind", "EntryModel", "TpMode", "TradeDirection",
           "CONFIG_DIR"]
