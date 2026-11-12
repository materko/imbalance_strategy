"""IBS EZ MYM — IBS Entry Zone na Micro E-mini Dow futures (MYM), prahy v násobkoch ATR.

Tá istá logika ako `ibsentry` (engine, config, kresby a vrstvy sa preberajú bez zmeny); vlastné sú profily
(`configs/`), v ktorých sú bodové a tickové prahy v násobkoch ATR (východisko je profil IBS EZ ES); ladí sa na MYM
odznova (používateľ 12. 11. 2026). Stratégie na NQ a ES sa nemenia.
"""

from __future__ import annotations

from dataclasses import replace

from tradebot.core.entry_filter import entry_filter_params

from ..ibsentry import SPEC as BASE_SPEC
from .config import CONFIG_DIR, IBSEntryMymConfig

_GF = "🧭 Filter trendu a volatility (len MYM)"

SPEC = replace(
    BASE_SPEC,
    key="ibsentrymym",
    title="IBS EZ MYM",
    config_cls=IBSEntryMymConfig,
    profile_dir=CONFIG_DIR,
    default_profile="mym_databento_3m",
    logic_of="ibsentry",  # celá logika (IBS + vrstva FVG) je balík predlohy
    param_meta={**BASE_SPEC.param_meta, **entry_filter_params(_GF)},
    param_groups=(*BASE_SPEC.param_groups, _GF),
    freqtrade_class="IBSEntryMymStrategy",
    multicharts_class="IBSEntryMymSignal",
    multicharts_template="IBSEntryMym_Signal.py",
)

__all__ = ["SPEC", "IBSEntryMymConfig", "CONFIG_DIR"]
