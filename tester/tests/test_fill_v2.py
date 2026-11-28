"""Fill v2 (SMERNICA V2 §3, zadanie U4): každý riadok oboch tabuliek vzorcov, okraj presne na hranici, gap cez úroveň,
CFD okná v čase New York a parita Python = C# na v2 pre každú C# stratégiu."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from tradebot.core.fill import REJECT, FillModel, model_for

NY = ZoneInfo("America/New_York")
T = 0.25
FUT = FillModel(kind="futures", instrument="mnq", tick=T, cost_ticks=1.75, slip_ticks=2, pass_ticks=1)
S = 2.0
CFD = FillModel(kind="cfd", instrument="us100", spread=S, off_mult=2, pass_sell=0.25, slip_sl=1.0, slip_mkt=0.5,
                open_mult=2, open_slip=2.0, news_mult=4, news_slip=4.0)


def ny(y, m, d, hh, mm) -> int:
    return int(datetime(y, m, d, hh, mm, tzinfo=NY).timestamp() * 1000)


RTH = ny(2026, 11, 25, 11, 0)        # streda 11:00 NY - hlavná seansa


# -- futures ----------------------------------------------------------------- #

def test_futures_limit_vstup_a_tp_az_pri_prechode_o_tick():
    P = 100.0
    # long limit: L ≤ P − pass·T, cena P (bez zlepšenia aj pri gape)
    assert FUT.entry(RTH, 101, 102, P - T, is_long=True, kind="limit", price=P, first_minute=False) == (P, False)
    assert FUT.entry(RTH, 101, 102, P - T + 1e-9, is_long=True, kind="limit", price=P, first_minute=False) is None
    assert FUT.entry(RTH, 98, 99, 97, is_long=True, kind="limit", price=P, first_minute=True) == (P, False)   # gap pod
    # short limit: H ≥ P + pass·T
    assert FUT.entry(RTH, 99, P + T, 98, is_long=False, kind="limit", price=P, first_minute=False) == (P, False)
    assert FUT.entry(RTH, 99, P + T - 1e-9, 98, is_long=False, kind="limit", price=P, first_minute=False) is None
    # TP: long H ≥ TP + pass·T, short L ≤ TP − pass·T; cena presne TP
    assert FUT.exit(RTH, 100, 110 + T, 99, is_long=True, stop=90, tp=110) == (110, False, False)
    assert FUT.exit(RTH, 100, 110 + T - 1e-9, 99, is_long=True, stop=90, tp=110) is None
    assert FUT.exit(RTH, 100, 101, 90 - T, is_long=False, stop=110, tp=90) == (90, False, False)


def test_futures_sl_a_stop_vstup_so_sklzom_a_gap():
    sl = 2 * T
    assert FUT.exit(RTH, 100, 101, 95, is_long=True, stop=95, tp=110) == (95 - sl, True, False)       # presne na SL
    assert FUT.exit(RTH, 93, 94, 92, is_long=True, stop=95, tp=110) == (93 - sl, True, False)         # gap pod SL
    assert FUT.exit(RTH, 100, 105, 99, is_long=False, stop=105, tp=90) == (105 + sl, True, False)
    assert FUT.exit(RTH, 107, 108, 106, is_long=False, stop=105, tp=90) == (107 + sl, True, False)
    # SL aj TP v jednej minúte -> SL, nerozhodnuteľné
    assert FUT.exit(RTH, 100, 111, 94, is_long=True, stop=95, tp=110) == (95 - sl, True, True)
    # stop vstup: long H ≥ E -> max(E, O) + slip; gap nad E sa plní na otvorení
    assert FUT.entry(RTH, 99, 100, 98, is_long=True, kind="stop", price=100, first_minute=False) == (100 + sl, False)
    assert FUT.entry(RTH, 101, 102, 100.5, is_long=True, kind="stop", price=100, first_minute=True) == (101 + sl, True)
    assert FUT.entry(RTH, 101, 102, 100.5, is_long=False, kind="stop", price=100, first_minute=False) is None
    assert FUT.entry(RTH, 99, 99.5, 98, is_long=False, kind="stop", price=100, first_minute=True) == (99 - sl, True)


def test_futures_market_a_naklad():
    sl = 2 * T
    assert FUT.entry(RTH, 100, 101, 99, is_long=True, kind="market", price=0, first_minute=True) == (100 + sl, True)
    assert FUT.entry(RTH, 100, 101, 99, is_long=False, kind="market", price=0, first_minute=True) == (100 - sl, True)
    assert FUT.entry(RTH, 100, 101, 99, is_long=True, kind="market", price=0, first_minute=False) is None
    assert FUT.market(RTH, 100, buy=False) == 100 - sl
    # náklad strany: cost_ticks · T · hodnota bodu = podiel nominálu × cena × qty × pv
    f = FUT.side_fee(20000.0, maker=False)
    assert f * 20000.0 * 2.0 == pytest.approx(1.75 * T * 2.0)
    btc = model_for("btcusdt_binance")
    assert (btc.side_fee(60000, maker=True), btc.side_fee(60000, maker=False)) == (0.0002, 0.0005)
    assert btc.market(RTH, 60000, buy=True) == pytest.approx(60000 * 1.0002)


# -- CFD --------------------------------------------------------------------- #

def test_cfd_okna_new_york_a_spravy():
    assert CFD.window(RTH) == (S, 0.0)
    assert CFD.window(ny(2026, 11, 25, 9, 35)) == (2 * S, 2.0)                   # otvorenie 9:30–9:40
    assert CFD.window(ny(2026, 11, 25, 9, 40)) == (S, 0.0)
    assert CFD.window(ny(2026, 11, 25, 16, 0)) == (2 * S, 0.0)                   # po seanse
    assert CFD.window(ny(2026, 11, 28, 11, 0)) == (2 * S, 0.0)                   # sobota
    news = FillModel(**{**CFD.to_dict(), "news": [ny(2026, 11, 25, 10, 0)]}) if False else \
        FillModel.from_dict({**CFD.to_dict(), "news": [ny(2026, 11, 25, 10, 0)]})
    assert news.window(ny(2026, 11, 25, 10, 5)) == (4 * S, 4.0)                  # ±5 min
    assert news.window(ny(2026, 11, 25, 10, 6)) == (S, 0.0)
    # letný čas: 9:35 NY v júli je 13:35 UTC, v novembri 14:35 UTC
    assert CFD.window(int(datetime(2026, 7, 15, 13, 35, tzinfo=timezone.utc).timestamp() * 1000))[0] == 2 * S
    assert CFD.window(int(datetime(2026, 11, 25, 14, 35, tzinfo=timezone.utc).timestamp() * 1000))[0] == 2 * S


def test_cfd_vzorce_kazdy_riadok():
    P = 100.0
    # long limit (nákup): L ≤ P − S, cena P
    assert CFD.entry(RTH, 105, 106, P - S, is_long=True, kind="limit", price=P, first_minute=False) == (P, False)
    assert CFD.entry(RTH, 105, 106, P - S + 1e-9, is_long=True, kind="limit", price=P, first_minute=False) is None
    # short limit (predaj): H ≥ P + pass_sell
    assert CFD.entry(RTH, 99, P + 0.25, 98, is_long=False, kind="limit", price=P, first_minute=False) == (P, False)
    # limit za trhom pri odoslaní sa neplní: long P ≥ O + S, short P ≤ O
    assert CFD.entry(RTH, 98, 99, 97, is_long=True, kind="limit", price=P, first_minute=True) == REJECT
    assert CFD.entry(RTH, 101, 102, 100.5, is_long=False, kind="limit", price=P, first_minute=True) == REJECT
    # long TP (predaj): H ≥ TP + pass_sell; short TP (nákup): L ≤ TP − S
    assert CFD.exit(RTH, 100, 110.25, 99, is_long=True, stop=90, tp=110) == (110, False, False)
    assert CFD.exit(RTH, 100, 101, 90 - S, is_long=False, stop=110, tp=90) == (90, False, False)
    assert CFD.exit(RTH, 100, 101, 90 - S + 1e-9, is_long=False, stop=110, tp=90) is None
    # long SL (predaj): L ≤ SL -> min(SL, O) − slip_sl; short SL (nákup): H + S ≥ SL -> max(SL, O + S) + slip_sl
    assert CFD.exit(RTH, 100, 101, 95, is_long=True, stop=95, tp=110) == (94.0, True, False)
    assert CFD.exit(RTH, 100, 103, 99, is_long=False, stop=105, tp=90) == (106.0, True, False)        # 103 + 2 ≥ 105
    assert CFD.exit(RTH, 100, 102.9, 99, is_long=False, stop=105, tp=90) is None
    assert CFD.exit(RTH, 106, 107, 105.5, is_long=False, stop=105, tp=90) == (109.0, True, False)     # gap: O + S
    # stop vstup: long (nákup) H + S ≥ E -> max(E, O + S) + slip_sl; short (predaj) L ≤ E -> min(E, O) − slip_sl
    assert CFD.entry(RTH, 97, 98, 96, is_long=True, kind="stop", price=100, first_minute=False) == (101.0, False)
    assert CFD.entry(RTH, 99, 99.5, 98, is_long=True, kind="stop", price=100, first_minute=True) == (102.0, True)
    assert CFD.entry(RTH, 101, 102, 99, is_long=False, kind="stop", price=100, first_minute=False) == (99.0, False)
    # market: nákup O + S + slip_mkt, predaj O − slip_mkt; v otvorení NY S×2 a sklz +2
    assert CFD.entry(RTH, 100, 101, 99, is_long=True, kind="market", price=0, first_minute=True) == (102.5, True)
    assert CFD.market(RTH, 100, buy=False) == 99.5
    assert CFD.market(ny(2026, 11, 25, 9, 31), 100, buy=True) == 100 + 4 + 0.5 + 2


def test_swap_noci_a_tabulka():
    a = int(datetime(2026, 11, 25, 15, tzinfo=timezone.utc).timestamp() * 1000)
    assert CFD.nights(a, a + 3_600_000) == 0
    assert CFD.nights(a, a + 86_400_000) == 1
    assert CFD.nights(a, a + 3 * 86_400_000) == 3
    for key in ("mnq_databento", "mym_databento", "es_databento", "mgc_databento", "6e_databento", "btcusdt_binance",
                "nas100_dukascopy", "us500_dukascopy", "xau_dukascopy"):
        assert model_for(key, news=()) is not None
    assert model_for("mnq_databento", "v1") is None
    with pytest.raises(ValueError):
        model_for("aapl_ibkr")
    m = model_for("nas100_dukascopy", news=(1, 2))
    assert FillModel.from_dict(m.to_dict()) == m


# -- emulátor a parita Python = C# na v2 ------------------------------------ #

def test_emulator_v2_je_horsi_nez_v1_a_v1_sa_nemeni():
    """Ten istý beh s fill v2 má náklad aj sklz (PF nie vyšší), v1 ostáva bit po bite (golden testy na v1)."""
    from tradebot.core.candles import timeframe_minutes
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies import get_spec
    from tester import engines
    from tester.compare.csharp_backtest import run_python

    inst = INSTRUMENTS["mnq_databento"]
    if not engines.one_minute_file(inst).exists():
        pytest.skip("chýbajú 1m dáta MNQ")
    tf = timeframe_minutes(get_spec("noanet").default_timeframe)
    a, b = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000), int(datetime(2025, 3, 1, tzinfo=timezone.utc).timestamp() * 1000)
    v1 = run_python("noanet", None, inst, tf, a, b, 0.0, {})
    v1b = run_python("noanet", None, inst, tf, a, b, 0.0, {})
    v2 = run_python("noanet", None, inst, tf, a, b, 0.0, {}, fill=model_for("mnq_databento"))
    assert v1 == v1b and v1 and v2
    assert all("fee_open" not in t for t in v1) and all(t["fee_open"] > 0 for t in v2)

    def pnl(rows):
        return sum((t["exit"] - t["entry"]) * t["dir"] * t["qty"] for t in rows)

    assert pnl(v2) <= pnl(v1) + 1e-9


from tester.tests.test_csharp_backtest import CASES  # noqa: E402


@pytest.mark.parametrize("strategy,profile,inst_key,day_from,day_to,sets", CASES,
                         ids=[f"{c[0]}-{c[2]}-v2" + ("-set" if c[5] else "") for c in CASES])
def test_v2_native_matches_python_emulator(strategy, profile, inst_key, day_from, day_to, sets):
    from tradebot.adapters.csharp import bridge
    from tradebot.core.candles import timeframe_minutes
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies import get_spec
    from tester import engines
    from tester.compare.csharp_backtest import compare_trades, run_csharp, run_python

    try:
        bridge._load_clr()
    except bridge.BridgeError as exc:
        pytest.skip(f"pythonnet/CLR nie je k dispozícii: {exc}")
    inst = INSTRUMENTS[inst_key]
    if not engines.one_minute_file(inst).exists():
        pytest.skip(f"chýbajú 1m dáta {engines.one_minute_file(inst)}")
    fill = model_for(inst_key)
    tf = timeframe_minutes(get_spec(strategy).default_timeframe)
    ms = lambda d: int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)  # noqa: E731
    args = (strategy, profile, inst, tf, ms(day_from), ms(day_to), 0.0005, sets)
    py = run_python(*args, fill=fill)
    cs = run_csharp(*args, fill=fill)
    assert compare_trades(py, cs["trades"]) == []
    for p, c in zip(py, cs["trades"]):
        assert p.get("fee_open") == pytest.approx(c.get("fee_open"), rel=1e-12)
        assert p.get("fee_close") == pytest.approx(c.get("fee_close"), rel=1e-12)
