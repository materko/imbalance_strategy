"""SD ZÓNY EURUSD 1.0 — supply / demand zóny z noci na 1 h, limitka na hrane pri prvom návrate v Londýne.

Zadanie používateľa 26. 10. 2026 (Euro FX futures 6E, „najpodstatnejšia je kvalita zón"). Python predloha pre C# jadro
`sdeurnet` (`tradebot/strategies/sdeur/ports/csharp`); zhodu bar po bare stráži `tester/tests/test_csharp_parity_6e.py`.
"""

from __future__ import annotations

from . import drawing as _drawing  # noqa: F401  — registrácia druhov kresieb musí byť prvá
from ..base import StrategySpec
from .config import CONFIG_DIR, SdEurConfig
from .engine import SdEurEngine
from .hyperopt import SdEurHyperopt
from .meta import FEATURES, INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, PARAM_NOTES, REMOVED_INPUTS
from .params import GROUPS, PARAMS

SPEC = StrategySpec(
    key="sdeur",
    title="SD ZÓNY EURUSD 1.0",
    config_cls=SdEurConfig,
    profile_dir=CONFIG_DIR,
    default_profile="eurusd_6e_5m",
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
    engine_factory=SdEurEngine,
    freqtrade_class="SdEurStrategy",
    multicharts_class="SdEurSignal",
    multicharts_template="SdEur_Signal.py",
    fixed_size_field="fixedQty",
    risk_field="riskDollar",
    hyperopt_cls=SdEurHyperopt,
    informative_tfs=None,
    htf_feeder=None,
)

__all__ = ["SPEC", "SdEurConfig", "SdEurEngine", "CONFIG_DIR"]
