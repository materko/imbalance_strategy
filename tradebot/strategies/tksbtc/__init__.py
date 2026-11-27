"""TKS 1.0 (BTC) — tá istá logika ako `tks` (NQ Kompas), vlastné profily na BTCUSDT.P (Binance futures).

Variant existuje, aby stratégia bola vo webapp aj v priečinku svojho trhu a smernica ju ladila na BTC odznova
(používateľ 17. 11. 2026: TKS naživo na MNQ sedí s backtestom, logiku preniesť na ES, MGC, MYM, BTC a euro. Kompas je pomerový (únik zo šumu v násobkoch bežného pohybu, poloha v nočnom range, tlak, čas nad VWAP); konštanta tlaku `PRESS_SCALE` vychádza na všetkých piatich trhoch ako na MNQ (90. percentil |tlak| 1m 2019-06 – 2025-09: MNQ 0,136, ES 0,133, MGC 0,129, MYM 0,131, BTC 0,131, 6E 0,128), preto sa kód nemení); engine, parametre aj kresby sú predlohy.
"""

from __future__ import annotations

from dataclasses import replace

from ..tks import SPEC as BASE_SPEC
from .config import CONFIG_DIR, TksBtcConfig

SPEC = replace(
    BASE_SPEC,
    key="tksbtc",
    title="TKS 1.0 (BTC)",
    config_cls=TksBtcConfig,
    profile_dir=CONFIG_DIR,
    default_profile="ZAKLAD_BTC",
    logic_of="tks",  # engine a čítanie polí má predloha
    freqtrade_class="TksBtcStrategy",
    multicharts_class="TksBtcSignal",
    multicharts_template="TksBtc_Signal.py",
)

__all__ = ["SPEC", "TksBtcConfig", "CONFIG_DIR"]
