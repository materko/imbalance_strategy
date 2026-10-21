"""IBS EZ MGC — IBS Entry Zone na zlate (MGC), prahy v násobkoch ATR.

Tá istá logika ako `ibsentry` (engine, config, kresby a vrstvy sa preberajú bez zmeny); vlastné sú profily
(`configs/`), v ktorých sú bodové a tickové prahy prepočítané na ATR — z IBS EZ 1 (prešiel smernicou na MNQ)
podľa mediánu ATR(14) 3m na MNQ 10/2021 – 9/2025 = 9,74 bodu. Stratégie na NQ sa nemenia.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.core.entry_filter import entry_filter_params

from ..ibsentry import SPEC as BASE_SPEC
from .config import CONFIG_DIR, IBSEntryMgcConfig

_GF = "🧭 Filter trendu a volatility (len MGC)"

SPEC = replace(
    BASE_SPEC,
    key="ibsentrymgc",
    title="IBS EZ MGC",
    config_cls=IBSEntryMgcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mgc_databento_3m",
    logic_of="ibsentry",  # celá logika (IBS + vrstva FVG) je balík predlohy
    param_meta={**BASE_SPEC.param_meta, **entry_filter_params(_GF)},
    param_groups=(*BASE_SPEC.param_groups, _GF),
    freqtrade_class="IBSEntryMgcStrategy",
    multicharts_class="IBSEntryMgcSignal",
    multicharts_template="IBSEntryMgc_Signal.py",
)

__all__ = ["SPEC", "IBSEntryMgcConfig", "CONFIG_DIR"]
