"""NOA 1.0 — Noise Area (Concretum): intraday momentum na Nasdaqu.

Vstup, keď cena na polhodinovej kontrole opustí pásmo šumu (priemerný pohyb od otvorenia v tej istej minúte
za 14 dní), výstup na kontrole pod VWAP / hranicou pásma alebo o 16:00 NY. Podľa Zarattini, Aziz, Barbon (2024).
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, NoaConfig, TradeDirection
from .engine import NoaEngine
from .hyperopt import NoaHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="noa",
    title="NOA 1.0 — Noise Area (Concretum)",
    config_cls=NoaConfig,
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
    engine_factory=NoaEngine,
    freqtrade_class="NoaStrategy",
    multicharts_class="NoaSignal",
    multicharts_template="Noa_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=NoaHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "NoaConfig", "NoaEngine", "TradeDirection", "CONFIG_DIR"]
