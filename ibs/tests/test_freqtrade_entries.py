"""Vstupy Freqtrade adaptéra — priradenie signálu k obchodu a životnosť limitky.

Dve veci, ktoré Freqtrade rieši inak než Pine a adaptér ich musí zosúladiť:

* **Ktorý signál patrí obchodu.** Freqtrade otvára na sviečke PO signáli; keď engine
  vygeneruje signál aj na nej (iná zóna), „posledný signál pred otvorením" vráti ten
  cudzí. Preto sa čas baru signálu nesie v `enter_tag`.
* **Kedy zrušiť nevyplnenú limitku.** Engine ju ruší po `state5MaxBars` baroch alebo
  na konci obchodného okna, ale tie CANCEL intenty Freqtrade nevidí — musí to
  povedať `check_entry_timeout`.

Testy nekontrolujú freqtrade samotný, len že adaptér používa správne rozhranie.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ibs.adapters.freqtrade.runner import SignalRow

strategy_mod = pytest.importorskip("ibs.adapters.freqtrade.strategy")
IBSImbalanceStrategy = strategy_mod.IBSImbalanceStrategy
ENTRY_TAG_PREFIX = strategy_mod.ENTRY_TAG_PREFIX

PAIR = "BTC/USDT:USDT"
MIN3 = timedelta(minutes=3)
#: 2026-08-26 14:00 UTC = 10:00 New York, začiatok obchodného okna seansy 2.
T_SIGNAL = datetime(2026, 8, 26, 14, 0, tzinfo=timezone.utc)


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class _StubTrade:
    def __init__(self, open_date: datetime, enter_tag: str | None) -> None:
        self.open_date_utc = open_date
        self.enter_tag = enter_tag
        self.is_short = False


class _Runner:
    """Dva signály na susedných baroch — presne situácia, v ktorej čas nestačí."""

    def __init__(self, first: SignalRow, second: SignalRow) -> None:
        self.rows = {_ms(T_SIGNAL): first, _ms(T_SIGNAL + MIN3): second}
        self.signal_ts = sorted(self.rows)

    def signal_at(self, ts_ms):
        return self.rows.get(ts_ms)

    def signal_at_or_before(self, ts_ms):
        import bisect

        idx = bisect.bisect_right(self.signal_ts, ts_ms) - 1
        return None if idx < 0 else self.rows[self.signal_ts[idx]]


@pytest.fixture
def strategy():
    from ibs.core import SessionClock, load_profile

    s = IBSImbalanceStrategy.__new__(IBSImbalanceStrategy)
    s._runners = {}
    s._extremes = {}
    s.ibs_cfg, s.ibs_inst = load_profile("golden_binance_btcusdt_3m")
    s._clock = SessionClock(s.ibs_cfg)
    return s


@pytest.fixture
def two_signals(strategy):
    first = SignalRow(enter_long=1, entry=100.0, stop_loss=95.0, take_profit=105.0, qty=1.0,
                      in_trade_window=True)
    second = SignalRow(enter_long=1, entry=200.0, stop_loss=190.0, take_profit=210.0, qty=2.0,
                       in_trade_window=False)
    strategy._runners[PAIR] = _Runner(first, second)
    return first, second


# --------------------------------------------------------------------------- #
# enter_tag -> signál
# --------------------------------------------------------------------------- #


def test_tag_sa_parsuje_len_s_prefixom():
    assert IBSImbalanceStrategy._tag_ts(f"{ENTRY_TAG_PREFIX}1756684800000") == 1756684800000
    assert IBSImbalanceStrategy._tag_ts("ibs") is None
    assert IBSImbalanceStrategy._tag_ts(f"{ENTRY_TAG_PREFIX}abc") is None
    assert IBSImbalanceStrategy._tag_ts(None) is None


def test_obchod_dostane_signal_zo_svojho_tagu_nie_z_novsieho(strategy, two_signals):
    """Obchod zo signálu T sa otvára na T+1, kde je už ďalší signál. Tag rozhodne."""
    first, second = two_signals
    trade = _StubTrade(T_SIGNAL + MIN3, f"{ENTRY_TAG_PREFIX}{_ms(T_SIGNAL)}")

    assert strategy._trade_signal(PAIR, trade) is first
    assert strategy._levels(PAIR, trade) == (95.0, 105.0)


def test_bez_tagu_sa_pouzije_zaloha_podla_casu(strategy, two_signals):
    """Force entry nemá náš tag — ostáva pôvodné správanie."""
    first, second = two_signals
    trade = _StubTrade(T_SIGNAL + MIN3, None)
    assert strategy._trade_signal(PAIR, trade) is second


def test_custom_entry_price_a_stake_idu_podla_tagu(strategy, two_signals):
    first, _ = two_signals
    tag = f"{ENTRY_TAG_PREFIX}{_ms(T_SIGNAL)}"
    when = T_SIGNAL + MIN3

    assert strategy.custom_entry_price(PAIR, None, when, 150.0, tag, "long") == 100.0
    stake = strategy.custom_stake_amount(
        PAIR, when, 100.0, 999.0, None, 1e9, 1.0, tag, "long"
    )
    assert stake == pytest.approx(first.qty * 100.0)
    assert strategy.confirm_trade_entry(PAIR, "limit", 1.0, 100.0, "GTC", when, tag, "long") is True
    # Druhý signál je mimo okna — s jeho tagom by vstup neprešiel.
    tag2 = f"{ENTRY_TAG_PREFIX}{_ms(T_SIGNAL + MIN3)}"
    assert strategy.confirm_trade_entry(PAIR, "limit", 1.0, 200.0, "GTC", when, tag2, "long") is False


# --------------------------------------------------------------------------- #
# check_entry_timeout
# --------------------------------------------------------------------------- #


def test_limitka_zije_state5MaxBars_sviecok(strategy):
    """Order z baru T sa vo Freqtrade otvorí na T+1 a posledná sviečka, na ktorej sa
    smie vyplniť, je T+state5MaxBars. Zrušiť sa má o sviečku neskôr."""
    n = strategy.ibs_cfg.state5MaxBars
    opened = T_SIGNAL + MIN3
    trade = _StubTrade(opened, None)

    assert strategy.check_entry_timeout(PAIR, trade, None, opened) is False
    assert strategy.check_entry_timeout(PAIR, trade, None, opened + (n - 1) * MIN3) is False
    assert strategy.check_entry_timeout(PAIR, trade, None, opened + n * MIN3) is True


def test_limitka_sa_zrusi_na_konci_obchodneho_okna(strategy):
    """Okno seansy 2 končí 15:45 NY = 19:45 UTC. Engine to vyhodnotí na zatvorení
    baru 19:45–19:48, teda Freqtrade ruší na sviečke 19:48."""
    opened = datetime(2026, 8, 26, 19, 30, tzinfo=timezone.utc)
    trade = _StubTrade(opened, None)

    assert strategy.check_entry_timeout(
        PAIR, trade, None, datetime(2026, 8, 26, 19, 45, tzinfo=timezone.utc)
    ) is False
    assert strategy.check_entry_timeout(
        PAIR, trade, None, datetime(2026, 8, 26, 19, 48, tzinfo=timezone.utc)
    ) is True


def test_config_timeout_nesmie_byt_kratsi_nez_engine():
    """Freqtrade ruší podľa `unfilledtimeout` nezávisle od callbacku — config
    musí dať enginu aspoň toľko času, koľko má Pine."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "platforms" / "freqtrade"
    from ibs.core import load_profile

    cfg, _ = load_profile("golden_binance_btcusdt_3m")
    need = cfg.state5MaxBars * 3
    for name in ("config.binance.json", "config.coinbase.json"):
        raw = json.loads((root / name).read_text(encoding="utf-8"))
        timeout = raw["unfilledtimeout"]
        assert timeout.get("unit", "minutes") == "minutes", name
        assert timeout["entry"] >= need, f"{name}: unfilledtimeout.entry < {need} min"


# --------------------------------------------------------------------------- #
# confirm_trade_exit uprace trailing
# --------------------------------------------------------------------------- #


def test_vystup_uprace_extrem_trailingu(strategy):
    trade = _StubTrade(T_SIGNAL + MIN3, None)
    strategy._extremes[(PAIR, trade.open_date_utc)] = 123.0
    strategy._extremes[("ETH/USDT:USDT", trade.open_date_utc)] = 1.0

    ok = strategy.confirm_trade_exit(
        PAIR, trade, "market", 1.0, 100.0, "GTC", "roi", T_SIGNAL + 5 * MIN3
    )

    assert ok is True
    assert (PAIR, trade.open_date_utc) not in strategy._extremes
    assert ("ETH/USDT:USDT", trade.open_date_utc) in strategy._extremes
