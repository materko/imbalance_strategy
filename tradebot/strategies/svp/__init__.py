"""Volume Profile POC — seansový volume profile (SVP) New York seansy a obchod na jeho POC.

Cena pod POC: na dotyk POC short; nad POC: long (POC ako odpor / podpora). Po prerazení POC zavretím
retest a vstup v smere prerazenia. Vstup limitkou na POC alebo cez IBS imbalance / pin bar.
Zadanie používateľa 2. 10. 2026; stratégia nemá Pine predlohu.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, EntryModel, PocSource, SlMode, SvpConfig, TpMode, TradeDirection, TradeMode
from .engine import SvpEngine
from .hyperopt import SvpHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="svp",
    title="Volume Profile POC 1.0",
    config_cls=SvpConfig,
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
    engine_factory=SvpEngine,
    freqtrade_class="SvpStrategy",
    multicharts_class="SvpSignal",
    multicharts_template="Svp_Signal.py",
    fixed_size_field="legacyPineSizing",
    risk_field="riskDollar",
    hyperopt_cls=SvpHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "SvpConfig", "SvpEngine", "PocSource", "TradeMode", "EntryModel", "SlMode",
           "TpMode", "TradeDirection", "CONFIG_DIR"]
