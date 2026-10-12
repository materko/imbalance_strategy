"""Symbol a TF nasadenia z profilu (`tradebot.live.symbols`)."""

from __future__ import annotations

import datetime as dt

from tradebot.core.types import INSTRUMENTS
from tradebot.live.symbols import deploy_defaults, front_month, platform_symbol, profile_tf


def test_front_month_a_roll():
    assert front_month("MNQ", dt.date(2026, 10, 12)) == "MNQ 12-26"
    # tretí piatok decembra 2026 je 18. 12., roll o 8 dní skôr (10. 12.)
    assert front_month("MNQ", dt.date(2026, 12, 9)) == "MNQ 12-26"
    assert front_month("MNQ", dt.date(2026, 12, 10)) == "MNQ 03-27"
    assert front_month("ES", dt.date(2027, 1, 5)) == "ES 03-27"


def test_platform_symbol():
    mnq, nas, eur, xau = (INSTRUMENTS[k] for k in ("mnq_databento", "nas100_dukascopy", "eurusd_dukascopy", "xau_dukascopy"))
    den = dt.date(2026, 10, 12)
    assert platform_symbol("ninjatrader", mnq, today=den) == ("MNQ 12-26", "front-month")
    # čo už na účte beží (rovnaký master), má prednosť — expiráciu niekto overil
    assert platform_symbol("ninjatrader", mnq, ["ES 12-26", "MNQ 03-27"], today=den) == ("MNQ 03-27", "účet")
    assert platform_symbol("mt5", nas) == ("NAS100", "profil")
    assert platform_symbol("mt5", eur) == ("EURUSD", "profil")
    assert platform_symbol("mt5", xau) == ("XAUUSD", "profil")
    sym, why = platform_symbol("mt5", mnq)
    assert sym is None and "MT5" in why
    sym, why = platform_symbol("ninjatrader", INSTRUMENTS["mgc_databento"])
    assert sym is None and "MGC" in why
    assert platform_symbol("mt5", None)[0] is None


def test_profile_tf_a_defaults():
    assert profile_tf("3m") == 3 and profile_tf("1h") == 60 and profile_tf("") is None and profile_tf("x") is None
    d = deploy_defaults("mt5", "nas100_dukascopy", "15m")
    assert d["symbol"] == "NAS100" and d["tf"] == 15 and d["symbol_error"] is None and d["tf_error"] is None
    d = deploy_defaults("mt5", None, None)
    assert d["symbol"] is None and d["symbol_error"] and d["tf"] is None and d["tf_error"]
