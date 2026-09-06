"""Výstupy Freqtrade adaptéra — TP musí ísť cez ROI, nie cez exit-signál.

Exit-signál sa v backteste vyhodnocuje **aj plní otváracou cenou sviečky**, takže
knôt cez TP neurobí nič a keď sa napokon spustí, cena je už za TP. Na golden dátach
to výstupy posúvalo o jednu až tri sviečky neskôr a o 7-11 bodov vyššie než TradingView.
ROI sa naopak vyhodnocuje proti `high` sviečky a plní sa presnou cenou.

Testy nekontrolujú freqtrade samotný, len že adaptér používa to správne rozhranie
a odovzdáva doň TP z plánu.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tradebot.adapters.freqtrade.runner import SignalRow

strategy_mod = pytest.importorskip("tradebot.adapters.freqtrade.strategy")
IBSImbalanceStrategy = strategy_mod.IBSImbalanceStrategy


class _StubTrade:
    """Minimum z freqtrade `Trade`, ktoré `custom_roi` potrebuje."""

    def __init__(self, open_rate: float, is_short: bool = False) -> None:
        self.open_rate = open_rate
        self.is_short = is_short
        self.open_date_utc = datetime(2026, 8, 24, 14, 54, tzinfo=timezone.utc)
        self.asked_for: list[float] = []

    def calc_profit_ratio(self, rate: float) -> float:
        self.asked_for.append(rate)
        return (rate - self.open_rate) / self.open_rate


@pytest.fixture
def strategy(monkeypatch):
    from tradebot.core import SessionClock, load_profile

    s = IBSImbalanceStrategy.__new__(IBSImbalanceStrategy)
    s._runners = {}
    s.ibs_cfg, s.ibs_inst = load_profile("golden_binance_btcusdt_3m")
    s._clock = SessionClock(s.ibs_cfg)
    return s


def _with_signal(strategy, row: SignalRow, ts_ms: int) -> None:
    class _Runner:
        def signal_at_or_before(self, _ts):
            return row

    strategy._runners["BTC/USDT:USDT"] = _Runner()


def test_tp_ide_cez_roi_nie_cez_exit_signal(strategy):
    """`custom_exit` na TP by výstup posunul a nadhodnotil — nesmie sa vrátiť.

    `custom_exit` na stratégii existuje, ale výhradne pre `closeAtSessionEnd`; TP
    ide cez `custom_roi`, lebo exit-signál sa v backteste plní otváracou cenou.
    """
    from datetime import datetime, timezone

    assert IBSImbalanceStrategy.use_custom_roi is True

    strategy.ibs_cfg.closeAtSessionEnd = False
    trade = _StubTrade(open_rate=79419.5)
    _with_signal(strategy, SignalRow(stop_loss=79231.7, take_profit=79607.3), 0)
    # Cena hlboko nad TP — a aj tak sa nesmie vrátiť žiadny dôvod na výstup.
    assert strategy.custom_exit(
        "BTC/USDT:USDT", trade, datetime(2026, 8, 24, 14, 0, tzinfo=timezone.utc),
        99999.0, 5.0,
    ) is None


def test_minimal_roi_je_nedosiahnutelne():
    """Globálne ROI nesmie zavrieť obchod skôr než TP z plánu."""
    assert min(IBSImbalanceStrategy.minimal_roi.values()) >= 1.0


def test_custom_roi_odovzda_take_profit_z_planu(strategy):
    trade = _StubTrade(open_rate=79419.5)
    _with_signal(strategy, SignalRow(stop_loss=79231.7, take_profit=79607.3), 0)

    roi = strategy.custom_roi(
        "BTC/USDT:USDT", trade, trade.open_date_utc, 0, "ibs", "long"
    )

    assert trade.asked_for == [79607.3]
    assert roi == pytest.approx((79607.3 - 79419.5) / 79419.5)


def test_custom_roi_bez_signalu_nechá_rozhodnutie_na_freqtrade(strategy):
    trade = _StubTrade(open_rate=79419.5)
    roi = strategy.custom_roi(
        "BTC/USDT:USDT", trade, trade.open_date_utc, 0, "ibs", "long"
    )
    assert roi is None


def test_custom_roi_ignoruje_nan_take_profit(strategy):
    trade = _StubTrade(open_rate=79419.5)
    _with_signal(strategy, SignalRow(stop_loss=79231.7), 0)  # take_profit ostáva NaN
    assert strategy.custom_roi("BTC/USDT:USDT", trade, trade.open_date_utc, 0, "ibs", "long") is None


# --------------------------------------------------------------------------- #
# closeAtSessionEnd
# --------------------------------------------------------------------------- #


def test_koniec_poslednej_seansy_zavrie_poziciu(strategy):
    """Po poslednej seanse dna Pine zatvara natvrdo — port musi tiez."""
    from datetime import datetime, timezone

    trade = _StubTrade(open_rate=78110.3)
    # Okno seansy 2 konci 15:45 New York = 19:45 UTC. Pine zatvara az na zatvoreni
    # baru 19:45-19:48, co je otvaracia cena baru 19:48 - preto sa testuje 19:48.
    when = datetime(2026, 8, 26, 19, 48, tzinfo=timezone.utc)
    assert strategy.custom_exit("BTC/USDT:USDT", trade, when, 78424.1, 0.004) == "session_end"


def test_posledny_bar_v_okne_este_nezavira(strategy):
    """Bar 19:42-19:45 je este v okne — Pine na nom nezatvara."""
    from datetime import datetime, timezone

    trade = _StubTrade(open_rate=78110.3)
    when = datetime(2026, 8, 26, 19, 45, tzinfo=timezone.utc)
    assert strategy.custom_exit("BTC/USDT:USDT", trade, when, 78424.1, 0.004) is None


def test_v_obchodnom_okne_sa_nezavira(strategy):
    from datetime import datetime, timezone

    trade = _StubTrade(open_rate=78110.3)
    when = datetime(2026, 8, 26, 15, 30, tzinfo=timezone.utc)  # 11:30 New York
    assert strategy.custom_exit("BTC/USDT:USDT", trade, when, 78424.1, 0.004) is None


def test_medzi_seansami_sa_este_nezavira(strategy):
    """Medzi seansou 3 a 2 este den nekonci — pozicia ma prezit."""
    from datetime import datetime, timezone

    trade = _StubTrade(open_rate=78110.3)
    when = datetime(2026, 8, 26, 11, 0, tzinfo=timezone.utc)  # 07:00 NY, pred seansou 2
    assert strategy.custom_exit("BTC/USDT:USDT", trade, when, 78424.1, 0.004) is None


def test_vypnuty_prepinac_nezavira_nic(strategy):
    from datetime import datetime, timezone

    strategy.ibs_cfg.closeAtSessionEnd = False
    trade = _StubTrade(open_rate=78110.3)
    when = datetime(2026, 8, 26, 19, 48, tzinfo=timezone.utc)
    assert strategy.custom_exit("BTC/USDT:USDT", trade, when, 78424.1, 0.004) is None
