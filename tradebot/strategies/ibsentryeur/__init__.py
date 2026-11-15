"""IBS EZ 6E — tá istá logika ako `ibsentry`, vlastné profily na 6E (CME Euro FX futures).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (EURUSD) a smernica ju ladila na 6E odznova (používateľ 15. 11. 2026: EUR sa vracia späť, živé okná London 2:00–5:00 a NY 8:00–11:00 NY, čisté dáta 6E od 2016 — ladenie 2016–2021/9, päť referenčných okien ako čisté overenie);
engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..ibsentrymym import SPEC as BASE_SPEC
from .config import CONFIG_DIR, IBSEntryEurConfig

SPEC = replace(
    BASE_SPEC,
    key="ibsentryeur",
    title="IBS EZ 6E",
    config_cls=IBSEntryEurConfig,
    profile_dir=CONFIG_DIR,
    default_profile="6e_databento_3m",
    logic_of="ibsentry",  # engine a čítanie polí má predloha
    param_meta=BASE_SPEC.param_meta,
    param_groups=BASE_SPEC.param_groups,
    freqtrade_class="IBSEntryEurStrategy",
    multicharts_class="IBSEntryEurSignal",
    multicharts_template="IBSEntryEur_Signal.py",
)

__all__ = ["SPEC", "IBSEntryEurConfig", "CONFIG_DIR"]
