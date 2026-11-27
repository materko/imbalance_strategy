"""SPRÁVY (EUR/USD) — tá istá logika ako `spravy`, vlastné pravidlá na 6E / EUR/USD.

Výskum 21. 11. 2026 (Mac mini, iCloud SPRAVY-EUR): 6E sa po správach USA (JOLTS, PPI, CPI, ISM služby, PCE, zápisnica FOMC)
vracia proti prvému pohybu, po FOMC a tlačovke ECB pokračuje v trende. Kalendár je spoločný `spravy/calendar.json`
(aj ECB a ECB_TK s časom New York pre každý deň); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..spravy import SPEC as BASE_SPEC
from .config import CONFIG_DIR, SpravyEurConfig

SPEC = replace(
    BASE_SPEC,
    key="spravyeur",
    title="SPRÁVY (EUR/USD)",
    config_cls=SpravyEurConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_6E",
    logic_of="spravy",  # engine a čítanie polí má predloha
    freqtrade_class="SpravyEurStrategy",
    multicharts_class="SpravyEurSignal",
    multicharts_template="SpravyEur_Signal.py",
)

__all__ = ["SPEC", "SpravyEurConfig", "CONFIG_DIR"]
