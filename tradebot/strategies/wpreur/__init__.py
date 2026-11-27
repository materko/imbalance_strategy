"""WILLIAMS %R LONG 1.0 (6E) — tá istá logika ako `wpr`, vlastné profily na 6E (CME Euro FX futures).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu (EURUSD) a smernica ju ladila na 6E odznova (používateľ 15. 11. 2026: EUR sa vracia späť, živé okná London 2:00–5:00 a NY 8:00–11:00 NY, čisté dáta 6E od 2016 — ladenie 2016–2021/9, päť referenčných okien ako čisté overenie);
engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..wpr import SPEC as BASE_SPEC
from .config import CONFIG_DIR, WprEurConfig

SPEC = replace(
    BASE_SPEC,
    key="wpreur",
    title="WILLIAMS %R LONG 1.0 (6E)",
    config_cls=WprEurConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_6E",
    logic_of="wpr",  # engine a čítanie polí má predloha
    freqtrade_class="WprEurStrategy",
    multicharts_class="WprEurSignal",
    multicharts_template="WprEur_Signal.py",
)

__all__ = ["SPEC", "WprEurConfig", "CONFIG_DIR"]
