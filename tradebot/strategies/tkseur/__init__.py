"""TKS 1.0 (6E) — tá istá logika ako `tks` (NQ Kompas), vlastné profily na Euro FX (6E).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju ladila na 6E odznova
(používateľ 17. 11. 2026: TKS naživo na MNQ sedí s backtestom, logiku preniesť na ES, MGC, MYM, BTC a euro. Kompas je pomerový (únik zo šumu v násobkoch bežného pohybu, poloha v nočnom range, tlak, čas nad VWAP); konštanta tlaku `PRESS_SCALE` vychádza na všetkých piatich trhoch ako na MNQ (90. percentil |tlak| 1m 2019-06 – 2025-09: MNQ 0,136, ES 0,133, MGC 0,129, MYM 0,131, BTC 0,131, 6E 0,128), preto sa kód nemení); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..tks import SPEC as BASE_SPEC
from .config import CONFIG_DIR, TksEurConfig

SPEC = replace(
    BASE_SPEC,
    key="tkseur",
    title="TKS 1.0 (6E)",
    config_cls=TksEurConfig,
    profile_dir=CONFIG_DIR,
    default_profile="6e_databento_3m",
    logic_of="tks",  # engine a čítanie polí má predloha
    freqtrade_class="TksEurStrategy",
    multicharts_class="TksEurSignal",
    multicharts_template="TksEur_Signal.py",
)

__all__ = ["SPEC", "TksEurConfig", "CONFIG_DIR"]
